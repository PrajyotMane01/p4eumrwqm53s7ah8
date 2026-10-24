"""In-memory copy of the data the API serves.

The January data is fixed, and every D1 query is a network round trip, so the API
loads both tables once and keeps them for TTL. A refresh shows up after the TTL.

If the database cannot be read (expired token, outage, missing credentials) or holds
no data yet (a first start before the loader has run), the default window is fetched
straight from Elexon instead, with the same parsing the loader uses. The database is
tried again when that copy expires.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from typing import Literal

import httpx
import pandas as pd

from app.analysis.selection import uk_day_bounds
from app.config import get_settings
from app.db import Database, DatabaseError, get_default_database
from app.ingest.elexon import ElexonError, fetch_actuals, fetch_forecasts, to_iso
from app.ingest.refresh import DEFAULT_END, DEFAULT_START
from app.ingest.store import migrate

TTL_SECONDS = 15 * 60
RECENT_RUNS = 20

log = logging.getLogger(__name__)

Source = Literal["database", "elexon"]


class DataUnavailableError(Exception):
    """Neither the database nor the Elexon fallback could provide data."""


@dataclass(frozen=True)
class Snapshot:
    actuals: pd.DataFrame  # start_time, generation_mw
    forecasts: pd.DataFrame  # publish_time, start_time, generation_mw
    refreshed_at: str | None  # when the data was loaded from Elexon (UTC ISO), if known
    source: Source = "database"
    runs: tuple[dict, ...] = ()  # recent ingest runs, newest first (none for live data)


def _frame(rows: list[dict], columns: list[str]) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=columns)
    for col in columns:
        if col.endswith("_time"):
            df[col] = pd.to_datetime(df[col], utc=True)
    df["generation_mw"] = df["generation_mw"].astype(float)
    return df


async def load_snapshot(db: Database) -> Snapshot:
    await migrate(db)  # a fresh database then reads as empty rather than failing
    actuals = await db.query("SELECT start_time, generation_mw FROM actuals")
    forecasts = await db.query("SELECT publish_time, start_time, generation_mw FROM forecasts")
    runs = await db.query(
        "SELECT dataset, range_start, range_end, row_count, finished_at FROM ingest_runs ORDER BY id DESC LIMIT ?",
        [RECENT_RUNS],
    )
    return Snapshot(
        actuals=_frame(actuals, ["start_time", "generation_mw"]),
        forecasts=_frame(forecasts, ["publish_time", "start_time", "generation_mw"]),
        refreshed_at=max((r["finished_at"] for r in runs), default=None),
        runs=tuple(runs),
    )


def elexon_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=get_settings().elexon_base_url, timeout=60)


async def load_live_snapshot() -> Snapshot:
    """The default window fetched straight from Elexon, without the database."""
    start, end = uk_day_bounds(DEFAULT_START, DEFAULT_END)
    async with elexon_client() as client:
        actuals = await fetch_actuals(client, start, end)
        forecasts = await fetch_forecasts(client, start, end)
    return Snapshot(
        actuals=_frame(
            [{"start_time": a.start_time, "generation_mw": a.generation_mw} for a in actuals],
            ["start_time", "generation_mw"],
        ),
        forecasts=_frame(
            [
                {"publish_time": f.publish_time, "start_time": f.start_time, "generation_mw": f.generation_mw}
                for f in forecasts
            ],
            ["publish_time", "start_time", "generation_mw"],
        ),
        refreshed_at=to_iso(datetime.now(UTC)),
        source="elexon",
    )


class DataStore:
    def __init__(self, ttl_seconds: float = TTL_SECONDS) -> None:
        self._ttl = ttl_seconds
        self._snapshot: Snapshot | None = None
        self._loaded_at = 0.0
        self._lock = asyncio.Lock()

    async def _load(self) -> Snapshot:
        fallback = get_settings().elexon_fallback
        try:
            # The database is looked up here, so missing credentials count as a database problem
            stored = await load_snapshot(get_default_database())
        except DatabaseError as exc:
            if not fallback:
                raise DataUnavailableError(str(exc)) from exc
            log.warning("Database unavailable (%s); fetching live from Elexon", exc)
            try:
                return await load_live_snapshot()
            except ElexonError as live_exc:
                raise DataUnavailableError(f"Database and Elexon both unavailable: {live_exc}") from live_exc

        if not stored.actuals.empty or not fallback:
            return stored
        log.warning("Database has no data yet; fetching live from Elexon")
        try:
            return await load_live_snapshot()
        except ElexonError as exc:
            # The database works, so show it as empty rather than failing
            log.warning("Elexon unavailable too (%s); serving the empty database", exc)
            return stored

    async def get(self) -> Snapshot:
        # One load at a time: concurrent requests wait for the same result
        async with self._lock:
            if self._snapshot is None or time.monotonic() - self._loaded_at > self._ttl:
                self._snapshot = await self._load()
                self._loaded_at = time.monotonic()
            return self._snapshot


@lru_cache
def get_data_store() -> DataStore:
    return DataStore()
