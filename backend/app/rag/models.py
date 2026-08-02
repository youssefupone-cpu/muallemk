"""نماذج RAG."""

from pydantic import BaseModel


class RAGQueryRequest(BaseModel):
    question: str
    top_k: int | None = None
    use_rerank: bool = (
        False  # م6: إعادة ترتيب اختيارية بعد الاسترجاع (tolerant — تعمل أو تعيد كما هو)
    )


class RAGAskRequest(BaseModel):
    """طلب "اسأل كتابك" — سؤال + إعدادات النموذج (من الواجهة)."""

    question: str
    top_k: int | None = None
    provider: str | None = None
    model: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    conversation_id: int | None = None


class RetrievedChunk(BaseModel):
    document_id: int
    filename: str
    heading: str = ""
    text: str
    score: float = 0.0


class RAGQueryResponse(BaseModel):
    question: str
    chunks: list[RetrievedChunk]


class RAGIndexResult(BaseModel):
    document_id: int
    indexed: int
    dim: int | None = None
