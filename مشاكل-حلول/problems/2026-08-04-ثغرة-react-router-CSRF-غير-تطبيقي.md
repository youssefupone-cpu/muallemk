# 2026-08-04 — react-router CSRF advisory (GHSA-qwww-vcr4-c8h2)

- **التاريخ**: 2026-08-04
- **النوع**: problem (security — تقييم applicability)
- **الوضعية**: reviewer/development
- **الحالة**: closed (غير تطبيقي — مقبول)

## الوصف
`npm audit` يُبلّغ عن ثغرة بجانبية "high" في:
- `react-router` (>= 7.12.0) و `react-router-dom` (>= 7.12.0) — المشروع يستخدم `react-router-dom ^7.18.2`.

## التحليل الموثّق (بدون تخمين)
مصدر: [GHSA-qwww-vcr4-c8h2](https://github.com/advisories/GHSA-qwww-vcr4-c8h2) (مُسترجع 2026-08-04):
- **الإصدارات المتأثرة**: `>= 7.12.0, < 8.3.0`.
- **الإصدار المُصلّح**: `8.3.0` (هَبْط رئيسي 7→8 — كسر قد يُعيد تشكيل التوجيه).
- **npm audit fix --force** يُقترح خفضاً إلى `react-router-dom@7.11.0` — هذا **تصرف غير دقيق** من محلّل npm (7.11.0 خارج النطاق المتأثر لكنه إصداراً أقدم/مخفّضاً، وليس "شيئاً مُصلحاً"). الإصدار الفعلي المُصلِّح هو 8.3.0.

**التوافق: ليس مُطبقاً على هذا المشروع.** نص الوصف الكامل للـ advisory ينص:
> «هذا يؤثر على تطبيقك فقط إذا كنت تستخدم **unstable RSC APIs**».

المشروع — Vite + React 19 + React Router DOM v7 (عميل فقط) — **لا يستخدم RSC/React Server Components أبداً** (لا server components، لا `react-dom/server` RSC entry، PWA SPA). لذا فإن تدفق CSRF الموصوف لا ينطبق.

## القرار
- **عدم التغيير الآن**: إجبار `npm audit fix --force` يُخفض react-router-dom إلى 7.11.0 (أو يرفعه إلى 8.3.0 بكسر) — كلاهما يهدد التوجيه العامل (9 مسارات في `App.tsx`).
- مقبول كما هو؛ CI مُضبوط على `npm audit --audit-level moderate || true` (ci.yml:71) — أي شدة ≥ moderate لا توقف البناء.
- **التوصية المستقبلية**: عند رفع react-router-dom إلى v8 (ارتقاء مخطط)، أعد التشغيل عبر `npm run build` + Playwright E2E على كل المسارات (9 صفحات).

## التحقق
- `npm audit --audit-level high` → الثنائيان في `react-router`/`react-router-dom` فقط؛ لا علاقة للـ compiler deps الجديدة (`@rolldown/plugin-babel@0.1.7`، `@types/babel__core`).
- لا استيرادات RSC في `frontend/src/` (`grep -rn "react-dom/server\|createFromReadableStream\|RSC\|server-action" src/` → لا شيء).
