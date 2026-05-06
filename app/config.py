from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with safe local defaults."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="EtoZheHelper", alias="APP_NAME")
    app_env: str = Field(default="dev", alias="APP_ENV")
    database_url: str = Field(default="sqlite:///./data/eto_zhe_helper.db", alias="DATABASE_URL")
    knowledge_base_dir: Path = Field(default=Path("./knowledge_base"), alias="KNOWLEDGE_BASE_DIR")
    max_search_results: int = Field(default=5, alias="MAX_SEARCH_RESULTS", ge=1, le=20)


@lru_cache
def get_settings() -> Settings:
    return Settings()
