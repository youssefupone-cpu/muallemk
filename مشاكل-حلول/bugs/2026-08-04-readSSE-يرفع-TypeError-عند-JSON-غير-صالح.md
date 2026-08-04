# `readSSE` يرفع TypeError عند JSON غير صالح — كراش كامل في الـ streaming

- **التاريخ**: 2026-08-04
- **النوع**: bug (frontend / SSE / crash)
- **الوضعية**: matching
- **الحالة**: open
- **الأولوية**: high
- **الملف**: `frontend/src/lib/api.ts:191-196`

## الوصف

دالة `readSSE` في `api.ts` تستدعي `JSON.parse()` على بيانات SSE دون أي `try/catch`. إذا أرسلت الخلفية أي سطر غير JSON (مثل رسالة خطأ، heartbeat، أو تنسيق غير متوقع)، فإن `JSON.parse` يرفع `SyntaxError` ويوقف **الكامل stream** — ويعني أن المحادثة تتوقف فجأة.

## الأدلة

```typescript
// frontend/src/lib/api.ts:191-196
function readSSE(reader: ReadableStreamDefaultReader<Uint8Array>) {
  const decoder = new TextDecoder();
  // ... buffer logic ...
  buffer.split("\n").forEach((line) => {
    if (line.startsWith("data: ")) {
      const data = line.slice(6);
      const parsed = JSON.parse(data);  // ← لا try/catch!
      yield parsed;
    }
  });
}
```

**السيناريو المحتمل**:
- الـ LLM يرسل chunk جزئي أو metadata غير JSON.
- الخلفية ترسل رسالة debug/maintenance في تنسيق غير JSON.
- الـ load balancer أو proxy يقاطع الـ stream.
- النتيجة: `SyntaxError: Unexpected token...` يوقف الـ stream بالكامل.

## التأثير

- **انهار الـ streaming**: أي سطر غير JSON يوقف الـ stream بالكامل.
- **تجربة مستخدم سيئة**: المحادثة تتوقف فجأة بدون رسالة خطأ واضحة.
- **difficult debugging**: الخطأ في Console يكون `SyntaxError` داخل `readSSE` — مستخدم عادي لن يفهمه.

## الحل

```typescript
function readSSE(reader: ReadableStreamDefaultReader<Uint8Array>) {
  const decoder = new TextDecoder();
  // ...
  buffer.split("\n").forEach((line) => {
    if (line.startsWith("data: ")) {
      const data = line.slice(6);
      try {
        const parsed = JSON.parse(data);
        yield parsed;
      } catch (err) {
        console.warn("SSE line ignored — invalid JSON:", data.slice(0, 100));
        // Continue processing remaining lines — don't crash the stream
      }
    }
  });
}
```

كذلك: استخدم `Event` parsing بدلاً من `data:` prefix checking إذا كان الـ backend يستخدم `event: "message"` format — انظر دمج SSE format في `2026-08-04-تضارب-تنسيق-SSE.md`.

## المراجع

- [Server-Sent Events spec — error handling](https://html.spec.whatwg.org/multipage/server-sent-events.html)
