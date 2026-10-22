"""
Domain Models and Data Transfer Objects (DTOs) for URL Shortener Service.
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, HttpUrl

class ShortenRequest(BaseModel):
    original_url: str = Field(..., description="The target destination URL to shorten")
    custom_alias: Optional[str] = Field(None, max_length=30, description="Optional alphanumeric custom short code")
    ttl_seconds: Optional[int] = Field(None, ge=60, description="Optional custom time-to-live in seconds (min 60s)")
    tags: Optional[Dict[str, str]] = Field(default_factory=dict, description="Metadata tags, e.g. campaign or source")

class ShortenResponse(BaseModel):
    short_code: str
    short_url: str
    original_url: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    is_custom_alias: bool = False
    tags: Dict[str, str] = Field(default_factory=dict)

class ShortURLRecord(BaseModel):
    short_code: str
    original_url: str
    custom_alias: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    is_active: bool = True
    tags: Dict[str, str] = Field(default_factory=dict)

class ClickEventRecord(BaseModel):
    event_id: str
    short_code: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ip_hash: str # GDPR-compliant salted hash
    referrer: Optional[str] = None
    user_agent: Optional[str] = None
    device_type: str = "desktop" # mobile, desktop, tablet, bot
    browser: str = "other"
    country: Optional[str] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None

class DateClickCount(BaseModel):
    date: str
    clicks: int

class ReferrerStat(BaseModel):
    referrer: str
    count: int

class DeviceStat(BaseModel):
    device: str
    count: int

class BrowserStat(BaseModel):
    browser: str
    count: int

class AnalyticsSummary(BaseModel):
    short_code: str
    original_url: str
    total_clicks: int
    unique_visitors: int
    created_at: datetime
    expires_at: Optional[datetime] = None
    clicks_by_date: List[DateClickCount] = Field(default_factory=list)
    top_referrers: List[ReferrerStat] = Field(default_factory=list)
    devices: List[DeviceStat] = Field(default_factory=list)
    browsers: List[BrowserStat] = Field(default_factory=list)

class SystemStats(BaseModel):
    service_name: str
    uptime_seconds: float
    total_urls: int
    total_clicks: int
    active_urls: int
    expired_urls: int
