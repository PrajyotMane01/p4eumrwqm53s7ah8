"""Minimal async client for Cloudflare D1 over its HTTP query API."""

from typing import Any

import httpx

from app.config import Settings

D1_API_BASE = "https://api.cloudflare.com/client/v4"


class D1Error(Exception):
    pass


class D1Client:
    def __init__(self, settings: Settings, timeout: float = 10.0) -> None:
        self._url = (
            f"{D1_API_BASE}/accounts/{settings.cloudflare_account_id}"
            f"/d1/database/{settings.d1_database_id}/query"
        )
        self._headers = {"Authorization": f"Bearer {settings.cloudflare_api_token}"}
        self._timeout = timeout

    async def query(self, sql: str, params: list[Any] | None = None) -> list[dict[str, Any]]:
        """Run one SQL statement and return its rows."""
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            res = await client.post(
                self._url, headers=self._headers, json={"sql": sql, "params": params or []}
            )
        body = res.json()
        if res.status_code != 200 or not body.get("success"):
            raise D1Error(f"D1 query failed: {body.get('errors')}")
        return body["result"][0]["results"]
