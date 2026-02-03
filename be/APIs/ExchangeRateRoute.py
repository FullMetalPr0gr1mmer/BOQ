"""
Exchange Rate Route - public endpoint for USD/AED rate
"""

from fastapi import APIRouter
from utils.exchange_rate import get_usd_aed_rate

exchangeRateRoute = APIRouter(tags=["Exchange Rate"])


@exchangeRateRoute.get("/exchange-rate/usd-aed")
async def usd_aed_rate():
    """
    Returns the current USD/AED exchange rate.

    - Fetches live from exchangerate-api.com (free, no key).
    - Falls back to the pegged rate (3.6725) if the network is unreachable.
    - Cached in memory for 1 hour.

    Response:
        { "rate": 3.6725, "source": "live" | "fallback", "fetched_at": "..." }
    """
    result = await get_usd_aed_rate()
    return {
        "rate": result["rate"],
        "source": result["source"],
        "fetched_at": result["fetched_at"].isoformat()
    }
