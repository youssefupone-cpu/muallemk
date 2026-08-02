"""طبقة التضمين (Embeddings) لمحرك RAG.

- `OllamaEmbedder`: تضمين عبر Ollama المحلي (POST /api/embed). النموذج الافتراضي
  `nomic-embed-text` — نموذج embeddings شائع ومتوفر افتراضياً؛ يمكن تجاوزه بمتغير
  بيئة `rag_embed_model` أو بمعامل المُنشئ.
- `FakeEmbedder`: تضمين حتمي تجريبي للاختبارات دون اتصال.
"""

from __future__ import annotations

import hashlib
import logging
from abc import ABC, abstractmethod

import httpx

logger = logging.getLogger(__name__)


class BaseEmbedder(ABC):
    dim: int

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """يعيد متجهات التضمين لكل نص."""


class OllamaEmbedder(BaseEmbedder):
    """تضمين عبر Ollama (nomic-embed-text افتراضياً أو أي نموذج embeddings مثبت)."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "nomic-embed-text",
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def embed(
        self, texts: list[str], client: httpx.AsyncClient | None = None
    ) -> list[list[float]]:
        """يعيد متجهات التضمين لكل نص؛ `client` اختياري للحقن في الاختبارات."""
        out: list[list[float]] = []
        owns_client = client is None
        client = client or httpx.AsyncClient(timeout=120)
        try:
            for t in texts:
                r = await client.post(
                    f"{self.base_url}/api/embed",
                    json={"model": self.model, "input": t},
                )
                if r.status_code == 404:
                    raise RuntimeError(
                        f"نموذج التضمين «{self.model}» غير مثبت في Ollama على "
                        f"{self.base_url} — تأكد منه بـ: ollama pull {self.model} "
                        "أو غيّر rag_embed_model عبر .env"
                    ) from None
                r.raise_for_status()
                data = r.json()
                out.append(data["embeddings"][0])
        finally:
            if owns_client:
                await client.aclose()
        if out:
            self.dim = len(out[0])
        return out


class FakeEmbedder(BaseEmbedder):
    """تضمين حتمي مبني على حقيبة الكلمات (word-bag) — للاختبارات.

    التشابه ~ يدل على تشابه المفردات العربية بعد التطبيع، فيكفي لاختبار
    الاسترجاع دون اتصال بنموذج حقيقي. الأبعاد: بعد لكل كلمة معلولة.
    """

    def __init__(self, dim: int = 256):
        self.dim = dim

    def _norm_ar(self, text: str) -> str:
        from app.rag.normalize import normalize_arabic

        return normalize_arabic(text)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        import math

        out: list[list[float]] = []
        for t in texts:
            words = [w for w in self._norm_ar(t).split() if len(w) >= 2]
            vec = [0.0] * self.dim
            for w in words:
                idx = int(hashlib.sha256(w.encode("utf-8")).digest()[0])
                vec[idx % self.dim] += 1.0
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
            out.append([v / norm for v in vec])
        return out
