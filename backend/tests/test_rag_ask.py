"""اختبارات م7 — خدمة "اسأل كتابك" (RAG + LLM + استشهادات) بدون اتصال خارجي."""

from app.rag.ask import ask_stream, build_context
from app.rag.embeddings import FakeEmbedder
from app.rag.engine import RAGEngine

CONTENT = (
    "# مقدمة في الرياضيات\n\n"
    "المشتقة تمثل ميل المماس. التفاضل يدرس معدل التغير.\n\n"
    "# التكامل\n\n"
    "التكامل عكس التفاضل ويحسب المساحات."
)


class FakeLLM:
    """نموذج وهمي يعيد نصاً يتضمن استشهاداً [1]."""

    def __init__(self, raw: str = "المشتقة هي ميل المماس كما في المادة [1]"):
        self.raw = raw

    async def stream(self, messages):
        for ch in self.raw:
            yield ch


async def test_build_context_numbers_chunks():
    chunks = [
        {"filename": "a.md", "heading": "فصل", "text": "x"},
        {"filename": "b.md", "heading": "", "text": "y"},
    ]
    ctx = build_context(chunks)
    assert "[1]" in ctx and "a.md" in ctx
    assert "[2]" in ctx and "b.md" in ctx


async def test_ask_stream_yields_sources_then_done_with_sources():
    engine = RAGEngine(uri="/tmp/rag-ask-test", embedder=FakeEmbedder(dim=32))
    await engine.index_document(7, "رياضيات.md", CONTENT)
    events = [
        ev async for ev in ask_stream(llm=FakeLLM(), engine=engine, question="ما التفاضل؟", top_k=2)
    ]

    types = [e["type"] for e in events]
    assert "sources" in types and "done" in types and "delta" in types

    sources_ev = next(e for e in events if e["type"] == "sources")
    assert len(sources_ev["sources"]) >= 1
    assert sources_ev["sources"][0]["filename"] == "رياضيات.md"

    done_ev = next(e for e in events if e["type"] == "done")
    assert "[1]" in done_ev["content"]
    assert len(done_ev["sources"]) >= 1


async def test_ask_stream_system_prompt_contains_context():
    engine = RAGEngine(uri="/tmp/rag-ask-test-2", embedder=FakeEmbedder(dim=32))
    await engine.index_document(1, "ب.md", "# رأس\n\nجسم النص")
    captured: list = []

    class CaptureLLM(FakeLLM):
        async def stream(self, messages):
            captured.append(messages)
            for ch in self.raw:
                yield ch

    [ev async for ev in ask_stream(llm=CaptureLLM(), engine=engine, question="سؤال", top_k=1)]
    system = captured[0][0]["content"]
    assert "[1]" in system and "ب.md" in system


async def test_ask_stream_no_index_returns_empty_sources():
    engine = RAGEngine(uri="/tmp/rag-ask-empty", embedder=FakeEmbedder(dim=32))
    events = [
        ev async for ev in ask_stream(llm=FakeLLM(), engine=engine, question="لا شيء", top_k=2)
    ]
    sources_ev = next(e for e in events if e["type"] == "sources")
    assert sources_ev["sources"] == []
