from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "FitMind Agent"
    environment: str = "local"
    debug: bool = True
    api_prefix: str = "/api/v1"
    web_origin: str = "http://localhost:5173"

    model_config = SettingsConfigDict(
        env_prefix="FITMIND_",
        env_file=".env",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
