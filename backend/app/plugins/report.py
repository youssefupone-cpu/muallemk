"""مولّد تقارير أكاديمية عند الطلب (م9.3) — RAG + LLM + استشهادات ثم حفظ.

يُستدعى من النواة (نقاط REST في app/plugins/router.py) وليس من داخل
الإضافة نفسها: الإضافات معزولة عن النموذج و RAG، لذا التوليد يحصل هنا
وتدير الإضافة تخزين النتائج فقط في مساحتها المعزولة.
"""

from __future__ import annotations

from pydantic import BaseModel

from app.core.llm.base import BaseLLM
from app.rag.ask import build_context
from app.rag.engine import RAGEngine
from app.rag.models import RetrievedChunk
from app.rag.reranker import OllamaReranker

SYSTEM_PROMPT = """أنت معلّمك، مساعد دراسي عربي بلهجة مصرية ودودة.
اكتب تقريراً منظماً عن الموضوع: «{topic}»
اعتمد فقط على الاقتباسات المرقّمة من مادة الطالب أدناه.
- ابدأ بعنوان التقرير، ثم ملخص تنفيذي، ثم فقرات/نقاط تفصيلية.
- الاستشهاد إجباري: كل معلومة من المادة اربطها بمرجعها هكذا [رقم].
- إن لم تجد في المادة ما يكفي للموضوع، قل ذلك صراحةً دون اختلاق.

المادة (اقتباسات مرقمة):
{context}
"""


class ReportRequest(BaseModel):
    """طلب توليد تقرير — الموضوع + (اختيارياً) إعدادات النموذج وفهرس RAG."""

    topic: str
    top_k: int | None = None
    provider: str | None = None
    model: str | None = None
    api_key: str | None = None
    base_url: str | None = None


class ReportResult(BaseModel):
    """تقرير مكتمل: محتوى Markdown + قائمة المصادر الحقيقية المسترجع بها."""

    topic: str
    markdown: str
    sources: list[RetrievedChunk]


async def generate_report(
    llm: BaseLLM,
    engine: RAGEngine,
    topic: str,
    top_k: int = 8,
    reranker: OllamaReranker | None = None,
) -> ReportResult:
    """يبحث عن مادة الموضوع في RAG ثم يولّد تقريراً Markdown مع استشهادات.

    الاستشهادات "حقيقية" لأنها تُبنى من المقتطفات المسترجعة فعلياً في
    LanceDB (list of RetrievedChunk)، وتُدرج قائمة المصادر في ذيل التقرير
    بصيغة [ن] تلقائياً — حتى لو جعل النموذج أرقاماً مشوشة.
    """
    chunks = await engine.query(topic, top_k=top_k)
    if reranker and chunks:
        chunks = await reranker.rerank(topic, chunks, top_k=top_k)

    sources = [
        RetrievedChunk(
            document_id=c["document_id"],
            filename=c["filename"],
            heading=c["heading"],
            text=c["text"][:400],
            score=c["score"],
        )
        for c in chunks
    ]

    if not chunks:
        markdown = (
            f"# تقرير: {topic}\n\n"
            "لا توجد مادة مفهرسة عن هذا الموضوع بعد. ارفع كتاباً ثم اضغط «فهرسة للأسئلة»."
        )
        return ReportResult(topic=topic, markdown=markdown, sources=[])

    context = build_context(chunks)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(topic=topic, context=context)},
        {"role": "user", "content": topic},
    ]
    body_parts: list[str] = []
    async for piece in llm.stream(messages):
        body_parts.append(piece)
    body = "".join(body_parts).strip() or "تعذّر توليد النص من النموذج."

    footer = ["", "---", "## المصادر", ""]
    footer += [
        f"- [{i}] {s.filename}" + (f" — {s.heading}" if s.heading else "")
        for i, s in enumerate(sources, 1)
    ]
    markdown = "\n".join([body, *footer])
    return ReportResult(topic=topic, markdown=markdown, sources=sources)
