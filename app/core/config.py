from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = "sqlite:///./widgetforge.db"
    jwt_secret: str = "development-only-change-me"
    jwt_expire_minutes: int = 60
    public_base_url: str = "http://localhost:8000"
    max_submission_bytes: int = 16384
    rate_limit_max_requests: int = 5
    rate_limit_window_seconds: int = 60
    ip_hash_secret: str = "development-ip-hash-secret"
    notifier_mode: str = "console"
    webhook_url: str = ""
    webhook_secret: str = ""
    webhook_previous_secret: str = ""
    webhook_timeout_seconds: float = 5.0
    geo_enrichment_enabled: bool = False
    geo_request_timeout_seconds: float = 1.5
    outbox_poll_seconds: float = 2.0

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

@lru_cache
def get_settings() -> Settings:
    return Settings()
