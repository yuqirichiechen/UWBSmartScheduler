"""Application configuration management."""
from pydantic_settings import BaseSettings
from typing import Optional
from pathlib import Path
import os


# Resolve cache dir relative to this file so it works regardless of cwd,
# both locally (cwd=backend/) and on Vercel (cwd=/var/task/).
_BACKEND_ROOT = Path(__file__).resolve().parent.parent  # .../backend
_DEFAULT_CACHE = _BACKEND_ROOT / "data" / "cache"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "UW Bothell Course Scheduler"
    environment: str = "development"
    debug: bool = True
    api_host: str = "localhost"
    api_port: int = 8000

    # LLM Configuration
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4"

    # Vector Store Configuration
    pinecone_api_key: Optional[str] = None
    pinecone_environment: Optional[str] = None
    pinecone_index_name: str = "uwbothell-courses"

    # Data Configuration
    uw_time_schedule_url: str = "https://www.bothell.uw.edu/time-schedule/"
    cache_dir: str = str(_DEFAULT_CACHE)

    # Serverless flag — set automatically by api/index.py on Vercel. When
    # truthy, the backend skips startup work that's slow on cold starts
    # (live scrape, embedding generation).
    serverless: bool = bool(os.environ.get("SMARTSCHED_SERVERLESS"))

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
