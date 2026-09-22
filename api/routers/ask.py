import time
import json
import uuid
import asyncio
import hashlib
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, desc

from api.core.config import settings
from api.core.llm_router import llm_router, ABSTENTION_MESSAGE, ABSTENTION_MESSAGE_HINDI, get_abstention_message
from api.core.cache import cache
from api.core.rate_limiter import rate_limiter
from api.core.auth import get_optional_current_user
from api.core.metrics import (
    RAG_QUERY_TOTAL,
    RAG_QUERY_DURATION,
    RAG_RETRIEVAL_DURATION,
    RAG_CACHE_HITS,
    RAG_CACHE_MISSES,
    RAG_RATE_LIMIT_EXCEEDED,
)
from api.rag.retriever import retriever
from db.session import async_session_factory
from db.models import QueryAuditLog, User, ChatSession, ChatMessage
from api.core.security_logger import record_security_incident_bg, detect_prompt_injection
from api.core.content_guard import inspect_content_safety

logger = logging.getLogger(__name__)


router = APIRouter(tags=["Student Q&A"])

class Citation(BaseModel):
    """Reference: Appendix B (Table 20)"""
    document_id: str
    title: str
    page_number: Optional[int] = None
    section: Optional[str] = None
    snippet: str

class AskRequest(BaseModel):
    """Reference: Appendix B (Table 19) with query alias and role context"""
    question: Optional[str] = Field(None, max_length=1000, description="Question string, max 1000 chars")
    query: Optional[str] = Field(None, max_length=1000, description="Query string alias for question")
    department: Optional[str] = None
    course: Optional[str] = None
    role: Optional[str] = "general"
    session_id: Optional[str] = None
    top_k: Optional[int] = None
    temperature: Optional[float] = None
    stream: bool = False

class AskResponse(BaseModel):
    """Reference: Appendix B (Table 20) with session tracking"""
    answer: str
    citations: List[Citation]
    served_by: str  # local | hosted | fallback | cache
    confidence: Optional[float] = 1.0
    crag_decision: Optional[str] = "CORRECT"
    session_id: Optional[str] = None

_BACKGROUND_TASKS: set = set()

def _spawn_bg_task(coro):
    """Spawns an asyncio background task with a strong reference to prevent GC."""
    task = asyncio.create_task(coro)
    _BACKGROUND_TASKS.add(task)
    task.add_done_callback(_BACKGROUND_TASKS.discard)
    return task

async def record_audit(
    question: str,
    served_by: str,
    latency_ms: float,
    tokens: int = 0,
    crag_decision: Optional[str] = None,
    confidence: Optional[float] = None
):
    """Privacy-preserving audit logging (Table 17 & Phase 19)."""
    try:
        q_hash = hashlib.sha256(question.strip().encode("utf-8")).hexdigest()
        async with async_session_factory() as session:
            entry = QueryAuditLog(
                question_hash=q_hash,
                served_by=served_by,
                latency_ms=latency_ms,
                tokens_used=tokens,
                crag_decision=crag_decision,
                confidence=confidence,
            )
            session.add(entry)
            await session.commit()
    except Exception as e:
        logger.warning(f"Audit log recording error: {e}")

async def record_chat_interaction_bg(
    session_id: str,
    user_identifier: str,
    role: str,
    department: Optional[str],
    course: Optional[str],
    user_query: str,
    assistant_answer: str,
    citations: List[Dict[str, Any]],
    confidence: Optional[float] = 1.0,
    crag_decision: Optional[str] = "CORRECT",
    served_by: str = "local",
    latency_ms: float = 0.0,
    tokens: int = 0
):
    """
    Asynchronously persists user questions and assistant answers to ChatSession and ChatMessage.
    Runs in the background with zero latency impact on live inference or streaming tokens.
    """
    try:
        is_low_conf = (confidence is not None and confidence < 0.75) or (crag_decision == "INCORRECT")
        citations_str = json.dumps(citations, ensure_ascii=False) if citations else None
        title_snippet = user_query.strip().split("\n")[0][:80]
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        async with async_session_factory() as session:
            stmt = select(ChatSession).where(ChatSession.session_id == session_id)
            chat_sess = (await session.execute(stmt)).scalar_one_or_none()

            if not chat_sess:
                chat_sess = ChatSession(
                    session_id=session_id,
                    title=title_snippet,
                    user_identifier=user_identifier,
                    role=role or "student",
                    department=department,
                    course=course,
                    message_count=2,
                    feedback_score=0,
                    has_negative_feedback=False,
                    has_low_confidence=is_low_conf,
                    created_at=now,
                    updated_at=now,
                )
                session.add(chat_sess)
            else:
                chat_sess.message_count += 2
                chat_sess.updated_at = now
                if is_low_conf:
                    chat_sess.has_low_confidence = True

            # Add User Message
            user_msg = ChatMessage(
                session_id=session_id,
                sender="user",
                content=user_query,
                created_at=now,
            )
            session.add(user_msg)

            # Add Assistant Message
            asst_msg = ChatMessage(
                session_id=session_id,
                sender="assistant",
                content=assistant_answer,
                citations_json=citations_str,
                confidence=confidence,
                crag_decision=crag_decision,
                served_by=served_by,
                latency_ms=latency_ms,
                tokens_used=tokens,
                created_at=now,
            )
            session.add(asst_msg)

            await session.commit()
    except Exception as e:
        logger.warning(f"Error persisting chat interaction for session {session_id}: {e}")

@router.post("/ask", responses={200: {"model": AskResponse}})
@router.post("/api/v1/ask", responses={200: {"model": AskResponse}})
async def ask_question(
    req: AskRequest,
    request: Request,
    user: Optional[User] = Depends(get_optional_current_user)
):
    """
    University RAG question-answering endpoint.
    Protected by rate limiter, Redis semantic cache, RBAC multi-tenancy, and Prometheus metrics.
    Supports both JSON response and real-time SSE streaming (req.stream=True).
    """
    start_time = time.time()
    session_id = req.session_id or str(uuid.uuid4())
    req.session_id = session_id
    role_val = user.role if user else (req.role or "student")
    q_text = (req.question or req.query or "").strip()
    if not q_text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Either 'question' or 'query' must be provided."
        )
    req.question = q_text
    dept_label = req.department or (user.department if user else "all")

    # 1. Rate limiting check (Phase 7 & 19)
    client_id = user.external_id if user else (request.client.host if request.client else "127.0.0.1")
    rate_limit_max = settings.RATE_LIMIT_PER_STUDENT_PER_MINUTE if user else settings.RATE_LIMIT_PER_IP_PER_MINUTE
    try:
        rate_limiter.check_rate_limit(client_id, limit=rate_limit_max)
    except HTTPException:
        RAG_RATE_LIMIT_EXCEEDED.inc()
        record_security_incident_bg(
            event_type="RATE_LIMIT_EXCEEDED",
            severity="MEDIUM",
            client_ip=request.client.host if request.client else "127.0.0.1",
            user_identifier=client_id,
            endpoint=request.url.path,
            detail=f"Rate limit exceeded ({rate_limit_max} req/min). Client: {client_id}",
            action_taken="RATE_LIMITED"
        )
        raise

    # 1.5. Indian Context Content Moderation & AI Safety Governor
    safety_result = inspect_content_safety(req.question, context="query")
    if not safety_result.is_safe:
        record_security_incident_bg(
            event_type=safety_result.category,
            severity=safety_result.severity,
            client_ip=request.client.host if request.client else "127.0.0.1",
            user_identifier=client_id,
            endpoint=request.url.path,
            detail=f"Safety violation [{safety_result.category}] snippet '{safety_result.matched_snippet}': {req.question[:150]}",
            action_taken="BLOCKED"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "content_policy_violation",
                    "category": safety_result.category,
                    "message": safety_result.user_message
                }
            }
        )

    # 1.6. Adversarial prompt injection & jailbreak detection
    injection_match = detect_prompt_injection(req.question)
    if injection_match:
        record_security_incident_bg(
            event_type="PROMPT_INJECTION",
            severity="HIGH",
            client_ip=request.client.host if request.client else "127.0.0.1",
            user_identifier=client_id,
            endpoint=request.url.path,
            detail=f"Adversarial signature '{injection_match['rule']}' detected in question: {req.question[:120]}",
            action_taken="BLOCKED"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "security_policy_violation",
                    "message": "Query contains adversarial or restricted instructional patterns. Request blocked by AI Safety Governor."
                }
            }
        )


    # 2. Multi-tenancy department scoping (Phase 11)
    target_dept = req.department or (user.department if user and user.role != "admin" else None)
    if target_dept in ("all", "ALL", "*"):
        target_dept = None
    scope_key = f"{target_dept or 'all'}|{req.course or 'all'}"

    # 3. Authorization-aware Semantic Cache check (Tier 1: Exact Key)
    cache_key = cache.make_cache_key(req.question, target_dept, req.course)
    cached_data = await cache.get(cache_key)

    if cached_data:
        duration_s = time.time() - start_time
        latency_ms = duration_s * 1000

        # Prometheus metrics
        RAG_CACHE_HITS.inc()
        RAG_QUERY_TOTAL.labels(status="success", served_by="cache", department=dept_label).inc()
        RAG_QUERY_DURATION.labels(served_by="cache").observe(duration_s)

        _spawn_bg_task(record_audit(req.question, served_by="cache", latency_ms=latency_ms, tokens=0))
        _spawn_bg_task(record_chat_interaction_bg(
            session_id=session_id,
            user_identifier=client_id,
            role=role_val,
            department=target_dept,
            course=req.course,
            user_query=req.question,
            assistant_answer=cached_data["answer"],
            citations=cached_data.get("citations", []),
            confidence=1.0,
            crag_decision="CORRECT",
            served_by="cache",
            latency_ms=latency_ms,
            tokens=0
        ))
        logger.info(f"Cache Tier-1 HIT for query: '{req.question[:40]}...' (Latency: {latency_ms:.2f}ms)")

        # Stream cached response if client requested stream
        if req.stream:
            async def stream_cached():
                yield f"data: {json.dumps({'type': 'metadata', 'session_id': session_id, 'served_by': 'cache'})}\n\n"
                yield f"data: {json.dumps({'type': 'citations', 'citations': cached_data.get('citations', [])})}\n\n"
                ans_words = cached_data.get("answer", "").split(" ")
                for idx, w in enumerate(ans_words):
                    chunk_str = w if idx == len(ans_words) - 1 else w + " "
                    yield f"data: {json.dumps({'type': 'token', 'delta': chunk_str})}\n\n"
                    await asyncio.sleep(0.01)
                yield f"data: {json.dumps({'type': 'done', 'session_id': session_id, 'total_latency_ms': round((time.time() - start_time) * 1000, 2)})}\n\n"

            return StreamingResponse(stream_cached(), media_type="text/event-stream")

        return AskResponse(
            answer=cached_data["answer"],
            citations=[Citation(**c) for c in cached_data.get("citations", [])],
            served_by="cache",
            session_id=session_id
        )

    # 3.5. Natural Conversational / Identity Query Handling (MDU Rohtak Assistant)
    from api.core.conversational import get_conversational_response
    conv_response = get_conversational_response(req.question)
    if conv_response:
        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        RAG_QUERY_TOTAL.labels(status="success", served_by="local", department=dept_label).inc()
        RAG_QUERY_DURATION.labels(served_by="local").observe((time.time() - start_time))
        asyncio.create_task(record_audit(req.question, served_by="local", latency_ms=elapsed_ms, tokens=len(conv_response.split())))
        _spawn_bg_task(record_chat_interaction_bg(
            session_id=session_id,
            user_identifier=client_id,
            role=role_val,
            department=target_dept,
            course=req.course,
            user_query=req.question,
            assistant_answer=conv_response,
            citations=[],
            confidence=1.0,
            crag_decision="CORRECT",
            served_by="local",
            latency_ms=elapsed_ms,
            tokens=len(conv_response.split())
        ))

        if req.stream:
            async def stream_conversational():
                yield f"data: {json.dumps({'type': 'metadata', 'session_id': session_id, 'served_by': 'local'})}\n\n"
                yield f"data: {json.dumps({'type': 'citations', 'citations': []})}\n\n"
                words = conv_response.split(" ")
                for idx, w in enumerate(words):
                    chunk_str = w if idx == len(words) - 1 else w + " "
                    yield f"data: {json.dumps({'type': 'token', 'delta': chunk_str})}\n\n"
                    await asyncio.sleep(0.015)
                yield f"data: {json.dumps({'type': 'done', 'session_id': session_id, 'total_latency_ms': elapsed_ms})}\n\n"

            return StreamingResponse(stream_conversational(), media_type="text/event-stream")

        return AskResponse(
            answer=conv_response,
            citations=[],
            served_by="local",
            session_id=session_id
        )

    # 3.8. Tier-2 Semantic Vector Cache Check (Cosine similarity >= 0.94)
    from api.rag.embedder import embedder
    query_vec = await asyncio.to_thread(embedder.embed_query, req.question)
    cached_semantic = cache.get_semantic(query_vec, scope=scope_key, threshold=0.94)
    if cached_semantic:
        duration_s = time.time() - start_time
        latency_ms = duration_s * 1000

        RAG_CACHE_HITS.inc()
        RAG_QUERY_TOTAL.labels(status="success", served_by="cache", department=dept_label).inc()
        RAG_QUERY_DURATION.labels(served_by="cache").observe(duration_s)

        asyncio.create_task(record_audit(req.question, served_by="cache", latency_ms=latency_ms, tokens=0))
        _spawn_bg_task(record_chat_interaction_bg(
            session_id=session_id,
            user_identifier=client_id,
            role=role_val,
            department=target_dept,
            course=req.course,
            user_query=req.question,
            assistant_answer=cached_semantic["answer"],
            citations=cached_semantic.get("citations", []),
            confidence=1.0,
            crag_decision="CORRECT",
            served_by="cache",
            latency_ms=latency_ms,
            tokens=0
        ))
        logger.info(f"Cache Tier-2 Semantic HIT for query: '{req.question[:40]}...' (Latency: {latency_ms:.2f}ms)")

        if req.stream:
            async def stream_cached_sem():
                yield f"data: {json.dumps({'type': 'metadata', 'session_id': session_id, 'served_by': 'cache'})}\n\n"
                yield f"data: {json.dumps({'type': 'citations', 'citations': cached_semantic.get('citations', [])})}\n\n"
                ans_words = cached_semantic.get("answer", "").split(" ")
                for idx, w in enumerate(ans_words):
                    chunk_str = w if idx == len(ans_words) - 1 else w + " "
                    yield f"data: {json.dumps({'type': 'token', 'delta': chunk_str})}\n\n"
                    await asyncio.sleep(0.01)
                yield f"data: {json.dumps({'type': 'done', 'session_id': session_id, 'total_latency_ms': round((time.time() - start_time) * 1000, 2)})}\n\n"

            return StreamingResponse(stream_cached_sem(), media_type="text/event-stream")

        return AskResponse(
            answer=cached_semantic["answer"],
            citations=[Citation(**c) for c in cached_semantic.get("citations", [])],
            served_by="cache",
            session_id=session_id
        )

    # 3.9. OpenViking-Inspired Adaptive Tiered Context Check (L1 Overview fast-path)
    from api.context.tiered_engine import tiered_engine
    if tiered_engine.is_overview_query(req.question):
        l1_answer = await tiered_engine.answer_overview_query(
            query=req.question,
            department=target_dept,
            course=req.course
        )
        if l1_answer:
            duration_s = time.time() - start_time
            latency_ms = duration_s * 1000
            RAG_QUERY_TOTAL.labels(status="success", served_by="local", department=dept_label).inc()
            RAG_QUERY_DURATION.labels(served_by="local").observe(duration_s)
            _spawn_bg_task(record_audit(req.question, served_by="tiered_context_l1", latency_ms=latency_ms, tokens=len(l1_answer["answer"].split())))
            _spawn_bg_task(record_chat_interaction_bg(
                session_id=session_id,
                user_identifier=client_id,
                role=role_val,
                department=target_dept,
                course=req.course,
                user_query=req.question,
                assistant_answer=l1_answer["answer"],
                citations=l1_answer.get("citations", []),
                confidence=1.0,
                crag_decision="CORRECT",
                served_by="tiered_context_l1",
                latency_ms=latency_ms,
                tokens=len(l1_answer["answer"].split())
            ))
            logger.info(f"OpenViking L1 Overview Fast-Path served for query: '{req.question[:40]}...' (Latency: {latency_ms:.2f}ms, Saved ~{l1_answer.get('tokens_saved_approx')} tokens)")

            citations = [Citation(**c) for c in l1_answer.get("citations", [])]

            if req.stream:
                async def stream_l1():
                    yield f"data: {json.dumps({'type': 'metadata', 'session_id': session_id, 'served_by': 'tiered_context_l1', 'uri': l1_answer.get('uri')})}\n\n"
                    yield f"data: {json.dumps({'type': 'citations', 'citations': [c.model_dump() for c in citations]})}\n\n"
                    words = l1_answer["answer"].split(" ")
                    for idx, w in enumerate(words):
                        chunk_str = w if idx == len(words) - 1 else w + " "
                        yield f"data: {json.dumps({'type': 'token', 'delta': chunk_str})}\n\n"
                        await asyncio.sleep(0.01)
                    yield f"data: {json.dumps({'type': 'done', 'session_id': session_id, 'total_latency_ms': round((time.time() - start_time) * 1000, 2)})}\n\n"

                return StreamingResponse(stream_l1(), media_type="text/event-stream")

            return AskResponse(
                answer=l1_answer["answer"],
                citations=citations,
                served_by="tiered_context_l1",
                session_id=session_id
            )

    # 4. Cache MISS -> Hybrid Scope-Filtered Retrieval with CRAG (Phase 4)
    RAG_CACHE_MISSES.inc()
    retrieval_start = time.time()
    chunks, crag_result = await retriever.retrieve_with_crag(
        query=req.question,
        department=target_dept,
        course=req.course,
        query_vector=query_vec,
    )
    RAG_RETRIEVAL_DURATION.observe(time.time() - retrieval_start)

    # Format verified citations with OCR cleaning and deduplication
    from api.rag.query_utils import clean_ocr_text
    seen_citations = set()
    citations = []
    for c in chunks:
        doc_id = str(c.get("document_id", ""))
        page_num = c.get("page_number")
        key = (doc_id, page_num)
        if key in seen_citations:
            continue
        seen_citations.add(key)

        cleaned_snip = clean_ocr_text(c.get("text", "")).strip()[:220]
        citations.append(
            Citation(
                document_id=doc_id,
                title=c.get("title", "Course Document"),
                page_number=page_num,
                section=c.get("section"),
                snippet=cleaned_snip
            )
        )
    citations = citations[:3]
    citations_payload = [c.model_dump() for c in citations]

    # 5. Explicit Abstention check if no matching evidence or CRAG INCORRECT
    if not chunks or (crag_result and crag_result.decision == "INCORRECT"):
        from api.core.conversational import is_mdu_institutional_query
        is_inst = is_mdu_institutional_query(req.question)

        if not is_inst:
            # The query is general academic, coding, math, science, general knowledge, or conversational.
            # Serve using Full Generative AI reasoning!
            logger.info(f"General AI fallback engaged for non-institutional query: '{req.question[:60]}'")
            gen_system_prompt = (
                "You are an intelligent, helpful AI Academic Assistant at Maharshi Dayanand University (MDU Rohtak). "
                "Provide clear, comprehensive, and accurate explanations for academic concepts, coding, mathematics, "
                "science, study techniques, and general knowledge. Answer warmly, politely, and thoroughly in the language used by the student."
            )
            messages = [
                {"role": "system", "content": gen_system_prompt},
                {"role": "user", "content": req.question}
            ]

            if req.stream:
                async def stream_general_ai():
                    yield f"data: {json.dumps({'type': 'metadata', 'session_id': session_id, 'served_by': 'general_ai', 'crag_decision': 'NOT_APPLICABLE', 'confidence': 1.0})}\n\n"
                    yield f"data: {json.dumps({'type': 'citations', 'citations': []})}\n\n"
                    accumulated_tokens = []
                    async for token in llm_router.stream_response(messages=messages, temperature=0.3):
                        accumulated_tokens.append(token)
                        yield f"data: {json.dumps({'type': 'token', 'delta': token})}\n\n"

                    full_answer = "".join(accumulated_tokens).strip()
                    elapsed_ms = round((time.time() - start_time) * 1000, 2)
                    yield f"data: {json.dumps({'type': 'done', 'session_id': session_id, 'total_latency_ms': elapsed_ms})}\n\n"

                    cache_payload = {"answer": full_answer, "citations": []}
                    await cache.set_semantic(cache_key, query_vec, scope_key, cache_payload, ttl=settings.CACHE_TTL_VOLATILE_SECONDS)
                    RAG_QUERY_TOTAL.labels(status="success", served_by="local", department=dept_label).inc()
                    RAG_QUERY_DURATION.labels(served_by="local").observe(time.time() - start_time)
                    _spawn_bg_task(record_audit(req.question, served_by="general_ai", latency_ms=elapsed_ms, tokens=len(accumulated_tokens)))
                    _spawn_bg_task(record_chat_interaction_bg(
                        session_id=session_id,
                        user_identifier=client_id,
                        role=role_val,
                        department=target_dept,
                        course=req.course,
                        user_query=req.question,
                        assistant_answer=full_answer,
                        citations=[],
                        confidence=1.0,
                        crag_decision="CORRECT",
                        served_by="general_ai",
                        latency_ms=elapsed_ms,
                        tokens=len(accumulated_tokens)
                    ))

                return StreamingResponse(stream_general_ai(), media_type="text/event-stream")

            # Non-streaming general AI fallback
            gen_resp = await llm_router.generate_response(messages=messages, temperature=0.3)
            gen_answer = gen_resp["choices"][0]["message"]["content"]
            elapsed_ms = round((time.time() - start_time) * 1000, 2)

            cache_payload = {"answer": gen_answer, "citations": []}
            await cache.set_semantic(cache_key, query_vec, scope_key, cache_payload, ttl=settings.CACHE_TTL_VOLATILE_SECONDS)
            RAG_QUERY_TOTAL.labels(status="success", served_by="local", department=dept_label).inc()
            RAG_QUERY_DURATION.labels(served_by="local").observe(time.time() - start_time)
            _spawn_bg_task(record_audit(req.question, served_by="general_ai", latency_ms=elapsed_ms, tokens=len(gen_answer.split())))
            _spawn_bg_task(record_chat_interaction_bg(
                session_id=session_id,
                user_identifier=client_id,
                role=role_val,
                department=target_dept,
                course=req.course,
                user_query=req.question,
                assistant_answer=gen_answer,
                citations=[],
                confidence=1.0,
                crag_decision="CORRECT",
                served_by="general_ai",
                latency_ms=elapsed_ms,
                tokens=len(gen_answer.split())
            ))
            return AskResponse(
                answer=gen_answer,
                citations=[],
                served_by="general_ai",
                confidence=1.0,
                crag_decision="CORRECT",
                session_id=session_id
            )

        duration_s = time.time() - start_time
        latency_ms = duration_s * 1000
        crag_dec = crag_result.decision if crag_result else "INCORRECT"
        crag_conf = crag_result.confidence if crag_result else 0.0
        RAG_QUERY_TOTAL.labels(status="abstained", served_by="local", department=dept_label).inc()
        RAG_QUERY_DURATION.labels(served_by="local").observe(duration_s)
        asyncio.create_task(record_audit(req.question, served_by="local", latency_ms=latency_ms, tokens=0, crag_decision=crag_dec, confidence=crag_conf))

        abstention_text = get_abstention_message(req.question)

        _spawn_bg_task(record_chat_interaction_bg(
            session_id=session_id,
            user_identifier=client_id,
            role=role_val,
            department=target_dept,
            course=req.course,
            user_query=req.question,
            assistant_answer=abstention_text,
            citations=[],
            confidence=crag_conf,
            crag_decision=crag_dec,
            served_by="local",
            latency_ms=latency_ms,
            tokens=0
        ))

        if req.stream:
            async def stream_abstention():
                yield f"data: {json.dumps({'type': 'metadata', 'session_id': session_id, 'served_by': 'local', 'crag_decision': crag_dec, 'confidence': crag_conf})}\n\n"
                yield f"data: {json.dumps({'type': 'citations', 'citations': []})}\n\n"
                yield f"data: {json.dumps({'type': 'token', 'delta': abstention_text})}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'session_id': session_id, 'total_latency_ms': round((time.time() - start_time) * 1000, 2)})}\n\n"

            return StreamingResponse(stream_abstention(), media_type="text/event-stream")

        return AskResponse(
            answer=abstention_text,
            citations=[],
            served_by="local",
            confidence=crag_conf,
            crag_decision=crag_dec,
            session_id=session_id
        )

    # 6. Stream or Non-Stream LLM synthesis
    if req.stream:
        async def stream_rag():
            try:
                yield f"data: {json.dumps({'type': 'metadata', 'session_id': session_id, 'served_by': 'local', 'crag_decision': crag_result.decision, 'confidence': crag_result.confidence})}\n\n"
                yield f"data: {json.dumps({'type': 'citations', 'citations': citations_payload})}\n\n"

                accumulated_tokens = []
                async for token in llm_router.stream_rag_response(
                    question=req.question,
                    chunks=chunks
                ):
                    accumulated_tokens.append(token)
                    yield f"data: {json.dumps({'type': 'token', 'delta': token})}\n\n"

                full_answer = "".join(accumulated_tokens).strip()
                from api.rag.chat_generator import clean_rag_answer
                cleaned_answer = clean_rag_answer(full_answer)

                elapsed_ms = round((time.time() - start_time) * 1000, 2)
                yield f"data: {json.dumps({'type': 'done', 'session_id': session_id, 'total_latency_ms': elapsed_ms})}\n\n"

                # Cache the response for future queries (Tier-1 key + Tier-2 semantic vector)
                cache_payload = {
                    "answer": cleaned_answer,
                    "citations": citations_payload,
                }
                await cache.set_semantic(cache_key, query_vec, scope_key, cache_payload, ttl=settings.CACHE_TTL_VOLATILE_SECONDS)
                RAG_QUERY_TOTAL.labels(status="success", served_by="local", department=dept_label).inc()
                RAG_QUERY_DURATION.labels(served_by="local").observe((time.time() - start_time))
                _spawn_bg_task(record_audit(req.question, served_by="local", latency_ms=elapsed_ms, tokens=len(accumulated_tokens)))
                _spawn_bg_task(record_chat_interaction_bg(
                    session_id=session_id,
                    user_identifier=client_id,
                    role=role_val,
                    department=target_dept,
                    course=req.course,
                    user_query=req.question,
                    assistant_answer=cleaned_answer,
                    citations=citations_payload,
                    confidence=crag_result.confidence if crag_result else 1.0,
                    crag_decision=crag_result.decision if crag_result else "CORRECT",
                    served_by="local",
                    latency_ms=elapsed_ms,
                    tokens=len(accumulated_tokens)
                ))
            finally:
                pass

        return StreamingResponse(stream_rag(), media_type="text/event-stream")

    # Non-stream path
    try:
        rag_result = await llm_router.generate_rag_response(
            question=req.question,
            chunks=chunks
        )

        served_by = rag_result.get("served_by", "local")

        abstention_text = get_abstention_message(req.question)
        if rag_result.get("abstained") or rag_result.get("answer") in [ABSTENTION_MESSAGE, ABSTENTION_MESSAGE_HINDI]:
            from api.core.conversational import is_mdu_institutional_query
            if not is_mdu_institutional_query(req.question):
                gen_system_prompt = (
                    "You are an intelligent, helpful AI Academic Assistant at Maharshi Dayanand University (MDU Rohtak). "
                    "Provide clear, comprehensive, and accurate explanations for academic concepts, coding, mathematics, "
                    "science, study techniques, and general knowledge. Answer warmly, politely, and thoroughly in the language used by the student."
                )
                messages = [
                    {"role": "system", "content": gen_system_prompt},
                    {"role": "user", "content": req.question}
                ]
                gen_resp = await llm_router.generate_response(messages=messages, temperature=0.3)
                gen_answer = gen_resp["choices"][0]["message"]["content"]
                elapsed_ms = round((time.time() - start_time) * 1000, 2)
                cache_payload = {"answer": gen_answer, "citations": []}
                await cache.set_semantic(cache_key, query_vec, scope_key, cache_payload, ttl=settings.CACHE_TTL_VOLATILE_SECONDS)
                _spawn_bg_task(record_audit(req.question, served_by="general_ai", latency_ms=elapsed_ms, tokens=len(gen_answer.split())))
                _spawn_bg_task(record_chat_interaction_bg(
                    session_id=session_id,
                    user_identifier=client_id,
                    role=role_val,
                    department=target_dept,
                    course=req.course,
                    user_query=req.question,
                    assistant_answer=gen_answer,
                    citations=[],
                    confidence=1.0,
                    crag_decision="CORRECT",
                    served_by="general_ai",
                    latency_ms=elapsed_ms,
                    tokens=len(gen_answer.split())
                ))
                return AskResponse(
                    answer=gen_answer,
                    citations=[],
                    served_by="general_ai",
                    confidence=1.0,
                    crag_decision="CORRECT",
                    session_id=session_id
                )

            duration_s = time.time() - start_time
            latency_ms = duration_s * 1000
            RAG_QUERY_TOTAL.labels(status="abstained", served_by=served_by, department=dept_label).inc()
            RAG_QUERY_DURATION.labels(served_by=served_by).observe(duration_s)
            _spawn_bg_task(record_audit(req.question, served_by=served_by, latency_ms=latency_ms, tokens=0))
            _spawn_bg_task(record_chat_interaction_bg(
                session_id=session_id,
                user_identifier=client_id,
                role=role_val,
                department=target_dept,
                course=req.course,
                user_query=req.question,
                assistant_answer=abstention_text,
                citations=[],
                confidence=0.0,
                crag_decision="INCORRECT",
                served_by=served_by,
                latency_ms=latency_ms,
                tokens=0
            ))
            return AskResponse(
                answer=abstention_text,
                citations=[],
                served_by=served_by,
                confidence=0.0,
                crag_decision="INCORRECT",
                session_id=session_id
            )

        # Store in Cache (Tier-1 key + Tier-2 semantic vector)
        response_payload = {
            "answer": rag_result["answer"],
            "citations": citations_payload,
        }
        await cache.set_semantic(cache_key, query_vec, scope_key, response_payload, ttl=settings.CACHE_TTL_VOLATILE_SECONDS)

        duration_s = time.time() - start_time
        latency_ms = duration_s * 1000

        # Prometheus metrics
        RAG_QUERY_TOTAL.labels(status="success", served_by=served_by, department=dept_label).inc()
        RAG_QUERY_DURATION.labels(served_by=served_by).observe(duration_s)

        _spawn_bg_task(record_audit(
            req.question,
            served_by=served_by,
            latency_ms=latency_ms,
            tokens=150,
            crag_decision=crag_result.decision if crag_result else "CORRECT",
            confidence=crag_result.confidence if crag_result else 1.0
        ))
        _spawn_bg_task(record_chat_interaction_bg(
            session_id=session_id,
            user_identifier=client_id,
            role=role_val,
            department=target_dept,
            course=req.course,
            user_query=req.question,
            assistant_answer=rag_result["answer"],
            citations=citations_payload,
            confidence=crag_result.confidence if crag_result else 1.0,
            crag_decision=crag_result.decision if crag_result else "CORRECT",
            served_by=served_by,
            latency_ms=latency_ms,
            tokens=150
        ))
        logger.info(f"Cache MISS for query: '{req.question[:40]}...' (Latency: {latency_ms:.2f}ms, CRAG: {crag_result.decision if crag_result else 'NONE'})")

        return AskResponse(
            answer=rag_result["answer"],
            citations=citations,
            served_by=served_by,
            confidence=crag_result.confidence if crag_result else 1.0,
            crag_decision=crag_result.decision if crag_result else "CORRECT",
            session_id=session_id
        )
    finally:
        pass


class FeedbackRequest(BaseModel):
    query_id: str
    feedback: str  # 'up' or 'down'
    reason: Optional[str] = None


@router.post("/feedback")
@router.post("/api/v1/feedback")
async def submit_user_feedback(req: FeedbackRequest, request: Request):
    """
    Submits student/employee feedback on RAG answers to feed Corrective RAG (CRAG) self-improvement.
    Guarded against feedback poisoning and abusive comments.
    Persists rating directly to ChatMessage and updates ChatSession aggregate satisfaction score.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    if req.reason:
        safety = inspect_content_safety(req.reason, context="feedback")
        if not safety.is_safe:
            record_security_incident_bg(
                event_type="FEEDBACK_POISONING",
                severity="HIGH",
                client_ip=client_ip,
                user_identifier=req.query_id,
                endpoint="/api/v1/feedback",
                detail=f"Feedback poisoning/abuse attempt: {req.reason[:150]}",
                action_taken="REJECTED"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": {
                        "code": "content_policy_violation",
                        "category": safety.category,
                        "message": "Feedback contains prohibited or abusive content and was rejected."
                    }
                }
            )

    # Update database record asynchronously
    async def _update_db_feedback():
        try:
            async with async_session_factory() as session:
                # 1. Try finding message by session_id (latest assistant message in that session)
                stmt = (
                    select(ChatMessage)
                    .where(
                        and_(
                            ChatMessage.session_id == req.query_id,
                            ChatMessage.sender == "assistant"
                        )
                    )
                    .order_by(desc(ChatMessage.created_at))
                    .limit(1)
                )
                msg_rec = (await session.execute(stmt)).scalar_one_or_none()

                # 2. If not found, try finding message by its primary key ID
                if not msg_rec:
                    try:
                        msg_uuid = uuid.UUID(req.query_id)
                        stmt_id = select(ChatMessage).where(ChatMessage.id == msg_uuid)
                        msg_rec = (await session.execute(stmt_id)).scalar_one_or_none()
                    except Exception:
                        pass

                if msg_rec:
                    msg_rec.feedback = req.feedback
                    msg_rec.feedback_reason = req.reason

                    # Update associated ChatSession score
                    sess_stmt = select(ChatSession).where(ChatSession.session_id == msg_rec.session_id)
                    sess_rec = (await session.execute(sess_stmt)).scalar_one_or_none()
                    if sess_rec:
                        if req.feedback == "up":
                            sess_rec.feedback_score += 1
                        elif req.feedback == "down":
                            sess_rec.feedback_score -= 1
                            sess_rec.has_negative_feedback = True
                        sess_rec.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

                    await session.commit()
                    logger.info(f"Feedback '{req.feedback}' persisted for session/msg {req.query_id}")
        except Exception as e:
            logger.warning(f"Error persisting feedback in database: {e}")

    _spawn_bg_task(_update_db_feedback())

    logger.info(f"User feedback received: query_id={req.query_id}, feedback={req.feedback}, reason={req.reason}")
    return {
        "status": "success",
        "message": f"Feedback '{req.feedback}' recorded successfully for query '{req.query_id}'"
    }


