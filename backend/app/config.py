from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# The backend/ directory (/app in Docker); relative paths are resolved against it
BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    # "sqlite" for local development, "d1" for Cloudflare D1
    db_backend: Literal["sqlite", "d1"] = "sqlite"
    sqlite_path: str = "data/wind.db"

    cloudflare_account_id: str = ""
    d1_database_id: str = ""
    # "token" uses CLOUDFLARE_API_TOKEN; "wrangler" borrows the local Wrangler login (development only)
    d1_auth: Literal["token", "wrangler"] = "token"
    cloudflare_api_token: str = ""

    elexon_base_url: str = "https://data.elexon.co.uk/bmrs/api/v1"

    @property
    def d1_configured(self) -> bool:
        has_auth = self.d1_auth == "wrangler" or bool(self.cloudflare_api_token)
        return bool(self.cloudflare_account_id and self.d1_database_id and has_auth)

    @property
    def sqlite_file(self) -> Path:
        """sqlite_path as an absolute path, independent of the working directory."""
        return BACKEND_DIR / self.sqlite_path


@lru_cache
def get_settings() -> Settings:
    return Settings()
