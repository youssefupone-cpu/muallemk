# [حرج] خطأ TypeError: top_k=None في RAG ask عندما يرسله الواجهة بدون قيمة

- **التاريخ**: 2026-08-04
- **النوع**: bug
- **الوضعية**: development
- **الحالة**: fixed
- **الأولوية**: critical
- **تم الإصلاح**: 2026-08-04

## الوصف

عند طلب "اسأل كتابك" عبر الواجهة (DocumentsPage → `streamAsk`)، الـ `Frontend` لا يرسل
`top_k` في الـ body. الـ backend يقبله كـ `None` (القيمة الافتراضية في `RAGAskRequest`).

ثم يُمرر `None` إلى `ask_stream(top_k=None)` → السطر 108 في `rag/ask.py`:
```python
ranked_lists = [await engine.query(q, top_k=top_k * 2) for q in queries]
```
→ `TypeError: unsupported operand type(s) for *: 'NoneType' and 'int'`

**هذا يمنع "اسأل كتابك" بالكلية — كل طلب RAG ask يفشل 500.**

## الخطوات لإعادة الإنتاج
1. رفع مستند في DocumentsPage.
2. فهرسه بنقر "فهرسة للأسئلة".
3. اكتب سؤالاً في "اسأل كتابك" واضغط.
4. استلم `500 Internal Server Error` + `TypeError` في سجلات uvicorn.

## السبب الجذري
- `rag/models.py:18`: `top_k: int | None = Field(default=None, ge=1, le=20)`
- `rag/ask.py:108`: `top_k * 2` — لا فحص None
- `rag/router.py:131`: يمرر `top_k=req.top_k` مباشرةً = `None`
- `frontend/src/lib/api.ts:153-168`: لا يرسل `top_k` في الـ body

## الحل / الإصلاح
في `backend/app/rag/ask.py`، في بداية `ask_stream`، أضف coalescing:
```python
top_k = top_k or get_settings().rag_top_k  # fallback للإعداد العام (افتراضياً 8)
```
هذا يضمن أن `None` يتحول إلى القيمة الافتراضية من الإعدادات (8) بدلاً من الانهيار.

بديلاً: في `rag/router.py:130-137`، استخدم:
```python
top_k=req.top_k or settings.rag_top_k,
```

## الملفات المتأثرة
- `backend/app/rag/ask.py:108`
- `backend/app/rag/router.py:131`
- `backend/app/rag/models.py:18`
- `frontend/src/lib/api.ts:153-168` (اختياري — يمكن إرسال top_k صريح)

## التحقق
- رفع `test_book.txt` → فهرسة → سؤال → استجابة SSE تحتوي `sources` + `delta` + `done`
- **الواقع المُوحّد بعد التحقق الكودي**: `rag/ask.py:101-108` يحتوي النسخ الاحتياطي:
  `top_k = top_k or settings.rag_top_k` (افتراضياً 8) قبل `top_k * 2` في السطر 114،
  و`rag/router.py:124-125` يحسب `effective_top_k = req.top_k or settings.rag_top_k`.
  → لا يحدث `TypeError` عندما ترسله الواجهة `top_k` بدون قيمة. `streamAsk` في
  `frontend/src/lib/api.ts:146-171` لا يرسل `top_k` (صحيح، يستخدم الافتراضي).
  → **RAG ask يعمل.**

## سجل
- 2026-08-04: اكتشاف في التدقيق الشامل.
- 2026-08-04: تحويل الحالة إلى `fixed` — التراجع الآمن موجود في `rag/ask.py:101-108` و`rag/router.py:124-125`؛ الاختبارات 115 ناجحة تشمل `test_rag_ask.py`.
