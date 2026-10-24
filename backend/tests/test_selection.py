import math
from datetime import UTC, date, datetime, time

import pandas as pd
import pytest

from app.analysis.selection import cutoff_for, half_hours, select_day_ahead

DAY = date(2026, 1, 15)  # GMT: UK time equals UTC


def utc(text: str) -> datetime:
    return datetime.fromisoformat(text).replace(tzinfo=UTC)


def frame(rows: list[tuple], columns: list[str]) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=columns)
    for col in columns:
        if col.endswith("_time"):
            df[col] = pd.to_datetime(df[col], utc=True)
    return df


def actuals(*rows: tuple[str, float]) -> pd.DataFrame:
    return frame(list(rows), ["start_time", "generation_mw"])


def forecasts(*rows: tuple[str, str, float]) -> pd.DataFrame:
    return frame(list(rows), ["publish_time", "start_time", "generation_mw"])


def slot(result: pd.DataFrame, when: str) -> pd.Series:
    return result.set_index("start_time").loc[pd.Timestamp(when, tz="UTC")]


def test_cutoff_is_0950_uk_time_on_the_day_before() -> None:
    assert cutoff_for(DAY) == utc("2026-01-14T09:50")
    assert cutoff_for(date(2026, 7, 15)) == utc("2026-07-14T08:50")  # BST is UTC+1
    assert cutoff_for(DAY, time(9, 20)) == utc("2026-01-14T09:20")


def test_half_hours_follow_uk_calendar_days() -> None:
    assert len(half_hours(DAY, date(2026, 1, 16))) == 48
    assert len(half_hours(date(2026, 3, 29), date(2026, 3, 30))) == 46  # clocks go forward
    assert len(half_hours(date(2026, 10, 25), date(2026, 10, 26))) == 50  # clocks go back
    # In summer the UK day starts at 23:00 UTC the evening before
    assert half_hours(date(2026, 7, 15), date(2026, 7, 16))[0] == pd.Timestamp("2026-07-14T23:00", tz="UTC")


def test_picks_latest_run_at_or_before_cutoff() -> None:
    target = "2026-01-15T12:00"
    result = select_day_ahead(
        actuals((target, 5000)),
        forecasts(
            ("2026-01-14T07:30", target, 4000),
            ("2026-01-14T09:50", target, 4500),  # exactly at the cutoff: counts
            ("2026-01-14T09:51", target, 9999),  # one minute late: ignored
            ("2026-01-14T11:30", target, 9999),
        ),
        DAY,
        date(2026, 1, 16),
    )
    row = slot(result, target)
    assert row["forecast_mw"] == 4500
    assert row["publish_time"] == pd.Timestamp("2026-01-14T09:50", tz="UTC")
    assert row["horizon_hours"] == pytest.approx(26 + 10 / 60)
    assert row["actual_mw"] == 5000


def test_falls_back_to_older_runs() -> None:
    target = "2026-01-15T03:00"
    result = select_day_ahead(actuals(), forecasts(("2026-01-13T22:30", target, 3000)), DAY, date(2026, 1, 16))
    assert slot(result, target)["forecast_mw"] == 3000


def test_hourly_forecast_covers_both_half_hours() -> None:
    result = select_day_ahead(
        actuals(),
        forecasts(("2026-01-14T09:30", "2026-01-15T12:00", 4200)),
        DAY,
        date(2026, 1, 16),
    )
    assert slot(result, "2026-01-15T12:00")["forecast_mw"] == 4200
    assert slot(result, "2026-01-15T12:30")["forecast_mw"] == 4200
    assert math.isnan(slot(result, "2026-01-15T13:00")["forecast_mw"])


def test_gaps_stay_visible() -> None:
    result = select_day_ahead(
        actuals(("2026-01-15T00:00", 5000)),
        forecasts(("2026-01-14T11:30", "2026-01-15T00:00", 4000)),  # only after the cutoff
        DAY,
        date(2026, 1, 16),
    )
    assert len(result) == 48
    row = slot(result, "2026-01-15T00:00")
    assert row["actual_mw"] == 5000
    assert math.isnan(row["forecast_mw"]) and pd.isna(row["publish_time"])
    assert result["actual_mw"].isna().sum() == 47


def test_summer_day_uses_uk_date_and_cutoff() -> None:
    target = "2026-07-14T23:30"  # 00:30 UK time on 15 July
    hour = "2026-07-14T23:00"  # WINDFOR targets are on the hour
    result = select_day_ahead(
        actuals(),
        forecasts(
            ("2026-07-14T07:30", hour, 1000),  # before the 08:50 UTC cutoff
            ("2026-07-14T09:30", hour, 9999),  # 10:30 UK: after the cutoff
        ),
        date(2026, 7, 15),
        date(2026, 7, 16),
    )
    row = slot(result, target)
    assert row["delivery_date"] == date(2026, 7, 15)
    assert row["forecast_mw"] == 1000


def test_empty_inputs_give_full_grid_of_gaps() -> None:
    result = select_day_ahead(actuals(), forecasts(), DAY, date(2026, 1, 17))
    assert len(result) == 96
    assert result["forecast_mw"].isna().all() and result["actual_mw"].isna().all()
