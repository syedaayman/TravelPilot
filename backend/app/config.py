"""
TravelPilot Configuration Management
Uses Pydantic BaseSettings to load and validate environment settings.
"""

from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Gemini AI
    GEMINI_API_KEY: Optional[str] = None

    # Supabase PostgreSQL
    SUPABASE_URL: Optional[str] = None
    SUPABASE_KEY: Optional[str] = None
    DATABASE_URL: Optional[str] = None

    # Operational & Frontend Integration
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    DB_MODE: str = "auto"  # 'auto', 'supabase', 'mock'
    API_PREFIX: str = "/api"
    FRONTEND_URL: str = "http://localhost:5173"
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def is_supabase_configured(self) -> bool:
        """Returns True if Supabase credentials are validly provided."""
        return bool(self.SUPABASE_URL and self.SUPABASE_KEY and "your-" not in self.SUPABASE_URL)


settings = Settings()
