"""مسارات الدردشة — SSE + السجل."""

import json
import logging

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from app.chat.models import (
    ChatRequest,
    ConversationDetail,
    ConversationOut,
    MessageOut,
)
from app.chat.service import chat_stream, get_conversation, get_messages, list_conversations
from app.core.config import get_settings
from app.core.llm.factory import get_llm

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])

settings = get_settings()


@router.post("", response_class=EventSourceResponse)
async def chat(request: ChatRequest):
    """بث استجابة النموذج عبر SSE — قطعة قطعة."""
    provider = request.provider or settings.default_provider
    model = request.model or settings.default_model
    base_url = request.base_url or (settings.ollama_base_url if provider == "ollama" else None)
    try:
        llm = get_llm(provider, model, base_url=base_url, api_key=request.api_key)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    async def event_gen():
        try:
            async for event in chat_stream(request, llm):
                yield {"event": "message", "data": json.dumps(event, ensure_ascii=False)}
        except Exception as e:  # أي خطأ أثناء البث → حدث خطأ واضح
            logger.exception("فشل بث الدردشة")
            yield {
                "event": "message",
                "data": json.dumps({"type": "error", "detail": str(e)}, ensure_ascii=False),
            }

    return EventSourceResponse(event_gen())


@router.get("/history", response_model=list[ConversationOut])
async def history():
    return list_conversations()


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def detail(conversation_id: int):
    conversation = get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="المحادثة غير موجودة")
    return ConversationDetail(
        conversation=ConversationOut(**conversation),
        messages=[MessageOut(**m) for m in get_messages(conversation_id)],
    )


@router.get("/{conversation_id}/messages", response_model=list[MessageOut])
async def messages(conversation_id: int):
    if get_conversation(conversation_id) is None:
        raise HTTPException(status_code=404, detail="المحادثة غير موجودة")
    return [MessageOut(**m) for m in get_messages(conversation_id)]
