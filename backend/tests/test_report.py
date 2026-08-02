"""اختبارات م9.3 — مولّد تقارير AI (RAG + LLM + استشهادات) بدون اتصال خارجي."""

from app.plugins.report import ReportResult, generate_report
from app.rag.embeddings import FakeEmbedder
from app.rag.engine import RAGEngine

CONTENT = (
    "# مقدمة في الرياضيات\n\n"
    "المشتقة تمثل ميل المماس. التفاضل يدرس معدل التغير.\n\n"
    "# التكامل\n\n"
    "التكامل عكس التفاضل ويحسب المساحات."
)


class FakeLLM:
    """نموذج وهمي يبث تقريراً يستشهد بالمادة [1]."""

    def __init__(self, raw: str = "التقرير: المشتقة هي ميل المماس كما في المادة [1]"):
        self.raw = raw

    async def stream(self, messages):
        for ch in self.raw:
            yield ch


async def test_generate_report_builds_markdown_with_sources():
    engine = RAGEngine(uri="/tmp/rag-report-test", embedder=FakeEmbedder(dim=32))
    await engine.index_document(7, "رياضيات.md", CONTENT)

    result = await generate_report(llm=FakeLLM(), engine=engine, topic="ما التفاضل؟", top_k=2)

    assert isinstance(result, ReportResult)
    assert result.topic == "ما التفاضل؟"
    assert "[1]" in result.markdown
    assert "## المصادر" in result.markdown
    assert "رياضيات.md" in result.markdown
    assert result.sources and result.sources[0].filename == "رياضيات.md"


async def test_generate_report_no_index_returns_empty_sources():
    engine = RAGEngine(uri="/tmp/rag-report-empty", embedder=FakeEmbedder(dim=32))
    result = await generate_report(llm=FakeLLM(), engine=engine, topic="لا شيء", top_k=2)
    assert result.sources == []
    assert "لا توجد مادة مفهرسة" in result.markdown


async def test_generate_report_is_typed_result():
    engine = RAGEngine(uri="/tmp/rag-report-typed", embedder=FakeEmbedder(dim=32))
    await engine.index_document(1, "ب.md", "# رأس\n\nجسم النص")
    result = await generate_report(llm=FakeLLM(), engine=engine, topic="سؤال", top_k=1)
    assert isinstance(result, ReportResult)
    assert len(result.sources) == 1
    assert result.sources[0].filename == "ب.md"
