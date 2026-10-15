"""
BADMINTON.AI - PHASE 7.4A.3 PAYMENT EXPIRY SERVICE — OPERATIONS HARDENED
Safely expires unpaid pending bookings past configured timeout.
Guarantees:
1. Strict fail-closed configuration guard: disabled by default (PAYMENT_PENDING_EXPIRY_ENABLED=False).
2. Explicit, approved timeout validation (PAYMENT_PENDING_EXPIRY_MINUTES must be positive integer).
3. Transactional safety with PostgreSQL row-level locking (with_for_update).
4. Never cancels bookings with confirmed (SUCCESS) or in-doubt (REQUIRES_RECONCILIATION) payments.
5. Only restores TimeSlot to AVAILABLE if no other active booking holds the slot.
6. Safe Redis lock release verifying ownership (never releases another user's lock).
7. Idempotent across multiple runs or competing concurrent workers.
8. Batch processing with configurable limit to prevent memory exhaustion.
9. Facility-scoped processing for OWNER/STAFF callers.
10. Lock acquisition order: Booking → Payment → TimeSlot (consistent with webhook handler).
"""

import os
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, or_

from app.config import settings
from app.models.all_models import (
    Booking,
    Payment,
    TimeSlot,
    PaymentStatus,
    TransactionStatus,
    SlotStatus
)
from app.core.redis import get_slot_lock_holder, release_slot_lock

logger = logging.getLogger("payment_expiry_service")

# Maximum bookings per scan to prevent memory exhaustion and long transactions
DEFAULT_BATCH_LIMIT = 50
MAX_BATCH_LIMIT = 200


def _is_expiry_enabled() -> bool:
    """
    Fail-closed configuration check.
    Returns True ONLY if PAYMENT_PENDING_EXPIRY_ENABLED is explicitly set to a truthy value.
    Missing or ambiguous configuration → disabled.
    """
    env_flag = os.getenv("PAYMENT_PENDING_EXPIRY_ENABLED")
    if env_flag is not None:
        return env_flag.strip().lower() in ("true", "1", "yes")
    return bool(getattr(settings, "PAYMENT_PENDING_EXPIRY_ENABLED", False))


def _get_timeout_minutes(custom_timeout_minutes: Optional[int] = None) -> Optional[int]:
    """
    Validates and returns the timeout in minutes.
    Returns None if invalid, missing, or non-positive (fail-closed).
    """
    timeout_raw = custom_timeout_minutes
    if timeout_raw is None:
        env_timeout = os.getenv("PAYMENT_PENDING_EXPIRY_MINUTES")
        if env_timeout is not None and env_timeout.strip().isdigit():
            timeout_raw = int(env_timeout.strip())
        else:
            timeout_raw = getattr(settings, "PAYMENT_PENDING_EXPIRY_MINUTES", None)

    try:
        timeout_minutes = int(timeout_raw) if timeout_raw is not None else None
    except (ValueError, TypeError):
        timeout_minutes = None

    if timeout_minutes is None or timeout_minutes <= 0:
        return None

    return timeout_minutes


async def expire_pending_bookings(
    db: AsyncSession,
    custom_timeout_minutes: Optional[int] = None,
    batch_limit: Optional[int] = None,
    facility_ids: Optional[List[int]] = None,
    force_enabled: bool = False,
    _internal_force_enabled: bool = False
) -> Dict[str, Any]:
    """
    Scans and expires unpaid pending bookings older than configured threshold.
    Returns structured execution report.

    Parameters:
        db: Database session.
        custom_timeout_minutes: Override timeout (for testing only). Must be positive.
        batch_limit: Max bookings to process per scan (default 50, max 200).
        facility_ids: Restrict processing to bookings for slots in these facilities.
                      Used for OWNER/STAFF facility-scoped access.
        force_enabled: INTERNAL / TEST USE ONLY - allows tests to simulate enabled state.
                       Never exposed via API endpoints.
        _internal_force_enabled: Alias for force_enabled.
    """
    # 1. Configuration Guard (Fail-closed)
    is_enabled = force_enabled or _internal_force_enabled or _is_expiry_enabled()

    if not is_enabled:
        logger.info("[expire_pending_bookings] Pending booking expiry is disabled by configuration.")
        return {
            "status": "expiry_disabled",
            "message": "Tính năng tự động hết hạn đơn đặt sân chưa được bật (PAYMENT_PENDING_EXPIRY_ENABLED=False). Dữ liệu được giữ nguyên.",
            "expired_count": 0,
            "processed_booking_ids": [],
            "skipped_booking_ids": []
        }

    # 2. Timeout Policy Validation
    timeout_minutes = _get_timeout_minutes(custom_timeout_minutes)

    if timeout_minutes is None:
        logger.warning(f"[expire_pending_bookings] Invalid or unconfigured timeout policy: {custom_timeout_minutes}")
        return {
            "status": "invalid_timeout_policy",
            "message": "Chính sách thời gian hết hạn (PAYMENT_PENDING_EXPIRY_MINUTES) chưa được cấu hình hoặc không hợp lệ. Dữ liệu được giữ nguyên.",
            "expired_count": 0,
            "processed_booking_ids": [],
            "skipped_booking_ids": []
        }

    # 3. Batch Limit Validation
    effective_batch = DEFAULT_BATCH_LIMIT
    if batch_limit is not None:
        try:
            effective_batch = int(batch_limit)
        except (ValueError, TypeError):
            effective_batch = DEFAULT_BATCH_LIMIT
    effective_batch = max(1, min(effective_batch, MAX_BATCH_LIMIT))

    # 4. Calculate Cutoff Timestamp
    now_utc = datetime.utcnow()
    cutoff_time = now_utc - timedelta(minutes=timeout_minutes)

    # 5. Detect Database Dialect for Row-level Locking
    is_postgres = False
    try:
        if db.bind and hasattr(db.bind, "dialect") and db.bind.dialect.name == "postgresql":
            is_postgres = True
    except Exception:
        pass

    # 6. Query Candidate Pending Bookings with Batch Limit
    candidate_stmt = select(Booking.id).where(
        and_(
            Booking.payment_status == PaymentStatus.PENDING.value,
            Booking.created_at <= cutoff_time
        )
    ).order_by(Booking.id.asc()).limit(effective_batch)

    # 6a. Facility-scoped filtering for OWNER/STAFF
    if facility_ids is not None and len(facility_ids) > 0:
        from app.models.all_models import Court
        # Join through slot -> court to filter by facility
        candidate_stmt = (
            select(Booking.id)
            .join(TimeSlot, Booking.slot_id == TimeSlot.id)
            .join(Court, TimeSlot.court_id == Court.id)
            .where(
                and_(
                    Booking.payment_status == PaymentStatus.PENDING.value,
                    Booking.created_at <= cutoff_time,
                    Court.facility_id.in_(facility_ids)
                )
            )
            .order_by(Booking.id.asc())
            .limit(effective_batch)
        )

    candidate_res = await db.execute(candidate_stmt)
    candidate_ids = candidate_res.scalars().all()

    processed_ids: List[int] = []
    skipped_ids: List[int] = []

    # 7. Process Each Candidate in Transactional Isolation
    # Lock acquisition order: Booking → Payment → TimeSlot
    # This order is consistent with process_payment_webhook to prevent deadlocks.
    for b_id in candidate_ids:
        try:
            # Step A: Row-level lock on Booking (Lock Order Position 1)
            bk_query = select(Booking).where(Booking.id == b_id)
            if is_postgres:
                bk_query = bk_query.with_for_update()
            bk_res = await db.execute(bk_query)
            booking = bk_res.scalar_one_or_none()

            if not booking:
                continue

            # Idempotency / Concurrency Guard: Re-verify status under lock
            if booking.payment_status != PaymentStatus.PENDING.value:
                skipped_ids.append(b_id)
                continue

            # Step B: Row-level lock on all Payments (Lock Order Position 2)
            pay_query = select(Payment).where(Payment.booking_id == booking.id)
            if is_postgres:
                pay_query = pay_query.with_for_update()
            pay_res = await db.execute(pay_query)
            payments = pay_res.scalars().all()

            # Safety Rule 1: Never cancel if ANY payment succeeded
            has_success_payment = any(p.status == TransactionStatus.SUCCESS.value for p in payments)
            if has_success_payment:
                logger.info(f"[expire_pending_bookings] Booking {b_id} has a SUCCESS payment. Skipping cancellation.")
                skipped_ids.append(b_id)
                continue

            # Safety Rule 2: Never cancel if ANY payment requires reconciliation
            has_doubt_payment = any(p.status == TransactionStatus.REQUIRES_RECONCILIATION.value for p in payments)
            if has_doubt_payment:
                logger.warning(f"[expire_pending_bookings] Booking {b_id} has a payment requiring reconciliation. Skipping cancellation.")
                skipped_ids.append(b_id)
                continue

            # Mark all pending payment attempts as EXPIRED
            for p in payments:
                if p.status == TransactionStatus.PENDING.value:
                    p.status = TransactionStatus.EXPIRED.value
                    p.updated_at = datetime.utcnow()

            # Transition Booking to CANCELLED
            booking.payment_status = PaymentStatus.CANCELLED.value

            # Step C: Slot Availability Re-check (Lock Order Position 3)
            # Check if any OTHER active booking exists for this slot
            conflict_stmt = select(Booking.id).where(
                and_(
                    Booking.slot_id == booking.slot_id,
                    Booking.id != booking.id,
                    Booking.payment_status.in_([
                        PaymentStatus.PENDING.value,
                        PaymentStatus.DEPOSITED.value,
                        PaymentStatus.PAID.value
                    ])
                )
            )
            conflict_res = await db.execute(conflict_stmt)
            other_active_booking = conflict_res.scalars().first()

            if not other_active_booking:
                slot_query = select(TimeSlot).where(TimeSlot.id == booking.slot_id)
                if is_postgres:
                    slot_query = slot_query.with_for_update()
                slot_res = await db.execute(slot_query)
                slot = slot_res.scalar_one_or_none()

                if slot and slot.status == SlotStatus.BOOKED.value:
                    slot.status = SlotStatus.AVAILABLE.value

            # Safe Redis Slot Lock Release (Verifying ownership — never releases another user's lock)
            try:
                holder = await get_slot_lock_holder(booking.slot_id)
                if holder is not None and str(holder) == str(booking.user_id):
                    await release_slot_lock(slot_id=booking.slot_id, user_id=booking.user_id)
            except Exception as r_err:
                logger.warning(f"[expire_pending_bookings] Redis lock release check warning: {r_err}")

            await db.commit()
            processed_ids.append(b_id)
            logger.info(f"[expire_pending_bookings] Booking {b_id} successfully cancelled due to payment timeout.")

        except Exception as exc:
            await db.rollback()
            logger.error(f"[expire_pending_bookings] Error processing expiry for booking {b_id}: {exc}", exc_info=True)
            skipped_ids.append(b_id)

    return {
        "status": "success",
        "message": f"Hoàn tất quét hết hạn: {len(processed_ids)} đơn đã hủy, {len(skipped_ids)} đơn bỏ qua.",
        "expired_count": len(processed_ids),
        "processed_booking_ids": processed_ids,
        "skipped_booking_ids": skipped_ids,
        "batch_limit": effective_batch
    }
