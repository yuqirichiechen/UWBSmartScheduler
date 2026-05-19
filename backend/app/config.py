"""Application configuration management."""
from pydantic_settings import BaseSettings
from typing import Optional


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
    cache_dir: str = "../data/cache"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
