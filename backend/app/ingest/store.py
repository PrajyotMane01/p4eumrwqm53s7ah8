"""Write ingested rows to the database."""

from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.db import MAX_PARAMS, Database

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"


def _statements(sql: str) -> list[str]:
    """Split a migration file into statements. Comments are removed first so a ';' inside one is harmless."""
    code = "\n".join(line.split("--", 1)[0] for line in sql.splitlines())
    return [piece.strip() for piece in code.split(";") if piece.strip()]


async def migrate(db: Database) -> None:
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        for statement in _statements(path.read_text()):
            await db.query(statement)


async def upsert(db: Database, table: str, columns: Sequence[str], rows: Sequence[Sequence[Any]]) -> int:
    """Insert or replace rows in batches that stay under the bound-parameter limit."""
    per_batch = MAX_PARAMS // len(columns)
    row_placeholder = "(" + ", ".join("?" * len(columns)) + ")"
    for i in range(0, len(rows), per_batch):
        batch = rows[i : i + per_batch]
        values = ", ".join([row_placeholder] * len(batch))
        params = [value for row in batch for value in row]
        await db.query(f"INSERT OR REPLACE INTO {table} ({', '.join(columns)}) VALUES {values}", params)
    return len(rows)


async def record_run(db: Database, dataset: str, start: str, end: str, row_count: int) -> None:
    finished_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    await db.query(
        "INSERT INTO ingest_runs (dataset, range_start, range_end, row_count, finished_at) VALUES (?, ?, ?, ?, ?)",
        [dataset, start, end, row_count, finished_at],
    )
