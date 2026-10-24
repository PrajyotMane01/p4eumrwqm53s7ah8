from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, Field


class Coverage(BaseModel):
    first_date: date | None = Field(description="First UK delivery day with stored actuals")
    last_date: date | None = Field(description="Last UK delivery day with stored actuals")
    refreshed_at: datetime | None = Field(description="When the data was last loaded from Elexon")
    default_cutoff: time
    source: Literal["database", "elexon"] = Field(
        description="'elexon' when the database was unavailable and data was fetched live from Elexon"
    )


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


class DayCoverage(BaseModel):
    delivery_date: date
    expected_half_hours: int = Field(description="46, 48 or 50, depending on clock changes")
    actual_half_hours: int
    forecast_runs: int = Field(description="WINDFOR runs published on this UK day")


class IngestRun(BaseModel):
    dataset: str
    range_start: datetime
    range_end: datetime
    row_count: int
    finished_at: datetime


class DataStatus(BaseModel):
    source: Literal["database", "elexon"]
    refreshed_at: datetime | None
    first_date: date | None
    last_date: date | None
    actual_rows: int
    forecast_rows: int
    forecast_runs: int = Field(description="Distinct WINDFOR publish times stored")
    first_publish_time: datetime | None
    last_publish_time: datetime | None
    days: list[DayCoverage]
    runs: list[IngestRun] = Field(description="Most recent loads, newest first; empty for live data")
