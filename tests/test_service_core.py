"""
Unit Tests for URL Shortener Core Components (Encoder, Validator, Cache, RateLimiter).
"""

from __future__ import annotations
import time
import pytest
from src.service.core.encoder import Base62Encoder, encode_base62, hash_64bit
from src.service.core.validator import URLValidator, ValidationError
from src.service.core.cache import LRUTTLCache
from src.service.core.rate_limiter import SlidingWindowRateLimiter

def test_base62_encoding():
    assert encode_base62(0, length=7) == "0000000"
    assert encode_base62(61, length=7) == "000000Z"
    assert len(encode_base62(123456789, length=7)) == 7

def test_hash_64bit_deterministic():
    h1 = hash_64bit("https://example.com/test")
    h2 = hash_64bit("https://example.com/test")
    assert h1 == h2
    assert isinstance(h1, int)
    assert h1 > 0

def test_encoder_collision_probing():
    encoder = Base62Encoder(salt="test_salt", code_length=7)
    code_initial = encoder.generate_code("https://example.com", collision_attempt=0)
    code_probe_1 = encoder.generate_code("https://example.com", collision_attempt=1)
    
    assert len(code_initial) == 7
    assert len(code_probe_1) == 7
    # Different collision attempts must produce distinct short codes
    assert code_initial != code_probe_1

def test_validator_valid_urls():
    validator = URLValidator()
    assert validator.validate_url("https://www.google.com/search?q=agentic") == "https://www.google.com/search?q=agentic"
    assert validator.validate_url("http://example.org:8080/path") == "http://example.org:8080/path"

def test_validator_blocks_invalid_schemes():
    validator = URLValidator()
    with pytest.raises(ValidationError, match="scheme"):
        validator.validate_url("ftp://files.example.com")
    with pytest.raises(ValidationError, match="scheme"):
        validator.validate_url("javascript:alert(1)")

def test_validator_ssrf_protection():
    validator = URLValidator()
    # Localhost blocked
    with pytest.raises(ValidationError, match="Prohibited"):
        validator.validate_url("http://localhost:3000")
    with pytest.raises(ValidationError, match="Prohibited"):
        validator.validate_url("http://127.0.0.1/admin")
    # AWS Metadata IP blocked
    with pytest.raises(ValidationError, match="Prohibited"):
        validator.validate_url("http://169.254.169.254/latest/meta-data")
    # Private subnets blocked
    with pytest.raises(ValidationError, match="Prohibited"):
        validator.validate_url("http://10.0.0.1/internal")
    with pytest.raises(ValidationError, match="Prohibited"):
        validator.validate_url("http://192.168.1.1/router")

def test_validator_self_loop_prevention():
    validator = URLValidator(service_domains={"short.aethersdlc.dev", "localhost:8001"})
    with pytest.raises(ValidationError, match="Self-referencing loop"):
        validator.validate_url("https://short.aethersdlc.dev/abc1234")

def test_validator_custom_alias():
    validator = URLValidator()
    assert validator.validate_custom_alias("my-promo_2026") == "my-promo_2026"
    
    # Too short
    with pytest.raises(ValidationError, match="Custom alias"):
        validator.validate_custom_alias("ab")
    
    # Reserved keyword
    with pytest.raises(ValidationError, match="reserved"):
        validator.validate_custom_alias("api")
    with pytest.raises(ValidationError, match="reserved"):
        validator.validate_custom_alias("admin")

def test_lru_cache_hit_and_eviction():
    cache = LRUTTLCache(max_size=2, default_ttl_seconds=10)
    cache.set("a", "url_a")
    cache.set("b", "url_b")
    
    assert cache.get("a") == "url_a"
    assert cache.get("b") == "url_b"
    
    # Adding 3rd item evicts LRU (which is 'a', because 'b' was accessed more recently)
    cache.set("c", "url_c")
    assert cache.get("c") == "url_c"
    assert cache.get("a") is None # Evicted!
    assert cache.get("b") == "url_b"

def test_lru_cache_ttl_expiration():
    cache = LRUTTLCache(max_size=10, default_ttl_seconds=1)
    cache.set("temp", "expiring_url", ttl_seconds=1)
    assert cache.get("temp") == "expiring_url"
    
    time.sleep(1.1)
    assert cache.get("temp") is None # Expired!

def test_sliding_window_rate_limiter():
    limiter = SlidingWindowRateLimiter(default_limit=3, window_seconds=2)
    client = "192.0.2.1"
    
    # 3 allowed
    ok1, rem1, _ = limiter.is_allowed(client)
    assert ok1 is True and rem1 == 2
    ok2, rem2, _ = limiter.is_allowed(client)
    assert ok2 is True and rem2 == 1
    ok3, rem3, _ = limiter.is_allowed(client)
    assert ok3 is True and rem3 == 0
    
    # 4th blocked
    ok4, rem4, reset_in = limiter.is_allowed(client)
    assert ok4 is False
    assert rem4 == 0
    assert reset_in > 0
    
    # Other client is not affected
    ok_other, _, _ = limiter.is_allowed("192.0.2.2")
    assert ok_other is True
