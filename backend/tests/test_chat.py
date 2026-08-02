"""اختبارات الدردشة (م3) — SSE + السجل + التخزين، بمزوّد وهمي."""

import json
from collections.abc import AsyncIterator

import pytest
from fastapi.testclient import TestClient

from app.chat.service import (
    create_conversation,
    get_conversation,
    get_messages,
    save_message,
)
from app.core.db import get_connection, init_db
from app.core.llm.base import BaseLLM
from app.main import app


@pytest.fixture(autouse=True)
def fresh_db():
    """تهيئة الجداول قبل كل اختبار وتفريغها بعده (بيئة نظيفة)."""
    init_db()
    yield
    with get_connection() as conn:
        conn.execute("DELETE FROM messages")
        conn.execute("DELETE FROM conversations")
        conn.commit()


class FakeLLM(BaseLLM):
    provider = "fake"
    model = "fake-model"

    async def chat(self, messages, **kwargs):
        return "رد وهمي"

    async def stream(self, messages, **kwargs) -> AsyncIterator[str]:
        for piece in ["مرحباً", " ", "بك"]:
            yield piece

    async def embed(self, texts):
        return [[0.0] * 8 for _ in texts]


@pytest.fixture(autouse=True)
def patch_llm(monkeypatch):
    """كل الاختبارات تستخدم مزوّداً وهمياً — لا اتصال حقيقي أبداً."""
    import app.chat.router as router

    monkeypatch.setattr(router, "get_llm", lambda *a, **k: FakeLLM())


def test_service_conversation_crud():
    cid = create_conversation("عنوان تجريبي")
    assert get_conversation(cid)["title"] == "عنوان تجريبي"
    mid = save_message(cid, "user", "سؤال؟")
    assert mid > 0
    msgs = get_messages(cid)
    assert len(msgs) == 1 and msgs[0]["role"] == "user"


def test_chat_stream_full_roundtrip():
    client = TestClient(app)
    with client.stream("POST", "/chat", json={"message": "اشرح التكامل"}) as res:
        assert res.status_code == 200
        events = []
        for line in res.iter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))
    types = [e["type"] for e in events]
    assert types == ["conversation", "delta", "delta", "delta", "delta", "done"]
    done = events[-1]
    assert done["content"] == "مرحباً بك"
    assert done["message_id"] is not None
    # الرسالتان مخزنتان
    msgs = get_messages(events[0]["id"])
    assert [m["role"] for m in msgs] == ["user", "assistant"]


def test_chat_follows_existing_conversation():
    client = TestClient(app)
    cid = create_conversation()
    with client.stream("POST", "/chat", json={"message": "تابع", "conversation_id": cid}) as res:
        lines = [line for line in res.iter_lines() if line.startswith("data: ")]
    events = [json.loads(line[6:]) for line in lines]
    assert events[0]["type"] == "delta"  # لا محادثة جديدة — تابع المحادثة
    assert get_conversation(cid) is not None
    assert len(get_messages(cid)) == 2


def test_history_and_detail_endpoints():
    client = TestClient(app)
    cid = create_conversation("محادثة للسجل")
    save_message(cid, "user", "س")
    save_message(cid, "assistant", "ج")

    res = client.get("/chat/history")
    assert res.status_code == 200
    convs = res.json()
    assert any(c["id"] == cid for c in convs)

    res = client.get(f"/chat/{cid}")
    assert res.status_code == 200
    body = res.json()
    assert len(body["messages"]) == 2

    res = client.get("/chat/999999")
    assert res.status_code == 404
