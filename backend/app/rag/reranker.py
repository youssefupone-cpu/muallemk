"""طبقة إعادة الترتيب (Reranker) — تحسين الجودة بعد الاسترجاع.

- `OllamaReranker`: يحاول استخدام bge-reranker-v2-m3 عبر Ollama /api/rerank
  (المتوفر في إصدارات Ollama الحديثة) — وإن تعذّر يعيد النتيجة كما هي.
- اختياري بالكامل: RAG يعمل بدونه.
"""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)


class OllamaReranker:
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "bge-reranker-v2-m3"):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._available: bool | None = None

    async def rerank(self, query: str, items: list[dict], top_k: int | None = None) -> list[dict]:
        """يعيد ترتيب عناصر الاسترجاع حسب النتيجة — أو العناصر الأصلية عند الفشل."""
        if not items:
            return items
        if self._available is False:
            return items
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post(
                    f"{self.base_url}/api/rerank",
                    json={
                        "model": self.model,
                        "query": query,
                        "documents": [i["text"] for i in items],
                    },
                )
                if r.status_code != 200:
                    self._available = False
                    return items
                data = r.json()
                order = sorted(data.get("results", []), key=lambda x: x.get("index", 0))
                ranked = [items[int(h["index"])] for h in order]
                k = top_k or len(ranked)
                return ranked[:k]
        except Exception:
            logger.debug("Reranker غير متاح — استخدام نتائج الاسترجاع الأصلية")
            self._available = False
            return items
