from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str
    test_database_url: str | None = None
    upload_root: Path = Field(default=PROJECT_ROOT / "storage" / "uploads")
    max_upload_bytes: int = 20 * 1024 * 1024
    chunk_size: int = 800
    chunk_overlap: int = 100


@lru_cache
def get_settings() -> Settings:
    return Settings()
