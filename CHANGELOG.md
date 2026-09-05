# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/)
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.2.0] — 2026-09-05

### Fixed (hardening pass)
- Backend install: setuptools package discovery (`app` only) — `pip install -e .` works again.
- SQLite schema: full books/quiz/activity tables + safe column migrations.
- Upload DoS: 50MB read cap + image pixel limit; documents upload rate-limited.
- Rate limits on chat, RAG ask, websearch, plugin invoke/report.
- API keys via `x-provider-key` header on LLM routes; plugin invoke action allowlist.
- Docker: non-root users, resource limits, selective env vars (no full `.env` dump), backend binds `0.0.0.0` in-container.
- Frontend: missing deps (`sonner`, `react-dropzone`, `katex`, `rehype-sanitize`), books API client, routes (`/books` `/exam` `/diagnostic` 404), ThemeProvider/ErrorBoundary, PWA theme bootstrap, XSS sanitize, Vite 8 manualChunks, npm audit clean.

## [0.2.0-rc.1] — 2026-08-04

### Added
- **PWA دون اتصال**: `vite-plugin-pwa` + Service Worker يخزن الكتب والنماذج (P4-237).
- **مكوّن رفع سحب-وأفلات**: `DragDropUpload` مع التحقق من الحجم/النوع والأثر (P4-238).
- **تبديل نمط بلا FOUC**: `ThemeProvider` + `theme-helmet.js` (pre-render script) (P4-239).
- **معادلات رياضية**: `react-katex` + `remark-math` + `rehype-katex` عبر `MathRenderer` (P3-115/P4-242).
- **مخطط أسبوعي**: `StudyChart` على Recharts 2.15.4 (P4-240).
- **إشعارات**: `sonner` يحل محل Toast المهجور (P3-169/P4-246).
- **نقطة نهاية `/api/llm/status`**: قوائم الموديلات المتوفرة من Ollama + OpenAI (P3-102).
- **خطأ غير متوقع + صفحة 404**: `ErrorBoundary` + راوت `NotFoundPage` (P3-85).
- **شخصية «معلّمك» المصرية**: رسالة نظام افتراضية في ChatPage (P3-101).
- **مكوّن SSE المشترك**: `readSSE` يقلّل التكرار بين `streamChat`/`streamAsk` (P3-82).
- اختبارات E2E: Playwright `rag-flow.spec.ts` (P4-204).
- اختبارات واجهة: 7 اختبارات Vitest (store + readSSE + MathRenderer + ThemeToggle).
- توثيق: `ARCHITECTURE.md`، `SECURITY.md`.

### Changed
- `DocumentsPage` يستخدم الآن `DragDropUpload` بدلاً من `<input type="file">`.
- `AppLayout` يدعم الوضع الليلي + زر تبديل المظهر.
- CI: أضيفت `npm audit` + وظيفة E2E بـ Playwright.

### Fixed
- تعليق مضلل في `settings.ts` حول إرسال `api_key` — موحّح وموحد (P3-80).
- حذف كود Vite النموذجي الميت (`App.css`، أصول-hero) (P3-81).
- توحيد `get_lesson()` لفك JSON strings→arrays تلقائياً (P2-91).

## [0.1.0] — 2026-07-15

### Added
- هيكل MVP: FastAPI backend + Vite React frontend.
- RAG hybrid (SQLite FTS5 + LanceDB embeddings).
- ChatPage مع دعم النوافذ المحادثة.
- مكتبة الكتب + محاكاة امتحان 2026.
- إضافات plugins (study-table, grades-tool).
- OCR عبر tesseract + bilingual (ar/en).
