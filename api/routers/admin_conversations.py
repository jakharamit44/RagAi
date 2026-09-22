"""
api/routers/admin_conversations.py
Enterprise Conversation Inspector & AI Self-Improvement Admin Router.

Provides administrative visibility, auditing, filtering, and prompt optimization
hooks for student and user conversations.
"""

import math
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func, or_, and_, desc, delete
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.auth import get_current_user, require_role
from api.rag.self_improver import self_improver, PromptRuleManager
from db.session import get_db, async_session_factory
from db.models import ChatSession, ChatMessage, User

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/admin/conversations",
    tags=["Admin Conversation Inspector"],
    dependencies=[Depends(require_role("admin"))],
)


# -----------------------------------------------------------------------------
# PYDANTIC RESPONSE SCHEMAS
# -----------------------------------------------------------------------------
class CitationModel(BaseModel):
    document_id: Optional[str] = None
    title: Optional[str] = None
    page_number: Optional[int] = None
    section: Optional[str] = None
    snippet: Optional[str] = None


class ChatMessageResponse(BaseModel):
    id: str
    session_id: str
    sender: str
    content: str
    citations: List[Dict[str, Any]] = []
    confidence: Optional[float] = None
    crag_decision: Optional[str] = None
    served_by: Optional[str] = None
    latency_ms: Optional[float] = None
    tokens_used: int = 0
    feedback: Optional[str] = None
    feedback_reason: Optional[str] = None
    created_at: str


class ChatSessionSummary(BaseModel):
    id: str
    session_id: str
    title: str
    user_identifier: Optional[str] = None
    role: str
    department: Optional[str] = None
    course: Optional[str] = None
    message_count: int
    feedback_score: int
    has_negative_feedback: bool
    has_low_confidence: bool
    created_at: str
    updated_at: str
    last_message_preview: Optional[str] = None


class PaginatedSessionsResponse(BaseModel):
    items: List[ChatSessionSummary]
    total: int
    page: int
    page_size: int
    total_pages: int


class ChatSessionDetailResponse(BaseModel):
    session: ChatSessionSummary
    messages: List[ChatMessageResponse]


class ConversationStatsResponse(BaseModel):
    total_sessions: int
    total_messages: int
    positive_feedback_count: int
    negative_feedback_count: int
    satisfaction_rate_pct: float
    low_confidence_count: int
    avg_latency_ms: float
    departments_breakdown: Dict[str, int]


class PurgeRequest(BaseModel):
    older_than_days: Optional[int] = Field(None, ge=1, description="Purge sessions older than N days")
    only_negative: bool = False


# -----------------------------------------------------------------------------
# API ENDPOINTS
# -----------------------------------------------------------------------------

@router.get("/sessions", response_model=PaginatedSessionsResponse)
async def list_chat_sessions(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search term in session title or user ID"),
    department: Optional[str] = Query(None, description="Filter by department"),
    feedback_filter: Optional[str] = Query(
        "all",
        description="Filter status: 'all', 'negative', 'positive', 'low_confidence'"
    ),
    db: AsyncSession = Depends(get_db)
):
    """
    Paginated list of chat sessions with search, department filtering,
    and feedback classification.
    """
    conditions = []

    if department and department not in ("all", "ALL", "*"):
        conditions.append(ChatSession.department == department)

    if feedback_filter == "negative":
        conditions.append(ChatSession.has_negative_feedback == True)
    elif feedback_filter == "positive":
        conditions.append(ChatSession.feedback_score > 0)
    elif feedback_filter == "low_confidence":
        conditions.append(ChatSession.has_low_confidence == True)

    if search and search.strip():
        term = f"%{search.strip()}%"
        conditions.append(
            or_(
                ChatSession.title.ilike(term),
                ChatSession.session_id.ilike(term),
                ChatSession.user_identifier.ilike(term),
            )
        )

    # Base query for count
    count_query = select(func.count(ChatSession.id))
    if conditions:
        count_query = count_query.where(and_(*conditions))

    total_count = (await db.execute(count_query)).scalar() or 0
    total_pages = max(1, math.ceil(total_count / page_size))
    offset = (page - 1) * page_size

    # Fetch rows
    stmt = (
        select(ChatSession)
        .order_by(desc(ChatSession.updated_at))
        .offset(offset)
        .limit(page_size)
    )
    if conditions:
        stmt = stmt.where(and_(*conditions))

    sessions = (await db.execute(stmt)).scalars().all()

    items = []
    for s in sessions:
        # Fetch last message preview snippet
        last_msg_stmt = (
            select(ChatMessage.content)
            .where(ChatMessage.session_id == s.session_id)
            .order_by(desc(ChatMessage.created_at))
            .limit(1)
        )
        last_msg = (await db.execute(last_msg_stmt)).scalar() or ""
        preview = (last_msg[:90] + "...") if len(last_msg) > 90 else last_msg

        items.append(
            ChatSessionSummary(
                id=str(s.id),
                session_id=s.session_id,
                title=s.title or f"Chat Session {s.session_id[:8]}",
                user_identifier=s.user_identifier or "Guest Student",
                role=s.role,
                department=s.department,
                course=s.course,
                message_count=s.message_count,
                feedback_score=s.feedback_score,
                has_negative_feedback=bool(s.has_negative_feedback),
                has_low_confidence=bool(s.has_low_confidence),
                created_at=s.created_at.isoformat() if s.created_at else "",
                updated_at=s.updated_at.isoformat() if s.updated_at else "",
                last_message_preview=preview,
            )
        )

    return PaginatedSessionsResponse(
        items=items,
        total=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/sessions/{session_id}", response_model=ChatSessionDetailResponse)
async def get_session_detail(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Returns full session details including complete chronological message transcript,
    citations, confidence scores, and student feedback.
    """
    stmt = select(ChatSession).where(ChatSession.session_id == session_id)
    session_row = (await db.execute(stmt)).scalar_one_or_none()

    if not session_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat session '{session_id}' not found."
        )

    msg_stmt = (
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
    )
    msg_rows = (await db.execute(msg_stmt)).scalars().all()

    messages = []
    for m in msg_rows:
        citations = []
        if m.citations_json:
            try:
                citations = json.loads(m.citations_json)
                if not isinstance(citations, list):
                    citations = []
            except Exception:
                citations = []

        messages.append(
            ChatMessageResponse(
                id=str(m.id),
                session_id=m.session_id,
                sender=m.sender,
                content=m.content,
                citations=citations,
                confidence=m.confidence,
                crag_decision=m.crag_decision,
                served_by=m.served_by,
                latency_ms=m.latency_ms,
                tokens_used=m.tokens_used,
                feedback=m.feedback,
                feedback_reason=m.feedback_reason,
                created_at=m.created_at.isoformat() if m.created_at else "",
            )
        )

    summary = ChatSessionSummary(
        id=str(session_row.id),
        session_id=session_row.session_id,
        title=session_row.title or f"Chat Session {session_row.session_id[:8]}",
        user_identifier=session_row.user_identifier or "Guest Student",
        role=session_row.role,
        department=session_row.department,
        course=session_row.course,
        message_count=session_row.message_count,
        feedback_score=session_row.feedback_score,
        has_negative_feedback=bool(session_row.has_negative_feedback),
        has_low_confidence=bool(session_row.has_low_confidence),
        created_at=session_row.created_at.isoformat() if session_row.created_at else "",
        updated_at=session_row.updated_at.isoformat() if session_row.updated_at else "",
    )

    return ChatSessionDetailResponse(session=summary, messages=messages)


@router.delete("/sessions/{session_id}")
async def delete_chat_session(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Deletes a single chat session and cascades deletion to all its messages.
    """
    stmt = select(ChatSession).where(ChatSession.session_id == session_id)
    session_row = (await db.execute(stmt)).scalar_one_or_none()

    if not session_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat session '{session_id}' not found."
        )

    await db.delete(session_row)
    await db.commit()
    logger.info(f"Admin deleted chat session {session_id}")
    return {"status": "success", "message": f"Session '{session_id}' deleted successfully."}


@router.post("/sessions/purge")
async def purge_chat_sessions(
    req: PurgeRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Bulk purges chat sessions (e.g. older than N days, or only negative).
    """
    conditions = []
    if req.older_than_days:
        cutoff = datetime.utcnow() - timedelta(days=req.older_than_days)
        conditions.append(ChatSession.created_at < cutoff)

    if req.only_negative:
        conditions.append(ChatSession.has_negative_feedback == True)

    stmt = select(ChatSession)
    if conditions:
        stmt = stmt.where(and_(*conditions))

    sessions_to_delete = (await db.execute(stmt)).scalars().all()
    count = len(sessions_to_delete)

    for s in sessions_to_delete:
        await db.delete(s)

    await db.commit()
    logger.info(f"Admin purged {count} chat sessions.")
    return {"status": "success", "purged_count": count}


@router.get("/stats", response_model=ConversationStatsResponse)
async def get_conversation_stats(db: AsyncSession = Depends(get_db)):
    """
    Aggregates holistic conversation health metrics: total sessions, total messages,
    satisfaction rate, average response latency, and low-confidence counts.
    """
    total_sessions = (await db.execute(select(func.count(ChatSession.id)))).scalar() or 0
    total_messages = (await db.execute(select(func.count(ChatMessage.id)))).scalar() or 0

    pos_feedback = (
        await db.execute(
            select(func.count(ChatMessage.id))
            .where(ChatMessage.feedback == "up")
        )
    ).scalar() or 0

    neg_feedback = (
        await db.execute(
            select(func.count(ChatMessage.id))
            .where(ChatMessage.feedback == "down")
        )
    ).scalar() or 0

    total_rated = pos_feedback + neg_feedback
    satisfaction_rate = round((pos_feedback / total_rated * 100), 1) if total_rated > 0 else 100.0

    low_conf = (
        await db.execute(
            select(func.count(ChatMessage.id))
            .where(
                and_(
                    ChatMessage.sender == "assistant",
                    or_(
                        ChatMessage.confidence < 0.75,
                        ChatMessage.crag_decision == "INCORRECT"
                    )
                )
            )
        )
    ).scalar() or 0

    avg_lat = (
        await db.execute(
            select(func.avg(ChatMessage.latency_ms))
            .where(ChatMessage.sender == "assistant")
        )
    ).scalar() or 0.0

    # Department breakdown
    dept_stmt = (
        select(ChatSession.department, func.count(ChatSession.id))
        .group_by(ChatSession.department)
        .limit(10)
    )
    dept_rows = (await db.execute(dept_stmt)).all()
    dept_map = {
        (d or "General Campus"): cnt
        for d, cnt in dept_rows
    }

    return ConversationStatsResponse(
        total_sessions=total_sessions,
        total_messages=total_messages,
        positive_feedback_count=pos_feedback,
        negative_feedback_count=neg_feedback,
        satisfaction_rate_pct=satisfaction_rate,
        low_confidence_count=low_conf,
        avg_latency_ms=round(float(avg_lat), 1),
        departments_breakdown=dept_map,
    )


@router.post("/optimize-from-failures")
async def optimize_from_conversation_failures():
    """
    Autonomous AI Self-Improvement Hook:
    Harvests failed, low-confidence, and thumbs-down student queries from real chat history,
    diagnoses weaknesses, generates targeted prompt mutation candidates,
    benchmarks against evaluation cases, and commits or rolls back using Karpathy guardrails.
    """
    try:
        result = await self_improver.run_optimization_from_conversations()
        return {
            "status": "success",
            "optimization_result": result,
            "message": (
                f"Optimization cycle {result.get('status')}. "
                f"Harvested {result.get('harvested_count', 0)} real failure cases. "
                f"Baseline: {result.get('baseline_score')}%, New: {result.get('new_score')}%"
            )
        }
    except Exception as e:
        logger.error(f"Failed to run self-improvement from conversations: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Optimization engine error: {str(e)}"
        )
