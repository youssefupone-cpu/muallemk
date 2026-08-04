# PWA Install Banner — beforeinstallprompt يبقى null في Chrome 125+

**التاريخ:** 2026-08-04
**الأولوية:** منخفضة (🟢)
**النوع:** `problems`
**الحالة:** fixed ✅

## الوصف
لم يكن `beforeinstallprompt` يُطلق على الأصل الإنتاجي، رغم أن الـ manifest كان كاملاً.
كان يعمل على localhost فقط.

## السبب (من البحث)
Chrome 127+ استخدم نموذج ML لاختيار متى يُطلق `beforeinstallprompt` — يعتمد على
زمن الزيارة والمشاركة. الأصل الإنتاجي (بدون مشاركة سابقة) يبقى في "قائمة الانتظار"
لفترة طويلة، لذا الـ event لا يأتي. كما أن الأيقونات المطلوبة (192×192، 512×512 PNG)
كانت مفقودة — كانت SVG فقط.

## الحل المطبق
1. **أيقونات PNG** — إنشاء `pwa-192x192.png` و `pwa-512x512.png` من `favicon.svg`
   باستخدام ImageMagick، إضافتها إلى `includeAssets` و `manifest.icons` في `vite.config.ts`.
2. **مكوّن PwaInstallPrompt** — يالتقط `beforeinstallprompt` ويدعّه، ويظهر زر تثبيت
   يدوي. لمستخدمي iOS/Safari: يُظهر تعليمات "إضافة إلى الشريحة" (فهؤلاء لا يدعمون
   beforeinstallprompt أصلاً).
3. **ReactQueryDevtools** — لا يُظهر البانر إذا كان التطبيق مثبتاً بالفعل.

## الملفات
- `frontend/src/components/PwaInstallPrompt.tsx` (مكوّن جديد)
- `frontend/public/pwa-192x192.png`, `frontend/public/pwa-512x512.png` (أيقونات جديدة)
- `frontend/vite.config.ts` — manifest icons + includeAssets
- `frontend/src/main.tsx` — إضافة PwaInstallPrompt + ReactQueryDevtools

## الحالة
مغلق ✅
