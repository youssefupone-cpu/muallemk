"""مسارات RAG — استرجاع مقتطفات من المستندات المفهرسة."""

import json

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse
from httpx import HTTPStatusError, RequestError

from app.chat.service import (
    create_conversation,
    get_conversation,
    save_message,
    save_message_sources,
)
from app.core.config import get_settings
from app.core.db import get_connection
from app.core.llm.factory import get_llm
from app.core.rate_limit import rate_limiter
from app.rag.ask import ask_stream
from app.rag.embeddings import OllamaEmbedder
from app.rag.engine import RAGEngine
from app.rag.models import (
    RAGAskRequest,
    RAGIndexResult,
    RAGQueryRequest,
    RAGQueryResponse,
    RetrievedChunk,
)
from app.rag.reranker import OllamaReranker

router = APIRouter(prefix="/rag", tags=["rag"])

_engine: RAGEngine | None = None


def get_engine() -> RAGEngine:
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = RAGEngine(
            uri=settings.data_dir + "/lancedb",
            embedder=OllamaEmbedder(
                base_url=settings.ollama_base_url, model=settings.rag_embed_model
            ),
        )
    return _engine


def _embedding_error(detail: str) -> HTTPException:
    base = get_settings().ollama_base_url
    return HTTPException(
        status_code=503,
        detail=f"تعذّر استدعاء محرك التضمين (Ollama على {base}؟). تفاصيل: {detail}",
    )


_EMBED_EXCEPTIONS = (HTTPStatusError, RequestError, OSError, RuntimeError)


@router.post("/index/{doc_id}", response_model=RAGIndexResult)
async def index_document(doc_id: int):
    """يفهرس مستنداً مخزناً في SQLite ليكون قابلًا لـ"اسأل كتابك"."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, filename, content FROM documents WHERE id = ?", (doc_id,)
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="المستند غير موجود")
    try:
        res = await get_engine().index_document(row["id"], row["filename"], row["content"])
    except _EMBED_EXCEPTIONS as e:
        raise _embedding_error(str(e)) from e
    return RAGIndexResult(**res)


@router.post("/query", response_model=RAGQueryResponse)
async def query(req: RAGQueryRequest):
    """يبحث في المستندات المفهرسة ويُرجع المقتطفات (بدون LLM — م6).

    عند طلب `use_rerank: true` تمر النتائج عبر Reranker لإعادة الترتيب؛
    وإن تعذّر (كما بلا تضمين) تُرجع النتائج الأصلية بلا فشل.
    """
    if not req.question.strip():
        raise HTTPException(status_code=422, detail="السؤال فارغ")
    try:
        chunks = await get_engine().query(req.question, top_k=req.top_k)
        if req.use_rerank and chunks:
            reranker = OllamaReranker(base_url=get_settings().ollama_base_url)
            chunks = await reranker.rerank(req.question, chunks, top_k=req.top_k)
    except _EMBED_EXCEPTIONS as e:
        raise _embedding_error(str(e)) from e
    if not chunks:
        raise HTTPException(
            status_code=404,
            detail="لا نتائج — لا مستندات مفهرسة بعد. ارفع كتاباً ثم اضغط «فهرسة للأسئلة».",
        )
    return RAGQueryResponse(
        question=req.question,
        chunks=[RetrievedChunk(**c) for c in chunks],
    )


@router.delete("/document/{doc_id}")
async def drop_document(doc_id: int):
    await get_engine().remove_document(doc_id)
    return {"deleted": doc_id}


@router.post("/ask")
async def ask(
    req: RAGAskRequest,
    x_provider_key: str | None = Header(default=None, alias="x-provider-key"),
    _: None = Depends(rate_limiter(15)),  # استهلاك LLM + تضمين — حد 15/دقيقة
):
    """ "اسأل كتابك": سؤال + مقتطفات مفهرسة + رد بثي مع استشهادات (م7)."""
    if not req.question.strip():
        raise HTTPException(status_code=422, detail="السؤال فارغ")

    settings = get_settings()
    api_key = x_provider_key or req.api_key
    llm = get_llm(
        provider=req.provider or settings.default_provider,
        model=req.model or settings.default_model,
        api_key=api_key,
        base_url=req.base_url or settings.ollama_base_url,
    )
    reranker = OllamaReranker(base_url=settings.ollama_base_url)

    async def events():
        conv_id = req.conversation_id
        if conv_id is None or get_conversation(conv_id) is None:
            conv_id = create_conversation(title=req.question[:40])
            ev = json.dumps({"type": "conversation", "id": conv_id}, ensure_ascii=False)
            yield f"data: {ev}\n\n"

        save_message(conv_id, "user", req.question)
        try:
            async for ev in ask_stream(
                llm=llm,
                engine=get_engine(),
                question=req.question,
                top_k=req.top_k,
                reranker=reranker,
            ):
                if ev["type"] == "done":
                    message_id = save_message(conv_id, "assistant", ev["content"])
                    save_message_sources(message_id, ev["sources"])
                    ev["message_id"] = message_id
                    ev["conversation_id"] = conv_id
                yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
        except (HTTPStatusError, RequestError, OSError) as e:
            err = json.dumps(
                {"type": "error", "detail": f"تعذّر التضمين/الاستدعاء (Ollama؟): {e}"},
                ensure_ascii=False,
            )
            yield f"data: {err}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")
