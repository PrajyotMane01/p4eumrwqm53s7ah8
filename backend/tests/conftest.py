from collections.abc import Iterator

import pytest

from app.config import get_settings
from app.data_store import get_data_store
from app.db import get_default_database
from app.ingest import elexon


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch: pytest.MonkeyPatch, tmp_path) -> Iterator[None]:
    """Each test gets its own SQLite file and fresh cached settings and database."""
    monkeypatch.setenv("DB_BACKEND", "sqlite")
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "test.db"))
    monkeypatch.setattr(elexon, "RETRY_DELAY", 0)
    caches = (get_settings, get_default_database, get_data_store)
    for cache in caches:
        cache.cache_clear()
    yield
    for cache in caches:
        cache.cache_clear()
