# إصلاح AttributeError عند قراءة usage في تدفق litellm

- **التاريخ**: 2026-08-02
- **النوع**: fix
- **الوضعية**: build
- **الحالة**: fixed
- **الأولوية**: high

## المشكلة المُصلَحة
في الاختبار الحي الأول لـ `/chat` عبر SSE مع مزوّد litellm (Ollama فعلي)، ظهر:
`'ModelResponseStream' object has no attribute 'usage'` — انكسار كامل لتدفق الدردشة قبل إنتاج أي قطعة.

السبب: `litellm_provider.py` كان يقرأ `chunk.usage` مباشرة في حلقة `async for chunk in stream`، لكن في وضع التدفق (stream=True) لا يظهر `usage` إلا في القطعة الأخيرة، والقراءة المباشرة من كائنات `ModelResponseStream` تُطلق AttributeError. لم يُكتشف سابقاً لأن اختبارات chat تستخدم `FakeLLM` فقط (لا اتصال حقيقي).

## الحل المطبّق
استخدام `getattr(chunk, "usage", None)` الآمن (يلتقط AttributeError من properties) في `stream()`، وكذلك `getattr(resp, "usage", None)` في `chat()`، مع `getattr(chunk, "choices", None)` قبل الوصول إلى `choices[0].delta`.

## كيف تحقق منه
- الاختبار الحي: `bash /tmp/opencode/live_test.sh` — بعد الإصلاح، `/chat` بثّ أحداث `conversation → start → delta…` بنجاح مع المعاملات الثلاثة.
- البوابة: `.venv/bin/python -m pytest -q` → 79 passed؛ black + ruff نظيفان.

## الملفات المعدّلة
- backend/app/core/llm/litellm_provider.py (قراءة usage/choices آمنة في chat + stream)
