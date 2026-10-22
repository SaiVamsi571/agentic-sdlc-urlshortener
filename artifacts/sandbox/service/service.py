"""
Core URL Shortener Service Facade.
Coordinates Encoding, Validation, Caching, Persistence, and GDPR-Compliant Analytics Tracking.
"""
import hashlib
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple
from urllib.parse import parse_qs, urlparse

from src.service.config import SETTINGS
from src.service.core.cache import LRUTTLCache
from src.service.core.encoder import Base62Encoder
from src.service.core.validator import URLValidator, ValidationError
from src.service.models import (
    AnalyticsSummary,
    ClickEventRecord,
    ShortenRequest,
    ShortenResponse,
    ShortURLRecord,
    SystemStats
)
from src.service.storage.base import BaseURLRepository
from src.service.storage.memory_sqlite import SQLiteURLRepository

class URLNotFoundError(Exception):
    pass

class URLExpiredError(Exception):
    pass

class AliasConflictError(Exception):
    pass

class URLShortenerService:
    def __init__(
        self,
        repo: Optional[BaseURLRepository] = None,
        cache: Optional[LRUTTLCache] = None,
        salt: Optional[str] = None
    ):
        self.salt = salt or SETTINGS.salt
        self.repo = repo or SQLiteURLRepository(SETTINGS.db_path)
        self.cache = cache or LRUTTLCache(max_size=SETTINGS.cache_max_size, default_ttl_seconds=SETTINGS.cache_ttl_seconds)
        self.encoder = Base62Encoder(salt=self.salt, code_length=SETTINGS.code_length)
        self.validator = URLValidator()

    def shorten_url(self, request: ShortenRequest) -> ShortenResponse:
        """
        Validates original URL, handles custom alias or generates Base62 short code,
        persists to repository, updates cache, and returns response.
        """
        # 1. URL validation & SSRF protection
        valid_url = self.validator.validate_url(request.original_url)

        # 2. Expiration calculation
        now = datetime.now(timezone.utc)
        if request.ttl_seconds is not None:
            expires_at = now + timedelta(seconds=request.ttl_seconds)
        else:
            expires_at = now + timedelta(days=SETTINGS.default_ttl_days)

        # 3. Handle custom alias vs auto-generated code
        if request.custom_alias:
            clean_alias = self.validator.validate_custom_alias(request.custom_alias)
            if self.repo.is_code_taken(clean_alias):
                raise AliasConflictError(f"Custom alias '{clean_alias}' is already in use.")
            short_code = clean_alias
            is_custom = True
        else:
            # Check for existing active mapping to avoid duplicate code creation
            existing = self.repo.get_by_original_url(valid_url)
            if existing and not existing.custom_alias:
                # Cache and return existing
                self.cache.set(existing.short_code, existing.original_url)
                return ShortenResponse(
                    short_code=existing.short_code,
                    short_url=f"{SETTINGS.base_url}/{existing.short_code}",
                    original_url=existing.original_url,
                    created_at=existing.created_at,
                    expires_at=existing.expires_at,
                    is_custom_alias=False,
                    tags=existing.tags
                )

            # Collision probing loop
            probe_attempt = 0
            while True:
                candidate_code = self.encoder.generate_code(valid_url, collision_attempt=probe_attempt)
                if not self.repo.is_code_taken(candidate_code):
                    short_code = candidate_code
                    break
                probe_attempt += 1
                if probe_attempt > 50:
                    # Fallback to random nonce if dense collision
                    short_code = self.encoder.generate_code(f"{valid_url}:{uuid.uuid4().hex[:6]}")
                    break
            is_custom = False

        record = ShortURLRecord(
            short_code=short_code,
            original_url=valid_url,
            custom_alias=short_code if is_custom else None,
            created_at=now,
            expires_at=expires_at,
            is_active=True,
            tags=request.tags or {}
        )

        saved = self.repo.save_url(record)
        if not saved:
            raise AliasConflictError(f"Code '{short_code}' experienced concurrency collision.")

        # Cache the valid mapping
        self.cache.set(short_code, valid_url)

        return ShortenResponse(
            short_code=short_code,
            short_url=f"{SETTINGS.base_url}/{short_code}",
            original_url=valid_url,
            created_at=now,
            expires_at=expires_at,
            is_custom_alias=is_custom,
            tags=request.tags or {}
        )

    def resolve_url(
        self,
        short_code: str,
        client_ip: str = "127.0.0.1",
        user_agent: Optional[str] = None,
        referrer: Optional[str] = None
    ) -> Tuple[str, ShortURLRecord]:
        """
        Resolves short code to original URL, evaluates expiration,
        records analytics, and returns (original_url, record).
        """
        # 1. Check LRU Cache
        cached_url = self.cache.get(short_code)
        
        # 2. Query Repository
        record = self.repo.get_url(short_code)
        if not record or not record.is_active:
            raise URLNotFoundError(f"Short URL code '{short_code}' not found.")

        # 3. Check Expiration
        if record.expires_at:
            now = datetime.now(timezone.utc)
            # Ensure timezone-aware comparison
            exp = record.expires_at if record.expires_at.tzinfo else record.expires_at.replace(tzinfo=timezone.utc)
            if now > exp:
                self.cache.delete(short_code)
                raise URLExpiredError(f"Short URL '{short_code}' expired at {record.expires_at.isoformat()}.")

        # 4. Cache populate if missed
        if not cached_url:
            self.cache.set(short_code, record.original_url)

        # 5. Record GDPR-compliant Analytics Event
        self._record_click_event(
            short_code=record.short_code,
            original_url=record.original_url,
            client_ip=client_ip,
            user_agent=user_agent,
            referrer=referrer
        )

        return record.original_url, record

    def _record_click_event(
        self,
        short_code: str,
        original_url: str,
        client_ip: str,
        user_agent: Optional[str],
        referrer: Optional[str]
    ) -> None:
        # GDPR Salted IP Hash
        salted_ip = f"{client_ip}:{self.salt}"
        ip_hash = hashlib.sha256(salted_ip.encode("utf-8")).hexdigest()[:16]

        # Parse User-Agent for Device & Browser
        ua = (user_agent or "").lower()
        if any(b in ua for b in ["bot", "crawler", "spider", "scraper"]):
            device_type = "bot"
        elif any(m in ua for m in ["mobi", "iphone", "android"]):
            device_type = "mobile"
        elif "ipad" in ua or "tablet" in ua:
            device_type = "tablet"
        else:
            device_type = "desktop"

        if "chrome" in ua and "edg" not in ua:
            browser = "Chrome"
        elif "firefox" in ua:
            browser = "Firefox"
        elif "safari" in ua and "chrome" not in ua:
            browser = "Safari"
        elif "edg" in ua:
            browser = "Edge"
        else:
            browser = "Other"

        # Parse UTM parameters from target URL if present
        parsed = urlparse(original_url)
        params = parse_qs(parsed.query)
        utm_source = params.get("utm_source", [None])[0]
        utm_medium = params.get("utm_medium", [None])[0]
        utm_campaign = params.get("utm_campaign", [None])[0]

        event = ClickEventRecord(
            event_id=str(uuid.uuid4()),
            short_code=short_code,
            timestamp=datetime.now(timezone.utc),
            ip_hash=ip_hash,
            referrer=referrer,
            user_agent=user_agent,
            device_type=device_type,
            browser=browser,
            utm_source=utm_source,
            utm_medium=utm_medium,
            utm_campaign=utm_campaign
        )
        self.repo.record_click(event)

    def get_analytics(self, short_code: str) -> AnalyticsSummary:
        analytics = self.repo.get_analytics(short_code)
        if not analytics:
            raise URLNotFoundError(f"Short URL code '{short_code}' not found.")
        return analytics

    def get_system_stats(self) -> SystemStats:
        return self.repo.get_system_stats()
