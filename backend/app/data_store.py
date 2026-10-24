"""In-memory copy of the stored data.

The January data is fixed, and every D1 query is a network round trip, so the API
loads both tables once and keeps them for TTL. A refresh shows up after the TTL.
"""

import asyncio
import time
from dataclasses import dataclass
from functools import lru_cache

import pandas as pd

from app.db import Database, get_default_database
from app.ingest.store import migrate

TTL_SECONDS = 15 * 60


@dataclass(frozen=True)
class Snapshot:
    actuals: pd.DataFrame  # start_time, generation_mw
    forecasts: pd.DataFrame  # publish_time, start_time, generation_mw
    refreshed_at: str | None  # when the newest ingest run finished (UTC ISO), if any


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
    runs = await db.query("SELECT MAX(finished_at) AS refreshed_at FROM ingest_runs")
    return Snapshot(
        actuals=_frame(actuals, ["start_time", "generation_mw"]),
        forecasts=_frame(forecasts, ["publish_time", "start_time", "generation_mw"]),
        refreshed_at=runs[0]["refreshed_at"] if runs else None,
    )


class DataStore:
    def __init__(self, db: Database, ttl_seconds: float = TTL_SECONDS) -> None:
        self._db = db
        self._ttl = ttl_seconds
        self._snapshot: Snapshot | None = None
        self._loaded_at = 0.0
        self._lock = asyncio.Lock()

    async def get(self) -> Snapshot:
        async with self._lock:
            if self._snapshot is None or time.monotonic() - self._loaded_at > self._ttl:
                self._snapshot = await load_snapshot(self._db)
                self._loaded_at = time.monotonic()
            return self._snapshot


@lru_cache
def get_data_store() -> DataStore:
    return DataStore(get_default_database())
