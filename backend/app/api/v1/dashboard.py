from decimal import Decimal, ROUND_HALF_UP
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, Optional
from app.services.cache import get_revenue_summary
from app.core.auth import authenticate_request as get_current_user

router = APIRouter()


@router.get("/dashboard/summary")
async def get_dashboard_summary(
    property_id: str,
    current_user: dict = Depends(get_current_user),
    year: Optional[int] = Query(None, ge=2000, le=2100),
    month: Optional[int] = Query(None, ge=1, le=12),
) -> Dict[str, Any]:

    tenant_id = getattr(current_user, "tenant_id", "default_tenant") or "default_tenant"

    if (year is None) ^ (month is None):
        raise HTTPException(
            status_code=400,
            detail="Provide both year and month for calendar-month revenue, or omit both for lifetime totals.",
        )

    revenue_data = await get_revenue_summary(
        property_id, tenant_id, year=year, month=month
    )

    # Money as a decimal string (2 places) avoids IEEE-754 drift in JSON and matches finance expectations.
    total_dec = Decimal(str(revenue_data["total"])).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    payload: Dict[str, Any] = {
        "property_id": revenue_data["property_id"],
        "total_revenue": f"{total_dec:.2f}",
        "currency": revenue_data["currency"],
        "reservations_count": revenue_data["count"],
    }

    if year is not None and month is not None:
        payload["period_year"] = year
        payload["period_month"] = month
        payload["revenue_basis"] = "check_in_property_local_month"
        tz = revenue_data.get("property_timezone")
        if tz:
            payload["property_timezone"] = tz
    else:
        payload["revenue_basis"] = "lifetime_all_check_ins"

    return payload
