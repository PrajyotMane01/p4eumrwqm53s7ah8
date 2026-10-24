from datetime import datetime

import httpx

from app.db import Database
from app.ingest.elexon import fetch_actuals, fetch_forecasts, to_iso
from app.ingest.store import migrate, record_run, upsert


async def refresh(db: Database, client: httpx.AsyncClient, start: datetime, end: datetime) -> dict[str, int]:
    """Replace stored actuals and forecasts with target times in [start, end) with fresh Elexon data."""
    await migrate(db)
    window = (to_iso(start), to_iso(end))

    # Fetch everything before writing, so a failed request leaves the database untouched
    actuals = await fetch_actuals(client, start, end)
    forecasts = await fetch_forecasts(client, start, end)

    # Replace the whole window, so rows Elexon no longer returns do not linger
    for table in ("actuals", "forecasts"):
        await db.query(f"DELETE FROM {table} WHERE start_time >= ? AND start_time < ?", list(window))

    await upsert(
        db,
        "actuals",
        ("start_time", "publish_time", "generation_mw"),
        [(to_iso(a.start_time), to_iso(a.publish_time), a.generation_mw) for a in actuals],
    )
    await record_run(db, "FUELHH", *window, len(actuals))
    await upsert(
        db,
        "forecasts",
        ("publish_time", "start_time", "generation_mw"),
        [(to_iso(f.publish_time), to_iso(f.start_time), f.generation_mw) for f in forecasts],
    )
    await record_run(db, "WINDFOR", *window, len(forecasts))

    return {"actuals": len(actuals), "forecasts": len(forecasts)}
