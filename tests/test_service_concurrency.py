"""
Concurrency Stress Tests for URL Shortener Service.
Validates thread-safety, race condition avoidance, and locking integrity under concurrent workloads.
"""

from __future__ import annotations
import concurrent.futures
from src.service.models import ShortenRequest
from src.service.service import URLShortenerService
from src.service.storage.memory_sqlite import SQLiteURLRepository

def test_concurrent_shortening_and_resolving():
    repo = SQLiteURLRepository(":memory:")
    svc = URLShortenerService(repo=repo)

    num_threads = 30
    urls_to_create = [f"https://www.example.com/page_{i}?v={i}" for i in range(num_threads)]

    # 1. Concurrent Shortening
    created_codes = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(svc.shorten_url, ShortenRequest(original_url=u)) for u in urls_to_create]
        for f in concurrent.futures.as_completed(futures):
            res = f.result()
            created_codes.append(res.short_code)

    assert len(created_codes) == num_threads
    assert len(set(created_codes)) == num_threads # All short codes must be unique!

    # 2. Concurrent Redirection and Click Logging
    def simulate_click(code: str, worker_id: int):
        dest, _ = svc.resolve_url(
            short_code=code,
            client_ip=f"10.0.1.{worker_id % 5}",
            user_agent="Mozilla/5.0 ConcurrencyTest",
            referrer="https://concurrency.test"
        )
        return dest

    clicks_per_url = 5
    click_tasks = []
    for code in created_codes:
        for i in range(clicks_per_url):
            click_tasks.append((code, i))

    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
        futures = [executor.submit(simulate_click, code, wid) for code, wid in click_tasks]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    assert len(results) == len(click_tasks)

    # 3. Verify total stats
    stats = svc.get_system_stats()
    assert stats.total_urls == num_threads
    assert stats.total_clicks == len(click_tasks)
