from functools import lru_cache

from pydantic import AliasChoices
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "FitMind Agent"
    environment: str = Field(
        default="local",
        validation_alias=AliasChoices("FITMIND_ENV", "FITMIND_ENVIRONMENT"),
    )
    debug: bool = True
    api_prefix: str = "/api/v1"
    web_origin: str = "http://localhost:5173"
    database_url: str = "mysql+pymysql://root:password@127.0.0.1:3306/fitmind?charset=utf8mb4"
    llm_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-v4-flash"
    llm_temperature: float = 0.7
    recent_context_rounds: int = 5
    summary_compression_workers: int = 2
    auth_secret_key: str = "local-development-only-change-me"
    auth_issuer: str = "fitmind"
    auth_audience: str = "fitmind-web"
    auth_access_token_minutes: int = 15
    auth_refresh_token_days: int = 30
    auth_refresh_cookie_name: str = "fitmind_refresh_token"
    auth_cookie_secure: bool = False

    model_config = SettingsConfigDict(
        env_prefix="FITMIND_",
        env_file=".env",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
