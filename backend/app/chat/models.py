"""نماذج (Schemas) الدردشة."""

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant|system)$")
    content: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=100_000)
    conversation_id: int | None = None
    provider: str | None = None  # من إعدادات المستخدم (يخزّنها في الواجهة)
    model: str | None = None
    base_url: str | None = None
    api_key: str | None = None


class ConversationOut(BaseModel):
    id: int
    title: str
    created_at: str


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    created_at: str


class ConversationDetail(BaseModel):
    conversation: ConversationOut
    messages: list[MessageOut]
