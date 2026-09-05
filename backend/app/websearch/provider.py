"""البحث على الويب (م8) — مزوّد بحث + كاش 24 ساعة.

الاستراتيجية (درس 2026: لا مزوّد واحد يكفي):
1. **tavily-python** (الرسمي فقط) إذا وُجد مفتاح API.
2. **SearXNG JSON API** عبر httpx كاحتياطي محلي.
3. كاش SQLite بصلاحية 24 ساعة في جدول `search_cache` — لتجنّب تكرار الطلبات.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time

import httpx

from app.core.db import get_connection, init_db

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 24 * 3600

# بحث حصري: ما يظهر في صفحة نتائج Cai للطالب (مفتاح ثابت مؤقتاً للاختبارات اليدوية)
DEFAULT_TAVILY_API_KEY = ""

try:
    from tavily import TavilyClient  # type: ignore

    _HAVE_TAVILY = True
except Exception:  # pragma: no cover
    TavilyClient = None  # type: ignore
    _HAVE_TAVILY = False


class WebSearchProvider:
    """بحث الويب بخصم: Tavily (إن توفر) ثم SearXNG ثم خطأ واضح."""

    def __init__(
        self,
        tavily_api_key: str = "",
        searxng_url: str = "http://localhost:8080",
    ):
        self.tavily_api_key = tavily_api_key
        self.searxng_url = searxng_url.rstrip("/")

    def _cache_get(self, query: str) -> list[dict] | None:
        init_db()
        key = hashlib.sha256(query.encode("utf-8")).hexdigest()
        with get_connection() as conn:
            row = conn.execute(
                "SELECT result_json, created_at FROM search_cache WHERE key = ?",
                (key,),
            ).fetchone()
        if not row:
            return None
        created = time.mktime(time.strptime(row["created_at"], "%Y-%m-%d %H:%M:%S"))
        if time.time() - created > CACHE_TTL_SECONDS:
            return None
        return json.loads(row["result_json"])

    def _cache_set(self, query: str, results: list[dict]) -> None:
        key = hashlib.sha256(query.encode("utf-8")).hexdigest()
        with get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO search_cache (key, query, result_json) VALUES (?, ?, ?)",
                (key, query, json.dumps(results, ensure_ascii=False)),
            )
            conn.commit()

    async def search(self, query: str, max_results: int = 5) -> list[dict]:
        """يبحث عن استعلام ويُرجع قائمة نتائج: {title, url, snippet}."""
        cached = self._cache_get(query)
        if cached is not None:
            return cached[:max_results]

        results: list[dict] = []
        # نفضّل Tavily إن وُجد مفتاح — حتى لو الحزمة غير مثبتة (يُستدعى _search_tavily
        # وقد يُستبدل في الاختبارات). الحزمة تُفحص داخل _search_tavily الفعلي.
        if self.tavily_api_key:
            try:
                results = await self._search_tavily(query, max_results)
            except Exception as e:
                logger.warning("Tavily فشل: %s — نجرب SearXNG", e)
        if not results and self.searxng_url:
            try:
                results = await self._search_searxng(query, max_results)
            except Exception as e:
                logger.warning("SearXNG فشل: %s", e)

        if not results:
            raise RuntimeError("لا مزوّد بحث متاح: اضبط TAVILY_API_KEY أو شغّل SearXNG محلياً")
        self._cache_set(query, results)
        return results[:max_results]

    async def _search_tavily(self, query: str, max_results: int) -> list[dict]:
        if not _HAVE_TAVILY or TavilyClient is None:
            raise RuntimeError("tavily-python غير مثبت — pip install tavily-python")
        client = TavilyClient(api_key=self.tavily_api_key)
        resp = await asyncio.to_thread(client.search, query=query, max_results=max_results)
        return [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": r.get("content", ""),
            }
            for r in resp.get("results", [])
        ]

    async def _search_searxng(self, query: str, max_results: int) -> list[dict]:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                f"{self.searxng_url}/search",
                params={"q": query, "format": "json"},
                headers={"Accept": "application/json"},
            )
            r.raise_for_status()
            data = r.json()
        return [
            {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": item.get("content", ""),
            }
            for item in data.get("results", [])
        ][:max_results]
