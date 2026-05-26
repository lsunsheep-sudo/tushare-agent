import time
from app.data.cache import CacheManager


class TestCacheManager:
    def test_get_set(self):
        cache = CacheManager()
        cache.set("key1", "value1", ttl_seconds=60)
        assert cache.get("key1") == "value1"

    def test_miss_returns_none(self):
        cache = CacheManager()
        assert cache.get("nonexistent") is None

    def test_ttl_expiry(self):
        cache = CacheManager()
        cache.set("key1", "value1", ttl_seconds=0.01)
        time.sleep(0.02)
        assert cache.get("key1") is None
