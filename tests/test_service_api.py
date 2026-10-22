"""
Integration Tests for URL Shortener HTTP Endpoints.
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
    # Fresh in-memory DB per test session
    repo = SQLiteURLRepository(":memory:")
    svc = URLShortenerService(repo=repo)
    set_service(svc)
    app = create_app()
    return TestClient(app)

def test_shorten_url_success(client):
    response = client.post("/api/v1/shorten", json={
        "original_url": "https://www.example.com/investment-products",
        "tags": {"campaign": "q4_onboarding"}
    })
    assert response.status_code == 201
    data = response.json()
    assert "short_code" in data
    assert len(data["short_code"]) == 7
    assert data["original_url"] == "https://www.example.com/investment-products"
    assert data["is_custom_alias"] is False
    assert data["tags"]["campaign"] == "q4_onboarding"

def test_shorten_url_idempotent(client):
    # Same URL should return same short code
    url = "https://www.example.com/ira"
    res1 = client.post("/api/v1/shorten", json={"original_url": url})
    res2 = client.post("/api/v1/shorten", json={"original_url": url})
    assert res1.status_code == 201
    assert res2.status_code == 201
    assert res1.json()["short_code"] == res2.json()["short_code"]

def test_shorten_url_with_custom_alias(client):
    res = client.post("/api/v1/shorten", json={
        "original_url": "https://www.example.com/trading",
        "custom_alias": "quick-trade"
    })
    assert res.status_code == 201
    data = res.json()
    assert data["short_code"] == "quick-trade"
    assert data["is_custom_alias"] is True

def test_custom_alias_conflict(client):
    client.post("/api/v1/shorten", json={
        "original_url": "https://www.example.com/one",
        "custom_alias": "my-shared-code"
    })
    # Attempting to reuse same alias for another URL
    res2 = client.post("/api/v1/shorten", json={
        "original_url": "https://www.example.com/two",
        "custom_alias": "my-shared-code"
    })
    assert res2.status_code == 409
    assert "already in use" in res2.json()["detail"]

def test_redirect_307(client):
    # Create URL
    res_create = client.post("/api/v1/shorten", json={
        "original_url": "https://news.google.com"
    })
    short_code = res_create.json()["short_code"]

    # Redirect
    res_redirect = client.get(f"/{short_code}", follow_redirects=False)
    assert res_redirect.status_code == 307
    assert res_redirect.headers["location"] == "https://news.google.com"

def test_redirect_missing_404(client):
    res = client.get("/nonexistent_code", follow_redirects=False)
    assert res.status_code == 404

def test_expired_url_410(client):
    # Create with 1 second TTL
    res_create = client.post("/api/v1/shorten", json={
        "original_url": "https://www.example.com/expiring",
        "ttl_seconds": 60  # minimum allowed is 60s in model
    })
    short_code = res_create.json()["short_code"]

    # Manually expire in DB to test 410 handling
    from src.service.routers.url import get_service
    from datetime import datetime, timezone, timedelta
    svc = get_service()
    past_date = datetime.now(timezone.utc) - timedelta(hours=1)
    with svc.repo._lock:
        svc.repo._conn.execute(
            "UPDATE short_urls SET expires_at = ? WHERE short_code = ?",
            (past_date.isoformat(), short_code)
        )
        svc.repo._conn.commit()
    svc.cache.delete(short_code)

    res_expired = client.get(f"/{short_code}", follow_redirects=False)
    assert res_expired.status_code == 410
    assert "expired" in res_expired.json()["detail"].lower()

def test_redirect_simulate_click(client):
    res_create = client.post("/api/v1/shorten", json={
        "original_url": "https://www.example.com/simulate"
    })
    short_code = res_create.json()["short_code"]

    # Simulated click returns 200 JSON with target URL instead of 307
    res_sim = client.get(f"/{short_code}?simulate=true")
    assert res_sim.status_code == 200
    data = res_sim.json()
    assert data["status"] == "CLICK_RECORDED"
    assert data["short_code"] == short_code
    assert data["target_url"] == "https://www.example.com/simulate"

    # Verify analytics counter incremented
    res_analytics = client.get(f"/api/v1/analytics/{short_code}")
    assert res_analytics.status_code == 200
    assert res_analytics.json()["total_clicks"] >= 1

