"""Database access. D1 is SQLite, so local SQLite and D1 share the same SQL."""

import asyncio
import sqlite3
from functools import lru_cache
from pathlib import Path
from typing import Any, Protocol

import httpx

from app.config import Settings, get_settings
from app.wrangler_auth import WranglerAuthError, WranglerToken

D1_API_BASE = "https://api.cloudflare.com/client/v4"

# D1 allows at most 100 bound parameters per statement; we use the same limit everywhere
MAX_PARAMS = 100


class DatabaseError(Exception):
    pass


class Database(Protocol):
    async def query(self, sql: str, params: list[Any] | None = None) -> list[dict[str, Any]]:
        """Run one SQL statement and return its rows."""
        ...


class SQLiteDatabase:
    def __init__(self, path: Path | str) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = asyncio.Lock()

    def _run(self, sql: str, params: list[Any]) -> list[dict[str, Any]]:
        try:
            with self._conn:
                rows = self._conn.execute(sql, params).fetchall()
        except sqlite3.Error as exc:
            raise DatabaseError(str(exc)) from exc
        return [dict(row) for row in rows]

    async def query(self, sql: str, params: list[Any] | None = None) -> list[dict[str, Any]]:
        async with self._lock:
            return await asyncio.to_thread(self._run, sql, params or [])


class D1Database:
    """Cloudflare D1 over its HTTP query API."""

    def __init__(self, settings: Settings, timeout: float = 30.0) -> None:
        self._url = (
            f"{D1_API_BASE}/accounts/{settings.cloudflare_account_id}/d1/database/{settings.d1_database_id}/query"
        )
        self._wrangler = WranglerToken() if settings.d1_auth == "wrangler" else None
        self._api_token = settings.cloudflare_api_token
        # One client for all queries, so a bulk load reuses the same connection
        self._client = httpx.AsyncClient(timeout=timeout)

    async def _token(self) -> str:
        if self._wrangler is None:
            return self._api_token
        try:
            # May run `wrangler whoami` to renew the login, so keep it off the event loop
            return await asyncio.to_thread(self._wrangler.get)
        except WranglerAuthError as exc:
            raise DatabaseError(str(exc)) from exc

    async def query(self, sql: str, params: list[Any] | None = None) -> list[dict[str, Any]]:
        headers = {"Authorization": f"Bearer {await self._token()}"}
        try:
            res = await self._client.post(self._url, headers=headers, json={"sql": sql, "params": params or []})
            body = res.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise DatabaseError(f"D1 request failed: {exc}") from exc
        if res.status_code != 200 or not body.get("success"):
            raise DatabaseError(f"D1 query failed: {body.get('errors')}")
        return body["result"][0]["results"]


def get_database(settings: Settings) -> Database:
    if settings.db_backend == "d1":
        if not settings.d1_configured:
            raise DatabaseError("DB_BACKEND=d1 but Cloudflare D1 credentials are missing")
        return D1Database(settings)
    return SQLiteDatabase(settings.sqlite_file)


@lru_cache
def get_default_database() -> Database:
    """The app-wide database, created once and reused across requests."""
    return get_database(get_settings())
