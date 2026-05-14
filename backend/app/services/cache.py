import json
import redis.asyncio as redis
from typing import Dict, Any, Optional
import os

# Initialize Redis client (typically configured centrally).
redis_client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))


async def get_revenue_summary(
    property_id: str,
    tenant_id: str,
    *,
    year: Optional[int] = None,
    month: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Fetches revenue summary, utilizing caching to improve performance.
    When year and month are set, totals are for that calendar month in the
    property's timezone (check-in date). Otherwise lifetime totals for the property.
    """
    # Tenant must be part of the key: same property_id can exist for different orgs;
    # omitting tenant_id caused cross-tenant cache hits (wrong revenue after refresh).
    if year is not None and month is not None:
        cache_key = f"revenue:{tenant_id}:{property_id}:y{year}:m{month:02d}"
    else:
        cache_key = f"revenue:{tenant_id}:{property_id}"

    # Try to get from cache
    cached = await redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    from app.services.reservations import calculate_total_revenue, calculate_revenue_calendar_month

    if year is not None and month is not None:
        result = await calculate_revenue_calendar_month(property_id, tenant_id, year, month)
    else:
        result = await calculate_total_revenue(property_id, tenant_id)

    # Cache the result for 5 minutes
    await redis_client.setex(cache_key, 300, json.dumps(result))

    return result
