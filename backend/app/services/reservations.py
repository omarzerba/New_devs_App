from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, List

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

async def calculate_monthly_revenue(property_id: str, month: int, year: int, db_session=None) -> Decimal:
    """
    Calculates revenue for a specific month.
    """

    start_date = datetime(year, month, 1)
    if month < 12:
        end_date = datetime(year, month + 1, 1)
    else:
        end_date = datetime(year + 1, 1, 1)
        
    print(f"DEBUG: Querying revenue for {property_id} from {start_date} to {end_date}")

    # SQL Simulation (This would be executed against the actual DB)
    query = """
        SELECT SUM(total_amount) as total
        FROM reservations
        WHERE property_id = $1
        AND tenant_id = $2
        AND check_in_date >= $3
        AND check_in_date < $4
    """
    
    # In production this query executes against a database session.
    # result = await db.fetch_val(query, property_id, tenant_id, start_date, end_date)
    # return result or Decimal('0')
    
    return Decimal('0') # Placeholder for now until DB connection is finalized

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
