"""اختبارات م6 — محرك RAG مع FakeEmbedder (لا اتصال خارجي)."""

import pytest

from app.rag.embeddings import FakeEmbedder
from app.rag.engine import RAGEngine
from app.rag.normalize import normalize_arabic


@pytest.fixture
def engine(tmp_path):
    return RAGEngine(uri=tmp_path / "lancedb", embedder=FakeEmbedder(dim=32), top_k=3)


CONTENT = """# مقدمة في الرياضيات

التفاضل هو دراسة معدل التغير. المشتقة تمثل ميل المماس في كل نقطة. هذا مفهوم أساسي في التحليل.

# التكامل

التكامل هو عكس التفاضل. يستخدم لحساب المساحات والحجوم. التفاضل والتكامل مرتبطان بالمبرهنة الأساسية.
"""

CONTENT2 = "# الأحياء\n\nالخلية هي وحدة بناء الكائنات الحية. النواة تحوي المادة الوراثية DNA."


async def test_engine_index_and_query_retrieves_relevant_chunk(engine):
    eng = engine
    res = await eng.index_document(1, "رياضيات.md", CONTENT)
    assert res["indexed"] >= 2
    top = await eng.query("ما هي المشتقة في التفاضل؟", top_k=2)
    assert top, "يجب إرجاع قطع"
    assert any("مشتقه" in normalize_arabic(r["text"]) for r in top)


async def test_engine_query_returns_filenames(tmp_path):
    eng = RAGEngine(uri=tmp_path / "lancedb", embedder=FakeEmbedder(dim=32), top_k=2)
    await eng.index_document(1, "رياضيات.md", CONTENT)
    await eng.index_document(2, "أحياء.md", CONTENT2)
    top = await eng.query("ما هي وحدة بناء الكائنات؟")
    assert top[0]["filename"] == "أحياء.md"


async def test_engine_remove_document(tmp_path):
    eng = RAGEngine(uri=tmp_path / "lancedb", embedder=FakeEmbedder(dim=32), top_k=2)
    await eng.index_document(1, "a.md", CONTENT)
    assert await eng.query("مشتقة")
    await eng.remove_document(1)
    assert await eng.query("مشتقة") == []


async def test_normalize_used_in_query(tmp_path):
    # استعلام بهمزات/تشكيل يجب أن يطابق المحقون الطبيعي
    eng = RAGEngine(uri=tmp_path / "lancedb", embedder=FakeEmbedder(dim=32), top_k=2)
    await eng.index_document(1, "a.md", "الدرس يتحدث عن الهمزة في كتابة السؤال")
    top = await eng.query("ما هي الهمزه؟")
    assert top, "التشكيل لا يشترط منع البحث"
