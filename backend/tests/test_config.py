import pytest

from app.config import BACKEND_DIR, Settings


def test_relative_sqlite_path_resolves_against_backend_dir(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)  # must not depend on where the server is started
    assert Settings(sqlite_path="data/wind.db").sqlite_file == BACKEND_DIR / "data" / "wind.db"


def test_absolute_sqlite_path_is_kept(tmp_path) -> None:
    assert Settings(sqlite_path=str(tmp_path / "x.db")).sqlite_file == tmp_path / "x.db"
