import subprocess
from datetime import UTC, datetime, timedelta

import pytest

from app import wrangler_auth
from app.wrangler_auth import WranglerAuthError, WranglerToken


def write_config(path, token: str, expires_in: timedelta) -> None:
    expires = (datetime.now(UTC) + expires_in).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    path.write_text(f'oauth_token = "{token}"\nexpiration_time = "{expires}"\nrefresh_token = "r"\n')


def test_uses_valid_token_without_running_wrangler(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = tmp_path / "default.toml"
    write_config(config, "good", timedelta(hours=1))
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: pytest.fail("wrangler should not run"))
    assert WranglerToken(config).get() == "good"


def test_renews_token_close_to_expiry(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = tmp_path / "default.toml"
    write_config(config, "old", timedelta(minutes=1))

    def fake_wrangler(cmd, **kwargs):
        assert cmd == wrangler_auth.WRANGLER_CMD
        write_config(config, "new", timedelta(hours=1))  # what `wrangler whoami` does

    monkeypatch.setattr(subprocess, "run", fake_wrangler)
    assert WranglerToken(config).get() == "new"


def test_reports_expired_login(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = tmp_path / "default.toml"
    write_config(config, "old", timedelta(hours=-1))
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: None)  # renewal does nothing
    with pytest.raises(WranglerAuthError, match="wrangler login"):
        WranglerToken(config).get()


def test_reports_missing_config(tmp_path) -> None:
    with pytest.raises(WranglerAuthError, match="Cannot read"):
        WranglerToken(tmp_path / "missing.toml").get()


def test_explains_how_to_renew_when_npx_is_missing(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = tmp_path / "default.toml"
    write_config(config, "old", timedelta(hours=-1))

    def no_npx(*args, **kwargs):
        raise FileNotFoundError("npx")

    monkeypatch.setattr(subprocess, "run", no_npx)
    with pytest.raises(WranglerAuthError, match="on the host"):
        WranglerToken(config).get()
