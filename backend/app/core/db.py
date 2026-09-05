"""قاعدة البيانات المحلية — SQLite مع WAL.

نمط بسيط: كل عملية تفتح اتصالاً جديداً (آمن للتزامن في FastAPI).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from app.core.config import get_settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL DEFAULT 'محادثة جديدة',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    metadata TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    file_type TEXT NOT NULL DEFAULT 'text',
    content TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS message_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    document_id INTEGER,
    filename TEXT NOT NULL,
    heading TEXT NOT NULL DEFAULT '',
    text TEXT NOT NULL DEFAULT '',
    score REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS search_cache (
    key TEXT PRIMARY KEY,
    query TEXT NOT NULL,
    result_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    file_type TEXT NOT NULL DEFAULT 'pdf',
    content TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'uploaded',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS book_lessons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    unit_index INTEGER NOT NULL DEFAULT 0,
    unit_title TEXT NOT NULL DEFAULT '',
    title TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending',
    content TEXT NOT NULL DEFAULT '',
    questions TEXT NOT NULL DEFAULT '[]',
    exercises TEXT NOT NULL DEFAULT '[]',
    glossary TEXT NOT NULL DEFAULT '[]',
    error TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS quiz_bank (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    lesson_id INTEGER REFERENCES book_lessons(id) ON DELETE SET NULL,
    qtype TEXT NOT NULL DEFAULT 'mcq',
    question TEXT NOT NULL DEFAULT '',
    options TEXT NOT NULL DEFAULT '[]',
    answer TEXT NOT NULL DEFAULT '',
    explanation TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS quiz_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quiz_id INTEGER NOT NULL REFERENCES quiz_bank(id) ON DELETE CASCADE,
    answer TEXT NOT NULL DEFAULT '',
    is_correct INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS book_templates (
    book_id INTEGER PRIMARY KEY REFERENCES books(id) ON DELETE CASCADE,
    template_key TEXT NOT NULL DEFAULT 'generic',
    detected_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS study_activity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    lesson_id INTEGER,
    activity TEXT NOT NULL DEFAULT 'lesson',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_book_lessons_book ON book_lessons(book_id);
CREATE INDEX IF NOT EXISTS idx_study_activity_book ON study_activity(book_id);
CREATE INDEX IF NOT EXISTS idx_quiz_bank_book ON quiz_bank(book_id);
CREATE INDEX IF NOT EXISTS idx_quiz_bank_lesson ON quiz_bank(lesson_id);
CREATE INDEX IF NOT EXISTS idx_quiz_attempts_quiz ON quiz_attempts(quiz_id);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
"""


def _db_path() -> Path:
    settings = get_settings()
    data_dir = Path(settings.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "muallemk.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path(), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def _add_column(conn: sqlite3.Connection, table: str, column: str, decl: str) -> None:
    """يضيف عموداً إن لم يكن موجوداً — آمن للترحيل على قواعد قديمة."""
    cols = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(SCHEMA)
        # ترحيل قواعد قديمة (أعمدة اختيارية ثابتة الافتراض — SQLite يرفض non-constant في ALTER)
        try:
            _add_column(conn, "conversations", "updated_at", "TEXT NOT NULL DEFAULT ''")
            _add_column(conn, "messages", "metadata", "TEXT NOT NULL DEFAULT ''")
            _add_column(conn, "books", "updated_at", "TEXT NOT NULL DEFAULT ''")
            _add_column(conn, "book_lessons", "glossary", "TEXT NOT NULL DEFAULT '[]'")
            _add_column(conn, "book_lessons", "error", "TEXT NOT NULL DEFAULT ''")
            _add_column(conn, "book_lessons", "updated_at", "TEXT NOT NULL DEFAULT ''")
            conn.execute(
                "UPDATE conversations SET updated_at = COALESCE(created_at, '') "
                "WHERE updated_at = '' OR updated_at IS NULL"
            )
        except sqlite3.OperationalError:
            # جداول غير موجودة بعد في قاعدة فارغة جداً — SCHEMA أعلاه كافٍ
            pass
        conn.commit()
