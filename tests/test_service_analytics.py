"""
Tests for GDPR-Compliant Click Analytics, Device Parsing, and Aggregation Reporting.
"""

from __future__ import annotations
from fastapi.testclient import TestClient
import pytest
from src.service.app import create_app
from src.service.routers.url import set_service
from src.service.service import URLShortenerService
from src.service.storage.memory_sqlite import SQLiteURLRepository

@pytest.fixture
def client():
    repo = SQLiteURLRepository(":memory:")
    svc = URLShortenerService(repo=repo)
    set_service(svc)
    app = create_app()
    return TestClient(app)

def test_click_tracking_and_gdpr_anonymization(client):
    # Create URL with UTM tracking
    res_create = client.post("/api/v1/shorten", json={
        "original_url": "https://www.example.com/landing?utm_source=linkedin&utm_medium=cpc&utm_campaign=spring2026"
    })
    short_code = res_create.json()["short_code"]

    # Perform 3 simulated clicks with different User-Agents and IPs
    client.get(
        f"/{short_code}",
        headers={"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1", "Referer": "https://linkedin.com", "X-Forwarded-For": "203.0.113.19"},
        follow_redirects=False
    )
    client.get(
        f"/{short_code}",
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36", "Referer": "https://google.com", "X-Forwarded-For": "203.0.113.20"},
        follow_redirects=False
    )
    client.get(
        f"/{short_code}",
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36", "Referer": "https://google.com", "X-Forwarded-For": "203.0.113.19"}, # Same IP as click 1
        follow_redirects=False
    )

    # Fetch Analytics Summary
    res_analytics = client.get(f"/api/v1/analytics/{short_code}")
    assert res_analytics.status_code == 200
    data = res_analytics.json()

    assert data["total_clicks"] == 3
    assert data["unique_visitors"] == 2 # 2 distinct IP hashes!

    # Check devices
    device_counts = {d["device"]: d["count"] for d in data["devices"]}
    assert device_counts.get("mobile", 0) == 1
    assert device_counts.get("desktop", 0) == 2

    # Check referrers
    ref_counts = {r["referrer"]: r["count"] for r in data["top_referrers"]}
    assert ref_counts.get("https://google.com", 0) == 2
    assert ref_counts.get("https://linkedin.com", 0) == 1

    # Verify GDPR compliance: raw IP "203.0.113.19" is NOT present anywhere in database
    from src.service.routers.url import get_service
    svc = get_service()
    with svc.repo._lock:
        rows = svc.repo._conn.execute("SELECT ip_hash FROM click_events").fetchall()
        for r in rows:
            assert "203.0.113" not in r["ip_hash"]
            assert len(r["ip_hash"]) == 16 # Salted hash truncation
