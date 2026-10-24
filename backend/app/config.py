from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    cloudflare_account_id: str = ""
    cloudflare_api_token: str = ""
    d1_database_id: str = ""

    @property
    def d1_configured(self) -> bool:
        return bool(self.cloudflare_account_id and self.cloudflare_api_token and self.d1_database_id)


@lru_cache
def get_settings() -> Settings:
    return Settings()
