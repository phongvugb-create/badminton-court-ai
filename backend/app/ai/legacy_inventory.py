"""Bridge the legacy website's central JSON database into the AI booking tables.

The browser application stores recurring slot templates without a date and stores
the selected date on each booking order. The AI API uses date-specific SQLAlchemy
rows, so this module materializes the shared templates for the requested date.
"""

import json
import logging
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.all_models import Booking, Court, Facility, SlotPricing, TimeSlot, User
from app.core.security import get_password_hash
from app.core.redis import get_slot_lock_holder

logger = logging.getLogger("legacy_inventory")


def _load_central_data() -> Dict[str, Any]:
    manager = None
    try:
        from db_engine import db_manager

        manager = db_manager
        if str(getattr(db_manager, "db_type", "")).upper() == "POSTGRESQL":
            result = db_manager.load_data() or {}
            if result.get("facilities"):
                return result
    except Exception as exc:
        logger.warning("Could not load central database manager data: %s", exc)

    root = Path(__file__).resolve().parents[3]
    data_path = root / "database.json"
    try:
        with data_path.open("r", encoding="utf-8") as source:
            value = json.load(source)
            if isinstance(value, dict) and value.get("facilities"):
                return value
    except Exception as exc:
        logger.warning("Could not load legacy database file: %s", exc)
    if manager is not None:
        try:
            return manager.load_data() or {}
        except Exception as exc:
            logger.warning("Central database fallback read failed: %s", exc)
    return {}


def legacy_facilities_matching(query: Optional[str]) -> List[Dict[str, Any]]:
    """Return central facilities matching a name/address query; None means all."""
    facilities = _load_central_data().get("facilities", [])
    if not isinstance(facilities, list):
        return []
    if not query or not query.strip():
        return [item for item in facilities if isinstance(item, dict)]

    key = query.strip().casefold()
    matches = []
    ignored = {"sân", "cầu", "lông", "cụm", "clb", "badminton", "club", "sport", "sports"}
    for item in facilities:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).casefold()
        address = str(item.get("address", "")).casefold()
        if key in name or key in address:
            matches.append(item)
            continue
        words = [word for word in re.findall(r"\w+", name) if word not in ignored]
        if any(" ".join(words[start:end]) in key
               for start in range(len(words))
               for end in range(start + 2, len(words) + 1)):
            matches.append(item)
            continue
        address_words = re.findall(r"\w+", address)
        if any(" ".join(address_words[start:end]) in key
               for start in range(len(address_words))
               for end in range(start + 2, len(address_words) + 1)):
            matches.append(item)
    return matches


def _date_key(raw: Any) -> Optional[str]:
    value = str(raw or "").strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(value, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _time_ranges(raw: Any) -> List[Tuple[str, str]]:
    return re.findall(r"([0-2]?\d:[0-5]\d)\s*[-–]\s*([0-2]?\d:[0-5]\d)", str(raw or ""))


def _order_blocks_slot(order: Dict[str, Any], facility: Dict[str, Any], court_name: str,
                       date: str, start_time: str, end_time: str) -> bool:
    if _date_key(order.get("booking_date") or order.get("date")) != date:
        return False
    order_facility = str(order.get("facility_name", "")).strip().casefold()
    if order_facility and order_facility != str(facility.get("name", "")).strip().casefold():
        return False
    status = " ".join(str(order.get(k, "")) for k in ("order_status", "deposit_status", "status")).casefold()
    if any(word in status for word in ("hủy", "huy", "cancel", "refund", "hoàn tiền")):
        return False
    order_court = str(order.get("court_name", "")).strip().casefold()
    if order_court and order_court != court_name.strip().casefold():
        # Legacy reservations may refer to a generated court by its visible number.
        number = re.search(r"([a-z]?\d+)", court_name.casefold())
        if not number or number.group(1) not in order_court:
            return False
    for busy_start, busy_end in _time_ranges(order.get("slot_time")):
        if busy_start < end_time and busy_end > start_time:
            return True
    return False


def _court_number(court: Dict[str, Any]) -> str:
    value = str(court.get("court_number") or "").strip()
    if value:
        return value
    match = re.search(r"(?:sân\s*)?([a-z]?\d+)\b", str(court.get("name", "")), re.IGNORECASE)
    return match.group(1) if match else ""


def _court_is_active(court: Dict[str, Any]) -> bool:
    status = str(court.get("status", "")).casefold()
    return not any(word in status for word in ("bảo trì", "bảo trì", "maintenance", "ngừng", "inactive"))


def record_confirmed_ai_booking(booking: Dict[str, Any], user_id: int) -> bool:
    """Mirror a confirmed AI booking into the website's shared central backup."""
    try:
        from db_engine import db_manager

        data = _load_central_data()
        result = booking.get("data") or booking
        booking_id = result.get("booking_id")
        if booking_id is None:
            return False
        orders = data.setdefault("booking_orders", [])
        booking_code = f"AI-BK-{booking_id}"
        if any(str(order.get("booking_code")) == booking_code for order in orders if isinstance(order, dict)):
            return True

        user = next(
            (item for item in data.get("users", [])
             if isinstance(item, dict) and str(item.get("id")) == str(user_id)),
            {},
        )
        date_key = _date_key(result.get("date"))
        display_date = datetime.strptime(date_key, "%Y-%m-%d").strftime("%d/%m/%Y") if date_key else str(result.get("date") or "")
        order = {
            "id": int(datetime.now().timestamp() * 1000),
            "booking_code": booking_code,
            "user_name": user.get("name") or user.get("full_name") or "Khách hàng",
            "user_phone": user.get("phone") or "",
            "facility_name": result.get("facility_name") or "",
            "court_name": f"Sân {result.get('court_number') or ''}".strip(),
            "slot_time": f"{result.get('start_time') or ''} - {result.get('end_time') or ''}",
            "booking_date": display_date,
            "total_amount": result.get("total_amount", 0),
            "deposit_amount": result.get("deposit_amount", 0),
            "deposit_status": "Chờ Cọc",
            "order_status": "Chờ Thanh Toán Cọc",
            "created_at": datetime.now().strftime("%H:%M:%S"),
        }
        orders.insert(0, order)
        db_manager.save_data(data)
        return True
    except Exception as exc:
        logger.error("Could not mirror AI booking to shared database: %s", exc, exc_info=True)
        return False


async def sync_legacy_inventory(
    db: AsyncSession,
    date: Optional[str] = None,
    facility_ids: Optional[Iterable[int]] = None,
    start_time: Optional[str] = None,
) -> Dict[str, int]:
    """Upsert shared facilities/courts and materialize date-specific slot rows."""
    data = _load_central_data()
    raw_facilities = data.get("facilities", [])
    if not isinstance(raw_facilities, list) or not raw_facilities:
        return {"facilities": 0, "courts": 0, "slots": 0}

    requested_ids = {int(value) for value in facility_ids} if facility_ids is not None else None
    facilities = [
        item for item in raw_facilities
        if isinstance(item, dict)
        and (requested_ids is None or int(item.get("id", -1)) in requested_ids)
    ]
    raw_users = data.get("users", []) if isinstance(data.get("users", []), list) else []
    users_by_source_id: Dict[int, User] = {}

    # Import central users only when absent; preserve existing AI credentials/roles.
    for source_user in raw_users:
        if not isinstance(source_user, dict) or source_user.get("id") is None:
            continue
        source_user_id = int(source_user["id"])
        phone = str(source_user.get("phone") or f"legacy-{source_user_id}")
        # Prefer the unique phone as the identity key. The legacy website and
        # AI database can both have a user with the same numeric ID but different
        # people; blindly trusting that ID could assign a facility to the wrong
        # owner or associate a booking with the wrong customer.
        existing_result = await db.execute(select(User).where(User.phone == phone))
        user = existing_result.scalar_one_or_none()
        if user is None:
            user = await db.get(User, source_user_id)
            if user is not None and user.phone != phone:
                user = None
        if user is None:
            plain_password = str(source_user.get("password") or uuid.uuid4().hex)
            user = User(
                full_name=str(source_user.get("name") or f"Người dùng {source_user_id}"),
                phone=phone,
                email=source_user.get("email"),
                password_hash=get_password_hash(plain_password),
                role=str(source_user.get("role") or "CUSTOMER").upper(),
                elo_rating=source_user.get("elo_rating") if isinstance(source_user.get("elo_rating"), int) else 1200,
                is_approved=bool(source_user.get("is_approved", True)),
            )
            db.add(user)
            await db.flush()
        users_by_source_id[source_user_id] = user

    owner_result = await db.execute(select(User).where(User.role.in_(["OWNER", "ADMIN"])).order_by(User.id))
    available_owners = owner_result.scalars().all()
    fallback_owner = available_owners[0] if available_owners else None

    existing_courts = data.get("courts", []) if isinstance(data.get("courts", []), list) else []
    templates = data.get("time_slots", []) if isinstance(data.get("time_slots", []), list) else []
    orders = data.get("booking_orders", []) if isinstance(data.get("booking_orders", []), list) else []
    counts = {"facilities": 0, "courts": 0, "slots": 0}

    for source_facility in facilities:
        facility_id = int(source_facility["id"])
        owner_source_id = next(
            (int(u["id"]) for u in raw_users
             if isinstance(u, dict) and str(u.get("role", "")).upper() == "OWNER"
             and str(u.get("facility_id", "")) == str(facility_id)
             and int(u["id"]) in users_by_source_id),
            None,
        )
        owner = users_by_source_id.get(owner_source_id) if owner_source_id else fallback_owner
        if owner is None:
            logger.warning("Skipping legacy facility %s because no owner/admin user is available", facility_id)
            continue

        facility = await db.get(Facility, facility_id)
        values = dict(
            owner_id=owner.id,
            name=str(source_facility.get("name") or f"Cơ sở {facility_id}"),
            address=str(source_facility.get("address") or ""),
            latitude=float(source_facility.get("latitude") or 0),
            longitude=float(source_facility.get("longitude") or 0),
            open_time=str(source_facility.get("open_time") or "05:00"),
            close_time=str(source_facility.get("close_time") or "23:00"),
            image_url=source_facility.get("img") or source_facility.get("image_url"),
            rating=float(source_facility.get("rating") or 4.8),
            is_approved=bool(source_facility.get("is_approved", True)),
        )
        if facility is None:
            facility = Facility(id=facility_id, **values)
            db.add(facility)
        else:
            for key, value in values.items():
                setattr(facility, key, value)
        counts["facilities"] += 1

        source_courts = [
            court for court in existing_courts
            if isinstance(court, dict) and int(court.get("facility_id", -1)) == facility_id
        ]
        by_number: Dict[str, Dict[str, Any]] = {}
        for source_court in source_courts:
            number = _court_number(source_court)
            if number:
                by_number[number.casefold()] = source_court

        total_courts = max(1, min(int(source_facility.get("courts_count") or len(source_courts) or 1), 100))
        court_specs: List[Tuple[int, str, str, bool, int]] = []
        used_numbers: Set[str] = set()
        for source_court in source_courts:
            number = _court_number(source_court)
            if not number:
                number = f"{len(court_specs) + 1:02d}"
            used_numbers.add(number.casefold())
            source_court_id = int(source_court["id"])
            existing_court = await db.get(Court, source_court_id)
            if existing_court is not None and existing_court.facility_id != facility_id:
                # Legacy IDs are only unique inside the website dataset. Avoid
                # stealing an AI court row with the same ID from another facility.
                source_court_id = 1_000_000 + facility_id * 100 + len(court_specs) + 1
                while True:
                    collision = await db.get(Court, source_court_id)
                    if collision is None or collision.facility_id == facility_id:
                        break
                    source_court_id += 1
            court_specs.append((
                source_court_id, number,
                str(source_court.get("surface_type") or source_court.get("court_type") or "Thảm cầu lông"),
                _court_is_active(source_court), len(court_specs) + 1
            ))

        next_number = 1
        while len(court_specs) < total_courts:
            number = f"{next_number:02d}"
            next_number += 1
            if number.casefold() in used_numbers:
                continue
            used_numbers.add(number.casefold())
            generated_id = 1_000_000 + facility_id * 100 + next_number
            while True:
                collision = await db.get(Court, generated_id)
                if collision is None or collision.facility_id == facility_id:
                    break
                generated_id += 1
            court_specs.append((generated_id, number, "Thảm cầu lông", True, next_number - 1))

        court_name_by_number: Dict[str, str] = {}
        for court_id, number, surface, active, court_order in court_specs:
            court = await db.get(Court, court_id)
            if court is None:
                court = Court(
                    id=court_id,
                    facility_id=facility_id,
                    court_number=number,
                    surface_type=surface,
                    is_active=active,
                )
                db.add(court)
            else:
                court.facility_id = facility_id
                court.court_number = number
                court.surface_type = surface
                court.is_active = active
            counts["courts"] += 1
            source_court = by_number.get(number.casefold())
            court_name_by_number[number.casefold()] = (
                str(source_court.get("name")) if source_court and source_court.get("name")
                else f"Sân {number}"
            )

            if not date or not active:
                continue

            # Website slot rows are recurring daily templates; the booking date is
            # stored on booking_orders, so materialize those templates for this date.
            for template_index, template in enumerate(templates, start=1):
                if not isinstance(template, dict):
                    continue
                start = str(template.get("start_time") or "")[:5]
                end = str(template.get("end_time") or "")[:5]
                if not re.fullmatch(r"\d{2}:\d{2}", start) or not re.fullmatch(r"\d{2}:\d{2}", end):
                    continue
                if start_time and start != start_time:
                    continue
                legacy_status = str(template.get("status") or "AVAILABLE").upper()
                if legacy_status == "MAINTENANCE":
                    slot_status = "MAINTENANCE"
                else:
                    court_label = court_name_by_number[number.casefold()]
                    booked = any(
                        isinstance(order, dict)
                        and _order_blocks_slot(order, source_facility, court_label, date, start, end)
                        for order in orders
                    )
                    slot_status = "BOOKED" if booked else "AVAILABLE"

                slot_id = 10_000_000 + facility_id * 1_000_000 + court_order * 1_000 + template_index
                slot = await db.get(TimeSlot, slot_id)
                if slot is None:
                    existing_slot_result = await db.execute(
                        select(TimeSlot).where(
                            TimeSlot.court_id == court_id,
                            TimeSlot.date == date,
                            TimeSlot.start_time == start,
                        )
                    )
                    slot = existing_slot_result.scalars().first()
                if slot is None:
                    slot = TimeSlot(
                        id=slot_id,
                        court_id=court_id,
                        date=date,
                        start_time=start,
                        end_time=end,
                        status=slot_status,
                    )
                    db.add(slot)
                    await db.flush()
                else:
                    slot.court_id = court_id
                    slot.date = date
                    slot.start_time = start
                    slot.end_time = end
                    active_booking_result = await db.execute(
                        select(Booking.id).where(
                            Booking.slot_id == slot.id,
                            Booking.payment_status != "CANCELLED",
                        ).limit(1)
                    )
                    has_active_booking = active_booking_result.first() is not None
                    try:
                        lock_holder = await get_slot_lock_holder(slot.id) if slot.status == "HELD" else None
                    except Exception:
                        # Keep existing state if lock service cannot be checked.
                        lock_holder = "unverified"
                    if has_active_booking:
                        slot.status = "BOOKED"
                    elif lock_holder:
                        slot.status = "HELD"
                    else:
                        slot.status = slot_status
                counts["slots"] += 1

                price = float(template.get("price") or template.get("base_price") or source_facility.get("base_price") or 80_000)
                pricing_result = await db.execute(select(SlotPricing).where(SlotPricing.slot_id == slot.id))
                pricing = pricing_result.scalar_one_or_none()
                if pricing is None:
                    pricing = SlotPricing(
                        slot_id=slot.id,
                        base_price=float(template.get("base_price") or source_facility.get("base_price") or price),
                        dynamic_price=price,
                        adjustment_reason=str(template.get("adjustment") or "Giá theo lịch website"),
                        is_ai_applied=bool(template.get("is_ai_dynamic", False)),
                    )
                    db.add(pricing)
                else:
                    pricing.base_price = float(template.get("base_price") or source_facility.get("base_price") or price)
                    pricing.dynamic_price = price
                    pricing.adjustment_reason = str(template.get("adjustment") or "Giá theo lịch website")
                    pricing.is_ai_applied = bool(template.get("is_ai_dynamic", False))

    await db.commit()
    return counts
