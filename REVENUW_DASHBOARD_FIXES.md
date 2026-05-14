# Revenue dashboard — assignment bug fixes
Short reference for what was fixed (see `ASSIGNMENT.md` for the original scenario). This complements the Loom walkthrough.
---
## 1. Sunset — March totals vs internal records
**Symptom:** “March” on the dashboard did not match finance’s March numbers.
**Cause:** The UI described monthly insights, but the API summed **lifetime** revenue for the property, not a **calendar month**, and did not respect the property’s **timezone** for month boundaries.
**Fix:**
- Backend: `calculate_revenue_calendar_month` in `backend/app/services/reservations.py` — loads `properties.timezone`, builds month start/end in that zone, converts to UTC, sums `reservations` where `check_in_date` falls in that range (same tenant + property).
- API: `GET /api/v1/dashboard/summary` accepts optional **`year`** and **`month`** together (`backend/app/api/v1/dashboard.py`). Response includes `revenue_basis`, `period_year`, `period_month`, and `property_timezone` when in monthly mode.
- Cache: monthly totals use a distinct Redis key pattern in `backend/app/services/cache.py` (tenant + property + year + month).
- Frontend: `frontend/src/components/Dashboard.tsx` — month picker (`type="month"`, default `2024-03` to match seed data). `RevenueSummary.tsx` and `secureApi.getDashboardSummary` pass `year` / `month`.
- Tooling: `tzdata` in `backend/requirements.txt` and `backend/Dockerfile` so IANA zones (e.g. `Europe/Paris`) resolve in Docker and local runs.
---
## 2. Ocean — another company’s revenue after refresh
**Symptom:** After refresh, revenue sometimes looked like it belonged to another organization.
**Cause:** Redis cached results under **`revenue:{property_id}`** only. The same `property_id` for different tenants could return **another tenant’s** cached payload until TTL expired.
**Fix:** Cache key is now **`revenue:{tenant_id}:{property_id}`** (and includes month segment when monthly mode is used). Implemented in `backend/app/services/cache.py`.
**Note:** Dev fallback mocks in `reservations.py` are also keyed by tenant so local testing without DB does not show identical totals for both clients on the same property id.
---
## 3. Finance — a few cents off
**Symptom:** Totals slightly disagreed with the ledger.
**Cause:** Revenue was exposed as a JSON **float** and the UI used float rounding, which introduces IEEE-754 drift vs decimal money.
**Fix:**
- `backend/app/api/v1/dashboard.py` — `Decimal` quantize (half-up) to cents, return **`total_revenue` as a string** (e.g. `"1234.56"`).
- `frontend/src/components/RevenueSummary.tsx` — normalize and display from **string** amounts (no `Math.round(x * 100)` on API values for the primary path).
---
## Other repo hygiene
- **`.gitignore`** (repo root) — ignores `__pycache__/`, `*.pyc`, `node_modules/`, common env and build artifacts so Docker/Python noise does not clutter commits.
---
## How to verify quickly
1. **March / Sunset:** Log in as `sunset@propertyflow.com`, pick **March 2024** and **Beach House Alpha (`prop-001`)** — expect monthly total aligned with seed (check-ins in **Europe/Paris** local March).
2. **Tenant isolation:** Log in as Sunset then Ocean; same property id should not show the other tenant’s **cached** total after the Redis key change (restart backend after deploy).
3. **Cents:** Inspect `GET /api/v1/dashboard/summary` — `total_revenue` should be a **quoted string** with two decimal places.
Restart **`backend`** after Python changes; **`frontend`** image must be rebuilt if you use Docker without a bind mount for the frontend (see `docker-compose.yml`).