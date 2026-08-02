"""اختبارات إصلاح bug — نموذج التضمين غير المثبت يعطي رسالة واضحة (بدل 404 غامض).

السيناريو: Ollama مثبت لكن النموذج المطلوب غير موجود (404 من /api/embed).
"""

import httpx
import pytest

from app.rag.embeddings import OllamaEmbedder


@pytest.mark.asyncio
async def test_ollama_embedder_missing_model_raises_clear_message():
    """Ollama يعيد 404 لنموذج غير مثبت → يجب RuntimeError عربية واضحة مع اسم النموذج."""

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/embed"
        import json as _json

        assert _json.loads(request.content)["model"] == "bge-m3"
        return httpx.Response(404, json={"error": "model 'bge-m3' not found"})

    transport = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    embedder = OllamaEmbedder(model="bge-m3")

    with pytest.raises(RuntimeError) as exc:
        await embedder.embed(["نص تجريبي"], client=transport)
    msg = str(exc.value)
    assert "bge-m3" in msg
    assert "غير مثبت" in msg
    assert "rag_embed_model" in msg


@pytest.mark.asyncio
async def test_ollama_embedder_success_path():
    """نموذج مثبت → يعيد التضمين بشكل طبيعي."""

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/embed"
        return httpx.Response(200, json={"embeddings": [[0.1, 0.2, 0.3]]})

    transport = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    embedder = OllamaEmbedder(model="nomic-embed-text")
    out = await embedder.embed(["نص تجريبي"], client=transport)
    assert len(out) == 1
    assert len(out[0]) == 3
    assert embedder.dim == 3
