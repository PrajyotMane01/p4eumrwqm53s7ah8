import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.config import Settings


@pytest.fixture
def client() -> TestClient:
    return TestClient(main.app)


def test_health_reports_unconfigured_db(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main, "get_settings", lambda: Settings(_env_file=None))
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "db": "not configured"}
