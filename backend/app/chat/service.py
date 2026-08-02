"""خدمة الدردشة — منطق المحادثات والتخزين.

المحادثة بلا حالة في الخادم: كل طلب يحمل مزوّده ونموذجه (من إعدادات الواجهة) —
الخادم لا يخزّن مفاتيح API أبداً (مفاتيح المستخدم تبقى في متصفحه).
"""

import logging
from collections.abc import AsyncIterator

from app.chat.models import ChatRequest
from app.core.db import get_connection
from app.core.llm.base import BaseLLM

logger = logging.getLogger(__name__)

MAX_HISTORY_MESSAGES = 20  # رسائل تُرسل للنموذج كسياق (أحدثها)


def create_conversation(title: str = "محادثة جديدة") -> int:
    with get_connection() as conn:
        cur = conn.execute("INSERT INTO conversations (title) VALUES (?)", (title,))
        conn.commit()
        return cur.lastrowid


def save_message(conversation_id: int, role: str, content: str) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
            (conversation_id, role, content),
        )
        conn.commit()
        return cur.lastrowid


def save_message_sources(message_id: int, sources: list[dict]) -> None:
    """يخزّن المصادر المرتبطة برسالة رد RAG (م7: تخزين المصدر بالرد)."""
    if not sources:
        return
    with get_connection() as conn:
        conn.executemany(
            "INSERT INTO message_sources "
            "(message_id, document_id, filename, heading, text, score) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            [
                (
                    message_id,
                    s.get("document_id"),
                    s.get("filename", ""),
                    s.get("heading", ""),
                    s.get("text", "")[:1000],
                    s.get("score", 0.0),
                )
                for s in sources
            ],
        )
        conn.commit()


def list_conversations() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, title, created_at FROM conversations ORDER BY id DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def get_conversation(conversation_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, title, created_at FROM conversations WHERE id = ?",
            (conversation_id,),
        ).fetchone()
        return dict(row) if row else None


def get_messages(conversation_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, role, content, created_at FROM messages "
            "WHERE conversation_id = ? ORDER BY id",
            (conversation_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def _history_messages(conversation_id: int) -> list[dict[str, str]]:
    """رسائل السجل (محدودة) بصيغة مزوّد النموذج."""
    rows = get_messages(conversation_id)
    return [{"role": r["role"], "content": r["content"]} for r in rows][-MAX_HISTORY_MESSAGES:]


async def chat_stream(request: ChatRequest, llm: BaseLLM) -> AsyncIterator[dict]:
    """يدير جولة دردشة كاملة ويرسل أحداثاً: بداية، قطعة، نهاية (الرد الكامل).

    الأحداث (JSON):
      {"type": "conversation", "id": ...}
      {"type": "delta", "content": "..."}
      {"type": "done", "content": "الرد الكامل", "message_id": ...}
    """
    conversation_id = request.conversation_id
    if conversation_id is None or get_conversation(conversation_id) is None:
        conversation_id = create_conversation(title=request.message[:40])
        yield {"type": "conversation", "id": conversation_id}

    # رسالة المستخدم تُخزَّن قبل الرد
    save_message(conversation_id, "user", request.message)

    messages = [*_history_messages(conversation_id)]
    pieces: list[str] = []

    yield {"type": "delta", "content": ""}  # إشارة البدء (يفتح المتصفح الحالة)
    async for piece in llm.stream(messages):
        pieces.append(piece)
        yield {"type": "delta", "content": piece}

    full = "".join(pieces).strip()
    message_id = save_message(conversation_id, "assistant", full) if full else None
    yield {"type": "done", "content": full, "message_id": message_id}
