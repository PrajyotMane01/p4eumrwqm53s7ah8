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
