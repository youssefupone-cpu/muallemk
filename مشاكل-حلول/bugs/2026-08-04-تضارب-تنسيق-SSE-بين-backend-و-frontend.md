# [مرتبط] تضارب تنسيق SSE بين backend EventSourceResponse و frontend readSSE

- **التاريخ**: 2026-08-04
- **النوع**: bug
- **الوضعية**: development
- **الحالة**: fixed
- **الأولوية**: critical
- **تم الإصلاح**: 2026-08-04

## الوصف

`backend/app/chat/router.py` يستخدم `EventSourceResponse` مع:
```python
yield {
    "event": "message",          # ← Event field مُرسّل
    "data": json.dumps(event),
}
```

لكن `frontend/src/lib/api.ts` (`readSSE`، السطر 191-196) يقرأ SSE يدوياً ويتوقع
تنسيق `data:` مباشرةً — **بدون`event:` field**:

```javascript
if (line.startsWith("data: ")) {
    onEvent(JSON.parse(line.slice(6)));  // ← لن يفعل أبداً!
}
```

بما أن `EventSourceResponse` يرسل:
```
event: message
data: {"type": "conversation", "id": 1}

```

فإن السطر الأول هو `event: message` — لا يبدأ بـ `data:`. والسطر الثاني `data: {...}`
لكنه يلي `event:` مباشرة (بلا سطر فارغ منفصل في بعض الحالات) — `buffer.indexOf("\n")`
قد يقسم الرسالة بشكل غير صحيح.

**نتيجة**: لا رسائل دردشة لا تصل إلى الواجهة → شات يبدو عالقاً أو لا شيء لا يُعرض.

## السبب الجذري
- `backend/app/chat/router.py:49-63`: يستخدم `event: "message"` field.
- `frontend/src/lib/api.ts:174-199`: `readSSE` لا يعالج `event:` field ولا ينظّره.
- الـ `EventSourceResponse` من `sse-starlette` يُضيف `event:` field دومًا.

## الحل / الإصلاح (خيار واحد — مقترح)

**الحل الأبسط والأكثر أماناً**: أزل `event` field من `EventSourceResponse` في backend:
```python
yield json.dumps(event, ensure_ascii=False)  # ليس "data:"، EventSourceResponse يضيفه
```
استخدم `EventSourceResponse(event_gen())` بدلاً من `yield {"event": "message", "data": ...}` —
حيث `EventSourceResponse` يقبل كائناً (dict) أو Generator يُرسل الـ data مباشرة.

أو استخدم `sse-starlette.SSE` (الـ low-level) لتحكم كامل.

## الملفات المتأثرة
- `backend/app/chat/router.py:49-65`
- `frontend/src/lib/api.ts:174-199`

## التحقق
- مناقحة SSE: شغّل الدردشة وتوجيه DevTools → Network → EventSource → تأكد من استلام `data: {"type":"conversation","id":1}`
- **الواقع المُوحّد بعد التحقق الكودي**: `backend/app/chat/router.py:46-58` يستخدم الآن
  `StreamingResponse` مع `yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"` — صريحاً بدون حقل `event:`،
  ويتطابق تماماً مع `readSSE` (`frontend/src/lib/api.ts:174-199`) الذي يقسم على `\n` ويقرأ `data:` فقط.
  التعليق في `chat/router.py:49-52` يوضح أن `event: "message"` تمّت إزالته عمداً (لمنع التفاعل غير المتوقع مع `\r\n`).
  → **الدردشة تعمل.** الخطأ كان `EventSourceResponse` (sse-starlette) المذكور في هذا الملف؛ تمّ استبداله.

## سجل
- 2026-08-04: اكتشاف في التدقيق الشامل.
- 2026-08-04: تحويل الحالة إلى `fixed` — التوافق الفعلي مُوضح في `chat/router.py:46-58` (StreamingResponse × readSSE).
