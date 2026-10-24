"""Borrow Wrangler's login for local development (D1_AUTH=wrangler).

Wrangler stores a short-lived OAuth token (about an hour) in its config file and
renews it whenever a wrangler command runs. When the token is close to expiry,
we run `wrangler whoami` to renew it, then read the file again.
"""

import logging
import subprocess
import threading
import tomllib
from datetime import UTC, datetime, timedelta
from pathlib import Path

CONFIG_FILE = Path.home() / ".config" / ".wrangler" / "config" / "default.toml"
RENEW_BEFORE = timedelta(minutes=5)
WRANGLER_CMD = ["npx", "-y", "wrangler@4", "whoami"]

log = logging.getLogger(__name__)


class WranglerAuthError(Exception):
    pass


class WranglerToken:
    def __init__(self, config_file: Path = CONFIG_FILE) -> None:
        self._config_file = config_file
        self._token = ""
        self._expires = datetime.min.replace(tzinfo=UTC)
        self._lock = threading.Lock()

    def _read(self) -> None:
        try:
            data = tomllib.loads(self._config_file.read_text())
            self._token = data["oauth_token"]
            self._expires = datetime.fromisoformat(data["expiration_time"].replace("Z", "+00:00"))
        except (OSError, KeyError, ValueError) as exc:
            raise WranglerAuthError(f"Cannot read Wrangler login from {self._config_file}: {exc}") from exc

    def _fresh(self) -> bool:
        return bool(self._token) and self._expires - datetime.now(UTC) > RENEW_BEFORE

    def get(self) -> str:
        with self._lock:
            if self._fresh():
                return self._token
            self._read()
            if self._fresh():
                return self._token
            log.info("Wrangler token expires soon, renewing it")
            try:
                subprocess.run(WRANGLER_CMD, capture_output=True, check=True, timeout=120)
            except (OSError, subprocess.SubprocessError) as exc:
                raise WranglerAuthError(f"Could not renew the Wrangler login: {exc}") from exc
            self._read()
            if not self._fresh():
                raise WranglerAuthError("Wrangler login is expired; run `npx wrangler login`")
            return self._token
