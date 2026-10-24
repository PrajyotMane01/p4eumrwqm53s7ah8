"""Pick the forecast a day-ahead trader would actually have had.

For every half-hour of delivery day D (a UK calendar day, 00:00-24:00 UK time), the
selected forecast is the latest WINDFOR run published at or before the decision cutoff
on D-1. The default cutoff is 09:50 UK time, the gate closure of the Nord Pool N2EX GB
day-ahead auction.

WINDFOR is hourly and actuals are half-hourly, so the forecast for hour H applies to
both the H:00 and H:30 half-hours.
"""

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pandas as pd

UK = ZoneInfo("Europe/London")
DEFAULT_CUTOFF = time(9, 50)

COLUMNS = [
    "start_time",
    "delivery_date",
    "cutoff_time",
    "actual_mw",
    "forecast_mw",
    "publish_time",
    "horizon_hours",
]


def cutoff_for(delivery_date: date, cutoff: time = DEFAULT_CUTOFF) -> datetime:
    """The decision cutoff for a delivery day: `cutoff` in UK time on the day before, as UTC."""
    return datetime.combine(delivery_date - timedelta(days=1), cutoff, tzinfo=UK).astimezone(UTC)


def uk_day_bounds(start: date, end: date) -> tuple[datetime, datetime]:
    """UTC instants spanning UK delivery days start..end-1: from UK midnight to UK midnight."""
    return (
        datetime.combine(start, time(0), tzinfo=UK).astimezone(UTC),
        datetime.combine(end, time(0), tzinfo=UK).astimezone(UTC),
    )


def _utc(values: pd.Series) -> pd.Series:
    # One resolution on both sides, as merge_asof requires matching dtypes
    return pd.to_datetime(values, utc=True).dt.as_unit("ns")


def half_hours(start: date, end: date) -> pd.DatetimeIndex:
    """Every half-hour of UK delivery days start..end-1, in UTC. DST days have 46 or 50."""
    first, last = uk_day_bounds(start, end)
    return pd.date_range(first, last, freq="30min", inclusive="left").as_unit("ns")


def select_day_ahead(
    actuals: pd.DataFrame,
    forecasts: pd.DataFrame,
    start: date,
    end: date,
    cutoff: time = DEFAULT_CUTOFF,
) -> pd.DataFrame:
    """One row per half-hour of delivery days start..end-1 with the actual and the selected forecast.

    actuals: start_time, generation_mw
    forecasts: publish_time, start_time (the target hour), generation_mw

    A half-hour with no forecast published by its cutoff, or no actual, keeps NaN in that
    column rather than being dropped, so gaps stay visible.
    """
    slots = pd.DataFrame({"start_time": half_hours(start, end)})
    slots["delivery_date"] = slots["start_time"].dt.tz_convert(UK).dt.date
    cutoffs = {day: cutoff_for(day, cutoff) for day in slots["delivery_date"].unique()}
    slots["cutoff_time"] = _utc(slots["delivery_date"].map(cutoffs))
    slots["forecast_hour"] = slots["start_time"].dt.floor("h")

    runs = pd.DataFrame(
        {
            "forecast_hour": _utc(forecasts["start_time"]),
            "publish_time": _utc(forecasts["publish_time"]),
            "forecast_mw": forecasts["generation_mw"].astype(float),
        }
    )
    # For each slot, the latest run for its hour published at or before the cutoff
    selected = pd.merge_asof(
        slots.sort_values("cutoff_time"),
        runs.sort_values("publish_time"),
        left_on="cutoff_time",
        right_on="publish_time",
        by="forecast_hour",
        direction="backward",
        allow_exact_matches=True,
    )

    observed = pd.DataFrame(
        {"start_time": _utc(actuals["start_time"]), "actual_mw": actuals["generation_mw"].astype(float)}
    )
    result = selected.merge(observed, on="start_time", how="left")
    result["horizon_hours"] = (result["start_time"] - result["publish_time"]) / pd.Timedelta(hours=1)
    return result.sort_values("start_time", ignore_index=True)[COLUMNS]
