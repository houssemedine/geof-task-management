import time
from collections import defaultdict, deque
from threading import Lock


class InMemoryRateLimiter:
    """Modélise la structure "InMemoryRateLimiter"."""

    def __init__(self, requests_per_window: int, window_seconds: int) -> None:
        """Initialise l'instance."""
        self.requests_per_window = max(1, requests_per_window)
        self.window_seconds = max(1, window_seconds)
        self._buckets: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str) -> tuple[bool, int]:
        """Applique la limite de debit pour une cle client et retourne la decision."""
        now = time.monotonic()
        with self._lock:
            bucket = self._buckets[key]
            cutoff = now - self.window_seconds
            while bucket and bucket[0] < cutoff:
                bucket.popleft()

            if len(bucket) >= self.requests_per_window:
                retry_after = int(self.window_seconds - (now - bucket[0]))
                return False, max(1, retry_after)

            bucket.append(now)
            return True, 0

    def clear(self) -> None:
        """Vide l'etat interne du rate limiter."""
        with self._lock:
            self._buckets.clear()
