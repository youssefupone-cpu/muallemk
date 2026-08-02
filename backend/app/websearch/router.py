"""مسارات البحث على الويب (م8)."""

from fastapi import APIRouter, HTTPException

from app.core.config import get_settings
from app.websearch.models import WebSearchRequest, WebSearchResponse
from app.websearch.provider import WebSearchProvider

router = APIRouter(prefix="/websearch", tags=["websearch"])

_provider: WebSearchProvider | None = None


def get_provider() -> WebSearchProvider:
    global _provider
    if _provider is None:
        settings = get_settings()
        _provider = WebSearchProvider(
            tavily_api_key=settings.tavily_api_key,
            searxng_url=settings.searxng_url,
        )
    return _provider


@router.post("/search", response_model=WebSearchResponse)
async def search(req: WebSearchRequest):
    if not req.query.strip():
        raise HTTPException(status_code=422, detail="الاستعلام فارغ")
    try:
        results = await get_provider().search(req.query, max_results=req.max_results)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    return WebSearchResponse(query=req.query, results=results)
