from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parent
STATIC_DIR = APP_DIR / "static"
TEMPLATES_DIR = APP_DIR / "templates"
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_DB_PATH = DEFAULT_DATA_DIR / "eto_zhe_helper.db"
DEFAULT_DATABASE_URL = f"sqlite:///{DEFAULT_DB_PATH.as_posix()}"
DEFAULT_KNOWLEDGE_BASE_DIR = PROJECT_ROOT / "knowledge_base"


class Settings(BaseSettings):
    """Application settings with safe local defaults."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="EtoZheHelper", alias="APP_NAME")
    app_env: str = Field(default="dev", alias="APP_ENV")
    database_url: str = Field(default=DEFAULT_DATABASE_URL, alias="DATABASE_URL")
    knowledge_base_dir: Path = Field(default=DEFAULT_KNOWLEDGE_BASE_DIR, alias="KNOWLEDGE_BASE_DIR")
    max_search_results: int = Field(default=5, alias="MAX_SEARCH_RESULTS", ge=1, le=20)


@lru_cache
def get_settings() -> Settings:
    return Settings()
