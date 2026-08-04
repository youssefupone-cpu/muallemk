# 2026-08-04-إغلاق-ثغرة-.gitignore-لـ-frontend/.venv

- **السبب**: `.gitignore` ينسّق `backend/.venv/` ولكنه لا ينتّق `frontend/.venv/` → كانت المجلد يظهر كـ untracked (`?? frontend/.venv/`) وقد يُرفَق بعملية commit بالخطأ.
- **الحل**: إضافة `frontend/.venv/` تحت قسم `# Python` — توحيده مع `backend/.venv/`.
- **كيف تحقق منه**: `git check-ignore frontend/.venv` → يطبع `frontend/.venv` (الآن مُهمّش)؛ `git status --short` لا يعرضه كـ untracked بعد.
- **الحالة**: `fixed`.
- **الملفات المعدّلة**: `.gitignore` (سطر واحد).
