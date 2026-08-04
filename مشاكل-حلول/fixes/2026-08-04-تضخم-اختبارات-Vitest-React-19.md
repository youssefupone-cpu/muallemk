# 2026-08-04-تضخم-اختبارات-Vitest-React-19

- **السبب**: اختبارات جديدة (MathRenderer/ThemeToggle) استخدمت globals Vitest (`describe`/`it`/`expect`) بدون استيراد، مما يكسر `tsc -b` لأن `tsconfig.app.json` يحدّد `"types": ["vite/client"]` لا يشمل `@testing-library/jest-dom`.
- **الحل**: 
  1. استيراد صريح `import { describe, expect, it } from "vitest"` (يطابق نمط `chat.test.ts` الموجود).
  2. استبدال `expect(...).toBeInTheDocument()` (jest-dom) بـ `expect(...).toBeTruthy()` و `querySelector` غير المعتمد على أنسبتنا DOM.
  3. إضافة `vite-env.d.ts` لوحدة افتراضية `virtual:pwa-register/react`.
- **الحالة**: `fixed` — `tsc -b` نظيف، 7 اختبارات خضراء.
