from __future__ import annotations

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


settings = Settings()

