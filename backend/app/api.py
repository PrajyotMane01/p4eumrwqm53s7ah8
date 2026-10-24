from datetime import date, time, timedelta
from typing import Annotated

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query

from app.analysis import metrics
from app.analysis.selection import DEFAULT_CUTOFF, UK, half_hours, select_day_ahead
from app.config import get_settings
from app.data_store import DataUnavailableError, Snapshot, get_data_store
from app.schemas import AccuracySummary, Coverage, DataStatus, DayCoverage, IngestRun, Metrics, Series, SeriesPoint

MAX_RANGE_DAYS = 62

router = APIRouter()


async def snapshot() -> Snapshot:
    try:
        return await get_data_store().get()
    except DataUnavailableError as exc:
        raise HTTPException(status_code=503, detail="Data unavailable") from exc


def _delivery_dates(snap: Snapshot) -> tuple[date | None, date | None]:
    """First and last UK delivery days with a complete set of actuals (46, 48 or 50 half-hours)."""
    counts = snap.actuals["start_time"].dt.tz_convert(UK).dt.date.value_counts()
    complete = sorted(day for day, n in counts.items() if n == len(half_hours(day, day + timedelta(days=1))))
    return (complete[0], complete[-1]) if complete else (None, None)


def _database_name() -> str:
    return "Cloudflare D1" if get_settings().db_backend == "d1" else "SQLite"


def _none_if_missing(value: object) -> object:
    return None if pd.isna(value) else value


@router.get("/coverage", response_model=Coverage)
async def coverage(snap: Annotated[Snapshot, Depends(snapshot)]) -> Coverage:
    first, last = _delivery_dates(snap)
    return Coverage(
        first_date=first,
        last_date=last,
        refreshed_at=snap.refreshed_at,
        default_cutoff=DEFAULT_CUTOFF,
        source=snap.source,
        database=_database_name(),
    )


StartQuery = Annotated[date | None, Query(description="First UK delivery day (inclusive)")]
EndQuery = Annotated[date | None, Query(description="Last UK delivery day (inclusive)")]
CutoffQuery = Annotated[time, Query(description="Decision cutoff, UK time on the day before delivery")]


def _range(snap: Snapshot, start: date | None, end: date | None) -> tuple[date, date] | None:
    """Fill in a missing start or end from the stored data and check the range. None if no data."""
    first, last = _delivery_dates(snap)
    end = end or last
    if start is None and end is not None:
        # Default to as much of the stored range as one request allows
        start = max(first or end, end - timedelta(days=MAX_RANGE_DAYS - 1))
    if start is None or end is None:
        return None
    if start > end:
        raise HTTPException(status_code=422, detail="start must be on or before end")
    if (end - start).days + 1 > MAX_RANGE_DAYS:
        raise HTTPException(status_code=422, detail=f"range is limited to {MAX_RANGE_DAYS} days")
    return start, end


@router.get("/series", response_model=Series)
async def series(
    snap: Annotated[Snapshot, Depends(snapshot)],
    start: StartQuery = None,
    end: EndQuery = None,
    cutoff: CutoffQuery = DEFAULT_CUTOFF,
) -> Series:
    """Actual wind generation and the day-ahead forecast available at the cutoff, per half-hour."""
    window = _range(snap, start, end)
    if window is None:
        return Series(start=date.today(), end=date.today(), cutoff=cutoff, points=[])
    start, end = window
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


@router.get("/metrics", response_model=Metrics)
async def accuracy(
    snap: Annotated[Snapshot, Depends(snapshot)],
    start: StartQuery = None,
    end: EndQuery = None,
    cutoff: CutoffQuery = DEFAULT_CUTOFF,
) -> Metrics:
    """How accurate the day-ahead forecast was over the range. Error is forecast minus actual."""
    window = _range(snap, start, end)
    if window is None:
        return Metrics(
            start=date.today(),
            end=date.today(),
            cutoff=cutoff,
            summary=None,
            histogram=[],
            by_hour=[],
            by_forecast_level=[],
            worst_days=[],
        )
    start, end = window
    rows = select_day_ahead(snap.actuals, snap.forecasts, start, end + timedelta(days=1), cutoff)
    summary = metrics.summarise(rows)
    return Metrics(
        start=start,
        end=end,
        cutoff=cutoff,
        summary=None
        if summary is None
        else AccuracySummary(
            **{k: v for k, v in vars(summary).items() if k != "percentiles_mw"},
            p10_mw=summary.percentiles_mw[10],
            p50_mw=summary.percentiles_mw[50],
            p90_mw=summary.percentiles_mw[90],
        ),
        histogram=metrics.histogram(rows),
        by_hour=metrics.by_hour(rows),
        by_forecast_level=metrics.by_forecast_level(rows),
        worst_days=metrics.worst_days(rows),
    )


@router.get("/data", response_model=DataStatus)
async def data_status(snap: Annotated[Snapshot, Depends(snapshot)]) -> DataStatus:
    """What is loaded: coverage per UK delivery day, forecast runs, and recent loads."""
    first, last = _delivery_dates(snap)
    actual_days = snap.actuals["start_time"].dt.tz_convert(UK).dt.date.value_counts()
    publish = snap.forecasts["publish_time"].drop_duplicates()
    run_days = publish.dt.tz_convert(UK).dt.date.value_counts()
    days = []
    if not actual_days.empty:
        day, final = min(actual_days.index), max(actual_days.index)
        while day <= final:
            days.append(
                DayCoverage(
                    delivery_date=day,
                    expected_half_hours=len(half_hours(day, day + timedelta(days=1))),
                    actual_half_hours=int(actual_days.get(day, 0)),
                    forecast_runs=int(run_days.get(day, 0)),
                )
            )
            day += timedelta(days=1)
    return DataStatus(
        source=snap.source,
        database=_database_name(),
        refreshed_at=snap.refreshed_at,
        first_date=first,
        last_date=last,
        actual_rows=len(snap.actuals),
        forecast_rows=len(snap.forecasts),
        forecast_runs=len(publish),
        first_publish_time=_none_if_missing(publish.min()) if len(publish) else None,
        last_publish_time=_none_if_missing(publish.max()) if len(publish) else None,
        days=days,
        runs=[IngestRun(**run) for run in snap.runs],
    )
