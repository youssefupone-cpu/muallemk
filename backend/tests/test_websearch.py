"""اختبارات م8 — البحث على الويب: كاش + ترتيب المزوّدين (بدون اتصال خارجي).

نستخدم mock للمزوّدين الفعليين ونختبر ما يخصنا: الكاش بصلاحية 24 ساعة،
تراجع Tavily → SearXNG، والفشل الواضح عند غياب كل المزوّدين.
"""

import pytest

from app.core.db import get_connection, init_db
from app.websearch.provider import WebSearchProvider

QUERY = "ما هي المشتقة؟"


def _clear_cache():
    init_db()
    with get_connection() as conn:
        conn.execute("DELETE FROM search_cache")
        conn.commit()


@pytest.fixture(autouse=True)
def clean_cache():
    _clear_cache()
    yield
    _clear_cache()


async def test_search_uses_cache_second_call(monkeypatch):
    provider = WebSearchProvider(tavily_api_key="")
    calls = {"n": 0}

    async def fake_searxng(query, max_results):
        calls["n"] += 1
        return [{"title": "t", "url": "u", "snippet": "s"}]

    monkeypatch.setattr(provider, "_search_searxng", fake_searxng)

    r1 = await provider.search(QUERY)
    r2 = await provider.search(QUERY)
    assert r1 == r2
    assert calls["n"] == 1, "الطلب الثاني يجب أن يأتي من الكاش"


async def test_tavily_preferred_over_searxng(monkeypatch):
    provider = WebSearchProvider(tavily_api_key="k")
    order: list[str] = []

    async def fake_searxng(query, max_results):
        order.append("searxng")
        raise RuntimeError("should not be called")

    async def fake_tavily(query, max_results):
        order.append("tavily")
        return [{"title": "t", "url": "u", "snippet": "s"}]

    monkeypatch.setattr(provider, "_search_searxng", fake_searxng)
    monkeypatch.setattr(provider, "_search_tavily", fake_tavily)

    results = await provider.search(QUERY)
    assert order == ["tavily"]
    assert results[0]["title"] == "t"


async def test_search_raises_when_all_providers_fail(monkeypatch):
    provider = WebSearchProvider(tavily_api_key="")

    async def fake_searxng(query, max_results):
        raise RuntimeError("searxng down")

    monkeypatch.setattr(provider, "_search_searxng", fake_searxng)

    with pytest.raises(RuntimeError):
        await provider.search(QUERY)


async def test_cache_honors_ttl(monkeypatch):
    provider = WebSearchProvider(tavily_api_key="")
    calls = {"n": 0}

    async def fake_searxng(query, max_results):
        calls["n"] += 1
        return [{"title": "t", "url": "u", "snippet": "s"}]

    monkeypatch.setattr(provider, "_search_searxng", fake_searxng)
    await provider.search(QUERY)

    # انتهاء الصلاحية يدوياً
    with get_connection() as conn:
        conn.execute("UPDATE search_cache SET created_at = datetime('now', '-2 days')")
        conn.commit()

    await provider.search(QUERY)
    assert calls["n"] == 2


# --- اختبارات مسار HTTP (بلا مزوّد خارجي) ---


def test_http_search_without_provider_returns_503():
    from fastapi.testclient import TestClient

    from app.main import app

    c = TestClient(app)
    r = c.post("/websearch/search", json={"query": "كيف تعمل الخوارزميات؟"})
    assert r.status_code == 503
    assert "TAVILY_API_KEY" in r.json()["detail"]


def test_http_search_empty_query_returns_422():
    from fastapi.testclient import TestClient

    from app.main import app

    c = TestClient(app)
    r = c.post("/websearch/search", json={"query": "  "})
    assert r.status_code == 422
