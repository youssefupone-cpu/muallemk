# إصلاح شامل — build + security + schema + frontend wiring

- **التاريخ**: 2026-09-05
- **النوع**: fix
- **الحالة**: fixed
- **الأولوية**: critical

## الوصف
جلسة إصلاح شاملة بعد اكتشاف أن commit `v0.2.0-rc.1` ادّعى إصلاحات لم تكتمل، وأن عدة أجزاء من التطبيق كانت مكسورة فعلياً.

## المشاكل التي أُصلحت

### Backend
1. **`pyproject.toml`**: setuptools فشل بـ "Multiple top-level packages" — أُضيف `[build-system]` + `packages.find` يستثني `plugins/`.
2. **مخطط SQLite ناقص**: جداول `books` / `book_lessons` / `quiz_bank` / `quiz_attempts` / `book_templates` / `study_activity` + ترحيل أعمدة قديمة.
3. **حد حجم الملفات (DoS)**: فحص 50MB قبل القراءة + `Image.MAX_IMAGE_PIXELS`.
4. **rate limiting** على chat / rag/ask / websearch / plugins/invoke+report.
5. **api_key من Header** `x-provider-key` في chat/rag/plugins.
6. **فرض إجراءات الإضافات** حسب النوع في `/invoke`.
7. **Docker**: non-root + host `0.0.0.0` داخل الحاوية + نسخ plugins/scripts + لا `env_file` كامل.
8. **Tavily**: يُفضَّل عند وجود مفتاح حتى لو الحزمة غير مثبتة (للاختبارات/mock).
9. **lifespan** بدل `on_event("startup")` المهجور.
10. **lancedb + pyarrow** كتبعية أساسية.

### Frontend
1. **تبعيات ناقصة**: `sonner`, `react-dropzone`, `katex`, `rehype-sanitize`.
2. **المسارات الناقصة**: `/books`, `/exam`, `/diagnostic`, `*` (404).
3. **lazy imports** مع named exports.
4. **API كتب كامل** في `lib/api.ts`.
5. **ThemeProvider + ErrorBoundary** في الجذر.
6. **theme-helmet** inline في `index.html`.
7. **DragDropUpload** متوافق مع `uploadDocument(File)`.
8. **manualChunks** function-form (Vite 8).
9. **XSS sanitize** عبر `rehype-sanitize`.
10. **npm audit**: 0 ثغرات high.
11. **TypeScript**: BeforeInstallPromptEvent، glossary types، unused imports.

## التحقق
- Backend: **92 passed**
- Frontend: **16 passed**, `tsc` clean, `vite build` OK, `npm audit` 0 high

## الملفات الرئيسية
- `backend/pyproject.toml`, `backend/app/core/db.py`, `backend/Dockerfile`
- `backend/app/{chat,documents,websearch,rag,plugins}/router.py`
- `frontend/package.json`, `frontend/src/{App,main,lib/api}.tsx?`
- `docker-compose.yml`, `frontend/nginx.conf`
