import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_with_sqlite() -> None:
    res = client.get("/api/v1/health")
    assert res.json() == {"status": "ok", "db": "ok"}


def test_health_reports_missing_d1_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DB_BACKEND", "d1")
    for name in ("CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_API_TOKEN", "D1_DATABASE_ID"):
        monkeypatch.setenv(name, "")
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "db": "error"}
