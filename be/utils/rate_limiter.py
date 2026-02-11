"""
Rate Limiter Utility

Provides simple in-memory rate limiting for API endpoints.
This implementation is suitable for single-instance deployments.
For multi-instance deployments, replace with Redis-based implementation.

Security Features:
- Prevents brute force attacks on authentication endpoints
- Configurable requests per window
- IP-based tracking
- Automatic cleanup of expired entries

Usage:
    from utils.rate_limiter import rate_limiter, RateLimitExceeded

    @router.post("/login")
    async def login(request: Request):
        client_ip = get_client_ip(request)
        rate_limiter.check_rate_limit(client_ip, "login", max_requests=5, window_seconds=60)
        # ... rest of the endpoint

Author: Security Hardening Initiative
Created: 2025
"""

import time
from collections import defaultdict
from threading import Lock
from typing import Dict, Tuple
from fastapi import HTTPException, status


class RateLimitExceeded(HTTPException):
    """Exception raised when rate limit is exceeded."""
    def __init__(self, retry_after: int):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many requests. Please try again in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)}
        )


class InMemoryRateLimiter:
    """
    In-memory rate limiter using sliding window algorithm.

    Thread-safe implementation suitable for single-instance deployments.
    For distributed systems, use Redis-based rate limiting instead.

    Attributes:
        _requests: Dictionary storing request timestamps by key
        _lock: Thread lock for safe concurrent access
        _cleanup_interval: How often to clean up expired entries
        _last_cleanup: Timestamp of last cleanup
    """

    def __init__(self, cleanup_interval: int = 300):
        """
        Initialize the rate limiter.

        Args:
            cleanup_interval: Seconds between cleanup of expired entries (default: 5 minutes)
        """
        self._requests: Dict[str, list] = defaultdict(list)
        self._lock = Lock()
        self._cleanup_interval = cleanup_interval
        self._last_cleanup = time.time()

    def _cleanup_expired(self, current_time: float, window_seconds: int = 3600) -> None:
        """Remove entries older than the maximum window."""
        if current_time - self._last_cleanup < self._cleanup_interval:
            return

        cutoff = current_time - window_seconds
        keys_to_remove = []

        for key, timestamps in self._requests.items():
            # Filter out expired timestamps
            self._requests[key] = [t for t in timestamps if t > cutoff]
            if not self._requests[key]:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self._requests[key]

        self._last_cleanup = current_time

    def check_rate_limit(
        self,
        identifier: str,
        endpoint: str,
        max_requests: int = 10,
        window_seconds: int = 60
    ) -> bool:
        """
        Check if request is allowed under rate limit.

        Args:
            identifier: Unique identifier (e.g., IP address, user ID)
            endpoint: Endpoint name for separate limits
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds

        Returns:
            True if request is allowed

        Raises:
            RateLimitExceeded: If rate limit is exceeded
        """
        current_time = time.time()
        key = f"{endpoint}:{identifier}"

        with self._lock:
            # Cleanup old entries periodically
            self._cleanup_expired(current_time)

            # Get timestamps for this key
            timestamps = self._requests[key]

            # Remove timestamps outside the window
            cutoff = current_time - window_seconds
            timestamps = [t for t in timestamps if t > cutoff]

            # Check if limit exceeded
            if len(timestamps) >= max_requests:
                # Calculate retry-after time
                oldest_in_window = min(timestamps) if timestamps else current_time
                retry_after = int(oldest_in_window + window_seconds - current_time) + 1
                raise RateLimitExceeded(retry_after=max(1, retry_after))

            # Add current request
            timestamps.append(current_time)
            self._requests[key] = timestamps

        return True

    def get_remaining_requests(
        self,
        identifier: str,
        endpoint: str,
        max_requests: int = 10,
        window_seconds: int = 60
    ) -> Tuple[int, int]:
        """
        Get remaining requests and reset time.

        Args:
            identifier: Unique identifier
            endpoint: Endpoint name
            max_requests: Maximum requests allowed
            window_seconds: Time window in seconds

        Returns:
            Tuple of (remaining_requests, seconds_until_reset)
        """
        current_time = time.time()
        key = f"{endpoint}:{identifier}"

        with self._lock:
            timestamps = self._requests.get(key, [])
            cutoff = current_time - window_seconds
            valid_timestamps = [t for t in timestamps if t > cutoff]

            remaining = max(0, max_requests - len(valid_timestamps))

            if valid_timestamps:
                oldest = min(valid_timestamps)
                reset_in = int(oldest + window_seconds - current_time) + 1
            else:
                reset_in = window_seconds

            return remaining, max(0, reset_in)

    def reset(self, identifier: str = None, endpoint: str = None) -> None:
        """
        Reset rate limit for an identifier/endpoint.

        Args:
            identifier: Specific identifier to reset (or all if None)
            endpoint: Specific endpoint to reset (or all if None)
        """
        with self._lock:
            if identifier is None and endpoint is None:
                self._requests.clear()
            elif identifier is None:
                keys_to_remove = [k for k in self._requests if k.startswith(f"{endpoint}:")]
                for key in keys_to_remove:
                    del self._requests[key]
            elif endpoint is None:
                keys_to_remove = [k for k in self._requests if k.endswith(f":{identifier}")]
                for key in keys_to_remove:
                    del self._requests[key]
            else:
                key = f"{endpoint}:{identifier}"
                self._requests.pop(key, None)


# Global rate limiter instance
rate_limiter = InMemoryRateLimiter()


# Default rate limit configurations for different endpoint types
RATE_LIMITS = {
    "login": {"max_requests": 5, "window_seconds": 60},      # 5 attempts per minute
    "register": {"max_requests": 3, "window_seconds": 300},  # 3 registrations per 5 minutes
    "password_reset": {"max_requests": 3, "window_seconds": 300},  # 3 resets per 5 minutes
    "api_default": {"max_requests": 100, "window_seconds": 60},    # 100 requests per minute
}


def check_auth_rate_limit(client_ip: str, endpoint: str) -> bool:
    """
    Convenience function to check rate limit for auth endpoints.

    Args:
        client_ip: Client IP address
        endpoint: Endpoint name (e.g., "login", "register")

    Returns:
        True if allowed

    Raises:
        RateLimitExceeded: If rate limit exceeded
    """
    config = RATE_LIMITS.get(endpoint, RATE_LIMITS["api_default"])
    return rate_limiter.check_rate_limit(
        identifier=client_ip,
        endpoint=endpoint,
        max_requests=config["max_requests"],
        window_seconds=config["window_seconds"]
    )
