import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.db import get_default_database
from app.ingest.store import migrate, record_run, upsert
from app.main import app

client = TestClient(app)

SPECIAL = {"2026-01-15T12:00:00Z": 5000.0, "2026-01-15T12:30:00Z": 5100.0, "2026-01-16T00:00:00Z": 6000.0}


def half_hour_rows(start: datetime, count: int) -> list[tuple]:
    rows = []
    for i in range(count):
        t = (start + timedelta(minutes=30 * i)).strftime("%Y-%m-%dT%H:%M:%SZ")
        rows.append((t, t, SPECIAL.get(t, 1000.0)))
    return rows


# 15 and 16 Jan complete (UK = UTC in January); 17 Jan has only 2 half-hours
ACTUALS = half_hour_rows(datetime(2026, 1, 15, tzinfo=UTC), 96) + half_hour_rows(datetime(2026, 1, 17, tzinfo=UTC), 2)
FORECASTS = [
    ("2026-01-14T07:30:00Z", "2026-01-15T12:00:00Z", 4000.0),
    ("2026-01-14T09:30:00Z", "2026-01-15T12:00:00Z", 4500.0),
]


@pytest.fixture(autouse=True)
def seeded() -> None:
    async def seed() -> None:
        db = get_default_database()
        await migrate(db)
        await upsert(db, "actuals", ("start_time", "publish_time", "generation_mw"), ACTUALS)
        await upsert(db, "forecasts", ("publish_time", "start_time", "generation_mw"), FORECASTS)
        await record_run(db, "FUELHH", "2026-01-15T00:00:00Z", "2026-01-17T00:00:00Z", 3)

    asyncio.run(seed())


def points_by_time(body: dict) -> dict[str, dict]:
    return {p["start_time"]: p for p in body["points"]}


def test_coverage_reports_complete_days_only_and_default_cutoff() -> None:
    body = client.get("/api/v1/coverage").json()
    assert (body["first_date"], body["last_date"]) == ("2026-01-15", "2026-01-16")
    assert body["default_cutoff"] == "09:50:00"
    assert body["refreshed_at"] is not None


def test_series_defaults_to_full_coverage_with_default_cutoff() -> None:
    body = client.get("/api/v1/series").json()
    assert (body["start"], body["end"], body["cutoff"]) == ("2026-01-15", "2026-01-16", "09:50:00")
    assert len(body["points"]) == 96  # two UK days of half-hours, end inclusive
    noon = points_by_time(body)["2026-01-15T12:00:00Z"]
    assert noon == {
        "start_time": "2026-01-15T12:00:00Z",
        "actual_mw": 5000.0,
        "forecast_mw": 4500.0,
        "publish_time": "2026-01-14T09:30:00Z",
        "horizon_hours": 26.5,
    }


def test_series_returns_null_for_gaps() -> None:
    body = client.get("/api/v1/series", params={"start": "2026-01-16", "end": "2026-01-16"}).json()
    midnight = points_by_time(body)["2026-01-16T00:00:00Z"]
    assert midnight["actual_mw"] == 6000.0
    assert midnight["forecast_mw"] is None and midnight["publish_time"] is None


def test_series_cutoff_changes_selected_forecast() -> None:
    body = client.get("/api/v1/series", params={"start": "2026-01-15", "end": "2026-01-15", "cutoff": "09:20"}).json()
    assert points_by_time(body)["2026-01-15T12:00:00Z"]["forecast_mw"] == 4000.0


def test_series_default_range_fits_the_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.api.MAX_RANGE_DAYS", 1)
    body = client.get("/api/v1/series").json()
    assert (body["start"], body["end"]) == ("2026-01-16", "2026-01-16")  # the latest day that fits


@pytest.mark.parametrize(
    "params",
    [
        {"start": "2026-01-16", "end": "2026-01-15"},  # reversed
        {"start": "2026-01-01", "end": "2026-03-31"},  # too long
        {"cutoff": "25:00"},
        {"start": "not-a-date"},
    ],
)
def test_series_rejects_bad_parameters(params: dict) -> None:
    assert client.get("/api/v1/series", params=params).status_code == 422


def test_fresh_database_reads_as_empty(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    from app.config import get_settings
    from app.data_store import get_data_store

    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "fresh.db"))  # no tables at all
    for cache in (get_settings, get_default_database, get_data_store):
        cache.cache_clear()
    res = client.get("/api/v1/coverage")
    assert res.status_code == 200
    assert (res.json()["first_date"], res.json()["last_date"]) == (None, None)


def test_missing_d1_credentials_give_503_not_500(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.config import get_settings
    from app.data_store import get_data_store

    monkeypatch.setenv("DB_BACKEND", "d1")
    monkeypatch.setenv("D1_AUTH", "token")
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "")
    for cache in (get_settings, get_default_database, get_data_store):
        cache.cache_clear()
    for path in ("/api/v1/coverage", "/api/v1/series"):
        res = client.get(path)
        assert res.status_code == 503
        assert res.json() == {"detail": "Data unavailable"}


def test_metrics_scores_only_half_hours_with_both_values() -> None:
    body = client.get("/api/v1/metrics", params={"start": "2026-01-15", "end": "2026-01-15"}).json()
    summary = body["summary"]
    # Forecasts exist only for 12:00 and 12:30 (4500 each) against actuals 5000 and 5100
    assert (summary["half_hours"], summary["missing"]) == (2, 46)
    assert summary["bias_mw"] == -550 and summary["mae_mw"] == 550
    assert summary["over_forecast_share"] == 0
    assert [d["delivery_date"] for d in body["worst_days"]] == ["2026-01-15"]
    assert sum(b["count"] for b in body["histogram"]) == 2


def test_metrics_cutoff_and_validation_match_series() -> None:
    early = client.get("/api/v1/metrics", params={"start": "2026-01-15", "end": "2026-01-15", "cutoff": "09:20"})
    assert early.json()["summary"]["bias_mw"] == -1050  # the 07:30 run (4000) is used for both half-hours
    assert client.get("/api/v1/metrics", params={"start": "2026-01-16", "end": "2026-01-15"}).status_code == 422


def test_metrics_without_scorable_data_has_null_summary() -> None:
    body = client.get("/api/v1/metrics", params={"start": "2026-01-16", "end": "2026-01-16"}).json()
    assert body["summary"] is None and body["histogram"] == [] and body["worst_days"] == []


def _break_database_and_mock_elexon(monkeypatch: pytest.MonkeyPatch, elexon_status: int = 200) -> list[str]:
    """Make the database unreadable and route Elexon calls to a fake. Returns the requested paths."""
    import httpx

    from app import data_store
    from app.config import get_settings
    from app.data_store import get_data_store

    calls: list[str] = []

    def fake_elexon(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if elexon_status != 200:
            return httpx.Response(elexon_status)
        if "FUELHH" in request.url.path:
            rows = [{"startTime": t, "publishTime": t, "fuelType": "WIND", "generation": 7000} for t, *_ in ACTUALS[:2]]
        else:
            rows = [{"publishTime": "2026-01-14T09:30:00Z", "startTime": "2026-01-15T00:00:00Z", "generation": 7500}]
        return httpx.Response(200, json=rows)

    monkeypatch.setattr(
        data_store,
        "elexon_client",
        lambda: httpx.AsyncClient(base_url="https://test", transport=httpx.MockTransport(fake_elexon)),
    )
    monkeypatch.setenv("DB_BACKEND", "d1")
    monkeypatch.setenv("D1_AUTH", "token")
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "")  # the database cannot be reached
    monkeypatch.setenv("ELEXON_FALLBACK", "true")
    for cache in (get_settings, get_default_database, get_data_store):
        cache.cache_clear()
    return calls


def test_falls_back_to_live_elexon_when_database_is_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _break_database_and_mock_elexon(monkeypatch)
    coverage = client.get("/api/v1/coverage")
    assert coverage.status_code == 200
    assert coverage.json()["source"] == "elexon"
    series = client.get("/api/v1/series", params={"start": "2026-01-15", "end": "2026-01-15"}).json()
    first = series["points"][0]
    assert (first["actual_mw"], first["forecast_mw"]) == (7000.0, 7500.0)
    fetched = len(calls)
    client.get("/api/v1/metrics", params={"start": "2026-01-15", "end": "2026-01-15"})
    assert len(calls) == fetched  # the live copy is cached, not fetched again per request


def test_503_when_database_and_elexon_are_both_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    _break_database_and_mock_elexon(monkeypatch, elexon_status=400)
    res = client.get("/api/v1/coverage")
    assert res.status_code == 503 and res.json() == {"detail": "Data unavailable"}


def test_coverage_reports_database_as_source() -> None:
    assert client.get("/api/v1/coverage").json()["source"] == "database"


def test_data_status_reports_coverage_runs_and_loads() -> None:
    body = client.get("/api/v1/data").json()
    assert body["source"] == "database"
    assert (body["first_date"], body["last_date"]) == ("2026-01-15", "2026-01-16")  # complete days only
    assert (body["actual_rows"], body["forecast_rows"], body["forecast_runs"]) == (98, 2, 2)
    assert [(d["delivery_date"], d["actual_half_hours"], d["expected_half_hours"]) for d in body["days"]] == [
        ("2026-01-15", 48, 48),
        ("2026-01-16", 48, 48),
        ("2026-01-17", 2, 48),  # partial day is listed, so the gap is visible
    ]
    assert body["days"][0]["forecast_runs"] == 0 and body["first_publish_time"] == "2026-01-14T07:30:00Z"
    assert [r["dataset"] for r in body["runs"]] == ["FUELHH"]


def test_data_status_on_empty_database(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    from app.config import get_settings
    from app.data_store import get_data_store

    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "fresh.db"))
    for cache in (get_settings, get_default_database, get_data_store):
        cache.cache_clear()
    body = client.get("/api/v1/data").json()
    assert body["days"] == [] and body["runs"] == [] and body["forecast_runs"] == 0
    assert body["first_publish_time"] is None
