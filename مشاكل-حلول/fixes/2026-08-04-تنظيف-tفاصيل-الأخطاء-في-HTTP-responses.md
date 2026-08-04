# حل: تنظيف تفاصيل الأخطاء في استجابات HTTP (Exception Leakage)

- **التاريخ**: 2026-08-04
- **النوع**: fix
- **الوضعية**: reviewer
- **الحالة**: open
- **الأولوية**: high
- **الملفات المستهدفة**:
  - `backend/app/books/router.py:231`
  - `backend/app/websearch/router.py:32`
  - `backend/app/main.py:175`

## الوصف

ثلاثة endpoints تُرجع `str(e)` أو `str(e)[:300]` مباشرة في `detail` استجابة HTTP. هذا يسرب تفاصيل داخلية مثل: أسماء النماذج، prompt templates، مسارات ملفات، أو جزر من stack traces.

## الأمثلة

```python
# app/books/router.py:231
raise HTTPException(status_code=500, detail=str(e)[:300])  # ← يسرب أخطاء LLM

# app/websearch/router.py:32
raise HTTPException(status_code=502, detail=str(e))  # ← يسرب Tavily/SearXNG errors

# app/main.py:175
return JSONResponse(status_code=404, content={"detail": str(e)})  # ← يسرب مسارات ملفات
```

## الحل العام (Exception Sanitization)

أنشئ utility مركزي:

```python
# backend/app/core/exceptions.py
import logging
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

def safe_error_detail(error: Exception, public_message: str = "Internal server error") -> str:
    """Log full error server-side, return generic message to client."""
    logger.exception("Detailed error (sanitized from client): %s", error)
    return public_message

# في كل endpoint:
# BEFORE:
# raise HTTPException(500, detail=str(e)[:300])
# AFTER:
# raise HTTPException(502, detail=safe_error_detail(e, "Failed to analyze book"))
```

### تطبيق محدد لكل ملف:

**`app/books/router.py`:**
```python
from app.core.exceptions import safe_error_detail
# ...
except Exception as e:
    logger.warning("Book analysis failed for book_id=%s", book_id, exc_info=e)
    raise HTTPException(
        status_code=500,
        detail="Failed to analyze book. Please check the model connection and try again."
    ) from e
```

**`app/websearch/router.py`:**
```python
except Exception as e:
    logger.error("Web search failed", exc_info=e)
    raise HTTPException(
        status_code=502,
        detail="Search service temporarily unavailable. Please try again later."
    ) from e
```

**`app/main.py`:**
```python
except FileNotFoundError as e:
    logger.warning("Backup file not found: %s", e)
    return JSONResponse(status_code=404, content={"detail": "Backup not found"})
```

## المراجع

- [OWASP: Error Handling](https://cheatsheetseries.owasp.org/cheatsheets/Error_Handling_Cheat_Sheet.html)
