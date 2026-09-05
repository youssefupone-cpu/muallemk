# مشكلة: Chat store لا يدعم إلغاء الـ streaming (AbortController)

- **التاريخ**: 2026-08-04
- **النوع**: bug (frontend / UX / resource-leak)
- **الوضعية**: matching
- **الحالة**: fixed
- **الأولوية**: medium
- **الملف المتأثر**: `frontend/src/store/chat.ts`, `frontend/src/pages/ChatPage.tsx`

## الوصف

دالة `streamChat` تقبل `AbortSignal` — لكن `useChatStore.send()` **لم تُمرر الإشارة أبداً**. هذا يعني أن المستخدم **لا يستطيع إيقاف رد الـ LLM المستمر** — إذا بدأ الرد وكان طويلاً، يجب أن ينتظره بالكامل أو يُنقّح الصفحة.

ملاحظة: `DocumentsPage` **تستخدم AbortSignal بشكل صحيح** → `[3.6] AbortController` في `api.ts`، لكن `ChatPage` لا.

## الأدلة

```typescript
// frontend/src/store/chat.ts
export const useChatStore = create<ChatState>((set, get) => ({
  send: async (message: string, opts) => {
    const stream = await streamChat({
      ...opts,
      // ← لا AbortSignal مُمرّر!
    });
    // المعالجة تستمر حتى انتهاء الـ stream بالكامل
  },
}));

// frontend/src/pages/ChatPage.tsx:84
<button onClick={() => chatStore.send(input, opts)}>
  إرسال {/* ← لا زر إيقاف */}
</button>
```

مقابل (صحيح):
```typescript
// frontend/src/pages/DocumentsPage.tsx — استخدام صحيح للـ AbortController
const controller = new AbortController();
const result = await askFromBook({
  ...query,
  signal: controller.signal,   // ← مُمرّر!
});
```

## التأثير

- **تجربة مستخدم سيئة**: لا زر "إيقاف" للرد المستمر.
- **استهلاك وحدات نطاقية (bandwidth)**: الـ stream يستمر حتى بعد أن يغلق المستخدم الصفحة.
- **Duplicate requests**: إرسال رسالة جديدة قبل انتهاء السابقة ينشئ stream مزدوج.

## الحل

1. أضف `AbortController` إلى `chat store`:

```typescript
// frontend/src/store/chat.ts
import { AbortController } from "@remix-run/web-fetch";  // or native AbortController

export const useChatStore = create<ChatState>((set, get) => ({
  abortController: null as AbortController | null,

  send: async (message: string, opts) => {
    // إلغاء الـ stream السابق إن وُجد
    if (get().abortController) {
      get().abortController.abort();
    }

    const controller = new AbortController();
    set({ abortController: controller });

    try {
      const stream = await streamChat({
        ...opts,
        signal: controller.signal,   // ← نمرر الآن!
      });
      // ...
    } catch (err) {
      if (err.name === "AbortError") {
        console.log("Stream aborted by user");
        return;
      }
      throw err;
    }
  },

  stop: () => {
    get().abortController?.abort();
    set({ abortController: null, isStreaming: false });
  },
}));
```

2. أضف زر إيقاف في `ChatPage`:

```tsx
// frontend/src/pages/ChatPage.tsx
{isStreaming && (
  <button
    onClick={() => chatStore.stop()}
    aria-label="إيقاف الرد"
    className="stop-button"
  >
    إيقاف
  </button>
)}
```

## المراجع

- [MDN: AbortController](https://developer.mozilla.org/en-US/docs/Web/API/AbortController)
- [FastAPI: StreamingResponse with cancellation](https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse)

## سجل
- 2026-09-05: حُدّثت الحالة إلى `fixed` بعد إصلاح شامل في جلسة Arena.
