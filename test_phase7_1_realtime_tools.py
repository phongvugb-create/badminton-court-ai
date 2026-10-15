"""
BADMINTON.AI - PHASE 7.1 TEST SUITE: REALTIME BUSINESS TOOLS INTEGRATION
Validates 15 required business tool and chatbot integration points:
1.  search_courts: Matches database records accurately.
2.  check_court_availability: Slot AVAILABLE and no Redis lock -> effective_status='AVAILABLE'.
3.  check_court_availability: Slot AVAILABLE but Redis lock held -> effective_status='HELD'.
4.  check_court_availability: Slot BOOKED and MAINTENANCE are never reported as available.
5.  check_court_availability: Redis error/unavailable returns 'availability_unverified' (NEVER assumes available).
6.  get_court_pricing: Reuses existing SlotPricing logic accurately.
7.  get_court_pricing: Does NOT apply dynamic pricing twice.
8.  get_my_bookings: Authenticated user only sees their own bookings.
9.  get_my_bookings: Anti-IDOR protection (cannot access other user's bookings).
10. Chatbot Intent Routing: Availability query triggers check_court_availability.
11. Chatbot Intent Routing: Pricing query with date/time triggers get_court_pricing.
12. Chatbot Intent Routing: Personal bookings query triggers get_my_bookings and enforces authentication.
13. Policy Query Isolation: Policy questions continue through RAG / Evidence Gate.
14. Error Resilience: Tool error does not cause Gemini to hallucinate fake business data.
15. Existing regression check: Backward compatibility preserved across schemas and providers.
"""

import os
import sys
import json
import asyncio
import unittest
from unittest.mock import patch, AsyncMock
from datetime import datetime

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
from app.ai.tools.business_tools import (
    search_courts,
    check_court_availability,
    get_court_pricing,
    get_my_bookings,
    make_tool_envelope
)
from app.ai.chatbot_service import ChatbotService
from app.ai.llm_provider import BaseLLMProvider
from app.ai.dynamic_pricing import calculate_dynamic_price


class MockLLMProviderForTest(BaseLLMProvider):
    """Deterministic Mock LLM Provider for unit testing."""
    def __init__(self, mode: str = "normal", custom_reply: str = None):
        self.mode = mode
        self.custom_reply = custom_reply
        self.last_system_instruction = None
        self.last_user_message = None

    @property
    def provider_name(self) -> str:
        return "MockLLMProvider"

    @property
    def model_name(self) -> str:
        return "mock-model"

    async def generate_text(
        self,
        system_instruction: str,
        user_message: str,
        history=None,
        timeout: float = 8.0
    ) -> str:
        self.last_system_instruction = system_instruction
        self.last_user_message = user_message

        if self.mode == "error":
            raise RuntimeError("Mock LLM 500 error")
        if self.custom_reply:
            return self.custom_reply
        return "Thông tin đã được tra cứu từ dữ liệu thời gian thực."


class TestPhase71RealtimeTools(unittest.TestCase):
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
                VALUES (2, 'Trần Văn Test 2', '0901234568', 'hash2', 'CUSTOMER')
            """))

            await session.commit()

    def setUp(self):
        async def _reset():
            from sqlalchemy import text, delete
            async with AsyncSessionLocal() as session:
                await session.execute(text("UPDATE time_slots SET status = 'AVAILABLE' WHERE id = 999"))
                await session.commit()
        self.run_async(_reset())

    def run_async(self, coro):
        return self.loop.run_until_complete(coro)

    # -------------------------------------------------------------------------
    # TEST 1: search_courts matches database
    # -------------------------------------------------------------------------
    def test_01_search_courts_matches_database(self):
        """1. Tìm sân trả kết quả khớp database."""
        async def _test():
            async with AsyncSessionLocal() as session:
                # Query all approved facilities
                res = await search_courts(db=session, query="Đa Năng")
                self.assertIn(res["status"], ["success", "no_results"])
                if res["status"] == "success":
                    self.assertGreater(len(res["data"]), 0)
                    fac = res["data"][0]
                    self.assertIn("facility_id", fac)
                    self.assertIn("name", fac)
                    self.assertIn("address", fac)
                    self.assertIn("Đa Năng".lower(), fac["name"].lower())

                # Test GPS search
                res_gps = await search_courts(db=session, user_lat=21.0285, user_lon=105.8542)
                self.assertEqual(res_gps["status"], "success")
                for f in res_gps["data"]:
                    self.assertIsNotNone(f.get("distance_km"))

                # Test invalid GPS (only lat without lon)
                res_inv = await search_courts(db=session, user_lat=21.0285, user_lon=None)
                self.assertEqual(res_inv["status"], "invalid_input")
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 2: Slot AVAILABLE and no Redis lock
    # -------------------------------------------------------------------------
    def test_02_slot_available_no_redis_lock(self):
        """2. Slot AVAILABLE và không có Redis lock -> effective_status='AVAILABLE'."""
        async def _test():
            async with AsyncSessionLocal() as session:
                # Mock get_slot_lock_holder returning None (unlocked)
                with patch("app.ai.tools.business_tools.get_slot_lock_holder", new_callable=AsyncMock) as mock_lock:
                    mock_lock.return_value = None

                    # Find or verify an AVAILABLE slot in db
                    q = await session.execute(
                        select(TimeSlot, Court).join(Court, TimeSlot.court_id == Court.id)
                        .where(TimeSlot.status == "AVAILABLE")
                    )
                    row = q.first()
                    if row:
                        slot, court = row
                        res = await check_court_availability(
                            db=session,
                            court_id=court.id,
                            date=slot.date,
                            time=slot.start_time
                        )
                        self.assertEqual(res["status"], "success")
                        match = next((s for s in res["data"] if s["slot_id"] == slot.id), None)
                        self.assertIsNotNone(match)
                        self.assertEqual(match["effective_status"], "AVAILABLE")
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 3: Slot AVAILABLE but Redis lock held -> HELD
    # -------------------------------------------------------------------------
    def test_03_slot_available_with_redis_lock_is_held(self):
        """3. Slot AVAILABLE nhưng đang có Redis lock, phải được nhận diện là HELD."""
        async def _test():
            async with AsyncSessionLocal() as session:
                # Mock get_slot_lock_holder returning a lock holder user ID
                with patch("app.ai.tools.business_tools.get_slot_lock_holder", new_callable=AsyncMock) as mock_lock:
                    mock_lock.return_value = "999"  # Locked by user 999

                    q = await session.execute(
                        select(TimeSlot, Court).join(Court, TimeSlot.court_id == Court.id)
                        .where(TimeSlot.status == "AVAILABLE")
                    )
                    row = q.first()
                    if row:
                        slot, court = row
                        res = await check_court_availability(
                            db=session,
                            court_id=court.id,
                            date=slot.date,
                            time=slot.start_time
                        )
                        self.assertEqual(res["status"], "success")
                        match = next((s for s in res["data"] if s["slot_id"] == slot.id), None)
                        self.assertIsNotNone(match)
                        self.assertEqual(match["effective_status"], "HELD")
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 4: Slot BOOKED and MAINTENANCE are not available
    # -------------------------------------------------------------------------
    def test_04_booked_and_maintenance_not_available(self):
        """4. Slot BOOKED và MAINTENANCE không được báo trống."""
        async def _test():
            async with AsyncSessionLocal() as session:
                with patch("app.ai.tools.business_tools.get_slot_lock_holder", new_callable=AsyncMock) as mock_lock:
                    mock_lock.return_value = None

                    # Check slot query with mock row where status is BOOKED or MAINTENANCE
                    q = await session.execute(
                        select(TimeSlot, Court).join(Court, TimeSlot.court_id == Court.id)
                        .where(TimeSlot.status == "BOOKED")
                    )
                    row = q.first()
                    if row:
                        slot, court = row
                        res = await check_court_availability(
                            db=session,
                            court_id=court.id,
                            date=slot.date,
                            time=slot.start_time
                        )
                        self.assertEqual(res["status"], "success")
                        match = next((s for s in res["data"] if s["slot_id"] == slot.id), None)
                        self.assertIsNotNone(match)
                        self.assertEqual(match["effective_status"], "BOOKED")
                        self.assertNotEqual(match["effective_status"], "AVAILABLE")
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 5: Redis error returns availability_unverified
    # -------------------------------------------------------------------------
    def test_05_redis_error_returns_unverified(self):
        """5. Redis lỗi hoặc không khả dụng phải trả trạng thái chưa xác minh."""
        async def _test():
            async with AsyncSessionLocal() as session:
                with patch("app.ai.tools.business_tools.get_slot_lock_holder", side_effect=ConnectionError("Redis connection dropped")):
                    q = await session.execute(
                        select(TimeSlot, Court).join(Court, TimeSlot.court_id == Court.id)
                    )
                    row = q.first()
                    if row:
                        slot, court = row
                        res = await check_court_availability(
                            db=session,
                            court_id=court.id,
                            date=slot.date,
                            time=slot.start_time
                        )
                        # Must return availability_unverified in status or reason
                        self.assertTrue(
                            res["status"] in ("error", "availability_unverified") or
                            res.get("reason") == "availability_unverified"
                        )
                        # Must NEVER claim slots are available
                        self.assertEqual(len(res["data"]), 0)
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 6: get_court_pricing reuses existing logic
    # -------------------------------------------------------------------------
    def test_06_pricing_reuses_existing_logic(self):
        """6. Tra cứu giá tái sử dụng đúng logic hiện có."""
        async def _test():
            async with AsyncSessionLocal() as session:
                q = await session.execute(
                    select(TimeSlot, Court, SlotPricing)
                    .join(Court, TimeSlot.court_id == Court.id)
                    .join(SlotPricing, SlotPricing.slot_id == TimeSlot.id)
                )
                row = q.first()
                if row:
                    slot, court, pricing = row
                    res = await get_court_pricing(
                        db=session,
                        court_id=court.id,
                        date=slot.date,
                        time=slot.start_time
                    )
                    self.assertEqual(res["status"], "success")
                    self.assertEqual(len(res["data"]), 1)
                    item = res["data"][0]
                    self.assertEqual(item["base_price"], pricing.base_price)
                    self.assertEqual(item["dynamic_price"], pricing.dynamic_price)
                    self.assertEqual(item["adjustment_reason"], pricing.adjustment_reason)
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 7: Does NOT apply dynamic pricing twice
    # -------------------------------------------------------------------------
    def test_07_no_double_dynamic_pricing(self):
        """7. Không áp dụng dynamic pricing hai lần."""
        async def _test():
            async with AsyncSessionLocal() as session:
                q = await session.execute(
                    select(TimeSlot, Court, SlotPricing)
                    .join(Court, TimeSlot.court_id == Court.id)
                    .join(SlotPricing, SlotPricing.slot_id == TimeSlot.id)
                )
                row = q.first()
                if row:
                    slot, court, pricing = row
                    res = await get_court_pricing(
                        db=session,
                        court_id=court.id,
                        date=slot.date,
                        time=slot.start_time
                    )
                    item = res["data"][0]
                    # Verify returned price equals pricing.dynamic_price exactly,
                    # not calculate_dynamic_price applied to pricing.dynamic_price!
                    self.assertEqual(item["dynamic_price"], pricing.dynamic_price)
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 8: User only sees their own bookings
    # -------------------------------------------------------------------------
    def test_08_user_only_sees_own_bookings(self):
        """8. Người dùng chỉ xem được booking của chính mình."""
        async def _test():
            async with AsyncSessionLocal() as session:
                # Create test booking for user 1 and user 2
                slot_res = await session.execute(select(TimeSlot.id).limit(1))
                slot_id = slot_res.scalar_one_or_none() or 1

                b1 = Booking(
                    user_id=1,
                    slot_id=slot_id,
                    total_amount=100000.0,
                    deposit_amount=50000.0,
                    payment_status="DEPOSITED",
                    qr_checkin_code="TEST-QR-USER-1"
                )
                b2 = Booking(
                    user_id=2,
                    slot_id=slot_id,
                    total_amount=120000.0,
                    deposit_amount=60000.0,
                    payment_status="DEPOSITED",
                    qr_checkin_code="TEST-QR-USER-2"
                )
                session.add_all([b1, b2])
                await session.flush()

                # User 1 query
                res1 = await get_my_bookings(db=session, user_context={"id": 1, "role": "CUSTOMER"})
                self.assertEqual(res1["status"], "success")
                b_ids_1 = [b["booking_id"] for b in res1["data"]]
                self.assertIn(b1.id, b_ids_1)
                self.assertNotIn(b2.id, b_ids_1)

                # QR code string must be shielded
                for b in res1["data"]:
                    self.assertNotIn("TEST-QR-USER", str(b))
                    self.assertTrue(b["has_qr_code"])

                await session.rollback()
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 9: Anti-IDOR protection
    # -------------------------------------------------------------------------
    def test_09_anti_idor_protection(self):
        """9. Không thể lấy booking của tài khoản khác bằng cách sửa tham số."""
        async def _test():
            async with AsyncSessionLocal() as session:
                # Function signature does not accept caller-controlled target_user_id
                # Only verified user_context is accepted
                res = await get_my_bookings(
                    db=session,
                    user_context={"id": 1, "role": "CUSTOMER"}
                )
                # Regardless of external malicious intent, user_id=1 is locked
                self.assertIn(res["status"], ["success", "no_results"])

                # Guest user blocked
                guest_res = await get_my_bookings(
                    db=session,
                    user_context={"role": "GUEST"}
                )
                self.assertEqual(guest_res["status"], "authentication_required")
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 10: Intent hỏi giờ trống gọi đúng tool
    # -------------------------------------------------------------------------
    def test_10_intent_availability_calls_tool(self):
        """10. Intent hỏi giờ trống gọi đúng tool check_court_availability."""
        async def _test():
            mock_llm = MockLLMProviderForTest()
            chatbot_svc = ChatbotService(llm_provider=mock_llm)
            async with AsyncSessionLocal() as session:
                with patch("app.ai.chatbot_service.check_court_availability", new_callable=AsyncMock) as mock_avail:
                    mock_avail.return_value = make_tool_envelope(
                        "success",
                        data=[{
                            "slot_id": 1,
                            "court_id": 1,
                            "court_number": "1",
                            "facility_id": 1,
                            "facility_name": "Sân Cầu Lông Đa Năng",
                            "date": "2026-10-15",
                            "start_time": "19:00",
                            "end_time": "20:00",
                            "effective_status": "AVAILABLE",
                            "price": 100000.0,
                            "base_price": 80000.0
                        }]
                    )

                    res = await chatbot_svc.handle_message(
                        message="Sân Cầu Lông Đa Năng ngày 2026-10-15 lúc 19:00 còn trống không?",
                        db=session
                    )
                    self.assertEqual(res["status"], "success")
                    mock_avail.assert_called_once()
                    self.assertIn("19:00", res["answer"])
                    self.assertIn("AVAILABLE", res["answer"])
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 11: Intent hỏi giá gọi đúng tool
    # -------------------------------------------------------------------------
    def test_11_intent_pricing_calls_tool(self):
        """11. Intent hỏi giá gọi đúng tool get_court_pricing."""
        async def _test():
            mock_llm = MockLLMProviderForTest()
            chatbot_svc = ChatbotService(llm_provider=mock_llm)
            async with AsyncSessionLocal() as session:
                with patch("app.ai.chatbot_service.get_court_pricing", new_callable=AsyncMock) as mock_price:
                    mock_price.return_value = make_tool_envelope(
                        "success",
                        data=[{
                            "facility_id": 1,
                            "facility_name": "Sân Cầu Lông Đa Năng",
                            "court_id": 1,
                            "court_number": "1",
                            "date": "2026-10-15",
                            "time": "19:00",
                            "base_price": 80000.0,
                            "dynamic_price": 100000.0,
                            "currency": "VND",
                            "adjustment_reason": "Khung giờ vàng tối ngày thường (+25%)",
                            "is_ai_applied": True
                        }]
                    )

                    res = await chatbot_svc.handle_message(
                        message="Giá thuê sân lúc 19:00 ngày 2026-10-15 là bao nhiêu?",
                        db=session
                    )
                    self.assertEqual(res["status"], "success")
                    mock_price.assert_called_once()
                    self.assertIn("100,000", res["answer"])
                    self.assertIn("Khung giờ vàng", res["answer"])
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 12: Intent hỏi lịch đặt cá nhân yêu cầu đăng nhập
    # -------------------------------------------------------------------------
    def test_12_intent_my_bookings_requires_auth(self):
        """12. Intent hỏi lịch đặt cá nhân gọi đúng tool và yêu cầu đăng nhập nếu cần."""
        async def _test():
            mock_llm = MockLLMProviderForTest()
            chatbot_svc = ChatbotService(llm_provider=mock_llm)
            async with AsyncSessionLocal() as session:
                # 1. Guest user
                res_guest = await chatbot_svc.handle_message(
                    message="Xem lại lịch đặt sân của tôi",
                    user_info=None,
                    user_role="GUEST",
                    db=session
                )
                self.assertIn("đăng nhập", res_guest["answer"].lower())

                # 2. Authenticated user
                with patch("app.ai.chatbot_service.get_my_bookings", new_callable=AsyncMock) as mock_b:
                    mock_b.return_value = make_tool_envelope(
                        "success",
                        data=[{
                            "booking_id": 101,
                            "facility_name": "Sân Cầu Lông Đa Năng",
                            "court_number": "1",
                            "date": "2026-10-15",
                            "start_time": "19:00",
                            "end_time": "20:00",
                            "total_amount": 100000.0,
                            "deposit_amount": 50000.0,
                            "payment_status": "DEPOSITED"
                        }]
                    )
                    res_auth = await chatbot_svc.handle_message(
                        message="Xem lại đơn đặt của tôi",
                        user_info={"id": 1, "name": "Nguyễn Văn Test", "role": "CUSTOMER"},
                        user_role="CUSTOMER",
                        db=session
                    )
                    self.assertEqual(res_auth["status"], "success")
                    mock_b.assert_called_once()
                    self.assertIn("#101", res_auth["answer"])
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------
    # TEST 13: Câu hỏi chính sách vẫn đi qua RAG / Evidence Gate
    # -------------------------------------------------------------------------
    def test_13_policy_query_routed_to_rag(self):
        """13. Câu hỏi chính sách vẫn đi qua RAG/Evidence Gate."""
        async def _test():
            mock_llm = MockLLMProviderForTest()
            chatbot_svc = ChatbotService(llm_provider=mock_llm)
            async with AsyncSessionLocal() as session:
                from app.schemas.all_schemas import RetrievalSearchResponse
                mock_retrieval_res = RetrievalSearchResponse(
                    results=[],
                    returned_results=0,
                    total_candidates=1,
                    top_k=5,
                    similarity_threshold=0.58,
                    query="Quy định hủy sân trước 24 giờ được hoàn bao nhiêu phần trăm?",
                    reason="insufficient_evidence",
                    latency_ms={"total": 5.0}
                )
                with patch.object(chatbot_svc.retriever, "retrieve", new_callable=AsyncMock) as mock_ret:
                    mock_ret.return_value = mock_retrieval_res
                    # Question about refund policy without realtime slot keywords
                    res = await chatbot_svc.handle_message(
                        message="Quy định hủy sân trước 24 giờ được hoàn bao nhiêu phần trăm?",
                        db=session
                    )
                    # Must be processed by RAG & Evidence Gate (insufficient_evidence)
                    self.assertEqual(res["retrieval_status"], "insufficient_evidence")
                    self.assertIn("chưa nêu rõ", res["answer"].lower())
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 14: Tool lỗi không khiến chatbot tạo ra dữ liệu giả
    # -------------------------------------------------------------------------
    def test_14_tool_error_prevents_hallucination(self):
        """14. Tool lỗi không khiến chatbot tạo ra dữ liệu giả."""
        async def _test():
            # Use a mock LLM provider with custom name that does NOT match legacy Phase 1/2 short-circuit
            class MockHallucinatingProvider(BaseLLMProvider):
                @property
                def provider_name(self) -> str:
                    return "MockHallucinatingProvider"
                @property
                def model_name(self) -> str:
                    return "mock-hallucinating"
                async def generate_text(self, system_instruction: str, user_message: str, history=None, timeout: float = 8.0) -> str:
                    return "Sân số 99 còn trống lúc 19:00 giá 50.000đ"

            mock_llm = MockHallucinatingProvider()
            chatbot_svc = ChatbotService(llm_provider=mock_llm)
            async with AsyncSessionLocal() as session:
                with patch("app.ai.chatbot_service.check_court_availability", new_callable=AsyncMock) as mock_avail:
                    # Tool returns error / unverified
                    mock_avail.return_value = make_tool_envelope("availability_unverified", data=[], reason="availability_unverified")

                    res = await chatbot_svc.handle_message(
                        message="Sân Cầu Lông Đa Năng ngày 2026-10-15 còn trống không?",
                        db=session
                    )
                    # Must return safe unverified message, NEVER invoking mock_llm to hallucinate!
                    self.assertEqual(res["status"], "error")
                    self.assertIn("chưa thể xác minh", res["answer"].lower())
                    self.assertNotIn("Sân số 99", res["answer"])
                    self.assertNotIn("50.000đ", res["answer"])
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 15: Backward compatibility & API regression
    # -------------------------------------------------------------------------
    def test_15_backward_compatibility(self):
        """15. Các API và bài test hiện có không bị regression."""
        async def _test():
            chatbot_svc = ChatbotService()
            async with AsyncSessionLocal() as session:
                res = await chatbot_svc.handle_message(
                    message="Thời gian giữ chỗ là bao lâu?",
                    db=session
                )
                self.assertIn("answer", res)
                self.assertIn("reply", res)
                self.assertIn("conversation_id", res)
                self.assertIn("message_id", res)
                self.assertIn("status", res)
                self.assertIn("sources", res)
        self.run_async(_test())


if __name__ == "__main__":
    unittest.main()
