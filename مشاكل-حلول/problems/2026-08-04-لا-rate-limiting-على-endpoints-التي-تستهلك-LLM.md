# مشكلة: لا rate limiting على endpoints التي تستهلك LLM (Tavily، Ollama)

- **التاريخ**: 2026-08-04
- **النوع**: problem (security / abuse / cost-control)
- **الوضعية**: reviewer
- **الحالة**: open
- **الأولوية**: high
- **الملفات المتأثرة**:
  - `backend/app/books/router.py:172` (`/books/{book_id}/analyze`)
  - `backend/app/books/router.py:186` (`/books/{book_id}/generate`)
  - `backend/app/books/router.py:210` (`/books/lessons/{lesson_id}/regenerate`)
  - `backend/app/websearch/router.py:25` (`/websearch/search`)

## الوصف

الـ endpoints التالية التي تستهلك LLM (Ollama) أو APIs خارجية (Tavily) **لا تملك أي rate limiting**. هذا يعني أن أي عميل يمكنه إرسال طلبات لا نهائية — خاصةً إذا كانت `access_token` مُعرف. هذا يؤدي إلى:

- **إهدار رصيد API** (OpenAI/Tavily tokens).
- **استنزاف CPU/GPU** على Ollama.
- **رفع تكاليف التشغيل** بلا حد.
- **نقطة DoS** واضحة.

## الأدلة

```python
# app/books/router.py — لا أي rate_limiter dependency
@router.post("/{book_id}/analyze", response_model=BookAnalysis)
async def analyze_book(book_id: int, body: AnalyzeBookRequest = Depends()):
    result = await analyze_service.analyze(...)  # ← استدعاء LLM مباشرة، بلا حد
    return result

@router.post("/{book_id}/generate")
async def generate_lesson(...):
    return await lesson_service.generate(...)     # ← استدعاء LLM مباشرة، بلا حد

# app/websearch/router.py
@router.post("/search")
async def search_web(...):
    return await websearch_service.search(...)      # ← استدعاء Tavily مباشرة، بلا حد
```

ملاحظة: `app/core/rate_limit.py` موجود ومُطبق على `/upload`، `/chat/reply`، `/rag/ask/stream`، `/plugins/invoke` — لكنه **مفقود تماماً** على endpoints LLM.

## الحل

أضف rate limiting مبني على `Depends(rate_limiter(...))` — استخدم نفس الآلية الموجودة في `rate_limit.py`:

```python
from app.core.rate_limit import rate_limiter

# إعدادات مخصصة حسب التكلفة
LLM_ANALYZE_LIMIT = rate_limiter(
    requests=3,       # 3 طلبات
    window_seconds=60,  # لكل دقيقة — تكلفة عالية
    key_func=lambda: "llm_analyze"  # shared للكل، أو per-user إذا كان auth
)

@router.post("/{book_id}/analyze", response_model=BookAnalysis)
async def analyze_book(
    book_id: int,
    body: AnalyzeBookRequest = Depends(),
    _: None = Depends(LLM_ANALYZE_LIMIT),  # ← rate limit
):
    result = await analyze_service.analyze(...)
    return result
```

وقدرتها:
| Endpoint | Limit المقترح | السبب |
|---|---|---|
| `/books/{id}/analyze` | 3/دقيقة | استدعاء LLM مكلف (full book analysis) |
| `/books/{id}/generate` | 10/دقيقة | توليد درس واحد |
| `/books/lessons/{id}/regenerate` | 10/دقيقة | تجديد درس |
| `/websearch/search` | 20/دقيقة | استدعاء Tavily API |

## المراجع

- [FastAPI + SlowAPI rate limiting patterns](https://slowapi.readthedocs.io/)
- [OWASP: API5:2023 Broken Function Level Authorization](https://owasp.org/API-Security/editions/2023/en/0xa5-broken-function-level-authorization/)
