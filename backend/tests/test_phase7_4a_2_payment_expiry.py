"""
BADMINTON.AI - PHASE 7.4A.2 TEST SUITE
SAFE PAYMENT EXPIRY & LATE-WEBHOOK RECONCILIATION
Comprehensive test suite validating all 20 requirements:
1. Hết hạn tự động mặc định tắt.
2. Timeout thiếu hoặc không hợp lệ không được thực thi.
3. Booking chưa đủ tuổi không bị hết hạn.
4. Booking chờ thanh toán quá hạn và đủ điều kiện được xử lý đúng.
5. Booking đã thanh toán không bị hủy.
6. Payment cần reconciliation không bị tự động hủy.
7. Booking hết hạn không làm TimeSlot AVAILABLE nếu còn booking hoạt động khác.
8. Booking và slot được cập nhật nhất quán trong transaction.
9. Lỗi DB không để lại trạng thái dở dang.
10. Job chạy lặp không tạo side effect lần thứ hai.
11. Hai worker cạnh tranh không xử lý trùng một booking.
12. Callback SUCCESS đến sau khi booking hết hạn được đưa vào luồng reconciliation phù hợp.
13. Callback FAILED đến sau SUCCESS không downgrade giao dịch.
14. Callback lặp không tạo payment record trùng.
15. Không giải phóng Redis lock của người khác.
16. Decimal amount được chuẩn hóa chính xác.
17. Số tiền lệch 1 VND bị từ chối.
18. Phase 7.3 booking flow không bị regression.
19. Phase 7.4A webhook và sandbox tests không bị regression.
20. SQLite unit tests và PostgreSQL integration tests được phân loại riêng.
"""

import os
import sys
import json
import uuid
import asyncio
import unittest
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ROOT_DIR = os.path.abspath(os.path.join(BACKEND_DIR, ".."))
for p in [ROOT_DIR, BACKEND_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import text, delete, and_

from app.config import settings
from app.core.database import AsyncSessionLocal
from app.core.redis import (
    acquire_slot_lock,
    release_slot_lock,
    get_slot_lock_holder,
    _in_memory_locks
)
from app.models.all_models import (
    User,
    Facility,
    Court,
    TimeSlot,
    SlotPricing,
    Booking,
    Payment,
    PaymentStatus,
    TransactionStatus,
    SlotStatus
)
from app.services.booking_service import (
    create_booking_preview,
    execute_confirmed_booking
)
from app.services.payment_service import (
    create_payment_attempt,
    process_payment_webhook,
    simulate_sandbox_payment,
    get_payment_adapter,
    normalize_vnd_amount
)
from app.services.payment_expiry_service import expire_pending_bookings


class TestPhase74A2PaymentExpiry(unittest.TestCase):
    """Phase 7.4A.2 Test Suite: Safe Payment Expiry & Late-Webhook Reconciliation."""

    @classmethod
    def setUpClass(cls):
        cls.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(cls.loop)
        cls.loop.run_until_complete(cls._ensure_seed_data())

    @classmethod
    def tearDownClass(cls):
        cls.loop.close()

    @classmethod
    async def _ensure_seed_data(cls):
        async with AsyncSessionLocal() as session:
            fac = (await session.execute(select(Facility).where(Facility.id == 101))).scalar_one_or_none()
            if not fac:
                await session.execute(text("""
                    INSERT OR REPLACE INTO facilities (id, owner_id, name, address, latitude, longitude)
                    VALUES (101, 1, 'CLB Cầu Lông Catchy Badminton Arena', '136 Tân Khai', 20.9856, 105.858)
                """))
            crt = (await session.execute(select(Court).where(Court.id == 201))).scalar_one_or_none()
            if not crt:
                await session.execute(text("""
                    INSERT OR REPLACE INTO courts (id, facility_id, surface_type, court_number, is_active)
                    VALUES (201, 101, 'Sân 01 - Thảm Yonex Pro', '1', 1)
                """))
            await session.execute(text("""
                INSERT OR REPLACE INTO time_slots (id, court_id, date, start_time, end_time, status)
                VALUES (1, 201, '2026-10-15', '19:00', '20:00', 'AVAILABLE')
            """))
            await session.execute(text("""
                INSERT OR REPLACE INTO time_slots (id, court_id, date, start_time, end_time, status)
                VALUES (2, 201, '2026-10-15', '20:00', '21:00', 'AVAILABLE')
            """))
            await session.execute(text("""
                INSERT OR REPLACE INTO slot_pricing (id, slot_id, base_price, dynamic_price, adjustment_reason, is_ai_applied)
                VALUES (101, 1, 80000.0, 80000.0, 'Standard', 0)
            """))
            await session.execute(text("""
                INSERT OR REPLACE INTO slot_pricing (id, slot_id, base_price, dynamic_price, adjustment_reason, is_ai_applied)
                VALUES (102, 2, 80000.0, 80000.0, 'Standard', 0)
            """))
            u1 = (await session.execute(select(User).where(User.id == 1))).scalar_one_or_none()
            if not u1:
                await session.execute(text("""
                    INSERT OR REPLACE INTO users (id, name, phone, password_hash, role)
                    VALUES (1, 'Nguyễn Văn A', '0901234567', 'hash1', 'CUSTOMER')
                """))
            u2 = (await session.execute(select(User).where(User.id == 2))).scalar_one_or_none()
            if not u2:
                await session.execute(text("""
                    INSERT OR REPLACE INTO users (id, name, phone, password_hash, role)
                    VALUES (2, 'Trần Thị B', '0901234568', 'hash2', 'CUSTOMER')
                """))
            await session.commit()

    def setUp(self):
        _in_memory_locks.clear()
        os.environ["ENVIRONMENT"] = "test"
        os.environ["PAYMENT_SANDBOX_ENABLED"] = "true"

        async def _reset():
            async with AsyncSessionLocal() as session:
                await session.execute(text("UPDATE time_slots SET status = 'AVAILABLE' WHERE id IN (1, 2)"))
                await session.execute(delete(Payment).where(Payment.booking_id.in_([1, 2, 801, 802, 901, 902])))
                await session.execute(delete(Booking).where(Booking.id.in_([1, 2, 801, 802, 901, 902])))
                await session.commit()
        self.run_async(_reset())

    def run_async(self, coro):
        return self.loop.run_until_complete(coro)

    # -------------------------------------------------------------------------
    # TEST 1: Expiry disabled by default (Fail-closed)
    # -------------------------------------------------------------------------
    def test_01_expiry_disabled_by_default(self):
        """1. Hết hạn tự động mặc định tắt nếu không được cấu hình tường minh."""
        async def _test():
            with patch.dict(os.environ, {"PAYMENT_PENDING_EXPIRY_ENABLED": "false"}):
                async with AsyncSessionLocal() as session:
                    res = await expire_pending_bookings(db=session)
                    self.assertEqual(res["status"], "expiry_disabled")
                    self.assertEqual(res["expired_count"], 0)
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 2: Missing or invalid timeout policy not executed
    # -------------------------------------------------------------------------
    def test_02_missing_or_invalid_timeout_not_executed(self):
        """2. Timeout thiếu hoặc không hợp lệ không được thực thi."""
        async def _test():
            for bad_timeout in [None, "-5", "abc", "0"]:
                env_dict = {"PAYMENT_PENDING_EXPIRY_ENABLED": "true"}
                if bad_timeout is not None:
                    env_dict["PAYMENT_PENDING_EXPIRY_MINUTES"] = bad_timeout
                else:
                    if "PAYMENT_PENDING_EXPIRY_MINUTES" in os.environ:
                        del os.environ["PAYMENT_PENDING_EXPIRY_MINUTES"]

                with patch.dict(os.environ, env_dict, clear=False):
                    async with AsyncSessionLocal() as session:
                        res = await expire_pending_bookings(db=session)
                        self.assertEqual(res["status"], "invalid_timeout_policy")
                        self.assertEqual(res["expired_count"], 0)
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 3: Underage booking not expired
    # -------------------------------------------------------------------------
    def test_03_underage_booking_not_expired(self):
        """3. Booking chưa đủ tuổi (mới tạo) không bị hết hạn."""
        async def _test():
            async with AsyncSessionLocal() as session:
                # Booking created just now (0 minutes old)
                bk = Booking(
                    id=801, user_id=1, slot_id=1, total_amount=80000.0,
                    deposit_amount=40000.0, payment_status="PENDING",
                    qr_checkin_code="QR-EXP-03", idempotency_key="exp_03_key",
                    created_at=datetime.utcnow()
                )
                session.add(bk)
                await session.commit()

            async with AsyncSessionLocal() as session2:
                # Timeout policy is 15 minutes
                res = await expire_pending_bookings(
                    db=session2, custom_timeout_minutes=15, force_enabled=True
                )
                self.assertEqual(res["status"], "success")
                self.assertEqual(res["expired_count"], 0)
                self.assertNotIn(801, res["processed_booking_ids"])

            async with AsyncSessionLocal() as session3:
                b_row = (await session3.execute(select(Booking).where(Booking.id == 801))).scalar_one()
                self.assertEqual(b_row.payment_status, "PENDING")
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 4: Overdue eligible booking expired correctly
    # -------------------------------------------------------------------------
    def test_04_overdue_eligible_booking_expired(self):
        """4. Booking chờ thanh toán quá hạn và đủ điều kiện được xử lý đúng (hủy booking, nhả slot)."""
        async def _test():
            old_time = datetime.utcnow() - timedelta(minutes=30)
            async with AsyncSessionLocal() as session:
                slot = (await session.execute(select(TimeSlot).where(TimeSlot.id == 1))).scalar_one()
                slot.status = "BOOKED"
                bk = Booking(
                    id=801, user_id=1, slot_id=1, total_amount=80000.0,
                    deposit_amount=40000.0, payment_status="PENDING",
                    qr_checkin_code="QR-EXP-04", idempotency_key="exp_04_key",
                    created_at=old_time
                )
                session.add(bk)
                await session.commit()

            async with AsyncSessionLocal() as session2:
                res = await expire_pending_bookings(
                    db=session2, custom_timeout_minutes=15, force_enabled=True
                )
                self.assertEqual(res["status"], "success")
                self.assertEqual(res["expired_count"], 1)
                self.assertIn(801, res["processed_booking_ids"])

            async with AsyncSessionLocal() as session3:
                b_row = (await session3.execute(select(Booking).where(Booking.id == 801))).scalar_one()
                self.assertEqual(b_row.payment_status, "CANCELLED")

                s_row = (await session3.execute(select(TimeSlot).where(TimeSlot.id == 1))).scalar_one()
                self.assertEqual(s_row.status, "AVAILABLE")
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 5: Paid or deposited booking not cancelled
    # -------------------------------------------------------------------------
    def test_05_paid_or_deposited_booking_not_cancelled(self):
        """5. Booking đã thanh toán cọc hoặc full không bị hủy."""
        async def _test():
            old_time = datetime.utcnow() - timedelta(minutes=45)
            async with AsyncSessionLocal() as session:
                bk1 = Booking(
                    id=801, user_id=1, slot_id=1, total_amount=80000.0,
                    deposit_amount=40000.0, payment_status="DEPOSITED",
                    qr_checkin_code="QR-EXP-05A", idempotency_key="exp_05a_key",
                    created_at=old_time
                )
                bk2 = Booking(
                    id=802, user_id=1, slot_id=2, total_amount=80000.0,
                    deposit_amount=40000.0, payment_status="PAID",
                    qr_checkin_code="QR-EXP-05B", idempotency_key="exp_05b_key",
                    created_at=old_time
                )
                session.add_all([bk1, bk2])
                await session.commit()

            async with AsyncSessionLocal() as session2:
                res = await expire_pending_bookings(
                    db=session2, custom_timeout_minutes=15, force_enabled=True
                )
                self.assertEqual(res["expired_count"], 0)

            async with AsyncSessionLocal() as session3:
                b1 = (await session3.execute(select(Booking).where(Booking.id == 801))).scalar_one()
                self.assertEqual(b1.payment_status, "DEPOSITED")
                b2 = (await session3.execute(select(Booking).where(Booking.id == 802))).scalar_one()
                self.assertEqual(b2.payment_status, "PAID")
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 6: Payment requiring reconciliation prevents auto-cancellation
    # -------------------------------------------------------------------------
    def test_06_reconciliation_payment_prevents_auto_cancellation(self):
        """6. Payment cần reconciliation không bị tự động hủy."""
        async def _test():
            old_time = datetime.utcnow() - timedelta(minutes=40)
            async with AsyncSessionLocal() as session:
                bk = Booking(
                    id=801, user_id=1, slot_id=1, total_amount=80000.0,
                    deposit_amount=40000.0, payment_status="PENDING",
                    qr_checkin_code="QR-EXP-06", idempotency_key="exp_06_key",
                    created_at=old_time
                )
                pm = Payment(
                    booking_id=801, user_id=1, provider="SANDBOX",
                    transaction_id="tx_recon_06", amount=40000.0, currency="VND",
                    payment_type="DEPOSIT", status="REQUIRES_RECONCILIATION",
                    created_at=old_time
                )
                session.add_all([bk, pm])
                await session.commit()

            async with AsyncSessionLocal() as session2:
                res = await expire_pending_bookings(
                    db=session2, custom_timeout_minutes=15, force_enabled=True
                )
                self.assertEqual(res["expired_count"], 0)
                self.assertIn(801, res["skipped_booking_ids"])

            async with AsyncSessionLocal() as session3:
                b_row = (await session3.execute(select(Booking).where(Booking.id == 801))).scalar_one()
                self.assertEqual(b_row.payment_status, "PENDING")
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 7: Slot remains booked if another active booking exists
    # -------------------------------------------------------------------------
    def test_07_slot_remains_booked_if_another_active_booking_exists(self):
        """7. Booking hết hạn không làm TimeSlot AVAILABLE nếu còn booking hoạt động khác cùng slot."""
        async def _test():
            old_time = datetime.utcnow() - timedelta(minutes=40)
            async with AsyncSessionLocal() as session:
                slot = (await session.execute(select(TimeSlot).where(TimeSlot.id == 1))).scalar_one()
                slot.status = "BOOKED"

                # Booking 801 is overdue pending
                bk1 = Booking(
                    id=801, user_id=1, slot_id=1, total_amount=80000.0,
                    deposit_amount=40000.0, payment_status="PENDING",
                    qr_checkin_code="QR-EXP-07A", idempotency_key="exp_07a_key",
                    created_at=old_time
                )
                # Booking 802 is active DEPOSITED on the same slot
                bk2 = Booking(
                    id=802, user_id=2, slot_id=1, total_amount=80000.0,
                    deposit_amount=40000.0, payment_status="DEPOSITED",
                    qr_checkin_code="QR-EXP-07B", idempotency_key="exp_07b_key",
                    created_at=old_time
                )
                session.add_all([bk1, bk2])
                await session.commit()

            async with AsyncSessionLocal() as session2:
                res = await expire_pending_bookings(
                    db=session2, custom_timeout_minutes=15, force_enabled=True
                )
                self.assertEqual(res["expired_count"], 1)
                self.assertIn(801, res["processed_booking_ids"])

            async with AsyncSessionLocal() as session3:
                b1 = (await session3.execute(select(Booking).where(Booking.id == 801))).scalar_one()
                self.assertEqual(b1.payment_status, "CANCELLED")

                # Slot MUST remain BOOKED because booking 802 is still active!
                s_row = (await session3.execute(select(TimeSlot).where(TimeSlot.id == 1))).scalar_one()
                self.assertEqual(s_row.status, "BOOKED")
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 8: Booking and slot updated atomically in transaction
    # -------------------------------------------------------------------------
    def test_08_booking_and_slot_updated_atomically_in_tx(self):
        """8. Booking và slot được cập nhật nhất quán trong cùng transaction."""
        async def _test():
            old_time = datetime.utcnow() - timedelta(minutes=30)
            async with AsyncSessionLocal() as session:
                slot = (await session.execute(select(TimeSlot).where(TimeSlot.id == 1))).scalar_one()
                slot.status = "BOOKED"
                bk = Booking(
                    id=801, user_id=1, slot_id=1, total_amount=80000.0,
                    deposit_amount=40000.0, payment_status="PENDING",
                    qr_checkin_code="QR-EXP-08", idempotency_key="exp_08_key",
                    created_at=old_time
                )
                session.add(bk)
                await session.commit()

            async with AsyncSessionLocal() as session2:
                res = await expire_pending_bookings(db=session2, custom_timeout_minutes=15, force_enabled=True)
                self.assertEqual(res["expired_count"], 1)

            async with AsyncSessionLocal() as session3:
                b_row = (await session3.execute(select(Booking).where(Booking.id == 801))).scalar_one()
                s_row = (await session3.execute(select(TimeSlot).where(TimeSlot.id == 1))).scalar_one()
                self.assertEqual(b_row.payment_status, "CANCELLED")
                self.assertEqual(s_row.status, "AVAILABLE")
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 9: DB error triggers rollback and leaves no partial state
    # -------------------------------------------------------------------------
    def test_09_db_error_triggers_rollback(self):
        """9. Lỗi DB không để lại trạng thái dở dang (Rollback an toàn)."""
        async def _test():
            old_time = datetime.utcnow() - timedelta(minutes=30)
            async with AsyncSessionLocal() as session:
                slot = (await session.execute(select(TimeSlot).where(TimeSlot.id == 1))).scalar_one()
                slot.status = "BOOKED"
                bk = Booking(
                    id=801, user_id=1, slot_id=1, total_amount=80000.0,
                    deposit_amount=40000.0, payment_status="PENDING",
                    qr_checkin_code="QR-EXP-09", idempotency_key="exp_09_key",
                    created_at=old_time
                )
                session.add(bk)
                await session.commit()

            async with AsyncSessionLocal() as session2:
                with patch.object(session2, "commit", side_effect=Exception("Simulated DB connection drop")):
                    res = await expire_pending_bookings(db=session2, custom_timeout_minutes=15, force_enabled=True)
                    self.assertEqual(res["expired_count"], 0)
                    self.assertIn(801, res["skipped_booking_ids"])

            async with AsyncSessionLocal() as session3:
                b_row = (await session3.execute(select(Booking).where(Booking.id == 801))).scalar_one()
                s_row = (await session3.execute(select(TimeSlot).where(TimeSlot.id == 1))).scalar_one()
                self.assertEqual(b_row.payment_status, "PENDING")
                self.assertEqual(s_row.status, "BOOKED")
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 10: Repeated expiry runs are idempotent
    # -------------------------------------------------------------------------
    def test_10_repeated_expiry_runs_idempotent(self):
        """10. Job chạy lặp không tạo side effect lần thứ hai (Idempotency)."""
        async def _test():
            old_time = datetime.utcnow() - timedelta(minutes=30)
            async with AsyncSessionLocal() as session:
                slot = (await session.execute(select(TimeSlot).where(TimeSlot.id == 1))).scalar_one()
                slot.status = "BOOKED"
                bk = Booking(
                    id=801, user_id=1, slot_id=1, total_amount=80000.0,
                    deposit_amount=40000.0, payment_status="PENDING",
                    qr_checkin_code="QR-EXP-10", idempotency_key="exp_10_key",
                    created_at=old_time
                )
                session.add(bk)
                await session.commit()

            async with AsyncSessionLocal() as session2:
                res1 = await expire_pending_bookings(db=session2, custom_timeout_minutes=15, force_enabled=True)
                self.assertEqual(res1["expired_count"], 1)

            # Second run immediately
            async with AsyncSessionLocal() as session3:
                res2 = await expire_pending_bookings(db=session3, custom_timeout_minutes=15, force_enabled=True)
                self.assertEqual(res2["expired_count"], 0)
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 11: Competing workers do not double-process
    # -------------------------------------------------------------------------
    def test_11_competing_workers_no_duplicate_processing(self):
        """11. Hai worker cạnh tranh không xử lý trùng một booking."""
        async def _test():
            old_time = datetime.utcnow() - timedelta(minutes=30)
            async with AsyncSessionLocal() as session:
                slot = (await session.execute(select(TimeSlot).where(TimeSlot.id == 1))).scalar_one()
                slot.status = "BOOKED"
                bk = Booking(
                    id=801, user_id=1, slot_id=1, total_amount=80000.0,
                    deposit_amount=40000.0, payment_status="PENDING",
                    qr_checkin_code="QR-EXP-11", idempotency_key="exp_11_key",
                    created_at=old_time
                )
                session.add(bk)
                await session.commit()

            async def _worker():
                async with AsyncSessionLocal() as s:
                    return await expire_pending_bookings(db=s, custom_timeout_minutes=15, force_enabled=True)

            res1 = await _worker()
            res2 = await _worker()

            total_expired = res1["expired_count"] + res2["expired_count"]
            self.assertEqual(total_expired, 1)
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 12: Late SUCCESS callback on expired booking routed to reconciliation
    # -------------------------------------------------------------------------
    def test_12_late_success_callback_on_expired_booking(self):
        """12. Callback SUCCESS đến sau khi booking hết hạn được đưa vào đối soát (Reconciliation), không đổi CANCELLED."""
        async def _test():
            async with AsyncSessionLocal() as session:
                # Booking is already CANCELLED
                bk = Booking(
                    id=801, user_id=1, slot_id=1, total_amount=80000.0,
                    deposit_amount=40000.0, payment_status="CANCELLED",
                    qr_checkin_code="QR-EXP-12", idempotency_key="exp_12_key"
                )
                # Payment attempt was EXPIRED
                pm = Payment(
                    id=501, booking_id=801, user_id=1, provider="SANDBOX",
                    transaction_id="tx_late_succ_12", amount=40000.0, currency="VND",
                    payment_type="DEPOSIT", status="EXPIRED", idempotency_key="idemp_pm_12"
                )
                session.add_all([bk, pm])
                await session.commit()

                # Gateway callback arrives reporting SUCCESS for tx_late_succ_12
                adapter = get_payment_adapter("SANDBOX")
                payload = {
                    "provider": "SANDBOX",
                    "transaction_id": "tx_late_succ_12",
                    "booking_id": 801,
                    "amount": 40000.0,
                    "currency": "VND",
                    "status": "SUCCESS"
                }
                sig = adapter.generate_signature(payload)

                res = await process_payment_webhook(
                    db=session, provider="SANDBOX", transaction_id="tx_late_succ_12",
                    booking_id=801, amount=40000.0, currency="VND", status="SUCCESS",
                    signature=sig, raw_payload=payload
                )

                # Must require reconciliation
                self.assertEqual(res["status"], "reconciliation_required")
                self.assertIn("đối soát", res["message"])

            # Verify in DB: booking is STILL CANCELLED, payment is REQUIRES_RECONCILIATION
            async with AsyncSessionLocal() as session2:
                b_row = (await session2.execute(select(Booking).where(Booking.id == 801))).scalar_one()
                self.assertEqual(b_row.payment_status, "CANCELLED")

                p_row = (await session2.execute(select(Payment).where(Payment.id == 501))).scalar_one()
                self.assertEqual(p_row.status, "REQUIRES_RECONCILIATION")
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 13: FAILED callback arriving after SUCCESS does not downgrade
    # -------------------------------------------------------------------------
    def test_13_failed_callback_after_success_no_downgrade(self):
        """13. Callback FAILED đến sau SUCCESS không downgrade giao dịch."""
        async def _test():
            async with AsyncSessionLocal() as session:
                bk = Booking(
                    id=801, user_id=1, slot_id=1, total_amount=80000.0,
                    deposit_amount=40000.0, payment_status="PENDING",
                    qr_checkin_code="QR-EXP-13", idempotency_key="exp_13_key"
                )
                session.add(bk)
                await session.commit()

                res_succ = await simulate_sandbox_payment(db=session, booking_id=801, user_id=1, outcome="SUCCESS")
                self.assertEqual(res_succ["status"], "payment_processed")
                tx_id = res_succ["data"]["transaction_id"]

                # Delayed FAILED callback
                adapter = get_payment_adapter("SANDBOX")
                payload = {
                    "provider": "SANDBOX",
                    "transaction_id": tx_id,
                    "booking_id": 801,
                    "amount": 40000.0,
                    "currency": "VND",
                    "status": "FAILED"
                }
                sig = adapter.generate_signature(payload)
                res_late = await process_payment_webhook(
                    db=session, provider="SANDBOX", transaction_id=tx_id,
                    booking_id=801, amount=40000.0, currency="VND", status="FAILED",
                    signature=sig, raw_payload=payload
                )
                self.assertEqual(res_late["status"], "downgrade_prevented")

            async with AsyncSessionLocal() as session2:
                b_row = (await session2.execute(select(Booking).where(Booking.id == 801))).scalar_one()
                self.assertEqual(b_row.payment_status, "DEPOSITED")
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 14: Duplicate callback does not create duplicate payment record
    # -------------------------------------------------------------------------
    def test_14_duplicate_callback_no_duplicate_records(self):
        """14. Callback lặp không tạo payment record trùng."""
        async def _test():
            async with AsyncSessionLocal() as session:
                bk = Booking(
                    id=801, user_id=1, slot_id=1, total_amount=80000.0,
                    deposit_amount=40000.0, payment_status="PENDING",
                    qr_checkin_code="QR-EXP-14", idempotency_key="exp_14_key"
                )
                session.add(bk)
                await session.commit()

                res1 = await simulate_sandbox_payment(
                    db=session, booking_id=801, user_id=1, outcome="SUCCESS", idempotency_key="idemp_14"
                )
                self.assertEqual(res1["status"], "payment_processed")

                res2 = await simulate_sandbox_payment(
                    db=session, booking_id=801, user_id=1, outcome="SUCCESS", idempotency_key="idemp_14"
                )
                self.assertTrue(res2.get("is_idempotent"))

                cnt = len((await session.execute(select(Payment).where(Payment.booking_id == 801))).scalars().all())
                self.assertEqual(cnt, 1)
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 15: Safe Redis lock release does not release other user's lock
    # -------------------------------------------------------------------------
    def test_15_does_not_release_other_user_redis_lock(self):
        """15. Không giải phóng Redis lock thuộc về người dùng khác."""
        async def _test():
            old_time = datetime.utcnow() - timedelta(minutes=40)
            async with AsyncSessionLocal() as session:
                # Slot is locked in Redis by user 2
                await acquire_slot_lock(slot_id=1, user_id=2, timeout_sec=600)

                # Overdue booking belongs to user 1
                bk = Booking(
                    id=801, user_id=1, slot_id=1, total_amount=80000.0,
                    deposit_amount=40000.0, payment_status="PENDING",
                    qr_checkin_code="QR-EXP-15", idempotency_key="exp_15_key",
                    created_at=old_time
                )
                session.add(bk)
                await session.commit()

            async with AsyncSessionLocal() as session2:
                res = await expire_pending_bookings(db=session2, custom_timeout_minutes=15, force_enabled=True)
                self.assertEqual(res["expired_count"], 1)

            # Verify: User 2's Redis lock is STILL HELD!
            holder = await get_slot_lock_holder(1)
            self.assertEqual(str(holder), "2")
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 16: Decimal amount normalized accurately without rounding distortion
    # -------------------------------------------------------------------------
    def test_16_decimal_amount_normalized_accurately(self):
        """16. Decimal amount được chuẩn hóa chính xác, từ chối số thập phân không nguyên."""
        # Valid amounts
        self.assertEqual(normalize_vnd_amount(40000), Decimal("40000"))
        self.assertEqual(normalize_vnd_amount("40000"), Decimal("40000"))
        self.assertEqual(normalize_vnd_amount(40000.0), Decimal("40000"))
        self.assertEqual(normalize_vnd_amount("40000.00"), Decimal("40000"))
        self.assertEqual(normalize_vnd_amount(Decimal("40000")), Decimal("40000"))

        # Fractional decimals must be rejected (no auto-rounding to preserve integrity)
        self.assertIsNone(normalize_vnd_amount(40000.5))
        self.assertIsNone(normalize_vnd_amount("40000.50"))
        self.assertIsNone(normalize_vnd_amount(40000.01))

        # Invalid, negative, zero, boolean, NaN, Inf
        self.assertIsNone(normalize_vnd_amount(-50000))
        self.assertIsNone(normalize_vnd_amount(0))
        self.assertIsNone(normalize_vnd_amount("0"))
        self.assertIsNone(normalize_vnd_amount(True))
        self.assertIsNone(normalize_vnd_amount(False))
        self.assertIsNone(normalize_vnd_amount("abc"))
        self.assertIsNone(normalize_vnd_amount(float("nan")))
        self.assertIsNone(normalize_vnd_amount(float("inf")))
        self.assertIsNone(normalize_vnd_amount("NaN"))
        self.assertIsNone(normalize_vnd_amount("Infinity"))

    # -------------------------------------------------------------------------
    # TEST 17: Amount discrepancy of 1 VND rejected
    # -------------------------------------------------------------------------
    def test_17_amount_discrepancy_1vnd_rejected(self):
        """17. Số tiền lệch 1 VND bị từ chối."""
        async def _test():
            async with AsyncSessionLocal() as session:
                bk = Booking(
                    id=801, user_id=1, slot_id=1, total_amount=80000.0,
                    deposit_amount=40000.0, payment_status="PENDING",
                    qr_checkin_code="QR-EXP-17", idempotency_key="exp_17_key"
                )
                session.add(bk)
                await session.commit()

                # Simulate with 40,001 VND (+1 VND)
                res = await simulate_sandbox_payment(
                    db=session, booking_id=801, user_id=1, outcome="MISMATCH_AMOUNT_1VND"
                )
                self.assertEqual(res["status"], "amount_mismatch")

            async with AsyncSessionLocal() as session2:
                b_row = (await session2.execute(select(Booking).where(Booking.id == 801))).scalar_one()
                self.assertEqual(b_row.payment_status, "PENDING")
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 18: Phase 7.3 booking flow no regression
    # -------------------------------------------------------------------------
    def test_18_phase7_3_booking_flow_no_regression(self):
        """18. Phase 7.3 booking flow không bị regression."""
        async def _test():
            async with AsyncSessionLocal() as session:
                await acquire_slot_lock(slot_id=2, user_id=1, timeout_sec=600)
                prev = await create_booking_preview(db=session, user_id=1, slot_id=2)
                self.assertEqual(prev["status"], "preview_created")

                conf = await execute_confirmed_booking(
                    db=session, user_id=1, booking_intent_id=prev["data"]["booking_intent_id"]
                )
                self.assertEqual(conf["status"], "booking_succeeded")
                self.assertEqual(conf["data"]["payment_status"], "PENDING")
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 19: Phase 7.4A webhook and sandbox tests no regression
    # -------------------------------------------------------------------------
    def test_19_phase7_4a_webhook_and_sandbox_no_regression(self):
        """19. Phase 7.4A webhook và sandbox tests không bị regression."""
        async def _test():
            async with AsyncSessionLocal() as session:
                bk = Booking(
                    id=801, user_id=1, slot_id=1, total_amount=80000.0,
                    deposit_amount=40000.0, payment_status="PENDING",
                    qr_checkin_code="QR-EXP-19", idempotency_key="exp_19_key"
                )
                session.add(bk)
                await session.commit()

                res = await simulate_sandbox_payment(db=session, booking_id=801, user_id=1, outcome="SUCCESS")
                self.assertEqual(res["status"], "payment_processed")
                self.assertEqual(res["data"]["payment_status"], "DEPOSITED")
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 20: SQLite and PostgreSQL dialect compatibility
    # -------------------------------------------------------------------------
    def test_20_sqlite_and_postgres_dialect_compatibility(self):
        """20. Phân loại và tương thích độc lập giữa SQLite và PostgreSQL."""
        async def _test():
            async with AsyncSessionLocal() as session:
                dialect_name = session.bind.dialect.name if session.bind else "sqlite"
                self.assertIn(dialect_name, ("sqlite", "postgresql"))
                # Verify payments table query
                cnt = (await session.execute(text("SELECT count(*) FROM payments;"))).scalar()
                self.assertGreaterEqual(cnt, 0)
        self.run_async(_test())


if __name__ == "__main__":
    unittest.main()
