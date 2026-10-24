"""Command line entry point.

python -m app.ingest migrate
python -m app.ingest refresh [--start 2026-01-01] [--end 2026-02-02]
"""

import argparse
import asyncio
import logging
from datetime import UTC, date, datetime

import httpx

from app.config import get_settings
from app.db import get_database
from app.ingest.refresh import refresh
from app.ingest.store import migrate

# Decisions made in January 2026 cover delivery from 1 Jan up to and including 1 Feb
DEFAULT_START = date(2026, 1, 1)
DEFAULT_END = date(2026, 2, 2)

log = logging.getLogger("ingest")


def _utc_midnight(day: date) -> datetime:
    return datetime(day.year, day.month, day.day, tzinfo=UTC)


async def _main(args: argparse.Namespace) -> None:
    settings = get_settings()
    db = get_database(settings)
    if args.command == "migrate":
        await migrate(db)
        log.info("Migrations applied")
        return

    start, end = _utc_midnight(args.start), _utc_midnight(args.end)
    if start >= end:
        raise SystemExit("--start must be before --end")
    log.info("Refreshing target times %s to %s (end exclusive)", start.date(), end.date())
    async with httpx.AsyncClient(base_url=settings.elexon_base_url, timeout=60) as client:
        counts = await refresh(db, client, start, end)
    log.info("Stored %(actuals)d actuals and %(forecasts)d forecasts", counts)


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.ingest")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("migrate", help="create or update database tables")
    ref = sub.add_parser("refresh", help="fetch data from Elexon and store it")
    ref.add_argument("--start", type=date.fromisoformat, default=DEFAULT_START, help="first target date (UTC)")
    ref.add_argument("--end", type=date.fromisoformat, default=DEFAULT_END, help="end target date, exclusive (UTC)")

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    asyncio.run(_main(parser.parse_args()))


if __name__ == "__main__":
    main()
