# حد الخطة المجانية لخادم Parallel Search MCP

- **الحالة**: fixed
- **التاريخ**: 2026-08-02
- **النوع**: مشكلة عامة (بحث)

## السبب
خادم `parallel-search` MCP له حد استخدام مجاني (free-tier rate limit). بعد 10 استدعاءات `web_search` في جلسة واحدة (دفعتان × 4 + دفعة أخيرة 2)، أُعيد الخطأ:
`You've hit the free-tier rate limit for Parallel Search MCP. To continue with higher limits, add your own API key — set header x-api-key: YOUR_KEY or Authorization: Bearer YOUR_KEY` (https://platform.parallel.ai).

## الحل (مُطبق)
استخدم أداة `websearch` البديلة (المتاحة في البيئة) لنفس الاستعلامات — نجحت في سد الفجوتين المتبقيتين (كتب Connect الرسمية + المنافسون ناجح/أبواب) خلال استدعاءين فقط.

## دروس مستفادة
1. لا تُهدر الاستدعاءات المجانية في استعلامات متكررة؛ اجمع كل ما يمكن في دفعات متوازية وابدأ بالمصادر الرسمية.
2. عند ظهور الخطأ: انتقل فوراً إلى `websearch` بدل التكرار.
3. للجلسات الطويلة: إضافة مفتاح API خاص (https://platform.parallel.ai) أو تقليل عدد الاستعلامات لكل مهمة.
