# حل: نقل `api_key` من POST body إلى Header

- **التاريخ**: 2026-08-04
- **النوع**: fix
- **الوضعية**: reviewer
- **الحالة**: open
- **الأولوية**: high
- **الملفات المستهدفة**: `frontend/src/lib/api.ts`, `backend/app/rag/router.py`, `backend/app/chat/router.py`, `backend/app/plugins/report.py`
- **المشكلة المرتبطة**: API keys في POST body

## الوصف

`api_key` يُرسل في `JSON body` للـ POST requests. هذا يجعله **مرئياً بوضوح في Network Tab** وproxy logs. الحل المؤقت هو نقله إلى **header** — يجعله أقل وضوحاً ويدمج مع نمط HTTP المعياري.

## الحل

### Frontend (api.ts):

```typescript
// BEFORE:
export async function streamAsk(opts: {
  provider: string;
  model: string;
  api_key?: string;        // ← في الـ body
  ...
}) {
  const res = await fetch(`${base}/rag/ask/stream`, {
    method: "POST",
    body: JSON.stringify(opts),     // ← api_key داخل JSON body
  });
}

// AFTER:
export async function streamAsk(opts: {
  provider: string;
  model: string;
  api_key?: string;
  ...
}) {
  const { api_key, ...body } = opts;  // ← استخراج api_key من الـ body
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (api_key) {
    headers["X-Provider-Key"] = api_key;   // ← نقل إلى header
  }
  const res = await fetch(`${base}/rag/ask/stream`, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });
}
```

طبّق نفس النمط على:
- `streamAsk` → `X-Provider-Key`
- `streamChat` → `X-Provider-Key`
- `askFromBook` → `X-Provider-Key`

### Backend (router.py):

```python
# app/chat/router.py:17
from fastapi import Header, HTTPException

@router.post("/reply")
async def chat_reply(
  body: ChatRequest,
  x_provider_key: str | None = Header(default=None, alias="X-Provider-Key"),
):
  # استخدم x_provider_key بدلاً من body.api_key
  request_with_key = ChatRequestWithKey(**body.dict(), api_key=x_provider_key)
  ...
```

## الملاحظة الأمنية

هذه **خطوة مؤقتة** فقط. الحلول المثلى لا تزال تتطلب [Backend-as-Proxy للمفاتيح](/مشاكل-حلول/bugs/2026-08-04-api-keys-من-الواجهة-الأمامية-للكخادم.md) — لكن نقل api_key من body إلى header يقلل بشكل كبير من مخاطر التسريب.

## المراجع

- [MDN: X-Custom-Headers vs Authorization](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/X-Custom-Header)
- [OWASP: API Keys should not be in request body](https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html)
