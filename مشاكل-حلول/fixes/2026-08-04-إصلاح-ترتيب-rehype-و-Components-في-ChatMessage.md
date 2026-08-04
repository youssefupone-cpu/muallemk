# إصلاح: ترتيب rehype وـ `as Components` في ChatMessage

**التاريخ**: 2026-08-04
**الملف**: `frontend/src/components/chat/ChatMessage.tsx`
**الحالة**: ✅ fixed
**النوع**: build / type-safety / i18n(رياضيات)

## السبب (Root Cause)
عند إضافة KaTeX إلى `ChatMessage` (كان `ReactMarkdown` عادياً بلا رياضيات)، تمّ تطبيق اختيارين تكتيكيان بهما فجوتان:

1. **ترتيب rehype plugins خاطئ**: `rehypePlugins={[rehypeKatex, rehypeSanitize]}`. `rehype-katex` يُنتج HTML من الرياضيات (عناصر `.katex`، وسم `<math>`، `style`/سمات)، ثم `rehype-sanitize` (بالمخطط الافتراضي) يمر على النتيجة و**يزيلّها** لأنها تحتوي عقد/sمات غير مسموحة. النتيجة: `.katex` اختفى في الـ runtime (والتحقق برمجياً فشل — `container.querySelector(".katex")` كان null)، مع خسارة حماية المعادلات.
   - `MathRenderer.test.tsx` كان **يجتاز** لأن `MathRenderer` لا يستخدم `rehypeSanitize` (لا حماية XSS).

2. **خطأ تعريف TypeScript**: `inlineMath`/`math` override لستا في نوع `Components` الافتراضي الخاص بـ `react-markdown` (هما من `remark-math`، تُعرّف خارجياً). بدون الـ cast `as Components`، `tsc -b` يفشل:
   ```
   src/components/chat/ChatMessage.tsx(38,15): error TS2353: Object literal may only specify known properties, and 'inlineMath' does not exist in type 'Components'.
   ```
   - هذا الخطأ **مسبق** (كان موجوداً في الـ working tree قبل جلسة التطوير — عند HEAD لم يكن هناك ReactMarkdown على الإطلاق). المخطط `DEVELOPMENT_PLAN` ادّعى خطأ أن `tsc -b` «exit 0» — **مُصحّح الآن**.

## الحل
- تبديل ترتيب الـ rehype plugins إلى `[rehypeSanitize, rehypeKatex]`:
  - `rehype-sanitize` يُنقّي HTML المستند من Markdown أولاً (يزيل `<script>`، `javascript:` URLs، `onerror`، …) — الحماية XSS تبقى.
  - `rehype-katex` يُنتج HTML الرياضي **بعد الـ sanitization**، لذا مخرجات KaTeX (.katex، `<math>`) لا تُقَرّص من قبل المخطط.
- إضافة `import type { Components } from "react-markdown"` وتطبيق cast `as Components` على كائن `components` (نفس نمط `MathRenderer.tsx` الذي يوضح تعليقه السبب).

## الإثبات (أرضي)
- `npx tsc -b` → `TSC_EXIT=0` (كان `TSC_EXIT=2`).
- `npx vitest run src/components/chat/ChatMessage.test.tsx` → 2 passed (math يرجع `.katex`؛ XSS يُزيل `<script>`/`onerror`/`javascript:` كليهما).
- `npx prettier --check` → All files ✅ · `npx oxlint` → 0 errors ✅ · `npm run build` → `✓ built in 3.41s` ✅.
- Backend غير متزامن: `ruff format --check` 65 ملف ✅ · `ruff check` passed ✅ · `pytest -q` → **115 passed** فوراً.

## الآلية المرجعية
- توثيق `rehype-sanitize` + `rehype-katex`: الترتيب الصحيح هو sanitize → katex (katex آخر لضمان بقاء مخرجات الرياضيات). انظر `frontend/src/components/MathRenderer.tsx:11-24` (`as Components`).
