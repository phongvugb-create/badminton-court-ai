"""
BADMINTON.AI - CORE BOOKING SERVICE (PHASE 7.3)
Shared transactional service for Confirmed Booking Creation & Concurrency Safety.
Provides:
1. create_booking_preview: Verifies preconditions & Redis lock ownership -> creates booking intent.
2. execute_confirmed_booking: Atomically consumes intent -> DB transaction with row locking & idempotency -> releases lock.
3. Strict anti-double-booking, anti-replay, anti-IDOR, and fail-closed security.
4. Masks sensitive credentials and QR tokens.
"""

import uuid
import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, or_

from app.models.all_models import Booking, TimeSlot, SlotPricing, Equipment, RentalItem, Court, Facility
from app.core.redis import release_slot_lock, get_slot_lock_holder
from app.ai.tools.booking_confirmation_manager import get_booking_confirmation_manager

logger = logging.getLogger("booking_service")


async def create_booking_preview(
    db: AsyncSession,
    user_id: int,
    slot_id: int,
    equipment_ids: Optional[List[int]] = None
) -> Dict[str, Any]:
    """
    Step A & B: Validates booking preconditions and creates an ephemeral booking confirmation intent.
    DOES NOT create any Booking in DB, DOES NOT mutate slot status, DOES NOT collect payment.
    """
    if not user_id:
        return {
            "status": "authentication_required",
            "message": "Bạn vui lòng đăng nhập trước khi tiến hành đặt sân nhé! 🏸",
            "data": None
        }

    # 1. Fetch Slot, Court, Facility from DB
    try:
        stmt = (
            select(TimeSlot, Court, Facility)
            .join(Court, TimeSlot.court_id == Court.id)
            .join(Facility, Court.facility_id == Facility.id)
            .where(TimeSlot.id == slot_id)
        )
        res = await db.execute(stmt)
        row = res.first()
        if not row:
            return {
                "status": "slot_not_found",
                "message": f"Khung giờ #{slot_id} không tồn tại trên hệ thống.",
                "data": None
            }

        slot, court, facility = row
    except Exception as e:
        logger.error(f"[create_booking_preview] DB query error: {e}", exc_info=True)
        return {
            "status": "internal_error",
            "message": "Lỗi truy vấn cơ sở dữ liệu khi kiểm tra khung giờ.",
            "data": None
        }

    # 2. Check slot status
    if slot.status in ("BOOKED", "MAINTENANCE"):
        return {
            "status": "slot_unavailable",
            "message": f"Khung giờ này hiện đã ở trạng thái {slot.status} và không thể đặt.",
            "data": None
        }

    # 3. Check Redis lock ownership (Must be held by this user)
    try:
        holder = await get_slot_lock_holder(slot.id)
    except Exception as redis_err:
        logger.error(f"[create_booking_preview] Redis error checking lock holder: {redis_err}", exc_info=True)
        return {
            "status": "availability_unverified",
            "message": "Dịch vụ phân tán Redis hiện không khả dụng để xác minh quyền giữ chỗ. Vui lòng thử lại sau!",
            "data": None
        }

    if not holder or holder != str(user_id):
        return {
            "status": "slot_not_held",
            "message": (
                "Khung giờ này hiện chưa được bạn giữ chỗ hoặc thời gian giữ chỗ (10 phút) đã hết hạn. "
                "Vui lòng thực hiện giữ chỗ trước khi tạo đơn đặt sân nhé! 🏸"
            ),
            "data": None
        }

    # 4. Check for active conflicting bookings on this slot in DB
    try:
        conflict_stmt = (
            select(Booking)
            .where(
                and_(
                    Booking.slot_id == slot.id,
                    Booking.payment_status != "CANCELLED"
                )
            )
        )
        c_res = await db.execute(conflict_stmt)
        active_booking = c_res.scalars().first()
        if active_booking:
            return {
                "status": "slot_unavailable",
                "message": "Khung giờ này đã có đơn đặt sân đang hoạt động trên hệ thống.",
                "data": None
            }
    except Exception as e:
        logger.error(f"[create_booking_preview] DB conflict check error: {e}", exc_info=True)
        return {
            "status": "internal_error",
            "message": "Lỗi kiểm tra trùng lặp đơn đặt sân.",
            "data": None
        }

    # 5. Authoritative price calculation
    try:
        price_stmt = select(SlotPricing).where(SlotPricing.slot_id == slot.id)
        p_res = await db.execute(price_stmt)
        pricing = p_res.scalar_one_or_none()
        court_price = pricing.dynamic_price if pricing else 80000.0
    except Exception:
        court_price = 80000.0

    equip_total = 0.0
    valid_equipment_ids = []
    if equipment_ids:
        for eq_id in equipment_ids:
            try:
                eq_stmt = select(Equipment).where(Equipment.id == eq_id)
                eq_res = await db.execute(eq_stmt)
                eq = eq_res.scalar_one_or_none()
                if eq and eq.available_qty > 0:
                    equip_total += float(eq.rental_price)
                    valid_equipment_ids.append(eq.id)
            except Exception:
                pass

    total_amount = float(court_price + equip_total)
    deposit_amount = float(round(total_amount * 0.5, -3)) # Standard 50% deposit rule

    # 6. Create booking confirmation intent
    mgr = get_booking_confirmation_manager()
    intent = await mgr.create_booking_intent(
        user_id=user_id,
        slot_id=slot.id,
        court_id=court.id,
        facility_id=facility.id,
        facility_name=facility.name,
        court_number=court.court_number,
        date=slot.date,
        start_time=slot.start_time,
        end_time=slot.end_time,
        total_amount=total_amount,
        deposit_amount=deposit_amount,
        equipment_ids=valid_equipment_ids,
        ttl_seconds=300
    )

    return {
        "status": "preview_created",
        "message": "Bản xem trước đặt sân đã sẵn sàng.",
        "data": {
            "booking_intent_id": intent["intent_id"],
            "slot_id": slot.id,
            "facility_id": facility.id,
            "facility_name": facility.name,
            "court_id": court.id,
            "court_number": court.court_number,
            "date": slot.date,
            "start_time": slot.start_time,
            "end_time": slot.end_time,
            "court_price": court_price,
            "equipment_total": equip_total,
            "total_amount": total_amount,
            "deposit_amount": deposit_amount,
            "expires_at": intent["expires_at"]
        }
    }


async def execute_confirmed_booking(
    db: AsyncSession,
    user_id: int,
    booking_intent_id: str,
    idempotency_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Step C, D, E, F: Atomically consumes booking intent, commits DB transaction with row locking,
    enforces idempotency, marks slot BOOKED, and releases Redis lock.
    """
    if not user_id:
        return {
            "status": "authentication_required",
            "message": "Yêu cầu đăng nhập tài khoản.",
            "data": None
        }

    if not booking_intent_id:
        return {
            "status": "invalid_input",
            "message": "Thiếu mã xác nhận đặt sân (booking_intent_id).",
            "data": None
        }

    effective_key = idempotency_key or booking_intent_id

    # 1. Idempotency Pre-Check: Has this intent or key already created a booking?
    try:
        existing_stmt = select(Booking).where(Booking.idempotency_key == effective_key)
        existing_res = await db.execute(existing_stmt)
        existing_booking = existing_res.scalar_one_or_none()
        if existing_booking:
            logger.info(f"[execute_confirmed_booking] Idempotent request: booking #{existing_booking.id} already exists.")
            # Fetch slot and facility for complete details
            slot_stmt = (
                select(TimeSlot, Court, Facility)
                .join(Court, TimeSlot.court_id == Court.id)
                .join(Facility, Court.facility_id == Facility.id)
                .where(TimeSlot.id == existing_booking.slot_id)
            )
            s_row = (await db.execute(slot_stmt)).first()
            s_data = {}
            if s_row:
                eslot, ecourt, efac = s_row
                s_data = {
                    "facility_name": efac.name,
                    "court_number": ecourt.court_number,
                    "date": eslot.date,
                    "start_time": eslot.start_time,
                    "end_time": eslot.end_time
                }

            return {
                "status": "booking_succeeded",
                "is_idempotent": True,
                "message": "Đơn đặt sân đã được xác nhận thành công trước đó (yêu cầu lặp hợp lệ). 🏸",
                "data": {
                    "booking_id": existing_booking.id,
                    "slot_id": existing_booking.slot_id,
                    "facility_name": s_data.get("facility_name", ""),
                    "court_number": s_data.get("court_number", ""),
                    "date": s_data.get("date", ""),
                    "start_time": s_data.get("start_time", ""),
                    "end_time": s_data.get("end_time", ""),
                    "total_amount": existing_booking.total_amount,
                    "deposit_amount": existing_booking.deposit_amount,
                    "payment_status": existing_booking.payment_status
                }
            }
    except Exception as e:
        logger.warning(f"[execute_confirmed_booking] Idempotency check error: {e}")

    # 2. Atomic consumption of booking intent via Redis Lua script
    mgr = get_booking_confirmation_manager()
    consumed_ok, intent, reason = await mgr.consume_booking_intent(
        intent_id=booking_intent_id,
        user_id=user_id
    )

    if not consumed_ok:
        if reason == "already_consumed":
            # Check DB reconciliation in case previous transaction succeeded
            try:
                rec_res = await db.execute(select(Booking).where(Booking.idempotency_key == effective_key))
                rec_booking = rec_res.scalar_one_or_none()
                if rec_booking:
                    return {
                        "status": "booking_succeeded",
                        "is_idempotent": True,
                        "message": "Đơn đặt sân đã được xác nhận thành công trước đó. 🏸",
                        "data": {
                            "booking_id": rec_booking.id,
                            "slot_id": rec_booking.slot_id,
                            "total_amount": rec_booking.total_amount,
                            "deposit_amount": rec_booking.deposit_amount,
                            "payment_status": rec_booking.payment_status
                        }
                    }
            except Exception:
                pass
            return {
                "status": "already_consumed",
                "message": "Yêu cầu đặt sân này đã được thực hiện trước đó (chống gửi lặp thao tác). 🏸",
                "data": None
            }
        elif reason == "booking_intent_expired":
            return {
                "status": "booking_intent_expired",
                "message": "Bản xem trước đặt sân đã hết hạn (5 phút). Vui lòng tạo bản xem trước mới nhé! 🏸",
                "data": None
            }
        elif reason == "permission_denied":
            return {
                "status": "permission_denied",
                "message": "Bạn không có quyền xác nhận yêu cầu đặt sân của tài khoản khác.",
                "data": None
            }
        elif reason == "redis_unavailable":
            return {
                "status": "availability_unverified",
                "message": "Dịch vụ phân tán Redis hiện không khả dụng để đảm bảo an toàn giao dịch. Vui lòng thử lại sau!",
                "data": None
            }
        else:
            return {
                "status": "booking_failed",
                "message": f"Không thể xử lý yêu cầu đặt sân: {reason}",
                "data": None
            }

    slot_id = intent["slot_id"]

    # 3. Verify Redis lock ownership right before DB write
    try:
        holder = await get_slot_lock_holder(slot_id)
        if holder != str(user_id):
            return {
                "status": "slot_unavailable",
                "message": "Khung giờ này đã hết thời gian giữ chỗ (10 phút) hoặc không còn thuộc quyền giữ chỗ của bạn. 🏸",
                "data": None
            }
    except Exception as redis_err:
        logger.error(f"[execute_confirmed_booking] Redis lock check error: {redis_err}", exc_info=True)
        return {
            "status": "availability_unverified",
            "message": "Hệ thống tạm thời không thể xác minh kết quả khóa Redis để tạo đơn đặt. Vui lòng thử lại sau!",
            "data": None
        }

    # 4. Database Transaction with row locking & conflict avoidance
    try:
        # On PostgreSQL, with_for_update() serializes concurrent transactions on the same slot
        # On SQLite, with_for_update() is safely ignored
        bind = db.bind or getattr(db, "sync_session", db).bind
        is_postgres = bool(bind and "postgres" in bind.dialect.name.lower())

        stmt = (
            select(TimeSlot, Court, Facility)
            .join(Court, TimeSlot.court_id == Court.id)
            .join(Facility, Court.facility_id == Facility.id)
            .where(TimeSlot.id == slot_id)
        )
        if is_postgres:
            stmt = stmt.with_for_update(of=TimeSlot)

        res = await db.execute(stmt)
        row = res.first()
        if not row:
            await db.rollback()
            return {
                "status": "slot_unavailable",
                "message": "Khung giờ không còn tồn tại trên hệ thống.",
                "data": None
            }

        slot, court, facility = row

        if slot.status in ("BOOKED", "MAINTENANCE"):
            await db.rollback()
            return {
                "status": "slot_unavailable",
                "message": f"Khung giờ này hiện đã ở trạng thái {slot.status} và không thể đặt.",
                "data": None
            }

        # Check conflicting active bookings inside transaction
        conflict_stmt = (
            select(Booking)
            .where(
                and_(
                    Booking.slot_id == slot.id,
                    Booking.payment_status != "CANCELLED"
                )
            )
        )
        c_res = await db.execute(conflict_stmt)
        if c_res.scalars().first():
            await db.rollback()
            return {
                "status": "slot_unavailable",
                "message": "Khung giờ này đã được đặt bởi khách hàng khác.",
                "data": None
            }

        # Create Booking record
        qr_code = f"QR-ALB-{uuid.uuid4().hex[:10].upper()}"
        booking = Booking(
            user_id=user_id,
            slot_id=slot.id,
            total_amount=intent["total_amount"],
            deposit_amount=intent["deposit_amount"],
            payment_status="PENDING", # Pending deposit payment
            qr_checkin_code=qr_code,
            idempotency_key=effective_key
        )
        db.add(booking)
        await db.flush()

        # Handle equipment rentals
        for eq_id in intent.get("equipment_ids", []):
            try:
                eq_stmt = select(Equipment).where(Equipment.id == eq_id)
                if is_postgres:
                    eq_stmt = eq_stmt.with_for_update()
                eq_res = await db.execute(eq_stmt)
                eq = eq_res.scalar_one_or_none()
                if eq and eq.available_qty > 0:
                    eq.available_qty -= 1
                    r_item = RentalItem(
                        booking_id=booking.id,
                        equipment_id=eq.id,
                        quantity=1,
                        price=eq.rental_price
                    )
                    db.add(r_item)
            except Exception as eq_err:
                logger.warning(f"[execute_confirmed_booking] Equipment rental error: {eq_err}")

        # Mark slot as BOOKED
        slot.status = "BOOKED"

        # Commit transaction
        await db.commit()
        await db.refresh(booking)

    except Exception as db_err:
        await db.rollback()
        logger.error(f"[execute_confirmed_booking] DB Transaction error: {db_err}", exc_info=True)
        # Check if error was unique constraint violation on idempotency_key
        if "unique" in str(db_err).lower() or "integrity" in str(db_err).lower():
            try:
                rec_res = await db.execute(select(Booking).where(Booking.idempotency_key == effective_key))
                rec_booking = rec_res.scalar_one_or_none()
                if rec_booking:
                    return {
                        "status": "booking_succeeded",
                        "is_idempotent": True,
                        "message": "Đơn đặt sân đã được xác nhận thành công trước đó. 🏸",
                        "data": {
                            "booking_id": rec_booking.id,
                            "slot_id": rec_booking.slot_id,
                            "facility_name": facility.name,
                            "court_number": court.court_number,
                            "date": slot.date,
                            "start_time": slot.start_time,
                            "end_time": slot.end_time,
                            "total_amount": rec_booking.total_amount,
                            "deposit_amount": rec_booking.deposit_amount,
                            "payment_status": rec_booking.payment_status
                        }
                    }
            except Exception:
                pass

        return {
            "status": "booking_failed",
            "message": "Lỗi lưu trữ dữ liệu khi tạo đơn đặt sân. Thao tác đã được khôi phục an toàn (rollback).",
            "data": None
        }

    # 5. Lock cleanup: Release Redis slot lock after DB transaction committed
    try:
        await release_slot_lock(slot.id, user_id)
    except Exception as lock_err:
        logger.warning(f"[execute_confirmed_booking] Lock release error after commit: {lock_err}")
        # DO NOT fail the booking: DB is already committed and lock will expire via TTL

    # 6. Return sanitized result (NO QR check-in code exposed in default response)
    return {
        "status": "booking_succeeded",
        "is_idempotent": False,
        "message": "Đặt sân thành công! Vui lòng hoàn tất thanh toán cọc trong vòng 10 phút. 🏸",
        "data": {
            "booking_id": booking.id,
            "slot_id": slot.id,
            "facility_name": facility.name,
            "court_number": court.court_number,
            "date": slot.date,
            "start_time": slot.start_time,
            "end_time": slot.end_time,
            "total_amount": booking.total_amount,
            "deposit_amount": booking.deposit_amount,
            "payment_status": booking.payment_status
        }
    }
