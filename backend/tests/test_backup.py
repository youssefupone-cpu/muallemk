"""اختبارات م10 — نسخة احتياطية قابلة للاستعادة عبر sqlite3 backup API."""

import sqlite3
from pathlib import Path

from scripts.backup import make_backup, restore_backup


def _seed_db(path: Path, rows: int = 2) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        "CREATE TABLE IF NOT EXISTS docs (id INTEGER PRIMARY KEY, title TEXT NOT NULL);"
    )
    for i in range(rows):
        conn.execute("INSERT INTO docs (title) VALUES (?)", (f"كتاب {i}",))
    conn.commit()
    conn.close()


def _row_count(path: Path) -> int:
    conn = sqlite3.connect(path)
    try:
        return conn.execute("SELECT COUNT(*) FROM docs").fetchone()[0]
    finally:
        conn.close()


def test_backup_restore_roundtrip(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    lancedb = data_dir / "lancedb"
    lancedb.mkdir()
    (lancedb / "docs.lance").write_text("fake-index", encoding="utf-8")
    _seed_db(data_dir / "muallemk.db")

    archive = make_backup(data_dir, tmp_path / "backup" / "muallemk.zip")
    assert archive.exists()

    # إتلاف جانب من البيانات ثم الاستعادة
    (lancedb / "docs.lance").unlink()
    restore_backup(archive, data_dir)
    assert (lancedb / "docs.lance").exists()
    assert _row_count(data_dir / "muallemk.db") == 2


def test_backup_restore_recovers_sqlite_rows(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _seed_db(data_dir / "muallemk.db", rows=5)

    archive = make_backup(data_dir, tmp_path / "muallemk.zip")
    (data_dir / "muallemk.db").unlink()  # فقدان كامل لقاعدة البيانات

    restore_backup(archive, data_dir)
    assert _row_count(data_dir / "muallemk.db") == 5


def test_restore_rejects_archive_without_db(tmp_path):
    bad = tmp_path / "bad.zip"
    import zipfile

    with zipfile.ZipFile(bad, "w") as zf:
        zf.writestr("readme.md", "no db here")
    try:
        restore_backup(bad, tmp_path / "out")
        raise AssertionError("يجب أن يرفض الأرشيف الذي لا يحوي قاعدة بيانات")
    except ValueError:
        pass
