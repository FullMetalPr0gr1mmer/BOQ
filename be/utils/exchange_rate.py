"""
Exchange Rate Utility - USD/AED

Fetches the live USD/AED rate from a free public API.
Falls back to the pegged rate (3.6725) if the network is unreachable.
Caches the result in memory for 1 hour to avoid repeated external calls.
"""

import logging
import httpx
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# AED is pegged to USD — this fallback is accurate to ~0.01%
FALLBACK_RATE = 3.6725
CACHE_TTL_HOURS = 1
API_TIMEOUT_SECONDS = 3
API_URL = "https://api.exchangerate-api.com/v4/latest/USD"

# In-memory cache: { "rate": float, "fetched_at": datetime, "source": str }
_cache: dict | None = None


async def get_usd_aed_rate() -> dict:
    """
    Returns the current USD/AED exchange rate.

    Response shape:
        {
            "rate": 3.6725,
            "source": "live" | "fallback",
            "fetched_at": "2026-02-03T12:00:00"  # when the rate was obtained
        }
    """
    global _cache

    # Return cached rate if still fresh
    if _cache and _cache["fetched_at"] + timedelta(hours=CACHE_TTL_HOURS) > datetime.now():
        return _cache

    # Attempt live fetch
    try:
        async with httpx.AsyncClient(timeout=API_TIMEOUT_SECONDS, verify=False) as client:
            response = await client.get(API_URL)
            response.raise_for_status()
            data = response.json()
            rate = float(data["rates"]["AED"])

        _cache = {
            "rate": rate,
            "source": "live",
            "fetched_at": datetime.now()
        }
        logger.info(f"USD/AED rate fetched live: {rate}")
        return _cache

    except Exception as e:
        logger.warning(f"Exchange rate API unreachable ({type(e).__name__}), using fallback rate")
        _cache = {
            "rate": FALLBACK_RATE,
            "source": "fallback",
            "fetched_at": datetime.now()
        }
        return _cache
