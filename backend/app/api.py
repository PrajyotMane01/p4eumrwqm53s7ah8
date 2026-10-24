from datetime import date, time, timedelta
from typing import Annotated

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query

from app.analysis.selection import DEFAULT_CUTOFF, UK, half_hours, select_day_ahead
from app.data_store import Snapshot, get_data_store
from app.db import DatabaseError
from app.schemas import Coverage, Series, SeriesPoint

MAX_RANGE_DAYS = 62

router = APIRouter()


async def snapshot() -> Snapshot:
    try:
        # Created inside the try: missing credentials are a database problem (503), not a crash
        return await get_data_store().get()
    except DatabaseError as exc:
        raise HTTPException(status_code=503, detail="Database unavailable") from exc


def _delivery_dates(snap: Snapshot) -> tuple[date | None, date | None]:
    """First and last UK delivery days with a complete set of actuals (46, 48 or 50 half-hours)."""
    counts = snap.actuals["start_time"].dt.tz_convert(UK).dt.date.value_counts()
    complete = sorted(day for day, n in counts.items() if n == len(half_hours(day, day + timedelta(days=1))))
    return (complete[0], complete[-1]) if complete else (None, None)


def _none_if_missing(value: object) -> object:
    return None if pd.isna(value) else value


@router.get("/coverage", response_model=Coverage)
async def coverage(snap: Annotated[Snapshot, Depends(snapshot)]) -> Coverage:
    first, last = _delivery_dates(snap)
    return Coverage(first_date=first, last_date=last, refreshed_at=snap.refreshed_at, default_cutoff=DEFAULT_CUTOFF)


@router.get("/series", response_model=Series)
async def series(
    snap: Annotated[Snapshot, Depends(snapshot)],
    start: Annotated[date | None, Query(description="First UK delivery day (inclusive)")] = None,
    end: Annotated[date | None, Query(description="Last UK delivery day (inclusive)")] = None,
    cutoff: Annotated[time, Query(description="Decision cutoff, UK time on the day before delivery")] = DEFAULT_CUTOFF,
) -> Series:
    """Actual wind generation and the day-ahead forecast available at the cutoff, per half-hour."""
    first, last = _delivery_dates(snap)
    end = end or last
    if start is None and end is not None:
        # Default to as much of the stored range as one request allows
        start = max(first or end, end - timedelta(days=MAX_RANGE_DAYS - 1))
    if start is None or end is None:
        return Series(start=date.today(), end=date.today(), cutoff=cutoff, points=[])
    if start > end:
        raise HTTPException(status_code=422, detail="start must be on or before end")
    if (end - start).days + 1 > MAX_RANGE_DAYS:
        raise HTTPException(status_code=422, detail=f"range is limited to {MAX_RANGE_DAYS} days")

    rows = select_day_ahead(snap.actuals, snap.forecasts, start, end + timedelta(days=1), cutoff)
    points = [
        SeriesPoint(
            start_time=row.start_time,
            actual_mw=_none_if_missing(row.actual_mw),
            forecast_mw=_none_if_missing(row.forecast_mw),
            publish_time=_none_if_missing(row.publish_time),
            horizon_hours=_none_if_missing(row.horizon_hours),
        )
        for row in rows.itertuples(index=False)
    ]
    return Series(start=start, end=end, cutoff=cutoff, points=points)
