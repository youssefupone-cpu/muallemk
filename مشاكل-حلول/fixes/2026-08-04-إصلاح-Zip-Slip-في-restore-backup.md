# حل: Zip Slip في `restore_backup`

- **التاريخ**: 2026-08-04
- **النوع**: fix
- **الوضعية**: reviewer
- **الحالة**: open
- **الأولوية**: high
- **الملف المستهدف**: `scripts/backup.py:76-97`
- **المشكلة المرتبطة**: `مشاكل-حلول/bugs/2026-08-04-...` (من اكتشاف security-reviewer)

## الوصف

`restore_backup()` يستخدم `zf.extractall(tmp_dir)` دون فحص مسارات الملفات. إذا كان الأرشيف يحتوي على ملفات ذات مسار `../`، فإنها يمكن أن تكتب خارج `tmp_dir` (Zip Slip / Path Traversal).

## الحل

أضف فحصاً يتحقق أن مسار كل ملف داخل الأرشيف يبقى داخل `tmp_dir`:

### قبل:
```python
def restore_backup(archive_path: Path, dest_dir: Path) -> int:
    with zipfile.ZipFile(archive_path) as zf:
        zf.extractall(tmp_dir)
```

### بعد:
```python
def restore_backup(archive_path: Path, dest_dir: Path) -> int:
    """Restore data from a backup archive with Zip Slip protection."""
    # Sanitize destination
    dest_real = os.path.realpath(dest_dir)
    os.makedirs(dest_real, exist_ok=True)

    with zipfile.ZipFile(archive_path) as zf:
        for member in zf.infolist():
            # Resolve the target path and ensure it's within dest
            member_path = os.path.realpath(os.path.join(dest_real, member.filename))
            if not member_path.startswith(dest_real + os.sep):
                raise ValueError(f"Unsafe path in archive: {member.filename}")
            zf.extract(member, dest_real)

    return count
```

## التوثيق البديل

بدلاً من الكتابة اليدوية، استخدم مكتبة موثوقة:
```bash
pip install zippath  # أو استخدم:
```

```python
# استخدام pathlib + check
from pathlib import Path
dest_root = dest_dir.resolve()
for member in zf.infolist():
    target = (dest_root / member.filename).resolve()
    if dest_root not in target.parents and target != dest_root:
        raise ValueError(f"Path traversal detected: {member.filename}")
```

## الملفات المرتبطة

- `backend/scripts/backup.py` — الدالة `restore_backup`
- `backend/tests/test_backup.py` — أضف test جديد لـ zip-slip scenario
