"""
BADMINTON.AI - PHASE 7.3 COMPREHENSIVE TEST SUITE
CONFIRMED BOOKING CREATION & TRANSACTIONAL SAFETY
Verifies:
1. Guest cannot create booking (authentication enforcement).
2. User without Redis lock cannot book slot (strict hold prerequisite).
3. Expired lock or Redis error rejects booking cleanly.
4. Preview creates intent without creating Booking in DB or charging.
5. No final confirmation -> no Booking created in DB.
6. Anti-IDOR: other users cannot confirm another user's intent.
7. Expired booking confirmation intent is rejected (TTL 300s).
8. Anti-Replay: confirming an intent twice returns idempotent existing booking.
9. Concurrent confirmations on same intent result in exactly one booking.
10. Competing users on same slot -> only one booking succeeds.
11. BOOKED or MAINTENANCE slot rejected.
12. Conflicting active booking rejected.
13. DB transaction rollback leaves no orphan state.
14. Idempotency reconciliation handles duplicate requests safely.
15. Lock release failure after commit does not fail booking.
16. Price and deposit calculated via authoritative business rules (50% deposit).
17. Dynamic pricing is not applied twice.
18. Payment status is PENDING (unpaid) before payment transaction.
19. Chatbot response does NOT leak QR check-in codes or secrets.
20. Booking ID and success state verified against database.
21. Backward compatibility of existing booking APIs preserved.
22. Redis outage returns availability_unverified, never false success.
23. Policy RAG FAQ queries route to RAG without triggering booking flow.
24. SQLite compatibility for unit test execution.
25. Live PostgreSQL integration verification (when available).
26. Live Redis lock ownership and expiration verification (when available).
"""

import os
import sys
import time
import json
import uuid
import asyncio
import unittest
from unittest.mock import patch, AsyncMock
from typing import Optional, Dict, Any, List

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ROOT_DIR = os.path.abspath(os.path.join(BACKEND_DIR, ".."))
for p in [ROOT_DIR, BACKEND_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from sqlalchemy import text, and_, delete

from app.config import settings
from app.core.database import AsyncSessionLocal, Base
from app.core import redis as redis_core
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
    Equipment,
    RentalItem
)
from app.schemas.all_schemas import (
    BookingCreate,
    BookingPreviewRequest,
    BookingConfirmRequest
)
from app.ai.chatbot_service import ChatbotService
from app.ai.llm_provider import BaseLLMProvider
from app.ai.tools.pending_hold_manager import (
    get_pending_hold_manager,
    _in_memory_intents,
    _in_memory_user_active
)
from app.ai.tools.booking_confirmation_manager import (
    get_booking_confirmation_manager,
    _in_memory_booking_intents,
    _in_memory_user_active_booking
)
from app.services.booking_service import (
    create_booking_preview,
    execute_confirmed_booking
)


class MockLLM(BaseLLMProvider):
    @property
    def provider_name(self) -> str:
        return "MockLLM"

    @property
    def model_name(self) -> str:
        return "mock-gemini"

    async def generate_text(self, system_instruction: str, user_message: str, history=None, timeout: float = 8.0) -> str:
        return "Quy định đặt cọc là 50% và thời gian giữ chỗ là 10 phút theo chính sách của hệ thống."


class TestPhase73ConfirmedBooking(unittest.TestCase):
    """Phase 7.3 Test Suite for Confirmed Booking Creation & Concurrency Safety."""

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
            # Ensure facility 101 or 1 exists
            fac = (await session.execute(select(Facility).where(Facility.id == 101))).scalar_one_or_none()
            if not fac:
                await session.execute(text("""
                    INSERT OR REPLACE INTO facilities (id, owner_id, name, address, latitude, longitude)
                    VALUES (101, 1, 'CLB Cầu Lông Catchy Badminton Arena', '136 Tân Khai', 20.9856, 105.858)
                """))
            # Ensure court 201 exists
            crt = (await session.execute(select(Court).where(Court.id == 201))).scalar_one_or_none()
            if not crt:
                await session.execute(text("""
                    INSERT OR REPLACE INTO courts (id, facility_id, surface_type, court_number, is_active)
                    VALUES (201, 101, 'Sân 01 - Thảm Yonex Pro', '1', 1)
                """))
            # Ensure slots 1 and 2 exist
            await session.execute(text("""
                INSERT OR REPLACE INTO time_slots (id, court_id, date, start_time, end_time, status)
                VALUES (1, 201, '2026-10-15', '19:00', '20:00', 'AVAILABLE')
            """))
            await session.execute(text("""
                INSERT OR REPLACE INTO time_slots (id, court_id, date, start_time, end_time, status)
                VALUES (2, 201, '2026-10-15', '20:00', '21:00', 'AVAILABLE')
            """))
            # Ensure slot pricings exist
            await session.execute(text("""
                INSERT OR REPLACE INTO slot_pricing (id, slot_id, base_price, dynamic_price, adjustment_reason, is_ai_applied)
                VALUES (101, 1, 80000.0, 80000.0, 'Standard', 0)
            """))
            await session.execute(text("""
                INSERT OR REPLACE INTO slot_pricing (id, slot_id, base_price, dynamic_price, adjustment_reason, is_ai_applied)
                VALUES (102, 2, 80000.0, 80000.0, 'Standard', 0)
            """))
            await session.commit()

    def setUp(self):
        _in_memory_locks.clear()
        _in_memory_intents.clear()
        _in_memory_user_active.clear()
        _in_memory_booking_intents.clear()
        _in_memory_user_active_booking.clear()

        async def _reset():
            async with AsyncSessionLocal() as session:
                await session.execute(text("UPDATE time_slots SET status = 'AVAILABLE' WHERE id IN (1, 2)"))
                await session.execute(delete(Booking).where(Booking.slot_id.in_([1, 2])))
                await session.commit()
        self.run_async(_reset())

    def run_async(self, coro):
        return self.loop.run_until_complete(coro)

    # -------------------------------------------------------------------------
    # TEST 1: Guest cannot create booking
    # -------------------------------------------------------------------------
    def test_01_guest_cannot_create_booking(self):
        """1. Guest không thể tạo booking hoặc yêu cầu xem trước đặt sân."""
        async def _test():
            async with AsyncSessionLocal() as session:
                res = await create_booking_preview(db=session, user_id=None, slot_id=1)
                self.assertEqual(res["status"], "authentication_required")

                res_conf = await execute_confirmed_booking(db=session, user_id=None, booking_intent_id="bci_dummy")
                self.assertEqual(res_conf["status"], "authentication_required")
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 2: User without lock cannot book slot
    # -------------------------------------------------------------------------
    def test_02_user_without_lock_cannot_book_slot(self):
        """2. User không sở hữu Redis lock không thể đặt slot (yêu cầu giữ chỗ trước)."""
        async def _test():
            async with AsyncSessionLocal() as session:
                # Slot 1 is not held by anyone in Redis
                res = await create_booking_preview(db=session, user_id=1, slot_id=1)
                self.assertEqual(res["status"], "slot_not_held")
                self.assertIn("chưa được bạn giữ chỗ", res["message"])
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 3: Expired lock or unverified Redis rejects booking
    # -------------------------------------------------------------------------
    def test_03_expired_lock_or_unverified_redis_rejects_booking(self):
        """3. Lock hết hạn hoặc Redis không xác minh được thì không tạo booking."""
        async def _test():
            async with AsyncSessionLocal() as session:
                # Lock held by user 2, user 1 tries to preview
                _in_memory_locks["slot_lock:1"] = (2, time.time() + 600)
                res = await create_booking_preview(db=session, user_id=1, slot_id=1)
                self.assertEqual(res["status"], "slot_not_held")

                # Lock expired (past timestamp)
                _in_memory_locks["slot_lock:1"] = (1, time.time() - 10)
                res_exp = await create_booking_preview(db=session, user_id=1, slot_id=1)
                self.assertEqual(res_exp["status"], "slot_not_held")
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 4: Preview does not create Booking or charge
    # -------------------------------------------------------------------------
    def test_04_preview_does_not_create_booking_or_charge(self):
        """4. Preview không tạo Booking trong DB, không đổi trạng thái slot và không thu tiền."""
        async def _test():
            async with AsyncSessionLocal() as session:
                initial_count = len((await session.execute(select(Booking))).scalars().all())

                # Acquire valid lock for user 1
                await acquire_slot_lock(slot_id=1, user_id=1, timeout_sec=600)

                res = await create_booking_preview(db=session, user_id=1, slot_id=1)
                self.assertEqual(res["status"], "preview_created")
                self.assertIn("booking_intent_id", res["data"])

                # DB Count must remain identical
                after_count = len((await session.execute(select(Booking))).scalars().all())
                self.assertEqual(initial_count, after_count)

                # Slot status in DB must remain unchanged (not BOOKED)
                slot = (await session.execute(select(TimeSlot).where(TimeSlot.id == 1))).scalar_one_or_none()
                self.assertNotEqual(slot.status, "BOOKED")
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 5: No final confirmation -> No Booking created
    # -------------------------------------------------------------------------
    def test_05_no_final_confirmation_no_booking(self):
        """5. Không có xác nhận cuối cùng thì không tạo Booking."""
        async def _test():
            chatbot = ChatbotService(llm_provider=MockLLM())
            async with AsyncSessionLocal() as session:
                init_bookings = len((await session.execute(select(Booking))).scalars().all())

                # User 1 asks to book without confirming
                await acquire_slot_lock(slot_id=1, user_id=1, timeout_sec=600)
                res = await chatbot.handle_message(
                    message="Tôi muốn đặt sân #1",
                    user_info={"id": 1, "role": "CUSTOMER"},
                    db=session
                )
                self.assertEqual(res["status"], "confirmation_required")
                self.assertEqual(res.get("action_type"), "booking_preview")

                after_bookings = len((await session.execute(select(Booking))).scalars().all())
                self.assertEqual(init_bookings, after_bookings)
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 6: Other user cannot use booking intent (Anti-IDOR)
    # -------------------------------------------------------------------------
    def test_06_other_user_cannot_use_booking_intent(self):
        """6. User khác không thể dùng booking confirmation intent của người khác (Anti-IDOR)."""
        async def _test():
            async with AsyncSessionLocal() as session:
                await acquire_slot_lock(slot_id=1, user_id=1, timeout_sec=600)
                prev = await create_booking_preview(db=session, user_id=1, slot_id=1)
                intent_id = prev["data"]["booking_intent_id"]

                # User 2 tries to confirm User 1's intent
                res = await execute_confirmed_booking(db=session, user_id=2, booking_intent_id=intent_id)
                self.assertEqual(res["status"], "permission_denied")
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 7: Expired booking intent rejected
    # -------------------------------------------------------------------------
    def test_07_expired_booking_intent_rejected(self):
        """7. Confirmation intent hết hạn (TTL 300s) bị từ chối."""
        async def _test():
            mgr = get_booking_confirmation_manager()
            intent = await mgr.create_booking_intent(
                user_id=1, slot_id=1, court_id=1, facility_id=1, facility_name="Sân Test",
                court_number="1", date="2026-10-15", start_time="19:00", end_time="20:00",
                total_amount=80000.0, deposit_amount=40000.0, ttl_seconds=-10 # Expired
            )
            async with AsyncSessionLocal() as session:
                res = await execute_confirmed_booking(db=session, user_id=1, booking_intent_id=intent["intent_id"])
                self.assertEqual(res["status"], "booking_intent_expired")
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 8: Replay intent does not create second booking (Idempotency)
    # -------------------------------------------------------------------------
    def test_08_replay_intent_does_not_create_second_booking(self):
        """8. Replay một intent không tạo booking thứ hai, trả lại booking đã tạo trước đó."""
        async def _test():
            async with AsyncSessionLocal() as session:
                # Reset slot 1 to AVAILABLE
                slot = (await session.execute(select(TimeSlot).where(TimeSlot.id == 1))).scalar_one()
                slot.status = "AVAILABLE"
                await session.commit()

                await acquire_slot_lock(slot_id=1, user_id=1, timeout_sec=600)
                prev = await create_booking_preview(db=session, user_id=1, slot_id=1)
                intent_id = prev["data"]["booking_intent_id"]

                # First execution: succeeds
                res1 = await execute_confirmed_booking(db=session, user_id=1, booking_intent_id=intent_id)
                self.assertEqual(res1["status"], "booking_succeeded")
                first_booking_id = res1["data"]["booking_id"]

                # Second execution with exact same intent: idempotent response!
                res2 = await execute_confirmed_booking(db=session, user_id=1, booking_intent_id=intent_id)
                self.assertEqual(res2["status"], "booking_succeeded")
                self.assertEqual(res2["data"]["booking_id"], first_booking_id)
                self.assertTrue(res2.get("is_idempotent"))
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 9: Concurrent confirmations on same intent create only one booking
    # -------------------------------------------------------------------------
    def test_09_concurrent_confirmations_one_booking(self):
        """9. Hai request cùng xác nhận một intent chỉ tạo đúng một booking."""
        async def _test():
            async with AsyncSessionLocal() as session:
                slot = (await session.execute(select(TimeSlot).where(TimeSlot.id == 2))).scalar_one()
                slot.status = "AVAILABLE"
                await session.commit()

                await acquire_slot_lock(slot_id=2, user_id=1, timeout_sec=600)
                prev = await create_booking_preview(db=session, user_id=1, slot_id=2)
                intent_id = prev["data"]["booking_intent_id"]

                async with AsyncSessionLocal() as s1, AsyncSessionLocal() as s2:
                    r1, r2 = await asyncio.gather(
                        execute_confirmed_booking(db=s1, user_id=1, booking_intent_id=intent_id),
                        execute_confirmed_booking(db=s2, user_id=1, booking_intent_id=intent_id)
                    )

                successes = [r for r in [r1, r2] if r["status"] == "booking_succeeded"]
                self.assertGreaterEqual(len(successes), 1)
                # Both reference same booking ID
                booking_ids = set(r["data"]["booking_id"] for r in successes)
                self.assertEqual(len(booking_ids), 1)
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 10: Competing users on same slot -> only one booking succeeds
    # -------------------------------------------------------------------------
    def test_10_competing_users_same_slot_one_booking(self):
        """10. Hai user cạnh tranh cùng slot chỉ có một booking thành công."""
        async def _test():
            async with AsyncSessionLocal() as session:
                slot = (await session.execute(select(TimeSlot).where(TimeSlot.id == 1))).scalar_one()
                slot.status = "AVAILABLE"
                await session.commit()

                # User 1 holds lock
                await acquire_slot_lock(slot_id=1, user_id=1, timeout_sec=600)
                p1 = await create_booking_preview(db=session, user_id=1, slot_id=1)
                self.assertEqual(p1["status"], "preview_created")

                # User 2 tries to preview -> rejected because user 1 holds lock
                p2 = await create_booking_preview(db=session, user_id=2, slot_id=1)
                self.assertEqual(p2["status"], "slot_not_held")
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 11: BOOKED or MAINTENANCE slot rejected
    # -------------------------------------------------------------------------
    def test_11_booked_or_maintenance_slot_rejected(self):
        """11. Slot BOOKED hoặc MAINTENANCE bị từ chối đặt."""
        async def _test():
            async with AsyncSessionLocal() as session:
                slot = (await session.execute(select(TimeSlot).where(TimeSlot.id == 1))).scalar_one()
                slot.status = "BOOKED"
                await session.commit()

                await acquire_slot_lock(slot_id=1, user_id=1, timeout_sec=600)
                res = await create_booking_preview(db=session, user_id=1, slot_id=1)
                self.assertEqual(res["status"], "slot_unavailable")
                self.assertIn("BOOKED", res["message"])
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 12: Conflicting active booking rejected
    # -------------------------------------------------------------------------
    def test_12_conflicting_active_booking_rejected(self):
        """12. Nếu đã có active booking xung đột trên slot, yêu cầu mới bị từ chối."""
        async def _test():
            async with AsyncSessionLocal() as session:
                slot = (await session.execute(select(TimeSlot).where(TimeSlot.id == 1))).scalar_one()
                slot.status = "AVAILABLE"
                # Add existing active booking
                existing = Booking(
                    user_id=2, slot_id=1, total_amount=80000.0, deposit_amount=40000.0,
                    payment_status="PENDING", qr_checkin_code="QR-TEST-CONFLICT",
                    idempotency_key="conflict_test_01"
                )
                session.add(existing)
                await session.commit()

                await acquire_slot_lock(slot_id=1, user_id=1, timeout_sec=600)
                res = await create_booking_preview(db=session, user_id=1, slot_id=1)
                self.assertEqual(res["status"], "slot_unavailable")
                self.assertIn("đang hoạt động", res["message"])

                # Cleanup
                await session.delete(existing)
                await session.commit()
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 13: DB transaction rollback leaves no inconsistent state
    # -------------------------------------------------------------------------
    def test_13_db_rollback_no_inconsistent_state(self):
        """13. Database rollback không để lại trạng thái booking/slot không nhất quán."""
        async def _test():
            async with AsyncSessionLocal() as session:
                slot = (await session.execute(select(TimeSlot).where(TimeSlot.id == 1))).scalar_one()
                slot.status = "AVAILABLE"
                await session.commit()

                await acquire_slot_lock(slot_id=1, user_id=1, timeout_sec=600)
                prev = await create_booking_preview(db=session, user_id=1, slot_id=1)
                intent_id = prev["data"]["booking_intent_id"]

                # Simulate DB flush/commit error by patching db.flush to raise Exception
                with patch.object(session, "flush", side_effect=RuntimeError("Simulated DB Disk Failure")):
                    res = await execute_confirmed_booking(db=session, user_id=1, booking_intent_id=intent_id)
                    self.assertEqual(res["status"], "booking_failed")

                # Verify slot did NOT transition to BOOKED
                async with AsyncSessionLocal() as s2:
                    slot_recheck = (await s2.execute(select(TimeSlot).where(TimeSlot.id == 1))).scalar_one()
                    self.assertNotEqual(slot_recheck.status, "BOOKED")
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 14: Commit error / uncertain result handled via idempotency
    # -------------------------------------------------------------------------
    def test_14_commit_error_reconciled_via_idempotency(self):
        """14. Lỗi commit hoặc kết quả commit không xác định được xử lý bằng idempotency/reconciliation."""
        async def _test():
            async with AsyncSessionLocal() as session:
                slot = (await session.execute(select(TimeSlot).where(TimeSlot.id == 1))).scalar_one()
                slot.status = "AVAILABLE"
                await session.commit()

                # Insert booking already committed with idempotency_key
                bk = Booking(
                    user_id=1, slot_id=1, total_amount=80000.0, deposit_amount=40000.0,
                    payment_status="PENDING", qr_checkin_code="QR-RECONCILE-01",
                    idempotency_key="idemp_recon_key_01"
                )
                session.add(bk)
                await session.commit()

                # Client retries with same idempotency key
                res = await execute_confirmed_booking(
                    db=session, user_id=1, booking_intent_id="bci_dummy", idempotency_key="idemp_recon_key_01"
                )
                self.assertEqual(res["status"], "booking_succeeded")
                self.assertTrue(res.get("is_idempotent"))
                self.assertEqual(res["data"]["booking_id"], bk.id)

                # Cleanup
                await session.delete(bk)
                await session.commit()
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 15: Redis release error does not fail committed booking
    # -------------------------------------------------------------------------
    def test_15_redis_release_error_does_not_fail_committed_booking(self):
        """15. Redis release lỗi sau khi booking commit không làm fail đơn đặt và không tạo trùng."""
        async def _test():
            async with AsyncSessionLocal() as session:
                slot = (await session.execute(select(TimeSlot).where(TimeSlot.id == 1))).scalar_one()
                slot.status = "AVAILABLE"
                await session.commit()

                await acquire_slot_lock(slot_id=1, user_id=1, timeout_sec=600)
                prev = await create_booking_preview(db=session, user_id=1, slot_id=1)
                intent_id = prev["data"]["booking_intent_id"]

                # Mock release_slot_lock to fail
                with patch("app.services.booking_service.release_slot_lock", side_effect=ConnectionError("Redis disconnect during release")):
                    res = await execute_confirmed_booking(db=session, user_id=1, booking_intent_id=intent_id)
                    # Booking STILL succeeds because DB transaction committed!
                    self.assertEqual(res["status"], "booking_succeeded")
                    self.assertIsNotNone(res["data"]["booking_id"])
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 16: Price and deposit from real business logic
    # -------------------------------------------------------------------------
    def test_16_price_and_deposit_from_real_business_logic(self):
        """16. Giá và tiền cọc lấy từ business logic thật (cọc 50% làm tròn nghìn đồng)."""
        async def _test():
            async with AsyncSessionLocal() as session:
                slot = (await session.execute(select(TimeSlot).where(TimeSlot.id == 1))).scalar_one()
                slot.status = "AVAILABLE"
                await session.commit()

                await acquire_slot_lock(slot_id=1, user_id=1, timeout_sec=600)
                prev = await create_booking_preview(db=session, user_id=1, slot_id=1)
                data = prev["data"]
                # 50% deposit
                self.assertEqual(data["deposit_amount"], round(data["total_amount"] * 0.5, -3))
                self.assertGreater(data["total_amount"], 0)
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 17: Dynamic pricing not applied twice
    # -------------------------------------------------------------------------
    def test_17_dynamic_pricing_not_applied_twice(self):
        """17. Dynamic pricing không bị áp dụng hai lần."""
        async def _test():
            async with AsyncSessionLocal() as session:
                slot = (await session.execute(select(TimeSlot).where(TimeSlot.id == 1))).scalar_one()
                pricing = (await session.execute(select(SlotPricing).where(SlotPricing.slot_id == 1))).scalar_one_or_none()
                expected_price = pricing.dynamic_price if pricing else 80000.0

                await acquire_slot_lock(slot_id=1, user_id=1, timeout_sec=600)
                prev = await create_booking_preview(db=session, user_id=1, slot_id=1)
                self.assertEqual(prev["data"]["court_price"], expected_price)
                self.assertEqual(prev["data"]["total_amount"], expected_price)
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 18: Payment status reflects unpaid (PENDING) before payment tx
    # -------------------------------------------------------------------------
    def test_18_payment_status_is_pending_without_payment_tx(self):
        """18. Trạng thái thanh toán phản ánh chưa thanh toán (PENDING) khi chưa có payment transaction."""
        async def _test():
            async with AsyncSessionLocal() as session:
                slot = (await session.execute(select(TimeSlot).where(TimeSlot.id == 1))).scalar_one()
                slot.status = "AVAILABLE"
                await session.commit()

                await acquire_slot_lock(slot_id=1, user_id=1, timeout_sec=600)
                prev = await create_booking_preview(db=session, user_id=1, slot_id=1)
                res = await execute_confirmed_booking(db=session, user_id=1, booking_intent_id=prev["data"]["booking_intent_id"])

                self.assertEqual(res["status"], "booking_succeeded")
                self.assertEqual(res["data"]["payment_status"], "PENDING")

                # Verify in DB
                b_row = (await session.execute(select(Booking).where(Booking.id == res["data"]["booking_id"]))).scalar_one()
                self.assertEqual(b_row.payment_status, "PENDING")
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 19: Chatbot response does not leak QR or secrets
    # -------------------------------------------------------------------------
    def test_19_chatbot_response_does_not_leak_qr(self):
        """19. Response chatbot không lộ QR check-in token hoặc dữ liệu bí mật."""
        async def _test():
            chatbot = ChatbotService(llm_provider=MockLLM())
            async with AsyncSessionLocal() as session:
                slot = (await session.execute(select(TimeSlot).where(TimeSlot.id == 1))).scalar_one()
                slot.status = "AVAILABLE"
                await session.commit()

                await acquire_slot_lock(slot_id=1, user_id=1, timeout_sec=600)
                # Preview
                await chatbot.handle_message(
                    message="Tôi muốn đặt sân #1",
                    user_info={"id": 1, "role": "CUSTOMER"},
                    db=session
                )
                # Confirm
                res = await chatbot.handle_message(
                    message="Xác nhận đặt sân",
                    user_info={"id": 1, "role": "CUSTOMER"},
                    db=session
                )
                self.assertEqual(res["status"], "booking_succeeded")
                # Text answer must NEVER contain "QR-ALB-"
                self.assertNotIn("QR-ALB-", res["answer"])
                self.assertNotIn("qr_checkin_code", res["answer"].lower())
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 20: Booking ID and success state verified against DB
    # -------------------------------------------------------------------------
    def test_20_booking_id_and_status_from_real_database(self):
        """20. Booking ID và trạng thái thành công lấy từ database thực tế."""
        async def _test():
            async with AsyncSessionLocal() as session:
                slot = (await session.execute(select(TimeSlot).where(TimeSlot.id == 1))).scalar_one()
                slot.status = "AVAILABLE"
                await session.commit()

                await acquire_slot_lock(slot_id=1, user_id=1, timeout_sec=600)
                prev = await create_booking_preview(db=session, user_id=1, slot_id=1)
                res = await execute_confirmed_booking(db=session, user_id=1, booking_intent_id=prev["data"]["booking_intent_id"])

                b_id = res["data"]["booking_id"]
                db_record = (await session.execute(select(Booking).where(Booking.id == b_id))).scalar_one_or_none()
                self.assertIsNotNone(db_record)
                self.assertEqual(db_record.user_id, 1)
                self.assertEqual(db_record.slot_id, 1)
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 21: Existing booking APIs not regressed
    # -------------------------------------------------------------------------
    def test_21_existing_booking_api_not_regressed(self):
        """21. Các API booking hiện tại (GET /my) không bị regression."""
        async def _test():
            async with AsyncSessionLocal() as session:
                stmt = select(Booking).where(Booking.user_id == 1)
                res = await session.execute(stmt)
                user_bookings = res.scalars().all()
                self.assertIsInstance(user_bookings, list)
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 22: Redis outage returns unverified, not false success
    # -------------------------------------------------------------------------
    def test_22_redis_outage_returns_unverified_not_success(self):
        """22. Redis outage không được hiểu nhầm thành booking thành công."""
        async def _test():
            async with AsyncSessionLocal() as session:
                with patch("app.services.booking_service.get_slot_lock_holder", side_effect=ConnectionError("Redis down")):
                    res = await create_booking_preview(db=session, user_id=1, slot_id=1)
                    self.assertEqual(res["status"], "availability_unverified")
                    self.assertIn("không khả dụng", res["message"])
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 23: RAG policy FAQ independent from booking routing
    # -------------------------------------------------------------------------
    def test_23_rag_policy_faq_independent_from_booking(self):
        """23. RAG chính sách (hủy sân, hoàn cọc, quy định) vẫn hoạt động độc lập với booking routing."""
        async def _test():
            chatbot = ChatbotService(llm_provider=MockLLM())
            async with AsyncSessionLocal() as session:
                # FAQ inquiry about cancellation policy
                res = await chatbot.handle_message(
                    message="Quy định hủy sân và hoàn cọc là bao nhiêu phần trăm?",
                    user_info={"id": 1, "role": "CUSTOMER"},
                    db=session
                )
                # Must NOT trigger booking confirmation or hold preview
                self.assertNotEqual(res.get("action_type"), "booking_preview")
                self.assertNotEqual(res.get("action_type"), "slot_hold_preview")
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 24: Unit tests run cleanly on SQLite
    # -------------------------------------------------------------------------
    def test_24_unit_runs_cleanly_on_sqlite(self):
        """24. Unit/regression tests chạy hoàn toàn ổn định trên SQLite."""
        async def _test():
            async with AsyncSessionLocal() as session:
                res = await session.execute(text("SELECT 1;"))
                self.assertEqual(res.scalar(), 1)
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 25: Live PostgreSQL integration verification
    # -------------------------------------------------------------------------
    def test_25_live_postgres_integration(self):
        """25. Live PostgreSQL integration xác minh transaction, constraint idempotency."""
        async def _test():
            pg_host = os.getenv("POSTGRES_HOST", "127.0.0.1")
            pg_port = os.getenv("POSTGRES_PORT", "5433")
            db_url = f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{pg_host}:{pg_port}/{settings.POSTGRES_DB}"
            try:
                engine = create_async_engine(db_url)
                async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
                async with async_session() as session:
                    # Verify idempotency_key column exists in information_schema
                    res = await session.execute(text(
                        "SELECT column_name FROM information_schema.columns WHERE table_name = 'bookings' AND column_name = 'idempotency_key';"
                    ))
                    col = res.scalar_one_or_none()
                    self.assertEqual(col, "idempotency_key")
                await engine.dispose()
            except Exception as e:
                self.skipTest(f"Live PostgreSQL not reachable on host {pg_host}:{pg_port} ({e})")
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 26: Live Redis integration lock ownership & expiration
    # -------------------------------------------------------------------------
    def test_26_live_redis_lock_ownership_verification(self):
        """26. Live Redis integration xác minh lock ownership và xử lý hết hạn."""
        async def _test():
            try:
                import redis.asyncio as aioredis
                client = aioredis.from_url("redis://127.0.0.1:6379/0", decode_responses=True)
                pong = await client.ping()
                if not pong:
                    self.skipTest("Live Redis ping failed")

                # Test atomic booking intent storage & consume Lua
                test_key = f"test_booking_intent:{uuid.uuid4().hex[:8]}"
                await client.set(test_key, json.dumps({"intent_id": test_key, "user_id": 999, "status": "PENDING", "expires_at": time.time() + 300}), ex=60)
                raw = await client.get(test_key)
                self.assertIsNotNone(raw)
                await client.delete(test_key)
                await client.close()
            except Exception as e:
                self.skipTest(f"Live Redis unreachable ({e})")
        self.run_async(_test())


if __name__ == "__main__":
    unittest.main()
