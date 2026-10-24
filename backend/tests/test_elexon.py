import asyncio
from collections.abc import Callable
from datetime import UTC, datetime

import httpx
import pytest

from app.ingest.elexon import (
    ElexonError,
    fetch_actuals,
    fetch_forecasts,
    parse_actuals,
    parse_forecasts,
    parse_time,
)

START = datetime(2026, 1, 1, tzinfo=UTC)
END = datetime(2026, 1, 2, tzinfo=UTC)


def actual(start: str, publish: str, mw: float | None, fuel: str = "WIND") -> dict:
    return {"startTime": start, "publishTime": publish, "fuelType": fuel, "generation": mw}


def forecast(start: str, publish: str, mw: float | None) -> dict:
    return {"startTime": start, "publishTime": publish, "generation": mw}


def run_fetch(handler: Callable[[httpx.Request], httpx.Response]) -> list:
    async def run() -> list:
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(base_url="https://test", transport=transport) as client:
            return await fetch_actuals(client, START, END)

    return asyncio.run(run())


def test_parse_time_treats_missing_offset_as_utc() -> None:
    assert parse_time("2026-01-01T00:00:00") == datetime(2026, 1, 1, tzinfo=UTC)
    assert parse_time("2026-01-01T00:00:00Z") == datetime(2026, 1, 1, tzinfo=UTC)
    assert parse_time("2026-01-01T05:30:00+05:30") == datetime(2026, 1, 1, tzinfo=UTC)


def test_parse_actuals_keeps_latest_publish_per_period() -> None:
    rows = [
        actual("2026-01-01T00:00:00Z", "2026-01-01T00:30:00Z", 100),
        actual("2026-01-01T00:00:00Z", "2026-01-01T01:00:00Z", 110),  # revision
    ]
    [result] = parse_actuals(rows, START, END)
    assert result.generation_mw == 110


def test_parse_actuals_filters_window_fuel_and_missing_values() -> None:
    rows = [
        actual("2025-12-31T23:30:00Z", "2026-01-01T00:00:00Z", 1),  # before window
        actual("2026-01-02T00:00:00Z", "2026-01-02T00:30:00Z", 2),  # end is exclusive
        actual("2026-01-01T10:00:00Z", "2026-01-01T10:30:00Z", 3, fuel="CCGT"),
        actual("2026-01-01T11:00:00Z", "2026-01-01T11:30:00Z", None),
        actual("2026-01-01T12:00:00Z", "2026-01-01T12:30:00Z", 4),
    ]
    assert [a.generation_mw for a in parse_actuals(rows, START, END)] == [4]


def test_parse_skips_malformed_rows() -> None:
    rows = [
        {"fuelType": "WIND", "generation": 1},  # no times
        actual("not a time", "2026-01-01T00:30:00Z", 2),
        actual("2026-01-01T00:00:00Z", "2026-01-01T00:30:00Z", "abc"),  # type: ignore[arg-type]
        actual("2026-01-01T01:00:00Z", "2026-01-01T01:30:00Z", 3),
    ]
    assert [a.generation_mw for a in parse_actuals(rows, START, END)] == [3]
    assert parse_forecasts([{"generation": 1}], START, END) == []


def test_parse_forecasts_dedupes_and_sorts_by_target_then_publish() -> None:
    rows = [
        forecast("2026-01-01T10:00:00Z", "2026-01-01T04:30:00Z", 20),
        forecast("2026-01-01T10:00:00Z", "2026-01-01T02:30:00Z", 10),
        forecast("2026-01-01T10:00:00Z", "2026-01-01T02:30:00Z", 10),  # repeated at a chunk edge
        forecast("2026-01-03T10:00:00Z", "2026-01-01T02:30:00Z", 30),  # target outside window
    ]
    result = parse_forecasts(rows, START, END)
    assert [(f.publish_time.hour, f.generation_mw) for f in result] == [(2, 10), (4, 20)]


def test_parse_forecasts_drops_targets_before_publish_time() -> None:
    rows = [
        forecast("2026-01-01T00:00:00Z", "2026-01-01T02:30:00Z", 1),  # in the past at publish
        forecast("2026-01-01T03:00:00Z", "2026-01-01T02:30:00Z", 2),
    ]
    assert [f.generation_mw for f in parse_forecasts(rows, START, END)] == [2]


def test_fetch_requests_cover_window_with_lookback() -> None:
    seen: list[httpx.QueryParams] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.params)
        return httpx.Response(200, json=[])

    async def run() -> None:
        async with httpx.AsyncClient(base_url="https://test", transport=httpx.MockTransport(handler)) as client:
            await fetch_actuals(client, START, END)
            await fetch_forecasts(client, START, END)

    asyncio.run(run())
    fuel, wind = seen
    assert (fuel["settlementDateFrom"], fuel["settlementDateTo"]) == ("2025-12-31", "2026-01-02")
    assert fuel["fuelType"] == "WIND"
    assert (wind["publishDateTimeFrom"], wind["publishDateTimeTo"]) == ("2025-12-29T00:00:00Z", "2026-01-02T00:00:00Z")


def test_retries_server_errors_then_succeeds() -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        if len(calls) < 3:
            return httpx.Response(503)
        return httpx.Response(200, json=[actual("2026-01-01T00:00:00Z", "2026-01-01T00:30:00Z", 5)])

    assert len(run_fetch(handler)) == 1
    assert len(calls) == 3


def test_gives_up_after_three_attempts() -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        raise httpx.ConnectError("down")

    with pytest.raises(ElexonError, match="after 3 attempts"):
        run_fetch(handler)
    assert len(calls) == 3


def test_does_not_retry_client_errors() -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(400)

    with pytest.raises(ElexonError, match="HTTP 400"):
        run_fetch(handler)
    assert len(calls) == 1


def test_rejects_non_list_response() -> None:
    with pytest.raises(ElexonError, match="expected a list"):
        run_fetch(lambda request: httpx.Response(200, json={"error": "x"}))
