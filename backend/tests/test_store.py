import asyncio
from collections.abc import Callable
from datetime import UTC, datetime

import httpx
import pytest

from app.db import MAX_PARAMS, SQLiteDatabase
from app.ingest.elexon import ElexonError
from app.ingest.refresh import refresh
from app.ingest.store import _statements, migrate, upsert

START, END = datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 1, 2, tzinfo=UTC)
ACTUAL = {
    "startTime": "2026-01-01T00:00:00Z",
    "publishTime": "2026-01-01T00:30:00Z",
    "fuelType": "WIND",
    "generation": 5000,
}
FORECAST = {"startTime": "2026-01-01T01:00:00Z", "publishTime": "2025-12-31T22:30:00Z", "generation": 5200}


def run_refresh(db: SQLiteDatabase, handler: Callable[[httpx.Request], httpx.Response]) -> None:
    async def run() -> None:
        async with httpx.AsyncClient(base_url="https://test", transport=httpx.MockTransport(handler)) as client:
            await refresh(db, client, START, END)

    asyncio.run(run())


def counts(db: SQLiteDatabase) -> dict:
    sql = "SELECT (SELECT COUNT(*) FROM actuals) AS a, (SELECT COUNT(*) FROM forecasts) AS f"
    return asyncio.run(db.query(sql))[0]


def test_statements_ignore_semicolons_in_comments() -> None:
    sql = "-- one; two\nCREATE TABLE a (x INT); -- trailing; note\nCREATE TABLE b (y INT);\n"
    assert _statements(sql) == ["CREATE TABLE a (x INT)", "CREATE TABLE b (y INT)"]


def test_upsert_batches_under_param_limit_and_replaces(tmp_path) -> None:
    db = SQLiteDatabase(tmp_path / "t.db")
    columns = ("start_time", "publish_time", "generation_mw")
    rows = [(f"2026-01-01T00:{i:02d}:00Z", "p", float(i)) for i in range(60)]

    async def run() -> list[dict]:
        await migrate(db)
        await upsert(db, "actuals", columns, rows)
        await upsert(db, "actuals", columns, [(rows[0][0], "p2", 999.0)])
        return await db.query("SELECT COUNT(*) AS n, MAX(generation_mw) AS top FROM actuals")

    assert len(rows) * len(columns) > MAX_PARAMS  # the test really spans several batches
    assert asyncio.run(run()) == [{"n": 60, "top": 999.0}]


def test_refresh_is_idempotent(tmp_path) -> None:
    db = SQLiteDatabase(tmp_path / "t.db")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[ACTUAL] if "FUELHH" in request.url.path else [FORECAST])

    run_refresh(db, handler)
    run_refresh(db, handler)
    assert counts(db) == {"a": 1, "f": 1}
    runs = asyncio.run(db.query("SELECT dataset FROM ingest_runs ORDER BY id"))
    assert [r["dataset"] for r in runs] == ["FUELHH", "WINDFOR", "FUELHH", "WINDFOR"]


def test_failed_forecast_fetch_writes_nothing(tmp_path) -> None:
    db = SQLiteDatabase(tmp_path / "t.db")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[ACTUAL]) if "FUELHH" in request.url.path else httpx.Response(400)

    with pytest.raises(ElexonError):
        run_refresh(db, handler)
    assert counts(db) == {"a": 0, "f": 0}


def test_refresh_removes_rows_no_longer_returned(tmp_path) -> None:
    db = SQLiteDatabase(tmp_path / "t.db")
    stale = ("2026-01-01T05:00:00Z", "2026-01-01T02:30:00Z", 1.0)
    outside = ("2026-01-05T05:00:00Z", "2026-01-01T02:30:00Z", 2.0)  # other window, must stay

    async def seed() -> None:
        await migrate(db)
        await upsert(db, "forecasts", ("start_time", "publish_time", "generation_mw"), [stale, outside])

    asyncio.run(seed())
    run_refresh(db, lambda request: httpx.Response(200, json=[]))
    rows = asyncio.run(db.query("SELECT start_time FROM forecasts"))
    assert rows == [{"start_time": outside[0]}]
