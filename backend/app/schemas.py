from datetime import date, datetime, time

from pydantic import BaseModel, Field


class Coverage(BaseModel):
    first_date: date | None = Field(description="First UK delivery day with stored actuals")
    last_date: date | None = Field(description="Last UK delivery day with stored actuals")
    refreshed_at: datetime | None = Field(description="When the data was last loaded from Elexon")
    default_cutoff: time


class SeriesPoint(BaseModel):
    start_time: datetime = Field(description="Start of the half-hour, UTC")
    actual_mw: float | None
    forecast_mw: float | None = Field(description="Day-ahead forecast selected at the cutoff; null if none")
    publish_time: datetime | None = Field(description="When the selected forecast was published")
    horizon_hours: float | None = Field(description="Hours between publish time and target time")


class Series(BaseModel):
    start: date
    end: date
    cutoff: time
    points: list[SeriesPoint]


class AccuracySummary(BaseModel):
    half_hours: int = Field(description="Half-hours with both an actual and a forecast")
    missing: int = Field(description="Half-hours left out because one of the two is missing")
    mean_actual_mw: float
    mean_forecast_mw: float
    bias_mw: float = Field(description="Mean of forecast minus actual; positive means over-forecast")
    mae_mw: float
    rmse_mw: float
    mae_pct: float = Field(description="MAE as a percentage of mean actual")
    p10_mw: float = Field(description="10th percentile of forecast minus actual")
    p50_mw: float
    p90_mw: float = Field(description="90th percentile: in 9 of 10 half-hours the shortfall was at most this")
    over_forecast_share: float = Field(description="Share of half-hours where the forecast was above actual")


class HistogramBin(BaseModel):
    from_mw: float
    to_mw: float
    count: int


class HourStats(BaseModel):
    hour: int = Field(description="UK hour of day, 0-23")
    half_hours: int
    bias_mw: float
    mae_mw: float


class LevelStats(BaseModel):
    from_mw: float
    to_mw: float | None = Field(description="Upper bound of the forecast band; null means no upper bound")
    half_hours: int
    bias_mw: float
    mae_mw: float


class DayStats(BaseModel):
    delivery_date: date
    half_hours: int
    bias_mw: float
    mae_mw: float
    max_abs_error_mw: float


class Metrics(BaseModel):
    start: date
    end: date
    cutoff: time
    summary: AccuracySummary | None = Field(description="Null when no half-hour can be scored")
    histogram: list[HistogramBin]
    by_hour: list[HourStats]
    by_forecast_level: list[LevelStats]
    worst_days: list[DayStats]
