"""خدمة "اسأل كتابك" — RAG + LLM مع استشهادات (م7).

يجمع مقتطفات من LanceDB، يبني سياقاً مقيّداً، ويبث رداً عبر النموذج
مع طلب الاستشهاد بالنمط [1]، [2]... ثم يعيد قائمة المصادر مع الرد.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator

from app.core.llm.base import BaseLLM
from app.rag.engine import RAGEngine
from app.rag.models import RetrievedChunk
from app.rag.reranker import OllamaReranker

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """أنت معلّمك، مساعد دراسي عربي بلهجة مصرية ودودة.
أجب على سؤال المستخدم اعتماداً على المادة التالية فقط (اقتباسات من كتابه).
- أجب بالعربية، واضحاً ومرتباً.
- **الاستشهاد إجباري**: كل معلومة تأتي من المادة اربطها بمرجعها هكذا [رقم] —
  الرقم هو فهرس الاقتباس بين الدرجات أدناه.
- إن لم يجد السؤال إجابة في المادة، قل ذلك بصراحة دون اختلاق.

المادة (مقتطفات مرقمة):
{context}

تعليمات التنسيق: أرقام الاستشهاد هي [1], [2], ... وقد تكرر عند إعادة استخدام نفس المقتطف."""


def build_context(chunks: list[dict]) -> str:
    parts = []
    for i, c in enumerate(chunks, 1):
        heading = f" — {c['heading']}" if c["heading"] else ""
        parts.append(f"[{i}] (من: {c['filename']}{heading})\n{c['text']}")
    return "\n\n".join(parts)


async def ask_stream(
    llm: BaseLLM,
    engine: RAGEngine,
    question: str,
    top_k: int = 6,
    reranker: OllamaReranker | None = None,
) -> AsyncIterator[dict]:
    """يبث أحداث إجابة RAG: {sources} ثم {delta...} ثم {done بكل شيء}."""
    chunks = await engine.query(question, top_k=top_k)
    if reranker:
        chunks = await reranker.rerank(question, chunks, top_k=top_k)

    sources = [
        RetrievedChunk(
            document_id=c["document_id"],
            filename=c["filename"],
            heading=c["heading"],
            text=c["text"][:600],
            score=c["score"],
        )
        for c in chunks
    ]
    yield {"type": "sources", "sources": [s.model_dump() for s in sources]}

    content = question  # آخر رسالة مستخدم للنموذج
    context = build_context(chunks)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(context=context)},
        {"role": "user", "content": content},
    ]

    pieces: list[str] = []
    async for piece in llm.stream(messages):
        pieces.append(piece)
        yield {"type": "delta", "content": piece}

    full = "".join(pieces).strip() if pieces else "لم أجد ما يكفي للإجابة."
    yield {
        "type": "done",
        "content": full,
        "sources": [s.model_dump() for s in sources],
    }
