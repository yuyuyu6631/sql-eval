from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    app_name: str = "Text-to-SQL Evaluation Platform"
    app_version: str = "1.0.0"
    database_url: str = "sqlite+aiosqlite:///./text2sql.db"
    cors_origins: list = [
        "http://localhost:5173", 
        "http://127.0.0.1:5173",
        "http://192.168.8.113:5173"
    ]
    debug: bool = False

    # Sandbox settings
    query_timeout_seconds: int = 5
    max_result_rows: int = 100
    rate_limit_qps: int = 10

    # LLM settings (optional)
    judge_llm_endpoint: Optional[str] = None
    judge_llm_api_key: Optional[str] = None
    judge_llm_default_model: Optional[str] = None

    class Config:
        env_file = ".env"

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug_value(cls, value):
        """Accept common deployment values like 'release'/'production' as False."""
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "prod", "production"}:
                return False
            if normalized in {"debug", "dev", "development"}:
                return True
        return value


settings = Settings()
