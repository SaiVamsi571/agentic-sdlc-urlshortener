"""
URL Shortener Service Configuration.
"""

from __future__ import annotations
import os

from pydantic import BaseModel

from src.constants import (
    DEFAULT_CACHE_MAX_SIZE,
    DEFAULT_CACHE_TTL_SECONDS,
    DEFAULT_DB_PATH,
    DEFAULT_ENCODER_SALT,
    DEFAULT_RATE_LIMIT_READ_PER_MIN,
    DEFAULT_RATE_LIMIT_WRITE_PER_MIN,
    DEFAULT_TTL_DAYS,
    SERVICE_TITLE,
)


class ServiceSettings(BaseModel):
    """Configuration for the URL Shortener microservice."""

    service_name: str = SERVICE_TITLE
    base_url: str = os.getenv("SHORTENER_BASE_URL", "http://localhost:8000/shortener")
    salt: str = os.getenv("SHORTENER_SALT", DEFAULT_ENCODER_SALT)
    default_ttl_days: int = DEFAULT_TTL_DAYS
    code_length: int = 7
    rate_limit_write_per_min: int = DEFAULT_RATE_LIMIT_WRITE_PER_MIN
    rate_limit_read_per_min: int = DEFAULT_RATE_LIMIT_READ_PER_MIN
    cache_max_size: int = DEFAULT_CACHE_MAX_SIZE
    cache_ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS
    db_path: str = os.getenv("DB_PATH", DEFAULT_DB_PATH)


SETTINGS = ServiceSettings()
