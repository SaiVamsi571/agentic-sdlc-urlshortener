"""
Thread-Safe SQLite Repository Implementation for URL Shortener.
Uses parameterized queries exclusively to prevent SQL injection and enforce compliance.
"""
import json
import sqlite3
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from src.service.models import (
    AnalyticsSummary,
    BrowserStat,
    ClickEventRecord,
    DateClickCount,
    DeviceStat,
    ReferrerStat,
    ShortURLRecord,
    SystemStats
)
from src.service.storage.base import BaseURLRepository

class SQLiteURLRepository(BaseURLRepository):
    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self._lock = threading.RLock()
        self._start_time = time.time()
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock:
            cursor = self._conn.cursor()
            # 1. URLs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS short_urls (
                    short_code TEXT PRIMARY KEY,
                    original_url TEXT NOT NULL,
                    custom_alias TEXT UNIQUE,
                    created_at TEXT NOT NULL,
                    expires_at TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    tags_json TEXT
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_urls_original ON short_urls (original_url)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_urls_alias ON short_urls (custom_alias)")

            # 2. Click events table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS click_events (
                    event_id TEXT PRIMARY KEY,
                    short_code TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    ip_hash TEXT NOT NULL,
                    referrer TEXT,
                    user_agent TEXT,
                    device_type TEXT NOT NULL,
                    browser TEXT NOT NULL,
                    country TEXT,
                    utm_source TEXT,
                    utm_medium TEXT,
                    utm_campaign TEXT,
                    FOREIGN KEY (short_code) REFERENCES short_urls (short_code)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_clicks_code ON click_events (short_code)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_clicks_time ON click_events (timestamp)")
            self._conn.commit()

    def save_url(self, record: ShortURLRecord) -> bool:
        with self._lock:
            try:
                cursor = self._conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO short_urls (
                        short_code, original_url, custom_alias, created_at, expires_at, is_active, tags_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.short_code,
                        record.original_url,
                        record.custom_alias,
                        record.created_at.isoformat(),
                        record.expires_at.isoformat() if record.expires_at else None,
                        1 if record.is_active else 0,
                        json.dumps(record.tags)
                    )
                )
                self._conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def get_url(self, short_code: str) -> Optional[ShortURLRecord]:
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                """
                SELECT short_code, original_url, custom_alias, created_at, expires_at, is_active, tags_json
                FROM short_urls
                WHERE short_code = ? OR custom_alias = ?
                """,
                (short_code, short_code)
            )
            row = cursor.fetchone()
            if not row:
                return None

            return ShortURLRecord(
                short_code=row["short_code"],
                original_url=row["original_url"],
                custom_alias=row["custom_alias"],
                created_at=datetime.fromisoformat(row["created_at"]),
                expires_at=datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None,
                is_active=bool(row["is_active"]),
                tags=json.loads(row["tags_json"] or "{}")
            )

    def get_by_original_url(self, original_url: str) -> Optional[ShortURLRecord]:
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                """
                SELECT short_code, original_url, custom_alias, created_at, expires_at, is_active, tags_json
                FROM short_urls
                WHERE original_url = ? AND (expires_at IS NULL OR expires_at > datetime('now'))
                LIMIT 1
                """,
                (original_url,)
            )
            row = cursor.fetchone()
            if not row:
                return None

            return ShortURLRecord(
                short_code=row["short_code"],
                original_url=row["original_url"],
                custom_alias=row["custom_alias"],
                created_at=datetime.fromisoformat(row["created_at"]),
                expires_at=datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None,
                is_active=bool(row["is_active"]),
                tags=json.loads(row["tags_json"] or "{}")
            )

    def is_code_taken(self, code: str) -> bool:
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                "SELECT 1 FROM short_urls WHERE short_code = ? OR custom_alias = ?",
                (code, code)
            )
            return cursor.fetchone() is not None

    def record_click(self, event: ClickEventRecord) -> None:
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                """
                INSERT INTO click_events (
                    event_id, short_code, timestamp, ip_hash, referrer,
                    user_agent, device_type, browser, country, utm_source, utm_medium, utm_campaign
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.short_code,
                    event.timestamp.isoformat(),
                    event.ip_hash,
                    event.referrer,
                    event.user_agent,
                    event.device_type,
                    event.browser,
                    event.country,
                    event.utm_source,
                    event.utm_medium,
                    event.utm_campaign
                )
            )
            self._conn.commit()

    def get_analytics(self, short_code: str) -> Optional[AnalyticsSummary]:
        with self._lock:
            url_record = self.get_url(short_code)
            if not url_record:
                return None

            actual_code = url_record.short_code
            cursor = self._conn.cursor()

            # Total clicks and unique visitors
            cursor.execute(
                """
                SELECT COUNT(*) as total_clicks, COUNT(DISTINCT ip_hash) as unique_visitors
                FROM click_events
                WHERE short_code = ?
                """,
                (actual_code,)
            )
            totals = cursor.fetchone()
            total_clicks = totals["total_clicks"] if totals else 0
            unique_visitors = totals["unique_visitors"] if totals else 0

            # Clicks by date (timeseries)
            cursor.execute(
                """
                SELECT substr(timestamp, 1, 10) as click_date, COUNT(*) as count
                FROM click_events
                WHERE short_code = ?
                GROUP BY click_date
                ORDER BY click_date ASC
                LIMIT 30
                """,
                (actual_code,)
            )
            date_stats = [DateClickCount(date=r["click_date"], clicks=r["count"]) for r in cursor.fetchall()]

            # Top referrers
            cursor.execute(
                """
                SELECT coalesce(referrer, 'Direct / None') as ref, COUNT(*) as count
                FROM click_events
                WHERE short_code = ?
                GROUP BY ref
                ORDER BY count DESC
                LIMIT 10
                """,
                (actual_code,)
            )
            referrer_stats = [ReferrerStat(referrer=r["ref"], count=r["count"]) for r in cursor.fetchall()]

            # Devices
            cursor.execute(
                """
                SELECT device_type, COUNT(*) as count
                FROM click_events
                WHERE short_code = ?
                GROUP BY device_type
                ORDER BY count DESC
                """,
                (actual_code,)
            )
            device_stats = [DeviceStat(device=r["device_type"], count=r["count"]) for r in cursor.fetchall()]

            # Browsers
            cursor.execute(
                """
                SELECT browser, COUNT(*) as count
                FROM click_events
                WHERE short_code = ?
                GROUP BY browser
                ORDER BY count DESC
                """,
                (actual_code,)
            )
            browser_stats = [BrowserStat(browser=r["browser"], count=r["count"]) for r in cursor.fetchall()]

            return AnalyticsSummary(
                short_code=actual_code,
                original_url=url_record.original_url,
                total_clicks=total_clicks,
                unique_visitors=unique_visitors,
                created_at=url_record.created_at,
                expires_at=url_record.expires_at,
                clicks_by_date=date_stats,
                top_referrers=referrer_stats,
                devices=device_stats,
                browsers=browser_stats
            )

    def get_system_stats(self) -> SystemStats:
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("SELECT COUNT(*) as c FROM short_urls")
            total_urls = cursor.fetchone()["c"]

            cursor.execute("SELECT COUNT(*) as c FROM click_events")
            total_clicks = cursor.fetchone()["c"]

            cursor.execute("SELECT COUNT(*) as c FROM short_urls WHERE expires_at IS NOT NULL AND expires_at <= datetime('now')")
            expired_urls = cursor.fetchone()["c"]

            active_urls = total_urls - expired_urls
            uptime = time.time() - self._start_time

            return SystemStats(
                service_name="Enterprise URL Shortener Service",
                uptime_seconds=round(uptime, 1),
                total_urls=total_urls,
                total_clicks=total_clicks,
                active_urls=active_urls,
                expired_urls=expired_urls
            )
