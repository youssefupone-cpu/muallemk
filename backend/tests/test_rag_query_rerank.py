"""اختبارات م6 — rerank اختياري في نقطة /rag/query.

تكفي لاختبار الواجهة (يتقبّل الحقل ويمرّر عبر النواة بلا فشل) دون اتصال
خارجي: نستبدل الـ Reranker الحقيقي بآخر محلي يعيد ترتيباً محاكياً، مثلما
تستبدل اختبارات أخرى محرّك RAG بالمحرك على FakeEmbedder.
"""

import asyncio

from fastapi.testclient import TestClient

from app.main import app
from app.rag.embeddings import FakeEmbedder
from app.rag.engine import RAGEngine


class DummyReranker:
    """يعيد نفس العناصر — لكن يثبت أن `rerank` استُدعي (مماثل للفشل اللين عند غياب Ollama)."""

    def __init__(self, *a, **kw):
        self.called = False

    async def rerank(self, query: str, items: list[dict], top_k: int | None = None):
        self.called = True
        return items[: (top_k or len(items))]


def test_query_accepts_use_rerank_without_error(monkeypatch, tmp_path):
    import app.rag.router as rag_router

    engine = RAGEngine(uri=str(tmp_path / "idx"), embedder=FakeEmbedder(dim=32))
    asyncio.run(
        engine.index_document(1, "م.md", "# فصل\n\nنص مقتطف للاختبار الذي يبحث عن الاسترجاع")
    )
    monkeypatch.setattr(rag_router, "get_engine", lambda: engine)
    fake = DummyReranker()
    monkeypatch.setattr(rag_router, "OllamaReranker", lambda *a, **kw: fake)

    c = TestClient(app)
    r = c.post("/rag/query", json={"question": "الاسترجاع", "use_rerank": True})
    assert r.status_code == 200
    assert fake.called, "يجب أن يُستدعى الـ Reranker عند طلب use_rerank"
    assert len(r.json()["chunks"]) >= 1
    assert r.json()["chunks"][0]["filename"] == "م.md"


def test_query_without_rerank_skips_reranker(monkeypatch, tmp_path):
    import app.rag.router as rag_router

    engine = RAGEngine(uri=str(tmp_path / "idx2"), embedder=FakeEmbedder(dim=32))
    asyncio.run(engine.index_document(2, "ب.md", "# رأس\n\nمحتوى قابل للبحث"))
    monkeypatch.setattr(rag_router, "get_engine", lambda: engine)
    fake = DummyReranker()
    monkeypatch.setattr(rag_router, "OllamaReranker", lambda *a, **kw: fake)

    c = TestClient(app)
    r = c.post("/rag/query", json={"question": "محتوى", "use_rerank": False})
    assert r.status_code == 200
    assert fake.called is False
