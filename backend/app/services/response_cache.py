import time
from collections import OrderedDict


class TTLCache:
    def __init__(self, capacity: int = 256, ttl_seconds: int = 60):
        self.capacity = capacity
        self.ttl = ttl_seconds
        self._cache: OrderedDict[str, tuple[object, float]] = OrderedDict()

    def get(self, key: str):
        if key not in self._cache:
            return None
        value, expiry = self._cache[key]
        if time.time() > expiry:
            del self._cache[key]
            return None
        self._cache.move_to_end(key)
        return value

    def set(self, key: str, value: object):
        self._cache[key] = (value, time.time() + self.ttl)
        self._cache.move_to_end(key)
        if len(self._cache) > self.capacity:
            self._cache.popitem(last=False)

    def invalidate(self, key: str):
        self._cache.pop(key, None)

    def clear(self):
        self._cache.clear()


cache = TTLCache()
