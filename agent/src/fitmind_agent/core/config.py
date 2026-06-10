from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "FitMind Agent"
    environment: str = "local"
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

    model_config = SettingsConfigDict(
        env_prefix="FITMIND_",
        env_file=".env",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
