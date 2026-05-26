"""Application configuration.

All settings are sourced from environment variables. In containers the variables come from the environment directly; for
local runs they may be supplied via a .env file.
"""

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Prozorro API
    prozorro_api_url: str = "https://public.api.openprocurement.org/api/2.5"

    # Collector
    sync_interval_minutes: int = 10
    max_tenders: int = 20000
    # Feed offset seed for the first run: Unix timestamp (default = 2026-01-01).
    initial_load_start_timestamp: int = 1767225600

    # Collection strategy.
    #
    # * ``continuous``  — walk the feed forward from the seed timestamp until
    #   the per-cycle cap (``max_tenders``) is reached. The historical default.
    # * ``monthly``     — stratified backfill: collect up to
    #   ``monthly_quota`` records per calendar month, starting at
    #   ``monthly_start_year_month`` and walking month-by-month until
    #   ``monthly_end_year_month`` (or the current month). Each month's
    #   pagination cursor is persisted independently as a ``sync_state`` row
    #   keyed ``tenders:YYYY-MM``; a month becomes "complete" once the quota
    #   is reached or the feed crosses into the next month.
    collection_mode: Literal["continuous", "monthly"] = "continuous"
    monthly_quota: int = 2000
    monthly_start_year_month: str = "2026-01"
    monthly_end_year_month: str | None = None

    # Cache
    cache_ttl_seconds: int = 300

    # Infrastructure — required, no defaults.
    database_url: str
    redis_url: str


settings = Settings()