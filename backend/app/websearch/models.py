"""نماذج البحث على الويب."""

from pydantic import BaseModel


class WebSearchRequest(BaseModel):
    query: str
    max_results: int = 5


class SearchResult(BaseModel):
    title: str = ""
    url: str = ""
    snippet: str = ""


class WebSearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
