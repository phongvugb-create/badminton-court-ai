"""
BADMINTON.AI - PHASE 7.2 TEST SUITE: SAFE SLOT HOLD & EXPLICIT USER CONFIRMATION
Validates 20 required points for safe slot hold, pending intent, and explicit user confirmation:
1.  Guest cannot hold slot (authentication_required).
2.  Missing information asks for clarification, no lock created.
3.  Successful preview does NOT create Redis lock.
4.  No confirmation -> no hold execution.
5.  Valid confirmation by intent owner executes hold (hold_succeeded).
6.  Anti-IDOR: Another user cannot confirm another user's pending intent.
7.  Expired pending intent cannot be used (pending_intent_expired).
8.  Anti-Replay: Consumed pending intent cannot be reused.
9.  Double-submit / double-click prevention.
10. Race condition: Two users competing for same slot -> only 1 lock granted.
11. Existing Redis lock by another user is NOT overwritten (slot_unavailable).
12. Slot BOOKED or MAINTENANCE cannot be held (slot_unavailable).
13. Redis unavailable returns unverified, never claims success.
14. Timeout / unverified state does not falsely claim success.
15. Slot changed after preview is re-verified at confirmation time.
16. Unrelated confirmation message without pending intent triggers no side effect.
17. Response contains verified slot data (facility, court, time, 10 min hold).
18. Booking and payment tables are NOT touched (strictly slot hold).
19. Phase 7.1 read-only tools and API compatibility preserved.
20. Expiry/cancellation of pending intent NEVER releases another user's lock.
"""

import os
import sys
import time
import asyncio
import unittest
from unittest.mock import patch, AsyncMock
from datetime import datetime, timedelta

# Setup module path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from sqlalchemy.future import select
from app.core.database import AsyncSessionLocal
from app.models.all_models import Facility, Court, TimeSlot, SlotPricing, Booking, User
from app.core.redis import acquire_slot_lock, release_slot_lock, get_slot_lock_holder, _in_memory_locks
from app.ai.tools.pending_hold_manager import (
    PendingHoldManager,
    get_pending_hold_manager,
    execute_slot_hold
)
from app.ai.chatbot_service import ChatbotService
from app.ai.llm_provider import BaseLLMProvider


class MockLLMProviderForTest(BaseLLMProvider):
    @property
    def provider_name(self) -> str:
        return "MockLLMProvider"

    @property
    def model_name(self) -> str:
        return "mock-model"

    async def generate_text(self, system_instruction: str, user_message: str, history=None, timeout: float = 8.0) -> str:
        return "Nội dung phản hồi từ mô hình kiểm thử."


class TestPhase72SlotHoldConfirmation(unittest.TestCase):
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
        from sqlalchemy import text
        async with AsyncSessionLocal() as session:
            # 1. Facility Đa Năng
            fac = (await session.execute(select(Facility).where(Facility.id == 999))).scalar_one_or_none()
            if not fac:
                await session.execute(text("""
                    INSERT OR REPLACE INTO facilities (id, owner_id, name, address, latitude, longitude, is_approved)
                    VALUES (999, 1, 'Sân Cầu Lông Đa Năng', '136 Xuân Thủy, Cầu Giấy, Hà Nội', 21.0362, 105.7836, 1)
                """))
            else:
                await session.execute(text("UPDATE facilities SET is_approved = 1, name = 'Sân Cầu Lông Đa Năng' WHERE id = 999"))

            # Facility 101 for test 12
            fac101 = (await session.execute(select(Facility).where(Facility.id == 101))).scalar_one_or_none()
            if not fac101:
                await session.execute(text("""
                    INSERT OR REPLACE INTO facilities (id, owner_id, name, address, latitude, longitude, is_approved)
                    VALUES (101, 1, 'CLB Catchy', 'Quận Cầu Giấy, Hà Nội', 21.03, 105.78, 1)
                """))
            else:
                await session.execute(text("UPDATE facilities SET is_approved = 1, name = 'CLB Catchy' WHERE id = 101"))

            # Ensure all other facilities in test DB are approved as well
            await session.execute(text("UPDATE facilities SET is_approved = 1 WHERE is_approved IS NULL"))

            # 2. Court 999
            crt = (await session.execute(select(Court).where(Court.id == 999))).scalar_one_or_none()
            if not crt:
                await session.execute(text("""
                    INSERT OR REPLACE INTO courts (id, facility_id, surface_type, court_number, is_active)
                    VALUES (999, 999, 'Thảm PVC chuyên dụng Enlio', '1', 1)
                """))
            else:
                await session.execute(text("UPDATE courts SET is_active = 1 WHERE id = 999"))

            # Court 201 for test 12
            crt201 = (await session.execute(select(Court).where(Court.id == 201))).scalar_one_or_none()
            if not crt201:
                await session.execute(text("""
                    INSERT OR REPLACE INTO courts (id, facility_id, surface_type, court_number, is_active)
                    VALUES (201, 101, 'Thảm PVC', '1', 1)
                """))
            else:
                await session.execute(text("UPDATE courts SET is_active = 1 WHERE id = 201"))

            # 3. TimeSlot 999
            await session.execute(text("""
                INSERT OR REPLACE INTO time_slots (id, court_id, date, start_time, end_time, status)
                VALUES (999, 999, '2026-10-15', '19:00', '20:00', 'AVAILABLE')
            """))

            # 4. SlotPricing for slot 999
            await session.execute(text("""
                INSERT OR REPLACE INTO slot_pricing (id, slot_id, base_price, dynamic_price, adjustment_reason, is_ai_applied)
                VALUES (999, 999, 80000.0, 100000.0, 'Khung giờ vàng tối ngày thường (+25%)', 1)
            """))

            # 5. User 1 and User 2
            await session.execute(text("""
                INSERT OR REPLACE INTO users (id, name, phone, password_hash, role)
                VALUES (1, 'Nguyễn Văn Test', '0901234567', 'hash1', 'CUSTOMER')
            """))
            await session.execute(text("""
                INSERT OR REPLACE INTO users (id, name, phone, password_hash, role)
                VALUES (2, 'Trần Thị Test', '0907654321', 'hash2', 'CUSTOMER')
            """))

            await session.commit()

    def setUp(self):
        # Clear in-memory locks and intents between tests
        _in_memory_locks.clear()

    def run_async(self, coro):
        return self.loop.run_until_complete(coro)

    # -------------------------------------------------------------------------
    # TEST 1: Guest cannot hold slot
    # -------------------------------------------------------------------------
    def test_01_guest_cannot_hold_slot(self):
        """1. Guest không thể giữ sân."""
        async def _test():
            chatbot_svc = ChatbotService(llm_provider=MockLLMProviderForTest())
            async with AsyncSessionLocal() as session:
                res = await chatbot_svc.handle_message(
                    message="Tôi muốn giữ sân Đa Năng ngày 2026-10-15 lúc 19:00",
                    user_info=None,
                    user_role="GUEST",
                    db=session
                )
                self.assertEqual(res["status"], "authentication_required")
                self.assertIn("đăng nhập", res["answer"].lower())
                # Check no lock was created
                holder = await get_slot_lock_holder(999)
                self.assertIsNone(holder)
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 2: Missing information asks for clarification, no lock
    # -------------------------------------------------------------------------
    def test_02_missing_info_asks_clarification_no_lock(self):
        """2. Yêu cầu thiếu thông tin chỉ trả câu hỏi bổ sung và không tạo lock."""
        async def _test():
            chatbot_svc = ChatbotService(llm_provider=MockLLMProviderForTest())
            async with AsyncSessionLocal() as session:
                res = await chatbot_svc.handle_message(
                    message="Tôi muốn giữ sân tối nay",
                    user_info={"id": 1, "role": "CUSTOMER"},
                    db=session
                )
                self.assertEqual(res["status"], "confirmation_required")
                self.assertIn("chưa đầy đủ", res["answer"])
                self.assertIsNone(res.get("pending_intent_id"))
                self.assertEqual(len(_in_memory_locks), 0)
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 3: Preview creation does NOT create Redis lock
    # -------------------------------------------------------------------------
    def test_03_preview_does_not_create_redis_lock(self):
        """3. Xem trước thành công nhưng không tạo Redis lock."""
        async def _test():
            chatbot_svc = ChatbotService(llm_provider=MockLLMProviderForTest())
            async with AsyncSessionLocal() as session:
                res = await chatbot_svc.handle_message(
                    message="Tôi muốn giữ sân Đa Năng ngày 2026-10-15 lúc 19:00",
                    user_info={"id": 1, "role": "CUSTOMER"},
                    db=session
                )
                self.assertEqual(res["status"], "confirmation_required")
                self.assertEqual(res.get("action_type"), "slot_hold_preview")
                self.assertIsNotNone(res.get("pending_intent_id"))
                slot_id = res["preview_data"]["slot_id"]

                # CRITICAL VERIFICATION: Slot lock MUST BE NONE in Redis/memory!
                holder = await get_slot_lock_holder(slot_id)
                self.assertIsNone(holder, "Preview MUST NOT acquire slot lock!")
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 4: No confirmation -> no hold execution
    # -------------------------------------------------------------------------
    def test_04_no_confirmation_no_hold_execution(self):
        """4. Không có xác nhận thì không thực hiện giữ sân."""
        async def _test():
            chatbot_svc = ChatbotService(llm_provider=MockLLMProviderForTest())
            async with AsyncSessionLocal() as session:
                # Step 1: Create preview
                res1 = await chatbot_svc.handle_message(
                    message="Tôi muốn giữ sân Đa Năng ngày 2026-10-15 lúc 19:00",
                    user_info={"id": 1, "role": "CUSTOMER"},
                    db=session
                )
                slot_id = res1["preview_data"]["slot_id"]

                # Step 2: User says something unrelated (not confirmation)
                res2 = await chatbot_svc.handle_message(
                    message="Giá thuê bao gồm nước uống không?",
                    user_info={"id": 1, "role": "CUSTOMER"},
                    db=session
                )
                # Still no lock created!
                holder = await get_slot_lock_holder(slot_id)
                self.assertIsNone(holder)
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 5: Valid confirmation by intent owner executes hold
    # -------------------------------------------------------------------------
    def test_05_valid_confirmation_executes_hold(self):
        """5. Xác nhận hợp lệ của đúng chủ sở hữu có thể giữ sân."""
        async def _test():
            chatbot_svc = ChatbotService(llm_provider=MockLLMProviderForTest())
            async with AsyncSessionLocal() as session:
                # Step 1: Preview
                res_prev = await chatbot_svc.handle_message(
                    message="Tôi muốn giữ sân Đa Năng ngày 2026-10-15 lúc 19:00",
                    user_info={"id": 1, "role": "CUSTOMER"},
                    db=session
                )
                slot_id = res_prev["preview_data"]["slot_id"]

                # Step 2: Confirm
                res_conf = await chatbot_svc.handle_message(
                    message="Xác nhận",
                    user_info={"id": 1, "role": "CUSTOMER"},
                    db=session
                )
                self.assertEqual(res_conf["status"], "hold_succeeded")
                self.assertEqual(res_conf.get("action_type"), "slot_hold_confirmed")
                self.assertIn("GIỮ CHỖ THÀNH CÔNG", res_conf["answer"])
                self.assertIn("10 phút", res_conf["answer"])

                # Redis lock must now be held by user 1
                holder = await get_slot_lock_holder(slot_id)
                self.assertEqual(holder, "1")
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 6: Anti-IDOR: Another user cannot confirm another's intent
    # -------------------------------------------------------------------------
    def test_06_anti_idor_another_user_cannot_confirm(self):
        """6. Người khác không thể xác nhận pending intent của tài khoản khác."""
        async def _test():
            mgr = get_pending_hold_manager()
            async with AsyncSessionLocal() as session:
                intent = await mgr.create_pending_intent(
                    user_id=1,
                    slot_id=999,
                    court_id=999,
                    facility_id=999,
                    facility_name="Sân Cầu Lông Đa Năng",
                    court_number="1",
                    date="2026-10-15",
                    start_time="19:00",
                    end_time="20:00",
                    price=100000.0
                )

                # User 2 attempts to confirm user 1's intent
                res = await execute_slot_hold(
                    db=session,
                    user_id=2,  # Attacker user 2
                    intent_id=intent["intent_id"]
                )
                self.assertEqual(res["status"], "hold_failed")
                self.assertIn("không có quyền", res["message"].lower())

                # Verify user 2 did not get the lock
                holder = await get_slot_lock_holder(999)
                self.assertIsNone(holder)
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 7: Expired pending intent cannot be used
    # -------------------------------------------------------------------------
    def test_07_expired_pending_intent_rejected(self):
        """7. Pending intent hết hạn không thể sử dụng."""
        async def _test():
            mgr = get_pending_hold_manager()
            async with AsyncSessionLocal() as session:
                # Create intent with negative TTL (already expired)
                intent = await mgr.create_pending_intent(
                    user_id=1,
                    slot_id=999,
                    court_id=999,
                    facility_id=999,
                    facility_name="Sân Cầu Lông Đa Năng",
                    court_number="1",
                    date="2026-10-15",
                    start_time="19:00",
                    end_time="20:00",
                    price=100000.0,
                    ttl_seconds=-10
                )

                res = await execute_slot_hold(
                    db=session,
                    user_id=1,
                    intent_id=intent["intent_id"]
                )
                self.assertEqual(res["status"], "pending_intent_expired")
                self.assertIn("hết hạn", res["message"].lower())
                self.assertIsNone(await get_slot_lock_holder(999))
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 8: Anti-Replay: Consumed pending intent cannot be reused
    # -------------------------------------------------------------------------
    def test_08_anti_replay_consumed_intent(self):
        """8. Pending intent đã tiêu thụ không được replay để tạo thao tác mới."""
        async def _test():
            mgr = get_pending_hold_manager()
            async with AsyncSessionLocal() as session:
                intent = await mgr.create_pending_intent(
                    user_id=1,
                    slot_id=999,
                    court_id=999,
                    facility_id=999,
                    facility_name="Sân Cầu Lông Đa Năng",
                    court_number="1",
                    date="2026-10-15",
                    start_time="19:00",
                    end_time="20:00",
                    price=100000.0
                )

                # First execution: success
                res1 = await execute_slot_hold(db=session, user_id=1, intent_id=intent["intent_id"])
                self.assertEqual(res1["status"], "hold_succeeded")

                # Second execution (Replay attack): rejected
                res2 = await execute_slot_hold(db=session, user_id=1, intent_id=intent["intent_id"])
                self.assertEqual(res2["status"], "hold_failed")
                self.assertIn("đã được thực hiện", res2["message"].lower())
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 9: Double-click / simultaneous confirm prevention
    # -------------------------------------------------------------------------
    def test_09_double_click_prevention(self):
        """9. Double-click hoặc gửi xác nhận lặp không tạo hai lần giữ chỗ."""
        async def _test():
            mgr = get_pending_hold_manager()
            async with AsyncSessionLocal() as session:
                intent = await mgr.create_pending_intent(
                    user_id=1,
                    slot_id=999,
                    court_id=999,
                    facility_id=999,
                    facility_name="Sân Cầu Lông Đa Năng",
                    court_number="1",
                    date="2026-10-15",
                    start_time="19:00",
                    end_time="20:00",
                    price=100000.0
                )

                # Run two concurrent confirmations with the same intent
                task1 = execute_slot_hold(session, 1, intent["intent_id"])
                task2 = execute_slot_hold(session, 1, intent["intent_id"])
                results = await asyncio.gather(task1, task2)

                statuses = [r["status"] for r in results]
                self.assertIn("hold_succeeded", statuses)
                self.assertIn("hold_failed", statuses)
                self.assertEqual(statuses.count("hold_succeeded"), 1)
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 10: Race condition: Two users competing for same slot
    # -------------------------------------------------------------------------
    def test_10_race_condition_competing_users(self):
        """10. Hai user tranh chấp cùng slot thì chỉ một lock hợp lệ được tạo."""
        async def _test():
            mgr = get_pending_hold_manager()
            async with AsyncSessionLocal() as session:
                intent1 = await mgr.create_pending_intent(
                    user_id=1,
                    slot_id=999,
                    court_id=999,
                    facility_id=999,
                    facility_name="Sân Cầu Lông Đa Năng",
                    court_number="1",
                    date="2026-10-15",
                    start_time="19:00",
                    end_time="20:00",
                    price=100000.0
                )
                intent2 = await mgr.create_pending_intent(
                    user_id=2,
                    slot_id=999,
                    court_id=999,
                    facility_id=999,
                    facility_name="Sân Cầu Lông Đa Năng",
                    court_number="1",
                    date="2026-10-15",
                    start_time="19:00",
                    end_time="20:00",
                    price=100000.0
                )

                # Both users confirm concurrently
                task1 = execute_slot_hold(session, 1, intent1["intent_id"])
                task2 = execute_slot_hold(session, 2, intent2["intent_id"])
                r1, r2 = await asyncio.gather(task1, task2)

                results = [r1["status"], r2["status"]]
                # Exactly one must succeed, the other must be slot_unavailable
                self.assertEqual(results.count("hold_succeeded"), 1)
                self.assertEqual(results.count("slot_unavailable"), 1)
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 11: Existing Redis lock by another user is NOT overwritten
    # -------------------------------------------------------------------------
    def test_11_existing_redis_lock_not_overwritten(self):
        """11. Redis đã có lock của người dùng khác thì không ghi đè."""
        async def _test():
            mgr = get_pending_hold_manager()
            async with AsyncSessionLocal() as session:
                # User 99 already locked slot 999
                await acquire_slot_lock(slot_id=999, user_id=99, timeout_sec=600)

                intent = await mgr.create_pending_intent(
                    user_id=1,
                    slot_id=999,
                    court_id=999,
                    facility_id=999,
                    facility_name="Sân Cầu Lông Đa Năng",
                    court_number="1",
                    date="2026-10-15",
                    start_time="19:00",
                    end_time="20:00",
                    price=100000.0
                )

                res = await execute_slot_hold(db=session, user_id=1, intent_id=intent["intent_id"])
                self.assertEqual(res["status"], "slot_unavailable")

                # Lock must still belong to user 99!
                holder = await get_slot_lock_holder(999)
                self.assertEqual(holder, "99")
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 12: Slot BOOKED or MAINTENANCE cannot be held
    # -------------------------------------------------------------------------
    def test_12_booked_or_maintenance_slot_rejected(self):
        """12. Slot BOOKED hoặc MAINTENANCE không được giữ."""
        async def _test():
            mgr = get_pending_hold_manager()
            async with AsyncSessionLocal() as session:
                from sqlalchemy import text
                # 1. Create dynamic test slots with BOOKED and MAINTENANCE status
                res_b_id = await session.execute(
                    text("INSERT INTO time_slots (court_id, date, start_time, end_time, status) VALUES (201, '2026-10-15', '20:00', '21:00', 'BOOKED') RETURNING id")
                )
                booked_id = res_b_id.scalar()

                res_m_id = await session.execute(
                    text("INSERT INTO time_slots (court_id, date, start_time, end_time, status) VALUES (201, '2026-10-15', '21:00', '22:00', 'MAINTENANCE') RETURNING id")
                )
                maint_id = res_m_id.scalar()
                await session.commit()

                try:
                    # Test rejection on BOOKED slot
                    intent_booked = await mgr.create_pending_intent(
                        user_id=1,
                        slot_id=booked_id,
                        court_id=201,
                        facility_id=101,
                        facility_name="CLB Catchy",
                        court_number="1",
                        date="2026-10-15",
                        start_time="20:00",
                        end_time="21:00",
                        price=120000.0
                    )
                    res_b = await execute_slot_hold(db=session, user_id=1, intent_id=intent_booked["intent_id"])
                    self.assertEqual(res_b["status"], "slot_unavailable")
                    self.assertIn("BOOKED", res_b["message"])

                    # Test rejection on MAINTENANCE slot
                    intent_maint = await mgr.create_pending_intent(
                        user_id=1,
                        slot_id=maint_id,
                        court_id=201,
                        facility_id=101,
                        facility_name="CLB Catchy",
                        court_number="1",
                        date="2026-10-15",
                        start_time="21:00",
                        end_time="22:00",
                        price=120000.0
                    )
                    res_m = await execute_slot_hold(db=session, user_id=1, intent_id=intent_maint["intent_id"])
                    self.assertEqual(res_m["status"], "slot_unavailable")
                    self.assertIn("MAINTENANCE", res_m["message"])
                finally:
                    # Clean up isolated test slots
                    await session.execute(text("DELETE FROM time_slots WHERE id IN (:b_id, :m_id)"), {"b_id": booked_id, "m_id": maint_id})
                    await session.commit()

        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 13: Redis unavailable returns unverified, never claims success
    # -------------------------------------------------------------------------
    def test_13_redis_unavailable_returns_unverified(self):
        """13. Redis không khả dụng trả trạng thái thất bại/chưa xác minh, không báo thành công."""
        async def _test():
            mgr = get_pending_hold_manager()
            async with AsyncSessionLocal() as session:
                intent = await mgr.create_pending_intent(
                    user_id=1,
                    slot_id=999,
                    court_id=999,
                    facility_id=999,
                    facility_name="Sân Cầu Lông Đa Năng",
                    court_number="1",
                    date="2026-10-15",
                    start_time="19:00",
                    end_time="20:00",
                    price=100000.0
                )

                # Mock Redis acquire raising ConnectionError
                with patch("app.ai.tools.pending_hold_manager.acquire_slot_lock", side_effect=ConnectionError("Redis down")):
                    res = await execute_slot_hold(db=session, user_id=1, intent_id=intent["intent_id"])
                    self.assertEqual(res["status"], "availability_unverified")
                    self.assertIn("Redis", res["message"])
                    self.assertIsNone(res.get("data"))
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 14: Timeout does not falsely claim success
    # -------------------------------------------------------------------------
    def test_14_timeout_does_not_claim_success(self):
        """14. Khi timeout và kết quả lock không rõ ràng, không tự kết luận thành công."""
        async def _test():
            mgr = get_pending_hold_manager()
            async with AsyncSessionLocal() as session:
                intent = await mgr.create_pending_intent(
                    user_id=1,
                    slot_id=999,
                    court_id=999,
                    facility_id=999,
                    facility_name="Sân Cầu Lông Đa Năng",
                    court_number="1",
                    date="2026-10-15",
                    start_time="19:00",
                    end_time="20:00",
                    price=100000.0
                )

                with patch("app.ai.tools.pending_hold_manager.acquire_slot_lock", side_effect=asyncio.TimeoutError("Lock timeout")):
                    res = await execute_slot_hold(db=session, user_id=1, intent_id=intent["intent_id"])
                    self.assertEqual(res["status"], "availability_unverified")
                    self.assertIsNone(res.get("data"))
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 15: Slot changed after preview is re-verified at hold time
    # -------------------------------------------------------------------------
    def test_15_slot_changed_after_preview_reverified(self):
        """15. Slot thay đổi sau khi hiển thị bản xem trước phải được kiểm tra lại."""
        async def _test():
            mgr = get_pending_hold_manager()
            async with AsyncSessionLocal() as session:
                # 1. Preview created while slot is AVAILABLE
                intent = await mgr.create_pending_intent(
                    user_id=1,
                    slot_id=999,
                    court_id=999,
                    facility_id=999,
                    facility_name="Sân Cầu Lông Đa Năng",
                    court_number="1",
                    date="2026-10-15",
                    start_time="19:00",
                    end_time="20:00",
                    price=100000.0
                )

                # 2. Before user confirms, slot in DB is updated to BOOKED by an offline cashier
                slot_obj = (await session.execute(select(TimeSlot).where(TimeSlot.id == 999))).scalar_one()
                slot_obj.status = "BOOKED"
                await session.flush()

                # 3. User attempts to confirm
                res = await execute_slot_hold(db=session, user_id=1, intent_id=intent["intent_id"])
                self.assertEqual(res["status"], "slot_unavailable")
                self.assertIn("BOOKED", res["message"])

                # Revert DB state
                slot_obj.status = "AVAILABLE"
                await session.flush()
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 16: Unrelated confirmation message triggers no side effect
    # -------------------------------------------------------------------------
    def test_16_unrelated_confirmation_triggers_no_side_effect(self):
        """16. Thông điệp xác nhận không liên quan đến pending intent không kích hoạt side effect."""
        async def _test():
            chatbot_svc = ChatbotService(llm_provider=MockLLMProviderForTest())
            async with AsyncSessionLocal() as session:
                # User says "Xác nhận" out of nowhere without any pending intent
                res = await chatbot_svc.handle_message(
                    message="Tôi đồng ý",
                    user_info={"id": 99, "role": "CUSTOMER"},
                    db=session
                )
                self.assertEqual(res["status"], "pending_intent_expired")
                self.assertIn("không tìm thấy", res["answer"].lower())
                self.assertEqual(len(_in_memory_locks), 0)
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 17: Success response contains verified business data
    # -------------------------------------------------------------------------
    def test_17_success_response_contains_verified_data(self):
        """17. Phản hồi thành công dựa trên kết quả tool/API thực tế."""
        async def _test():
            chatbot_svc = ChatbotService(llm_provider=MockLLMProviderForTest())
            async with AsyncSessionLocal() as session:
                # Preview
                await chatbot_svc.handle_message(
                    message="Tôi muốn giữ sân Đa Năng ngày 2026-10-15 lúc 19:00",
                    user_info={"id": 1, "role": "CUSTOMER"},
                    db=session
                )
                # Confirm
                res = await chatbot_svc.handle_message(
                    message="Xác nhận",
                    user_info={"id": 1, "role": "CUSTOMER"},
                    db=session
                )
                self.assertEqual(res["status"], "hold_succeeded")
                self.assertIn("GIỮ CHỖ THÀNH CÔNG", res["answer"])
                self.assertIn("Sân Cầu Lông Đa Năng", res["answer"])
                self.assertIn("19:00", res["answer"])
                self.assertIn("#999", res["answer"])
                self.assertEqual(res["hold_result"]["held_for_seconds"], 600)
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 18: Booking and payment endpoints NOT called in Phase 7.2
    # -------------------------------------------------------------------------
    def test_18_booking_and_payment_not_called(self):
        """18. Booking và payment endpoint không bị gọi trong Phase 7.2."""
        async def _test():
            chatbot_svc = ChatbotService(llm_provider=MockLLMProviderForTest())
            async with AsyncSessionLocal() as session:
                initial_booking_count = (await session.execute(select(Booking))).scalars().all()

                await chatbot_svc.handle_message(
                    message="Tôi muốn giữ sân Đa Năng ngày 2026-10-15 lúc 19:00",
                    user_info={"id": 1, "role": "CUSTOMER"},
                    db=session
                )
                await chatbot_svc.handle_message(
                    message="Xác nhận",
                    user_info={"id": 1, "role": "CUSTOMER"},
                    db=session
                )

                # Count bookings in DB: MUST REMAIN UNCHANGED!
                after_booking_count = (await session.execute(select(Booking))).scalars().all()
                self.assertEqual(len(initial_booking_count), len(after_booking_count))
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 19: Phase 7.1 regression check
    # -------------------------------------------------------------------------
    def test_19_phase_7_1_regression_check(self):
        """19. Các API và test Phase 7.1 không bị regression."""
        async def _test():
            chatbot_svc = ChatbotService(llm_provider=MockLLMProviderForTest())
            async with AsyncSessionLocal() as session:
                # 1. Facility search
                res_search = await chatbot_svc.handle_message(message="Tìm sân ở Cầu Giấy", db=session)
                self.assertEqual(res_search["status"], "success")

                # 2. Availability query (read-only query from Phase 7.1)
                res_avail = await chatbot_svc.handle_message(message="Sân Đa Năng ngày 2026-10-15 lúc 19:00 còn trống không?", db=session)
                self.assertEqual(res_avail["status"], "success")
                self.assertIn("AVAILABLE", res_avail["answer"])

                # 3. Pricing query
                res_price = await chatbot_svc.handle_message(message="Giá thuê sân lúc 19:00 ngày 2026-10-15 là bao nhiêu?", db=session)
                self.assertEqual(res_price["status"], "success")
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 20: Cancellation/Expiry of pending intent NEVER releases another user's lock
    # -------------------------------------------------------------------------
    def test_20_cancellation_never_releases_other_user_lock(self):
        """20. Kiểm thử cancellation/expiry của pending intent không vô tình giải phóng lock thuộc về người khác."""
        async def _test():
            mgr = get_pending_hold_manager()

            # User 99 legally holds slot 999
            await acquire_slot_lock(slot_id=999, user_id=99, timeout_sec=600)
            self.assertEqual(await get_slot_lock_holder(999), "99")

            # User 1 creates a pending intent on a DIFFERENT or same slot, then cancels it
            intent = await mgr.create_pending_intent(
                user_id=1,
                slot_id=999,
                court_id=999,
                facility_id=999,
                facility_name="Sân Đa Năng",
                court_number="1",
                date="2026-10-15",
                start_time="19:00",
                end_time="20:00",
                price=100000.0
            )

            # User 1 cancels their pending intent
            cancelled = await mgr.cancel_pending_intent(intent["intent_id"], user_id=1)
            self.assertTrue(cancelled)

            # CRITICAL CHECK: Lock for slot 999 MUST STILL BELONG TO USER 99!
            holder_after = await get_slot_lock_holder(999)
            self.assertEqual(holder_after, "99", "Cancelling user 1's pending intent must NEVER release user 99's lock!")
        self.run_async(_test())


if __name__ == "__main__":
    unittest.main()
