import math
from datetime import date

import pandas as pd
import pytest

from app.analysis import metrics


def selection(rows: list[tuple[str, float | None, float | None]]) -> pd.DataFrame:
    """Rows of (UTC start time, actual, forecast), shaped like select_day_ahead output."""
    df = pd.DataFrame(rows, columns=["start_time", "actual_mw", "forecast_mw"])
    df["start_time"] = pd.to_datetime(df["start_time"], utc=True)
    df["delivery_date"] = df["start_time"].dt.tz_convert("Europe/London").dt.date
    return df.astype({"actual_mw": float, "forecast_mw": float})


# Errors (forecast - actual): +10, -10, +30; two rows cannot be scored
ROWS = [
    ("2026-01-15T06:00Z", 100, 110),
    ("2026-01-15T06:30Z", 100, 90),
    ("2026-01-16T18:00Z", 100, 130),
    ("2026-01-16T18:30Z", None, 100),
    ("2026-01-16T19:00Z", 100, None),
]


def test_summary_values_by_hand() -> None:
    s = metrics.summarise(selection(ROWS))
    assert s is not None
    assert (s.half_hours, s.missing) == (3, 2)
    assert s.bias_mw == pytest.approx(10)
    assert s.mae_mw == pytest.approx(50 / 3)
    assert s.rmse_mw == pytest.approx(math.sqrt((100 + 100 + 900) / 3))
    assert s.mae_pct == pytest.approx(50 / 3)  # mean actual is 100
    assert s.over_forecast_share == pytest.approx(2 / 3)
    # Linear interpolation between sorted errors -10, 10, 30
    assert s.percentiles_mw == pytest.approx({10: -6, 50: 10, 90: 26})


def test_summary_is_none_when_nothing_can_be_scored() -> None:
    assert metrics.summarise(selection([("2026-01-15T06:00Z", None, 100)])) is None


def test_histogram_uses_fixed_bins_and_counts_every_error() -> None:
    bins = metrics.histogram(selection(ROWS), bin_mw=1000)
    assert bins == [
        {"from_mw": -1000.0, "to_mw": 0.0, "count": 1},
        {"from_mw": 0.0, "to_mw": 1000.0, "count": 2},
    ]
    wide = selection([("2026-01-15T00:00Z", 0, 2500), ("2026-01-15T00:30Z", 3000, 0)])
    counts = [b["count"] for b in metrics.histogram(wide, bin_mw=1000)]
    assert sum(counts) == 2 and len(counts) == 6  # -3000..3000, empty bins kept


def test_by_hour_uses_uk_time() -> None:
    summer = selection([("2026-07-15T06:00Z", 100, 120), ("2026-07-15T06:30Z", 100, 80)])
    [row] = metrics.by_hour(summer)
    assert row["hour"] == 7  # 06:00 UTC is 07:00 BST
    assert (row["half_hours"], row["bias_mw"], row["mae_mw"]) == (2, 0, 20)


def test_by_forecast_level_bands() -> None:
    rows = selection([("2026-01-15T00:00Z", 4000, 4500), ("2026-01-15T00:30Z", 18000, 21000)])
    levels = metrics.by_forecast_level(rows)
    assert [(b["from_mw"], b["to_mw"], b["bias_mw"]) for b in levels] == [(0.0, 5000.0, 500.0), (20000.0, None, 3000.0)]


def test_worst_days_sorted_by_mae() -> None:
    days = metrics.worst_days(selection(ROWS))
    assert [d["delivery_date"] for d in days] == [date(2026, 1, 16), date(2026, 1, 15)]
    assert days[0]["mae_mw"] == 30 and days[0]["max_abs_error_mw"] == 30
