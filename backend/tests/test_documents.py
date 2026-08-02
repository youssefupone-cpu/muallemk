"""اختبارات المستندات (م5) — الاستخراج والتخزين عبر markitdown + OCR."""

import io

import pytest
from fastapi import UploadFile
from fastapi.testclient import TestClient

from app.core.db import get_connection, init_db
from app.documents.service import extract_text
from app.main import app


@pytest.fixture(autouse=True)
def fresh_db():
    """TestClient لا يشغّل startup خارج with — نهيّئ وننظف القاعدة يدوياً."""
    init_db()
    yield
    with get_connection() as conn:
        conn.execute("DELETE FROM documents")


def test_extract_text_txt():
    content = extract_text(
        UploadFile(
            file=io.BytesIO("نص تجريبي للاختبار".encode()),
            filename="note.txt",
        )
    )
    assert "نص تجريبي" in content


def test_extract_text_markdown():
    md = "# عنوان\n\nفقرة بالعربية **غامقة**"
    content = extract_text(UploadFile(file=io.BytesIO(md.encode("utf-8")), filename="doc.md"))
    assert "عنوان" in content
    assert "غامقة" in content


def test_upload_and_list_documents():
    client = TestClient(app)
    res = client.post(
        "/documents",
        files={"file": ("ملاحظات.txt", "نص الملف الأول".encode(), "text/plain")},
    )
    assert res.status_code == 200
    doc = res.json()
    assert doc["filename"] == "ملاحظات.txt"
    assert "نص الملف الأول" in doc["preview"]

    res = client.get("/documents")
    assert res.status_code == 200
    assert any(d["filename"] == "ملاحظات.txt" for d in res.json())

    cid = doc["id"]
    res = client.get(f"/documents/{cid}/content")
    assert res.status_code == 200
    assert "نص الملف الأول" in res.json()["content"]


def test_delete_document():
    client = TestClient(app)
    res = client.post(
        "/documents",
        files={"file": ("m.md", "# مؤقت".encode(), "text/markdown")},
    )
    doc_id = res.json()["id"]
    res = client.delete(f"/documents/{doc_id}")
    assert res.status_code == 200
    res = client.delete(f"/documents/{doc_id}")
    assert res.status_code == 404


def test_unsupported_file_rejected():
    client = TestClient(app)
    res = client.post(
        "/documents",
        files={"file": ("evil.exe", b"MZ\x90\x00", "application/octet-stream")},
    )
    assert res.status_code == 415
