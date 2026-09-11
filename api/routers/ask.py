import time
import json
import asyncio
import hashlib
import logging
from typing import List, Optional
from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

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
from db.models import QueryAuditLog, User
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
    """Reference: Appendix B (Table 20)"""
    answer: str
    citations: List[Citation]
    served_by: str  # local | hosted | fallback | cache
    confidence: Optional[float] = 1.0
    crag_decision: Optional[str] = "CORRECT"

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
        logger.info(f"Cache Tier-1 HIT for query: '{req.question[:40]}...' (Latency: {latency_ms:.2f}ms)")

        # Stream cached response if client requested stream
        if req.stream:
            async def stream_cached():
                yield f"data: {json.dumps({'type': 'metadata', 'served_by': 'cache'})}\n\n"
                yield f"data: {json.dumps({'type': 'citations', 'citations': cached_data.get('citations', [])})}\n\n"
                ans_words = cached_data.get("answer", "").split(" ")
                for idx, w in enumerate(ans_words):
                    chunk_str = w if idx == len(ans_words) - 1 else w + " "
                    yield f"data: {json.dumps({'type': 'token', 'delta': chunk_str})}\n\n"
                    await asyncio.sleep(0.01)
                yield f"data: {json.dumps({'type': 'done', 'total_latency_ms': round((time.time() - start_time) * 1000, 2)})}\n\n"

            return StreamingResponse(stream_cached(), media_type="text/event-stream")

        return AskResponse(
            answer=cached_data["answer"],
            citations=[Citation(**c) for c in cached_data.get("citations", [])],
            served_by="cache"
        )

    # 3.5. Natural Conversational / Identity Query Handling (MDU Rohtak Assistant)
    from api.core.conversational import get_conversational_response
    conv_response = get_conversational_response(req.question)
    if conv_response:
        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        RAG_QUERY_TOTAL.labels(status="success", served_by="local", department=dept_label).inc()
        RAG_QUERY_DURATION.labels(served_by="local").observe((time.time() - start_time))
        asyncio.create_task(record_audit(req.question, served_by="local", latency_ms=elapsed_ms, tokens=len(conv_response.split())))

        if req.stream:
            async def stream_conversational():
                yield f"data: {json.dumps({'type': 'metadata', 'served_by': 'local'})}\n\n"
                yield f"data: {json.dumps({'type': 'citations', 'citations': []})}\n\n"
                words = conv_response.split(" ")
                for idx, w in enumerate(words):
                    chunk_str = w if idx == len(words) - 1 else w + " "
                    yield f"data: {json.dumps({'type': 'token', 'delta': chunk_str})}\n\n"
                    await asyncio.sleep(0.015)
                yield f"data: {json.dumps({'type': 'done', 'total_latency_ms': elapsed_ms})}\n\n"

            return StreamingResponse(stream_conversational(), media_type="text/event-stream")

        return AskResponse(
            answer=conv_response,
            citations=[],
            served_by="local"
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
        logger.info(f"Cache Tier-2 Semantic HIT for query: '{req.question[:40]}...' (Latency: {latency_ms:.2f}ms)")

        if req.stream:
            async def stream_cached_sem():
                yield f"data: {json.dumps({'type': 'metadata', 'served_by': 'cache'})}\n\n"
                yield f"data: {json.dumps({'type': 'citations', 'citations': cached_semantic.get('citations', [])})}\n\n"
                ans_words = cached_semantic.get("answer", "").split(" ")
                for idx, w in enumerate(ans_words):
                    chunk_str = w if idx == len(ans_words) - 1 else w + " "
                    yield f"data: {json.dumps({'type': 'token', 'delta': chunk_str})}\n\n"
                    await asyncio.sleep(0.01)
                yield f"data: {json.dumps({'type': 'done', 'total_latency_ms': round((time.time() - start_time) * 1000, 2)})}\n\n"

            return StreamingResponse(stream_cached_sem(), media_type="text/event-stream")

        return AskResponse(
            answer=cached_semantic["answer"],
            citations=[Citation(**c) for c in cached_semantic.get("citations", [])],
            served_by="cache"
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
        duration_s = time.time() - start_time
        latency_ms = duration_s * 1000
        crag_dec = crag_result.decision if crag_result else "INCORRECT"
        crag_conf = crag_result.confidence if crag_result else 0.0
        RAG_QUERY_TOTAL.labels(status="abstained", served_by="local", department=dept_label).inc()
        RAG_QUERY_DURATION.labels(served_by="local").observe(duration_s)
        asyncio.create_task(record_audit(req.question, served_by="local", latency_ms=latency_ms, tokens=0, crag_decision=crag_dec, confidence=crag_conf))

        abstention_text = get_abstention_message(req.question)

        if req.stream:
            async def stream_abstention():
                yield f"data: {json.dumps({'type': 'metadata', 'served_by': 'local', 'crag_decision': crag_dec, 'confidence': crag_conf})}\n\n"
                yield f"data: {json.dumps({'type': 'citations', 'citations': []})}\n\n"
                yield f"data: {json.dumps({'type': 'token', 'delta': abstention_text})}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'total_latency_ms': round((time.time() - start_time) * 1000, 2)})}\n\n"

            return StreamingResponse(stream_abstention(), media_type="text/event-stream")

        return AskResponse(
            answer=abstention_text,
            citations=[],
            served_by="local",
            confidence=crag_conf,
            crag_decision=crag_dec
        )

    # 6. Stream or Non-Stream LLM synthesis
    if req.stream:
        async def stream_rag():
            try:
                yield f"data: {json.dumps({'type': 'metadata', 'served_by': 'local', 'crag_decision': crag_result.decision, 'confidence': crag_result.confidence})}\n\n"
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
                yield f"data: {json.dumps({'type': 'done', 'total_latency_ms': elapsed_ms})}\n\n"

                # Cache the response for future queries (Tier-1 key + Tier-2 semantic vector)
                cache_payload = {
                    "answer": cleaned_answer,
                    "citations": citations_payload,
                }
                await cache.set_semantic(cache_key, query_vec, scope_key, cache_payload, ttl=settings.CACHE_TTL_VOLATILE_SECONDS)
                RAG_QUERY_TOTAL.labels(status="success", served_by="local", department=dept_label).inc()
                RAG_QUERY_DURATION.labels(served_by="local").observe((time.time() - start_time))
                _spawn_bg_task(record_audit(req.question, served_by="local", latency_ms=elapsed_ms, tokens=len(accumulated_tokens)))
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
            duration_s = time.time() - start_time
            latency_ms = duration_s * 1000
            RAG_QUERY_TOTAL.labels(status="abstained", served_by=served_by, department=dept_label).inc()
            RAG_QUERY_DURATION.labels(served_by=served_by).observe(duration_s)
            _spawn_bg_task(record_audit(req.question, served_by=served_by, latency_ms=latency_ms, tokens=0))
            return AskResponse(
                answer=abstention_text,
                citations=[],
                served_by=served_by
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
        logger.info(f"Cache MISS for query: '{req.question[:40]}...' (Latency: {latency_ms:.2f}ms, CRAG: {crag_result.decision if crag_result else 'NONE'})")

        return AskResponse(
            answer=rag_result["answer"],
            citations=citations,
            served_by=served_by,
            confidence=crag_result.confidence if crag_result else 1.0,
            crag_decision=crag_result.decision if crag_result else "CORRECT"
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

    logger.info(f"User feedback received: query_id={req.query_id}, feedback={req.feedback}, reason={req.reason}")
    return {
        "status": "success",
        "message": f"Feedback '{req.feedback}' recorded successfully for query '{req.query_id}'"
    }

