"""Accuracy of the day-ahead forecasts selected by `select_day_ahead`.

Error is forecast minus actual, in MW: positive means the forecast was too high
(over-forecast), so a trader relying on it would have bought too little.
Only half-hours with both an actual and a forecast are scored.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from app.analysis.selection import UK

PERCENTILES = (10, 50, 90)
HISTOGRAM_BIN_MW = 1000
LEVEL_BANDS_MW = (0, 5000, 10000, 15000, 20000, np.inf)
WORST_DAYS = 5


@dataclass(frozen=True)
class Summary:
    half_hours: int  # scored half-hours
    missing: int  # half-hours without an actual or a forecast
    mean_actual_mw: float
    mean_forecast_mw: float
    bias_mw: float
    mae_mw: float
    rmse_mw: float
    mae_pct: float  # MAE as % of mean actual
    percentiles_mw: dict[int, float]  # error percentiles
    over_forecast_share: float  # share of half-hours where forecast > actual


def _scored(selection: pd.DataFrame) -> pd.DataFrame:
    scored = selection.dropna(subset=["actual_mw", "forecast_mw"]).copy()
    scored["error_mw"] = scored["forecast_mw"] - scored["actual_mw"]
    return scored


def summarise(selection: pd.DataFrame) -> Summary | None:
    scored = _scored(selection)
    if scored.empty:
        return None
    err = scored["error_mw"]
    mean_actual = float(scored["actual_mw"].mean())
    mae = float(err.abs().mean())
    return Summary(
        half_hours=len(scored),
        missing=len(selection) - len(scored),
        mean_actual_mw=mean_actual,
        mean_forecast_mw=float(scored["forecast_mw"].mean()),
        bias_mw=float(err.mean()),
        mae_mw=mae,
        rmse_mw=float(np.sqrt((err**2).mean())),
        mae_pct=mae / mean_actual * 100 if mean_actual else float("nan"),
        percentiles_mw={p: float(np.percentile(err, p)) for p in PERCENTILES},
        over_forecast_share=float((err > 0).mean()),
    )


def histogram(selection: pd.DataFrame, bin_mw: int = HISTOGRAM_BIN_MW) -> list[dict]:
    """Counts of errors in fixed-width bins, empty bins included so the shape is honest."""
    err = _scored(selection)["error_mw"]
    if err.empty:
        return []
    lo = np.floor(err.min() / bin_mw) * bin_mw
    hi = np.ceil(err.max() / bin_mw) * bin_mw
    if hi == lo:
        hi = lo + bin_mw
    edges = np.arange(lo, hi + bin_mw, bin_mw)
    counts, _ = np.histogram(err, bins=edges)
    return [
        {"from_mw": float(a), "to_mw": float(b), "count": int(n)}
        for a, b, n in zip(edges[:-1], edges[1:], counts, strict=True)
    ]


def _group_stats(scored: pd.DataFrame, key: pd.Series) -> pd.DataFrame:
    return scored.groupby(key, observed=True)["error_mw"].agg(
        half_hours="size",
        bias_mw="mean",
        mae_mw=lambda e: e.abs().mean(),
    )


def by_hour(selection: pd.DataFrame) -> list[dict]:
    """Bias and MAE for each UK hour of the day."""
    scored = _scored(selection)
    if scored.empty:
        return []
    hours = scored["start_time"].dt.tz_convert(UK).dt.hour.rename("hour")
    stats = _group_stats(scored, hours)
    return [{"hour": int(h), **row} for h, row in stats.to_dict("index").items()]


def by_forecast_level(selection: pd.DataFrame) -> list[dict]:
    """Bias and MAE grouped by how much wind was forecast."""
    scored = _scored(selection)
    if scored.empty:
        return []
    bands = pd.cut(scored["forecast_mw"], LEVEL_BANDS_MW, right=False).rename("band")
    stats = _group_stats(scored, bands)
    return [
        {"from_mw": float(band.left), "to_mw": None if np.isinf(band.right) else float(band.right), **row}
        for band, row in stats.to_dict("index").items()
    ]


def worst_days(selection: pd.DataFrame, limit: int = WORST_DAYS) -> list[dict]:
    """Delivery days with the largest MAE."""
    scored = _scored(selection)
    if scored.empty:
        return []
    stats = scored.groupby("delivery_date")["error_mw"].agg(
        half_hours="size",
        bias_mw="mean",
        mae_mw=lambda e: e.abs().mean(),
        max_abs_error_mw=lambda e: e.abs().max(),
    )
    top = stats.sort_values("mae_mw", ascending=False).head(limit)
    return [{"delivery_date": day, **row} for day, row in top.to_dict("index").items()]
