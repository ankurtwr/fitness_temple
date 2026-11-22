"""
Application configuration loaded from environment variables.

Uses pydantic-settings so every value can be overridden via env vars or .env file.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Database ──
    DATABASE_URL: str  # e.g. mysql+mysqlconnector://user:pass@host:3306/dbname

    # ── Security ──
    SECRET_KEY: str                     # used for signing session cookies
    ADMIN_USERNAME: str = "admin"       # default admin created by seed script
    ADMIN_PASSWORD: str = "admin123"

    # ── App ──
    TIMEZONE: str = "Asia/Kolkata"
    SESSION_MAX_AGE: int = 86400        # 24 hours in seconds
    LOGIN_LOCKOUT_SECONDS: int = 300    # 5 minutes
    LOGIN_MAX_ATTEMPTS: int = 5
    CARD_ASSIGN_TTL_SECONDS: int = 30   # pending_assignment expiry

    model_config = {
        "env_file": (".env", "../.env"),
        "extra": "ignore",             # ignore extra env vars like MYSQL_*
    }


# Singleton — imported everywhere as `from app.config import settings`
settings = Settings()
