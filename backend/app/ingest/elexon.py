"""Fetch wind actuals (FUELHH) and forecasts (WINDFOR) from the Elexon BMRS API."""

import asyncio
import logging
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any

import httpx

# Requests are split into chunks so no single response gets too large
CHUNK = timedelta(days=7)

# A WINDFOR run covers roughly the next 3 days, so runs published this long
# before the window can still hold forecasts for it
FORECAST_LOOKBACK = timedelta(days=3)

# Rate limits and server errors are retried; other errors fail at once
RETRY_STATUSES = {429, 500, 502, 503, 504}
ATTEMPTS = 3
RETRY_DELAY = 1.0  # seconds, multiplied by the attempt number

log = logging.getLogger(__name__)


class ElexonError(Exception):
    pass


@dataclass(frozen=True)
class Actual:
    start_time: datetime
    publish_time: datetime
    generation_mw: float


@dataclass(frozen=True)
class Forecast:
    publish_time: datetime
    start_time: datetime
    generation_mw: float


def parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    # Elexon times are UTC; never let a missing offset fall back to the machine's local zone
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)


def to_iso(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _chunks[T: date](start: T, end: T, step: timedelta) -> Iterator[tuple[T, T]]:
    """Split [start, end) into consecutive [a, b) pieces of at most `step`."""
    a = start
    while a < end:
        b = min(a + step, end)
        yield a, b
        a = b


async def _get(client: httpx.AsyncClient, path: str, params: dict[str, str]) -> list[dict[str, Any]]:
    for attempt in range(1, ATTEMPTS + 1):
        try:
            res = await client.get(path, params=params)
            if res.status_code not in RETRY_STATUSES:
                break
            problem = f"HTTP {res.status_code}"
        except httpx.TransportError as exc:
            problem = str(exc) or type(exc).__name__
        if attempt == ATTEMPTS:
            raise ElexonError(f"Elexon request to {path} failed after {ATTEMPTS} attempts: {problem}")
        log.warning("Elexon request to %s failed (%s), retrying %d/%d", path, problem, attempt, ATTEMPTS - 1)
        await asyncio.sleep(RETRY_DELAY * attempt)

    try:
        res.raise_for_status()
        data = res.json()
    except httpx.HTTPStatusError as exc:
        raise ElexonError(f"Elexon request to {path} failed: HTTP {res.status_code}") from exc
    except ValueError as exc:
        raise ElexonError(f"Elexon returned invalid JSON for {path}") from exc
    if not isinstance(data, list):
        raise ElexonError(f"Unexpected response from {path}: expected a list")
    return data


def parse_actuals(rows: list[dict[str, Any]], start: datetime, end: datetime) -> list[Actual]:
    """Keep WIND rows inside [start, end); if a period appears twice, keep the latest publish."""
    latest: dict[datetime, Actual] = {}
    skipped = 0
    for row in rows:
        if row.get("fuelType") != "WIND" or row.get("generation") is None:
            continue
        try:
            actual = Actual(
                start_time=parse_time(row["startTime"]),
                publish_time=parse_time(row["publishTime"]),
                generation_mw=float(row["generation"]),
            )
        except (KeyError, TypeError, ValueError):
            skipped += 1
            continue
        if not start <= actual.start_time < end:
            continue
        prev = latest.get(actual.start_time)
        if prev is None or actual.publish_time > prev.publish_time:
            latest[actual.start_time] = actual
    if skipped:
        log.warning("Skipped %d malformed FUELHH rows", skipped)
    return sorted(latest.values(), key=lambda a: a.start_time)


def parse_forecasts(rows: list[dict[str, Any]], start: datetime, end: datetime) -> list[Forecast]:
    """Keep forecasts whose target time is inside [start, end), one per (publish, target).

    Each WINDFOR run also carries a few hours before its publish time. Those are not
    forecasts, so they are dropped.
    """
    unique: dict[tuple[datetime, datetime], Forecast] = {}
    skipped = 0
    for row in rows:
        if row.get("generation") is None:
            continue
        try:
            forecast = Forecast(
                publish_time=parse_time(row["publishTime"]),
                start_time=parse_time(row["startTime"]),
                generation_mw=float(row["generation"]),
            )
        except (KeyError, TypeError, ValueError):
            skipped += 1
            continue
        if start <= forecast.start_time < end and forecast.start_time >= forecast.publish_time:
            unique[(forecast.publish_time, forecast.start_time)] = forecast
    if skipped:
        log.warning("Skipped %d malformed WINDFOR rows", skipped)
    return sorted(unique.values(), key=lambda f: (f.start_time, f.publish_time))


async def fetch_actuals(client: httpx.AsyncClient, start: datetime, end: datetime) -> list[Actual]:
    # settlementDate is the UK local date, so widen by a day each side and filter on startTime
    rows: list[dict[str, Any]] = []
    for a, b in _chunks(start.date() - timedelta(days=1), end.date() + timedelta(days=1), CHUNK):
        rows += await _get(
            client,
            "/datasets/FUELHH/stream",
            {
                "settlementDateFrom": a.isoformat(),
                "settlementDateTo": (b - timedelta(days=1)).isoformat(),  # inclusive
                "fuelType": "WIND",
            },
        )
    return parse_actuals(rows, start, end)


async def fetch_forecasts(client: httpx.AsyncClient, start: datetime, end: datetime) -> list[Forecast]:
    rows: list[dict[str, Any]] = []
    for a, b in _chunks(start - FORECAST_LOOKBACK, end, CHUNK):
        # Chunk edges may return the same run twice; parse_forecasts removes duplicates
        rows += await _get(
            client,
            "/datasets/WINDFOR/stream",
            {"publishDateTimeFrom": to_iso(a), "publishDateTimeTo": to_iso(b)},
        )
    return parse_forecasts(rows, start, end)
