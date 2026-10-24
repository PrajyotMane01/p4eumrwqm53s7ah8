-- Half-hourly actual wind generation (FUELHH, fuelType = WIND)
CREATE TABLE IF NOT EXISTS actuals (
    start_time    TEXT PRIMARY KEY,  -- ISO 8601 UTC
    publish_time  TEXT NOT NULL,
    generation_mw REAL NOT NULL
);

-- Hourly wind forecasts (WINDFOR); one row per forecast run and target hour
CREATE TABLE IF NOT EXISTS forecasts (
    publish_time  TEXT NOT NULL,
    start_time    TEXT NOT NULL,
    generation_mw REAL NOT NULL,
    PRIMARY KEY (publish_time, start_time)
);

CREATE INDEX IF NOT EXISTS forecasts_by_start ON forecasts (start_time, publish_time);

-- One row per completed refresh, used to show data freshness
CREATE TABLE IF NOT EXISTS ingest_runs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset       TEXT NOT NULL,
    range_start   TEXT NOT NULL,
    range_end     TEXT NOT NULL,
    row_count     INTEGER NOT NULL,
    finished_at   TEXT NOT NULL
);
