import time
import uuid
import json
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from api.core.llm_router import llm_router
from api.core.auth import get_optional_current_user
from db.models import User
from api.core.rate_limiter import rate_limiter
from api.core.config import settings
from api.core.security_logger import record_security_incident_bg

router = APIRouter(tags=["OpenAI Compatibility"])

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    """Reference: Appendix B (Table 21)"""
    model: str = "university-rag"
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.2
    stream: Optional[bool] = False

class ChoiceMessage(BaseModel):
    role: str = "assistant"
    content: str

class ChatChoice(BaseModel):
    index: int = 0
    message: ChoiceMessage
    finish_reason: str = "stop"

class ChatCompletionResponse(BaseModel):
    """Reference: Appendix B (Table 22)"""
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatChoice]

@router.post("/v1/chat/completions", responses={200: {"model": ChatCompletionResponse}})
@router.post("/v1/responses")
async def chat_completions(req: ChatCompletionRequest, request: Request, user: Optional[User] = Depends(get_optional_current_user)):
    """
    OpenAI-compatible drop-in chat completions endpoint.
    Routes to local-first LLM backend.
    Supports both standard JSON payload and real-time SSE streaming (stream=True).
    """
    client_id = user.external_id if user else (request.client.host if request.client else "127.0.0.1")
    rate_limit_max = settings.RATE_LIMIT_PER_STUDENT_PER_MINUTE if user else settings.RATE_LIMIT_PER_IP_PER_MINUTE
    try:
        rate_limiter.check_rate_limit(client_id, limit=rate_limit_max)
    except HTTPException:
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

    raw_messages = [{"role": m.role, "content": m.content} for m in req.messages]

    if req.stream:
        cmpl_id = str(uuid.uuid4())
        created_ts = int(time.time())

        async def stream_openai_chunks():
            # Initial chunk establishing assistant role
            initial_chunk = {
                "id": f"chatcmpl-{cmpl_id}",
                "object": "chat.completion.chunk",
                "created": created_ts,
                "model": req.model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"role": "assistant"},
                        "finish_reason": None,
                    }
                ],
            }
            yield f"data: {json.dumps(initial_chunk, ensure_ascii=False)}\n\n"

            async for token in llm_router.stream_response(
                messages=raw_messages,
                temperature=req.temperature or 0.2,
            ):
                chunk = {
                    "id": f"chatcmpl-{cmpl_id}",
                    "object": "chat.completion.chunk",
                    "created": created_ts,
                    "model": req.model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": token},
                            "finish_reason": None,
                        }
                    ],
                }
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

            # Final stopping chunk
            final_chunk = {
                "id": f"chatcmpl-{cmpl_id}",
                "object": "chat.completion.chunk",
                "created": created_ts,
                "model": req.model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {},
                        "finish_reason": "stop",
                    }
                ],
            }
            yield f"data: {json.dumps(final_chunk, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(stream_openai_chunks(), media_type="text/event-stream")

    result = await llm_router.generate_response(
        messages=raw_messages,
        temperature=req.temperature or 0.2,
        stream=False,
    )

    content = result.get("choices", [{}])[0].get("message", {}).get("content", "")

    return ChatCompletionResponse(
        id=f"chatcmpl-{uuid.uuid4()}",
        created=int(time.time()),
        model=req.model,
        choices=[
            ChatChoice(
                index=0,
                message=ChoiceMessage(role="assistant", content=content),
                finish_reason="stop"
            )
        ]
    )

