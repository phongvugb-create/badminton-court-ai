"""
BADMINTON.AI - READ-ONLY BUSINESS TOOLS (PHASE 7.1)
Provides verified, read-only tools to retrieve live business data directly
from the database, redis locks, and pricing engine:
1. search_courts: Query approved facilities by keyword, district, or GPS distance.
2. check_court_availability: Query effective slot status (TimeSlot + Redis hold).
3. get_court_pricing: Look up authoritative court rental pricing (SlotPricing / calculate_dynamic_price).
4. get_my_bookings: Retrieve personal bookings for authenticated users (Anti-IDOR, strictly current_user.id).

STRICT SAFETY RULES:
- All tools are strictly READ-ONLY.
- No booking creation, cancellation, slot locking, or DB mutations.
- No arbitrary SQL generation or raw DB access for LLMs.
- Sensitive data (JWTs, passwords, full QR check-in codes) are strictly shielded.
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.models.all_models import Facility, Court, TimeSlot, SlotPricing, Booking
from app.ai.haversine import haversine_distance
from app.ai.dynamic_pricing import calculate_dynamic_price
from app.core.redis import get_slot_lock_holder

logger = logging.getLogger("business_tools")


def make_tool_envelope(
    status: str,
    data: Optional[List[Dict[str, Any]]] = None,
    reason: Optional[str] = None
) -> Dict[str, Any]:
    """
    Standard envelope format for all read-only business tools:
    - status: 'success' | 'no_results' | 'invalid_input' | 'authentication_required' | 'permission_denied' | 'data_unavailable' | 'error'
    - data: List of structured records
    - reason: Optional machine-readable explanation string
    """
    return {
        "status": status,
        "data": data if data is not None else [],
        "reason": reason
    }


# ==============================================================================
# TOOL A: search_courts
# ==============================================================================
async def search_courts(
    db: AsyncSession,
    query: Optional[str] = None,
    user_lat: Optional[float] = None,
    user_lon: Optional[float] = None,
    limit: int = 5
) -> Dict[str, Any]:
    """
    Search approved facilities by name, address keyword, or GPS coordinates.
    Reuses business logic from GET /api/v1/facilities.
    """
    # 1. Validate GPS coordinates if provided
    has_lat = user_lat is not None
    has_lon = user_lon is not None
    if has_lat != has_lon:
        return make_tool_envelope("invalid_input", reason="both_lat_lon_required")

    if has_lat and has_lon:
        try:
            lat_f = float(user_lat)
            lon_f = float(user_lon)
            if not (-90.0 <= lat_f <= 90.0 and -180.0 <= lon_f <= 180.0):
                return make_tool_envelope("invalid_input", reason="coordinates_out_of_range")
        except (ValueError, TypeError):
            return make_tool_envelope("invalid_input", reason="invalid_coordinates")

    # 2. Validate query string
    clean_query = None
    if query is not None:
        clean_query = str(query).strip()
        if len(clean_query) > 200:
            return make_tool_envelope("invalid_input", reason="query_too_long")
        if not clean_query:
            clean_query = None

    effective_limit = max(1, min(limit, 100))

    try:
        stmt = (
            select(Facility)
            .options(selectinload(Facility.courts))
            .where(Facility.is_approved == True)
        )
        res = await db.execute(stmt)
        facilities = res.scalars().all()

        results = []
        for f in facilities:
            # Match query keyword
            if clean_query:
                q_lower = clean_query.lower()
                if q_lower not in f.name.lower() and q_lower not in f.address.lower():
                    continue

            dist = None
            if has_lat and has_lon:
                dist = haversine_distance(user_lat, user_lon, f.latitude, f.longitude)

            active_courts = len([c for c in (f.courts or []) if c.is_active])

            results.append({
                "facility_id": f.id,
                "name": f.name,
                "address": f.address,
                "open_time": f.open_time,
                "close_time": f.close_time,
                "rating": f.rating,
                "distance_km": dist,
                "total_courts": active_courts
            })

        # Sort by distance if GPS provided
        if has_lat and has_lon:
            results.sort(key=lambda x: x["distance_km"] if x["distance_km"] is not None else 9999.0)

        if not results:
            return make_tool_envelope("no_results", data=[], reason="no_matching_facilities")

        return make_tool_envelope("success", data=results[:effective_limit], reason=None)

    except Exception as e:
        logger.error(f"[search_courts] Unexpected error: {e}", exc_info=True)
        return make_tool_envelope("internal_error", data=[], reason=str(e))


# ==============================================================================
# TOOL B: check_court_availability
# ==============================================================================
async def check_court_availability(
    db: AsyncSession,
    facility_id: Optional[int] = None,
    court_id: Optional[int] = None,
    date: Optional[str] = None,
    time: Optional[str] = None,
    limit: int = 20
) -> Dict[str, Any]:
    """
    Check real-time effective availability of slots.
    Reuses business logic from GET /api/v1/slots and Redis atomic lock mechanism.
    Effective Status Formula:
      TimeSlot.status + Redis slot lock = effective_status
    - AVAILABLE + Redis lock -> HELD
    - BOOKED / MAINTENANCE -> BOOKED / MAINTENANCE
    - Redis error -> error / availability_unverified (NEVER assumes AVAILABLE)
    """
    # 1. Validate date
    if not date:
        return make_tool_envelope("invalid_input", reason="missing_date")
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return make_tool_envelope("invalid_input", reason="invalid_date_format")

    # 2. Validate time if provided
    if time:
        clean_time = time.strip()
        try:
            # Support both "19:00" and "19:00:00"
            parts = clean_time.split(":")
            if len(parts) >= 2:
                datetime.strptime(f"{parts[0].zfill(2)}:{parts[1].zfill(2)}", "%H:%M")
                clean_time = f"{parts[0].zfill(2)}:{parts[1].zfill(2)}"
            else:
                return make_tool_envelope("invalid_input", reason="invalid_time_format")
        except ValueError:
            return make_tool_envelope("invalid_input", reason="invalid_time_format")
    else:
        clean_time = None

    # 3. Require at least facility_id or court_id
    if facility_id is None and court_id is None:
        return make_tool_envelope("invalid_input", reason="missing_facility_or_court")

    effective_limit = max(1, min(limit, 500))

    try:
        stmt = (
            select(TimeSlot, Court, Facility, SlotPricing)
            .join(Court, TimeSlot.court_id == Court.id)
            .join(Facility, Court.facility_id == Facility.id)
            .outerjoin(SlotPricing, SlotPricing.slot_id == TimeSlot.id)
            .where(TimeSlot.date == date)
            .where(Court.is_active == True)
            .where(Facility.is_approved == True)
        )

        if court_id is not None:
            stmt = stmt.where(TimeSlot.court_id == court_id)
        if facility_id is not None:
            stmt = stmt.where(Court.facility_id == facility_id)

        if clean_time:
            stmt = stmt.where(TimeSlot.start_time == clean_time)

        stmt = stmt.order_by(Court.court_number, TimeSlot.start_time)
        res = await db.execute(stmt)
        rows = res.all()

        if not rows:
            return make_tool_envelope("no_results", data=[], reason="no_slots_found")

        results = []
        for slot, court, facility, pricing in rows:
            # Check Redis atomic lock holder
            try:
                holder = await get_slot_lock_holder(slot.id)
            except Exception as lock_err:
                logger.error(f"[check_court_availability] Redis lock verification failed for slot {slot.id}: {lock_err}")
                return make_tool_envelope("availability_unverified", data=[], reason="availability_unverified")

            # Calculate effective status
            effective_status = slot.status
            if slot.status == "AVAILABLE" and holder:
                effective_status = "HELD"

            # Determine price
            if pricing:
                base_price = pricing.base_price
                dyn_price = pricing.dynamic_price
            else:
                dyn = calculate_dynamic_price(80000.0, slot.date, slot.start_time)
                base_price = 80000.0
                dyn_price = dyn["dynamic_price"]

            results.append({
                "slot_id": slot.id,
                "court_id": court.id,
                "court_number": court.court_number,
                "facility_id": facility.id,
                "facility_name": facility.name,
                "date": slot.date,
                "start_time": slot.start_time,
                "end_time": slot.end_time,
                "effective_status": effective_status,
                "price": dyn_price,
                "base_price": base_price
            })

        return make_tool_envelope("success", data=results[:effective_limit], reason=None)

    except Exception as e:
        logger.error(f"[check_court_availability] Query error: {e}", exc_info=True)
        return make_tool_envelope("internal_error", data=[], reason=str(e))


# ==============================================================================
# TOOL C: get_court_pricing
# ==============================================================================
async def get_court_pricing(
    db: AsyncSession,
    facility_id: Optional[int] = None,
    court_id: Optional[int] = None,
    date: Optional[str] = None,
    time: Optional[str] = None
) -> Dict[str, Any]:
    """
    Retrieve authoritative pricing for a specific court/slot/time.
    Reuses SlotPricing records if already present, or executes calculate_dynamic_price().
    Strictly avoids duplicate dynamic surcharge calculations or price fabrication.
    """
    # 1. Validate date
    if not date:
        return make_tool_envelope("invalid_input", reason="missing_date")
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return make_tool_envelope("invalid_input", reason="invalid_date_format")

    # 2. Validate time
    if not time:
        return make_tool_envelope("invalid_input", reason="missing_time")
    clean_time = time.strip()
    try:
        parts = clean_time.split(":")
        if len(parts) >= 2:
            datetime.strptime(f"{parts[0].zfill(2)}:{parts[1].zfill(2)}", "%H:%M")
            clean_time = f"{parts[0].zfill(2)}:{parts[1].zfill(2)}"
        else:
            return make_tool_envelope("invalid_input", reason="invalid_time_format")
    except ValueError:
        return make_tool_envelope("invalid_input", reason="invalid_time_format")

    # 3. Require facility_id or court_id
    if facility_id is None and court_id is None:
        return make_tool_envelope("invalid_input", reason="missing_facility_or_court")

    try:
        # Search for exact slot in DB first
        stmt = (
            select(TimeSlot, Court, Facility, SlotPricing)
            .join(Court, TimeSlot.court_id == Court.id)
            .join(Facility, Court.facility_id == Facility.id)
            .outerjoin(SlotPricing, SlotPricing.slot_id == TimeSlot.id)
            .where(TimeSlot.date == date)
            .where(TimeSlot.start_time == clean_time)
        )
        if court_id is not None:
            stmt = stmt.where(TimeSlot.court_id == court_id)
        if facility_id is not None:
            stmt = stmt.where(Court.facility_id == facility_id)

        res = await db.execute(stmt)
        row = res.first()

        if row:
            slot, court, facility, pricing = row
            if pricing:
                return make_tool_envelope("success", data=[{
                    "facility_id": facility.id,
                    "facility_name": facility.name,
                    "court_id": court.id,
                    "court_number": court.court_number,
                    "date": date,
                    "time": clean_time,
                    "base_price": pricing.base_price,
                    "dynamic_price": pricing.dynamic_price,
                    "currency": "VND",
                    "adjustment_reason": pricing.adjustment_reason,
                    "is_ai_applied": pricing.is_ai_applied
                }])
            else:
                calc = calculate_dynamic_price(80000.0, date, clean_time)
                return make_tool_envelope("success", data=[{
                    "facility_id": facility.id,
                    "facility_name": facility.name,
                    "court_id": court.id,
                    "court_number": court.court_number,
                    "date": date,
                    "time": clean_time,
                    "base_price": calc["base_price"],
                    "dynamic_price": calc["dynamic_price"],
                    "currency": "VND",
                    "adjustment_reason": calc["adjustment_reason"],
                    "is_ai_applied": calc["is_ai_applied"]
                }])

        # If no slot row exists yet, check if facility/court exists to compute valid quote
        fac_name = "Cụm sân"
        c_num = None
        if court_id is not None:
            c_res = await db.execute(select(Court, Facility).join(Facility, Court.facility_id == Facility.id).where(Court.id == court_id))
            c_row = c_res.first()
            if not c_row:
                return make_tool_envelope("no_results", data=[], reason="court_not_found")
            court_obj, fac_obj = c_row
            fac_name = fac_obj.name
            c_num = court_obj.court_number
            facility_id = fac_obj.id
        elif facility_id is not None:
            f_res = await db.execute(select(Facility).where(Facility.id == facility_id))
            fac_obj = f_res.scalar_one_or_none()
            if not fac_obj:
                return make_tool_envelope("no_results", data=[], reason="facility_not_found")
            fac_name = fac_obj.name

        calc = calculate_dynamic_price(80000.0, date, clean_time)
        return make_tool_envelope("success", data=[{
            "facility_id": facility_id,
            "facility_name": fac_name,
            "court_id": court_id,
            "court_number": c_num,
            "date": date,
            "time": clean_time,
            "base_price": calc["base_price"],
            "dynamic_price": calc["dynamic_price"],
            "currency": "VND",
            "adjustment_reason": calc["adjustment_reason"],
            "is_ai_applied": calc["is_ai_applied"]
        }])

    except Exception as e:
        logger.error(f"[get_court_pricing] Error: {e}", exc_info=True)
        return make_tool_envelope("internal_error", data=[], reason=str(e))


# ==============================================================================
# TOOL D: get_my_bookings
# ==============================================================================
async def get_my_bookings(
    db: AsyncSession,
    user_context: Optional[Dict[str, Any]] = None,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Retrieve personal bookings for the currently authenticated user.
    Anti-IDOR: user_id is strictly extracted from backend-verified user_context.
    Never accepts arbitrary user_id from user prompt or LLM arguments.
    Excludes sensitive payment credentials and full QR check-in codes.
    """
    # 1. Verify authentication
    if not user_context:
        return make_tool_envelope("authentication_required", data=[], reason="login_required")

    raw_uid = user_context.get("id") or user_context.get("user_id")
    role = str(user_context.get("role", "GUEST")).upper()

    if not raw_uid or role == "GUEST":
        return make_tool_envelope("authentication_required", data=[], reason="login_required")

    try:
        user_id = int(raw_uid)
    except (ValueError, TypeError):
        return make_tool_envelope("authentication_required", data=[], reason="invalid_user_id")

    effective_limit = max(1, min(limit, 20))

    try:
        stmt = (
            select(Booking, TimeSlot, Court, Facility)
            .outerjoin(TimeSlot, Booking.slot_id == TimeSlot.id)
            .outerjoin(Court, TimeSlot.court_id == Court.id)
            .outerjoin(Facility, Court.facility_id == Facility.id)
            .where(Booking.user_id == user_id)
            .order_by(Booking.id.desc())
            .limit(effective_limit)
        )
        res = await db.execute(stmt)
        rows = res.all()

        if not rows:
            return make_tool_envelope("no_results", data=[], reason="no_bookings_found")

        results = []
        for booking, slot, court, facility in rows:
            results.append({
                "booking_id": booking.id,
                "facility_name": facility.name if facility else "Cụm sân",
                "court_number": court.court_number if court else None,
                "date": slot.date if slot else None,
                "start_time": slot.start_time if slot else None,
                "end_time": slot.end_time if slot else None,
                "total_amount": booking.total_amount,
                "deposit_amount": booking.deposit_amount,
                "payment_status": booking.payment_status,
                "created_at": booking.created_at.strftime("%Y-%m-%d %H:%M") if booking.created_at else None,
                "has_qr_code": bool(booking.qr_checkin_code)
                # Full qr_checkin_code token is intentionally shielded to avoid leakage in conversation logs
            })

        return make_tool_envelope("success", data=results, reason=None)

    except Exception as e:
        logger.error(f"[get_my_bookings] Error: {e}", exc_info=True)
        return make_tool_envelope("internal_error", data=[], reason=str(e))
