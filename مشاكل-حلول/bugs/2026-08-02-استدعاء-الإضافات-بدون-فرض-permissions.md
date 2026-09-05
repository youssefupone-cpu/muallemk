# استدعاء الإضافات (/invoke) يمرر kwargs خام بلا فرض permissions

- **التاريخ**: 2026-08-02
- **النوع**: bug (أمان — سطح هجوم)
- **الوضعية**: reviewer
- **الحالة**: open
- **الأولوية**: major

## الوصف
`POST /plugins/{name}/invoke` يستقبل `body: dict | None` من المستخدم ويفككه مباشرة:
- `backend/app/plugins/router.py:131` → `result = await p.run(**(body or {}))`
- `backend/app/plugins/manager.py:119` → `mod.run(self.ctx, *args, **kwargs)`

أي مستخدم يتحكم في **كل معاملات استدعاء كود الإضافة** (action, payload, وكل ما يصرّح به توقيع `run`) بلا تحقق من مخطط أو فرض للأذونات.

## السبب الجذري
حقل `permissions` معرّف ومتحقق منه في `manifest.py:35-43` ومخزّن في `PluginInfo` (`manager.py:57`)، لكنه **لا يُفرض في أي مسار** — توثيقي فقط.

## الأثر
- إضافة تملك أذونات مقيدة (مثلاً `read-only`) يمكن استدعاؤها بمعاملات اعتباطية.
- إضافة معطوبة/خبيثة ستنكشف بمعاملات عشوائية يتحكم بها المستخدم — لا تسريب مباشر حالياً (الإضافات المثبتة موثوقة ومحلية)، لكن التصميم العام غير محصّن.

## الحل المقترح
1. تحديد `allowed_actions: list[str] | None` في manifest (إن غاب → استدعاء محظور أو allowlist فارغ).
2. في `invoke_plugin`: تحقق `body.get("action") in p.info.allowed_actions` (أو نمط action قسري) قبل `p.run`، وإلا 403.
3. فرض `permissions` فعلياً (مثال: منع `write` للإضافات غير المصرّحة) أو حذف الحقل إن كان توثيقياً فقط لتجنّب الأمان الوهمي.
