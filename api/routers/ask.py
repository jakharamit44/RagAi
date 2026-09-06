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
from api.core.llm_router import llm_router, ABSTENTION_MESSAGE
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
    """Reference: Appendix B (Table 19)"""
    question: str = Field(..., max_length=1000, description="Question string, max 1000 chars (Phase 19)")
    department: Optional[str] = None
    course: Optional[str] = None
    stream: bool = False

class AskResponse(BaseModel):
    """Reference: Appendix B (Table 20)"""
    answer: str
    citations: List[Citation]
    served_by: str  # local | hosted | fallback | cache

async def record_audit(question: str, served_by: str, latency_ms: float, tokens: int = 0):
    """Privacy-preserving audit logging (Table 17 & Phase 19)."""
    try:
        q_hash = hashlib.sha256(question.strip().encode("utf-8")).hexdigest()
        async with async_session_factory() as session:
            entry = QueryAuditLog(
                question_hash=q_hash,
                served_by=served_by,
                latency_ms=latency_ms,
                tokens_used=tokens,
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

    # 1.5. Adversarial prompt injection & jailbreak detection
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
    target_dept = req.department or (user.department if user else None)

    # 3. Authorization-aware Semantic Cache check (Phase 7)
    cache_key = cache.make_cache_key(req.question, target_dept, req.course)
    cached_data = await cache.get(cache_key)

    if cached_data:
        duration_s = time.time() - start_time
        latency_ms = duration_s * 1000

        # Prometheus metrics
        RAG_CACHE_HITS.inc()
        RAG_QUERY_TOTAL.labels(status="success", served_by="cache", department=dept_label).inc()
        RAG_QUERY_DURATION.labels(served_by="cache").observe(duration_s)

        asyncio.create_task(record_audit(req.question, served_by="cache", latency_ms=latency_ms, tokens=0))
        logger.info(f"Cache HIT for query: '{req.question[:40]}...' (Latency: {latency_ms:.2f}ms)")

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

    # 4. Cache MISS -> Hybrid Scope-Filtered Retrieval (Phase 4)
    RAG_CACHE_MISSES.inc()
    retrieval_start = time.time()
    chunks = await retriever.retrieve(
        query=req.question,
        department=target_dept,
        course=req.course,
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

    # 5. Explicit Abstention check if no matching evidence
    if not chunks:
        duration_s = time.time() - start_time
        latency_ms = duration_s * 1000
        RAG_QUERY_TOTAL.labels(status="abstained", served_by="local", department=dept_label).inc()
        RAG_QUERY_DURATION.labels(served_by="local").observe(duration_s)
        asyncio.create_task(record_audit(req.question, served_by="local", latency_ms=latency_ms, tokens=0))

        if req.stream:
            async def stream_abstention():
                yield f"data: {json.dumps({'type': 'metadata', 'served_by': 'local'})}\n\n"
                yield f"data: {json.dumps({'type': 'citations', 'citations': []})}\n\n"
                yield f"data: {json.dumps({'type': 'token', 'delta': ABSTENTION_MESSAGE})}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'total_latency_ms': round((time.time() - start_time) * 1000, 2)})}\n\n"

            return StreamingResponse(stream_abstention(), media_type="text/event-stream")

        return AskResponse(
            answer=ABSTENTION_MESSAGE,
            citations=[],
            served_by="local"
        )

    # 6. Stream or Non-Stream LLM synthesis
    if req.stream:
        async def stream_rag():
            yield f"data: {json.dumps({'type': 'metadata', 'served_by': 'local'})}\n\n"
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

            # Cache the response for future queries
            cache_payload = {
                "answer": cleaned_answer,
                "citations": citations_payload,
            }
            await cache.set(cache_key, cache_payload, ttl=settings.CACHE_TTL_VOLATILE_SECONDS)
            RAG_QUERY_TOTAL.labels(status="success", served_by="local", department=dept_label).inc()
            RAG_QUERY_DURATION.labels(served_by="local").observe((time.time() - start_time))
            asyncio.create_task(record_audit(req.question, served_by="local", latency_ms=elapsed_ms, tokens=len(accumulated_tokens)))

        return StreamingResponse(stream_rag(), media_type="text/event-stream")

    # Non-stream path
    rag_result = await llm_router.generate_rag_response(
        question=req.question,
        chunks=chunks
    )

    served_by = rag_result.get("served_by", "local")

    if rag_result.get("abstained") or rag_result.get("answer") == ABSTENTION_MESSAGE:
        duration_s = time.time() - start_time
        latency_ms = duration_s * 1000
        RAG_QUERY_TOTAL.labels(status="abstained", served_by=served_by, department=dept_label).inc()
        RAG_QUERY_DURATION.labels(served_by=served_by).observe(duration_s)
        asyncio.create_task(record_audit(req.question, served_by=served_by, latency_ms=latency_ms, tokens=0))
        return AskResponse(
            answer=ABSTENTION_MESSAGE,
            citations=[],
            served_by=served_by
        )

    # Store in Cache (Phase 7)
    response_payload = {
        "answer": rag_result["answer"],
        "citations": citations_payload,
    }
    await cache.set(cache_key, response_payload, ttl=settings.CACHE_TTL_VOLATILE_SECONDS)

    duration_s = time.time() - start_time
    latency_ms = duration_s * 1000

    # Prometheus metrics
    RAG_QUERY_TOTAL.labels(status="success", served_by=served_by, department=dept_label).inc()
    RAG_QUERY_DURATION.labels(served_by=served_by).observe(duration_s)

    asyncio.create_task(record_audit(req.question, served_by=served_by, latency_ms=latency_ms, tokens=150))
    logger.info(f"Cache MISS for query: '{req.question[:40]}...' (Latency: {latency_ms:.2f}ms)")

    return AskResponse(
        answer=rag_result["answer"],
        citations=citations,
        served_by=served_by
    )

