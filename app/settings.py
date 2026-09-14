from __future__ import annotations

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")

    DATABASE_URL: str = "sqlite:///./app.db"
    SESSION_SECRET: str = "dev-secret-change-me"
    UPLOADS_DIR: str = "uploads"
    REPORTS_DIR: str = "reports"
    LOGS_DIR: str = "logs"
    SECURE_COOKIES: bool = False
    RATE_LIMIT_PER_MINUTE: int = 60
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""
    ENVIRONMENT: str = "production"
    LOG_LEVEL: str = "INFO"

    @field_validator("SECURE_COOKIES", mode="before")
    @classmethod
    def parse_secure_cookies(cls, v):
        if isinstance(v, str):
            val = v.strip().lower()
            return val in ("true", "1", "yes", "on", "t")
        return bool(v) if v is not None else False

    @field_validator("RATE_LIMIT_PER_MINUTE", mode="before")
    @classmethod
    def parse_rate_limit(cls, v):
        if isinstance(v, str):
            val = v.strip()
            if not val:
                return 60
            try:
                return int(val)
            except ValueError:
                return 60
        if v is None:
            return 60
        return v


settings = Settings()
