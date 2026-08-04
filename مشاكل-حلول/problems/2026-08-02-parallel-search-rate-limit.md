# مشكلة: فشل البحث عبر parallel-search (Rate Limit)

- **الحالة**: open
- **التاريخ**: 2026-08-02
- **السبب**: الوصول للحد المجاني (free-tier rate limit) لخادم Parallel Search MCP — `"You've hit the free-tier rate limit for Parallel Search MCP"`.
- **التأثير**: تعذّر تنفيذ web_search/web_fetch عبر parallel-search.
- **الحل البديل المستخدم**: الاعتماد على أداة `websearch` المدمجة (النظام) بدلاً من parallel-search.
- **الحل الدائم المقترح**: إضافة API key عبر الرأس `x-api-key` أو `Authorization: Bearer` من https://platform.parallel.ai.
