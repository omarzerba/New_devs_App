from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Any, Tuple

from zoneinfo import ZoneInfo

# When the DB pool is unavailable, revenue falls back to this map. It MUST be keyed by
# tenant_id first, then property_id — otherwise Sunset and Ocean would see identical
# figures for the same property id (confusing when testing tenant isolation).
# IDs align with database/seed.sql and backend/app/api/v1/login.py (tenant-a / tenant-b).
_DEV_MOCK_REVENUE: Dict[str, Dict[str, Dict[str, Any]]] = {
    "tenant-a": {
        "prop-001": {"total": "2250.01", "count": 4},
        "prop-002": {"total": "4975.50", "count": 4},
        "prop-003": {"total": "6100.50", "count": 2},
        "prop-004": {"total": "0.00", "count": 0},
        "prop-005": {"total": "0.00", "count": 0},
    },
    "tenant-b": {
        "prop-001": {"total": "9420.77", "count": 5},
        "prop-002": {"total": "0.00", "count": 0},
        "prop-003": {"total": "0.00", "count": 0},
        "prop-004": {"total": "1776.50", "count": 4},
        "prop-005": {"total": "3256.00", "count": 3},
    },
}


def _mock_revenue_row(tenant_id: str, property_id: str) -> Dict[str, Any]:
    by_tenant = _DEV_MOCK_REVENUE.get(tenant_id) or _DEV_MOCK_REVENUE.get("tenant-a", {})
    row = by_tenant.get(property_id, {"total": "0.00", "count": 0})
    return {
        "property_id": property_id,
        "tenant_id": tenant_id,
        "total": row["total"],
        "currency": "USD",
        "count": row["count"],
    }


# March 2024 totals match database/seed.sql (check-in in property local calendar month).
_DEV_MOCK_MONTHLY: Dict[str, Dict[str, Any]] = {
    "tenant-a:prop-001:2024-03": {"total": "1000.00", "count": 3},
    "tenant-a:prop-001:2024-02": {"total": "1250.00", "count": 1},
    "tenant-a:prop-002:2024-03": {"total": "4975.50", "count": 4},
    "tenant-a:prop-003:2024-03": {"total": "6100.50", "count": 2},
    "tenant-b:prop-001:2024-03": {"total": "0.00", "count": 0},
    "tenant-b:prop-004:2024-03": {"total": "1776.50", "count": 4},
    "tenant-b:prop-005:2024-03": {"total": "3256.00", "count": 3},
}


def _mock_monthly_row(tenant_id: str, property_id: str, year: int, month: int) -> Dict[str, Any]:
    key = f"{tenant_id}:{property_id}:{year}-{month:02d}"
    row = _DEV_MOCK_MONTHLY.get(key, {"total": "0.00", "count": 0})
    return {
        "property_id": property_id,
        "tenant_id": tenant_id,
        "total": row["total"],
        "currency": "USD",
        "count": row["count"],
        "period_year": year,
        "period_month": month,
    }


def _calendar_month_bounds_utc(year: int, month: int, tz_name: str) -> Tuple[datetime, datetime]:
    """First instant of month and first instant of next month, as UTC, in tz_name local clocks."""
    try:
        zi = ZoneInfo(tz_name)
    except Exception:
        zi = ZoneInfo("UTC")
    start_local = datetime(year, month, 1, 0, 0, 0, tzinfo=zi)
    if month == 12:
        end_local = datetime(year + 1, 1, 1, 0, 0, 0, tzinfo=zi)
    else:
        end_local = datetime(year, month + 1, 1, 0, 0, 0, tzinfo=zi)
    return (
        start_local.astimezone(timezone.utc),
        end_local.astimezone(timezone.utc),
    )


async def calculate_revenue_calendar_month(
    property_id: str, tenant_id: str, year: int, month: int
) -> Dict[str, Any]:
    """
    Sum reservation revenue for check-ins falling in [year-month) in the property's IANA timezone.
    Aligns board-style "March revenue" with local calendar month at the property.
    """
    if month < 1 or month > 12:
        raise ValueError("month must be 1-12")

    try:
        from app.core.database_pool import DatabasePool

        db_pool = DatabasePool()
        await db_pool.initialize()

        if db_pool.session_factory:
            async with db_pool.get_session() as session:
                from sqlalchemy import text

                tz_row = await session.execute(
                    text(
                        """
                    SELECT timezone FROM properties
                    WHERE id = :property_id AND tenant_id = :tenant_id
                    LIMIT 1
                    """
                    ),
                    {"property_id": property_id, "tenant_id": tenant_id},
                )
                tr = tz_row.fetchone()
                tz_name = (tr[0] if tr else None) or "UTC"

                start_utc, end_utc = _calendar_month_bounds_utc(year, month, tz_name)

                result = await session.execute(
                    text(
                        """
                    SELECT
                        property_id,
                        SUM(total_amount) AS total_revenue,
                        COUNT(*) AS reservation_count
                    FROM reservations
                    WHERE property_id = :property_id
                      AND tenant_id = :tenant_id
                      AND check_in_date >= :start_utc
                      AND check_in_date < :end_utc
                    GROUP BY property_id
                    """
                    ),
                    {
                        "property_id": property_id,
                        "tenant_id": tenant_id,
                        "start_utc": start_utc,
                        "end_utc": end_utc,
                    },
                )
                row = result.fetchone()

                if row is not None:
                    total_revenue = Decimal(str(row.total_revenue or 0))
                    return {
                        "property_id": property_id,
                        "tenant_id": tenant_id,
                        "total": str(total_revenue),
                        "currency": "USD",
                        "count": int(row.reservation_count or 0),
                        "period_year": year,
                        "period_month": month,
                        "property_timezone": tz_name,
                    }
                return {
                    "property_id": property_id,
                    "tenant_id": tenant_id,
                    "total": "0.00",
                    "currency": "USD",
                    "count": 0,
                    "period_year": year,
                    "period_month": month,
                    "property_timezone": tz_name,
                }
        raise Exception("Database pool not available")
    except Exception as e:
        print(f"Database error (monthly) for {property_id} (tenant: {tenant_id}): {e}")
        return _mock_monthly_row(tenant_id, property_id, year, month)

async def calculate_total_revenue(property_id: str, tenant_id: str) -> Dict[str, Any]:
    """
    Aggregates revenue from database.
    """
    try:
        # Import database pool
        from app.core.database_pool import DatabasePool
        
        # Initialize pool if needed
        db_pool = DatabasePool()
        await db_pool.initialize()
        
        if db_pool.session_factory:
            async with db_pool.get_session() as session:
                # Use SQLAlchemy text for raw SQL
                from sqlalchemy import text
                
                query = text("""
                    SELECT 
                        property_id,
                        SUM(total_amount) as total_revenue,
                        COUNT(*) as reservation_count
                    FROM reservations 
                    WHERE property_id = :property_id AND tenant_id = :tenant_id
                    GROUP BY property_id
                """)
                
                result = await session.execute(query, {
                    "property_id": property_id, 
                    "tenant_id": tenant_id
                })
                row = result.fetchone()
                
                if row:
                    total_revenue = Decimal(str(row.total_revenue))
                    return {
                        "property_id": property_id,
                        "tenant_id": tenant_id,
                        "total": str(total_revenue),
                        "currency": "USD", 
                        "count": row.reservation_count
                    }
                else:
                    # No reservations found for this property
                    return {
                        "property_id": property_id,
                        "tenant_id": tenant_id,
                        "total": "0.00",
                        "currency": "USD",
                        "count": 0
                    }
        else:
            raise Exception("Database pool not available")
            
    except Exception as e:
        print(f"Database error for {property_id} (tenant: {tenant_id}): {e}")

        return _mock_revenue_row(tenant_id, property_id)
