"""اختبارات نقطة فحص الصحة (Health) — م1."""

from fastapi.testclient import TestClient

from app.main import app


def test_health_ok():
    client = TestClient(app)
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"


def test_root_redirects_to_docs():
    client = TestClient(app)
    res = client.get("/")
    assert res.status_code == 200
