"""Application configuration.

All settings are sourced from environment variables. In containers the variables come from the environment directly; for
local runs they may be supplied via a .env file.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Prozorro API
    prozorro_api_url: str = "https://public.api.openprocurement.org/api/2.5"

    # Collector
    sync_interval_minutes: int = 10
    max_tenders: int = 20000
    # Feed offset seed for the first run: Unix timestamp (default = 2025-01-01).
    initial_load_start_timestamp: int = 1735689600

    # Cache
    cache_ttl_seconds: int = 300

    # Infrastructure — required, no defaults.
    database_url: str
    redis_url: str


settings = Settings()