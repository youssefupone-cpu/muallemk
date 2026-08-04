"""نسخة احتياطية قابلة للاستعادة (م10) — SQLite + بيانات التطبيق في أرشيف واحد.

طريقة آمنة لقاعدة البيانات عبر sqlite3 backup API (وليست نسخ ملف خام أثناء
الكتابة)، ثم تُضمّن بقية المجلد (LanceDB، ملفات إضافية) في نفس الأرشيف.

- make_backup(data_dir, dest) → يعيد مسار الأرشيف.
- restore_archive(dest, data_dir) → يستعيد محتويات متطابقة.
- سطر أوامر: python scripts/backup.py backup | restore.
"""

from __future__ import annotations

import sqlite3
import sys
import tempfile
import zipfile
from pathlib import Path

DB_FILENAME = "muallemk.db"


def _db_in_zip(archive: Path) -> str:
    """اسم ملف قاعدة البيانات داخل الأرشيف (نفس الاسم في مجلد البيانات)."""
    return DB_FILENAME


def make_backup(data_dir: str | Path, dest: str | Path) -> Path:
    """يُنشئ أرشيف ZIP كامل قابل للاستعادة من مجلد البيانات."""
    src = Path(data_dir)
    if not src.exists():
        raise FileNotFoundError(f"مجلد البيانات غير موجود: {src}")
    out = Path(dest)
    out.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        db_copy = Path(tmp) / DB_FILENAME
        # sqlite3 backup API — نسخة متسقة حتى أثناء الكتابة (WAL).
        if (src / DB_FILENAME).exists():
            src_conn = sqlite3.connect(src / DB_FILENAME)
            dst_conn = sqlite3.connect(db_copy)
            src_conn.backup(dst_conn)
            src_conn.close()
            dst_conn.close()

        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
            if db_copy.exists():
                zf.write(db_copy, DB_FILENAME)
            for path in sorted(src.iterdir()):
                if path.name == DB_FILENAME:
                    continue  # قاعدة البيانات تُرصد عبر API أعلاه
                if path.is_dir():
                    for f in sorted(path.rglob("*")):
                        if f.is_file():
                            zf.write(f, f.relative_to(src))
                else:
                    zf.write(path, path.name)
    return out


def restore_backup(archive_path: str | Path, data_dir: str | Path) -> Path:
    """يستعيد محتوى بيانات متطابقاً من الأرشيف إلى مجلد البيانات المستهدف."""
    arc = Path(archive_path)
    if not arc.exists():
        raise FileNotFoundError(f"الأرشيف غير موجود: {arc}")
    dst = Path(data_dir)
    dst.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(arc) as zf:
        names = zf.namelist()
    if DB_FILENAME not in names:
        raise ValueError(f"الأرشيف لا يحوي {DB_FILENAME}")

    # --- Zip Slip protection ---
    # التحقق من أن مسارات الملفات داخل الأرشيف لا تتجاوز مجلد البيانات المستهدف.
    import os

    data_dir_resolved = dst.resolve()

    def _is_safe(member_path: str) -> bool:
        """True إذا كان المسار آمنًا (لا يحتوي على .. أو مسار مطلق)."""
        target = (dst / member_path).resolve()
        return (
            str(target).startswith(str(data_dir_resolved) + os.sep) or target == data_dir_resolved
        )

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        with zipfile.ZipFile(arc) as zf:
            # استخراج آمن — فحص كل مسار قبل الاستخراج
            for member in zf.namelist():
                if not _is_safe(member):
                    raise ValueError(f"مسار غير آمن في الأرشيف (Zip Slip): {member}")
            zf.extractall(tmp_dir)

        db_tmp = tmp_dir / DB_FILENAME
        if db_tmp.exists():
            src_conn = sqlite3.connect(db_tmp)
            dst_conn = sqlite3.connect(dst / DB_FILENAME)
            src_conn.backup(dst_conn)  # استعادة عبر API للحفاظ على الاتساق
            src_conn.close()
            dst_conn.close()

        for item in sorted(tmp_dir.iterdir()):
            if item.name == DB_FILENAME:
                continue
            if item.is_dir():
                for f in sorted(item.rglob("*")):
                    if f.is_file():
                        relative = f.relative_to(tmp_dir)
                        target = dst / relative
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_bytes(f.read_bytes())
            else:
                (dst / item.name).write_bytes(item.read_bytes())
    return dst


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) < 2:
        print(
            "الاستخدام: python scripts/backup.py backup <data_dir> <dest.zip>"
            " | restore <dest.zip> <data_dir>"
        )
        return 2
    cmd, a, b = args[0], Path(args[1]), Path(args[2])
    if cmd == "backup":
        print(make_backup(a, b))
    elif cmd == "restore":
        restore_backup(a, b)
        print(f"استُعيدت البيانات إلى {b}")
    else:
        print(f"أمر غير معروف: {cmd}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
