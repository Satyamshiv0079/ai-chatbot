import time
import os
import threading
from collections import defaultdict
from functools import wraps
from flask import request, jsonify

class InMemoryRateLimiter:
    """
    Lightweight, thread-safe in-memory sliding window rate limiter.
    Does not require external services (Redis/Memcached).
    Configurable via environment variables.
    """
    def __init__(self):
        self._records = defaultdict(list)
        self._lock = threading.Lock()

    def limit(self, max_requests: int = 10, window_seconds: int = 60, key_func=None):
        def decorator(f):
            @wraps(f)
            def wrapped(*args, **kwargs):
                if os.environ.get("RATE_LIMIT_ENABLED", "true").lower() in ("false", "0"):
                    return f(*args, **kwargs)

                key = key_func() if key_func else (request.headers.get("X-Forwarded-For") or request.remote_addr or "unknown")
                endpoint_key = f"{request.endpoint or f.__name__}:{key}"
                now = time.time()

                with self._lock:
                    # Filter timestamps within current window
                    valid_timestamps = [t for t in self._records[endpoint_key] if now - t < window_seconds]
                    if len(valid_timestamps) >= max_requests:
                        self._records[endpoint_key] = valid_timestamps
                        return jsonify({
                            "error": f"Rate limit exceeded. Maximum {max_requests} requests per {window_seconds}s. Please try again shortly."
                        }), 429

                    valid_timestamps.append(now)
                    self._records[endpoint_key] = valid_timestamps

                return f(*args, **kwargs)
            return wrapped
        return decorator

limiter = InMemoryRateLimiter()
