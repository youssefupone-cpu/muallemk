# فشل خادم parallel-search (free-tier rate limit)

- **الحالة**: open
- **التاريخ**: 2026-08-02
- **السبب**: ضرب حد الاستخدام المجاني (free-tier rate limit) في خادم parallel-search MCP عند أول استدعاء — الخطأ: "You've hit the free-tier rate limit for Parallel Search MCP" (code -32000).
- **الحل المعتمد**: بديل موثوق وفعلي:
  1. GitHub REST API عبر curl (`api.github.com/repos/{owner}/{repo}` و `search/repositories`) للنجوم/الترخيص/آخر نشاط/الأرشفة.
  2. npm registry API (`registry.npmjs.org/{pkg}/latest`) للنسخ + peerDependencies (توافق React 19) + `api.npmjs.org/downloads/point/last-week/{pkg}` للتحميلات.
  3. أداة `websearch` المدمجة للأسئلة النوعية (حالة RTL، مناقشات، مقارنات 2026).
- **الدرس**: عند فشل parallel-search، استخدم GitHub API + npm registry أولاً (أدق للتحقق من المشاريع)، واحتفظ بـ websearch للمحتوى النوعي.
