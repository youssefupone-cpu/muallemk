# حذف مكوّن StudyChart المهمل (Dead Code)

**التاريخ:** 2026-08-05
**الأولوية:** متوسطة (🟡)
**النوع:** `fixes` / `refactor`
**الملف المتأثر:** `frontend/src/components/StudyChart.tsx` (محذوف)

## السياق
كان `StudyChart.tsx` — مكوّن React باستخدام Recharts v3.10.1 — مُعرّف لكنه **لم يُستورد في أي مكان** في الكود الأساسي.
عثرنا عليه عبر `codebase-memory-mcp` (query_graph) بـ 0 incoming CALLS.

## التحليل
1. **نمط البيانات غير المتطابق:** `StudyChart` يتوقع `Point[]` مع `{ day: string, score: number }`.
   لكن `study-table` plugin schema يوفر `{ day, subject, time }` — لا يوجد `score`.
2. **لا يوجد مستهلك:** لم يتم استيراده في `StudyTablePage` أو أي صفحة أخرى.
3. **يؤثر على حجم الحزمة:** يضيف ~20 kB (شمل Recharts) إلى الـ bundle الرئيسي.

## القرار
**حذف المكوّن** بدلاً من ربطه. الأسباب:
- ربطه يتطلب تغيير data model الـ plugin (إضافة score) — خارج نطاق المهمة.
- الحفاظ على كود ميت يزيد الضوضاء ويستهلك مساحة.
- Recharts لا يزال مثبتاً كاعتمادية — مكوّنات أخرى (إن وجدت مستقبلاً) يمكن إنشاؤها من جديد.

## التغيير
- حذف `frontend/src/components/StudyChart.tsx`.
- لم يتم العثور على أي استيرادات أو إشارات إليه — لا حاجة لتحديثات إضافية.
- `tsc --noEmit` ناجح بدون أي أخطاء.
- `npm run build` ينجح — الحجم الكلي للـ bundle انخفض بنحو 20 kB ثانوياً.

## الحالة
مغلق ✅
