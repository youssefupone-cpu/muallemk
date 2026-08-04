# حد استخدام خادم Parallel Search (Rate Limit)

**الحالة:** open
**التاريخ:** 2026-08-02
**النوع:** مشكلة بحث (فشل خادم/حظر)

## الوصف
أثناء بحث ويب معمق (جلسة session_id: a1b2c3d4e5f67890abcdef1234567890)، بعد 8 عمليات web_search ناجحة في جولتين، رفض الخادم العمليات اللاحقة برسالة:

> You've hit the free-tier rate limit for Parallel Search MCP. To continue with higher limits, add your own API key — set header `x-api-key: YOUR_KEY` or `Authorization: Bearer YOUR_KEY`.

## السبب
الحد المجاني لخادم MCP (parallel-search) يُستنفد بعد عدد محدود من الاستدعاءات — حصل ذلك بعد 8 عمليات بحث في نفس الجلسة.

## الحل
- التبديل إلى أداة البحث المدمجة `websearch` (مزوّد آخر) — عملت بنجاح وأكملت المهمة.
- للحصول على حدود أعلى مستقبلاً: إضافة مفتاح API من https://platform.parallel.ai عبر الهيدر `x-api-key` أو `Authorization: Bearer`.

## سجل الحوادث
- 2026-08-02 (جولة تحقق مشاريع المساعد الدراسي، session_id: a3f9c2e8-7d4b-4f1a-9c6e-2b8d5a0f3e71): أول 3 استدعاءات web_search متوازية فشلت فوراً برسالة rate limit — يبدو أن الحد يُحتسب عبر عدة مفاتيح/جلسات مشتركة وأن الحد توقف تماماً. تم التبديل إلى `websearch` المدمجة وأكملت كل الاستعلامات الستة بنجاح.
