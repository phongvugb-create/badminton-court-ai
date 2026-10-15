"""
BADMINTON.AI - PHASE 7.2.1 UNIT TEST SUITE: DISTRIBUTED PENDING STATE & REDIS HARDENING
Verifies:
1. Multi-worker & process restart simulation for pending intents.
2. Distributed atomic consume (anti-concurrency & anti-double-submit).
3. Anti-IDOR enforcement.
4. Anti-replay protection on consumed/expired intents.
5. Production fail-closed behavior when Redis is unavailable.
6. Safe reconciliation on ambiguous timeout / disconnect.
7. Lock release protection (never release another user's lock).
"""

import os
import sys
import time
import asyncio
import unittest
from unittest.mock import patch, AsyncMock, MagicMock

# Setup paths
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ROOT_DIR = os.path.abspath(os.path.join(BACKEND_DIR, ".."))
for p in [ROOT_DIR, BACKEND_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

from app.config import settings
from app.core import redis as redis_module
from app.core.redis import (
    acquire_slot_lock,
    release_slot_lock,
    get_slot_lock_holder,
    is_production,
    _in_memory_locks
)
from app.ai.tools.pending_hold_manager import (
    PendingHoldManager,
    get_pending_hold_manager,
    execute_slot_hold,
    _in_memory_intents,
    _in_memory_user_active
)
from app.core.database import AsyncSessionLocal


class TestPhase721DistributedHardening(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(cls.loop)
        async def _seed():
            from app.models.all_models import TimeSlot
            from sqlalchemy.future import select
            from sqlalchemy import text
            async with AsyncSessionLocal() as session:
                slot = (await session.execute(select(TimeSlot).where(TimeSlot.id == 999))).scalar_one_or_none()
                if not slot:
                    await session.execute(text("""
                        INSERT OR REPLACE INTO time_slots (id, court_id, date, start_time, end_time, status)
                        VALUES (999, 201, '2026-10-15', '19:00', '20:00', 'AVAILABLE')
                    """))
                    await session.commit()
        cls.loop.run_until_complete(_seed())

    @classmethod
    def tearDownClass(cls):
        cls.loop.close()

    def setUp(self):
        _in_memory_intents.clear()
        _in_memory_user_active.clear()
        _in_memory_locks.clear()
        # Reset settings environment to test/development
        settings.NODE_ENV = "development"

    def run_async(self, coro):
        return self.loop.run_until_complete(coro)

    # -------------------------------------------------------------------------
    # TEST 1: Multi-worker / Process restart simulation
    # -------------------------------------------------------------------------
    def test_01_process_restart_multi_worker_simulation(self):
        """1. Intent được tạo ở worker A có thể được truy xuất và xác nhận ở worker B."""
        async def _test():
            worker_a = PendingHoldManager(ttl_seconds=300)
            worker_b = PendingHoldManager(ttl_seconds=300)

            # Worker A creates intent
            intent = await worker_a.create_pending_intent(
                user_id=1,
                slot_id=999,
                court_id=999,
                facility_id=999,
                facility_name="Sân Cầu Lông Đa Năng",
                court_number="1",
                date="2026-10-15",
                start_time="19:00",
                end_time="20:00",
                price=80000.0
            )
            intent_id = intent["intent_id"]

            # Simulate worker B (shares storage)
            intent_from_b = await worker_b.get_pending_intent(intent_id)
            self.assertIsNotNone(intent_from_b)
            self.assertEqual(intent_from_b["slot_id"], 999)

            # Active intent lookup works across workers
            active_b = await worker_b.get_active_intent_for_user(1)
            self.assertIsNotNone(active_b)
            self.assertEqual(active_b["intent_id"], intent_id)
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 2: Concurrent consume calls -> only ONE passes (Atomic claim)
    # -------------------------------------------------------------------------
    def test_02_concurrent_consume_only_one_succeeds(self):
        """2. Hai request xác nhận đồng thời chỉ có đúng một request consume thành công."""
        async def _test():
            mgr = PendingHoldManager(ttl_seconds=300)
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
                price=80000.0
            )
            intent_id = intent["intent_id"]

            # Launch two concurrent consume calls
            res1, res2 = await asyncio.gather(
                mgr.consume_pending_intent(intent_id, 1),
                mgr.consume_pending_intent(intent_id, 1)
            )

            successes = [r for r in [res1, res2] if r[0] is True]
            failures = [r for r in [res1, res2] if r[0] is False]

            self.assertEqual(len(successes), 1, "Exactly one consume must succeed")
            self.assertEqual(len(failures), 1, "The competing request must be rejected")
            self.assertEqual(failures[0][2], "already_consumed")
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 3: Anti-IDOR protection
    # -------------------------------------------------------------------------
    def test_03_anti_idor_protection(self):
        """3. Người dùng khác không thể tiêu thụ intent của chủ sở hữu."""
        async def _test():
            mgr = PendingHoldManager(ttl_seconds=300)
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
                price=80000.0
            )
            intent_id = intent["intent_id"]

            # User 2 tries to consume User 1's intent
            ok, data, reason = await mgr.consume_pending_intent(intent_id, user_id=2)
            self.assertFalse(ok)
            self.assertEqual(reason, "permission_denied")
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 4: Anti-Replay on already consumed intent
    # -------------------------------------------------------------------------
    def test_04_anti_replay_on_consumed_intent(self):
        """4. Intent đã tiêu thụ không thể được sử dụng lại (Anti-replay)."""
        async def _test():
            mgr = PendingHoldManager(ttl_seconds=300)
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
                price=80000.0
            )
            intent_id = intent["intent_id"]

            # First consumption
            ok1, _, _ = await mgr.consume_pending_intent(intent_id, 1)
            self.assertTrue(ok1)

            # Replay consumption
            ok2, _, reason = await mgr.consume_pending_intent(intent_id, 1)
            self.assertFalse(ok2)
            self.assertEqual(reason, "already_consumed")
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 5: Expired intent rejected (TTL 300s)
    # -------------------------------------------------------------------------
    def test_05_expired_intent_rejected(self):
        """5. Intent hết hạn (TTL 300s) bị từ chối ngay lập tức."""
        async def _test():
            mgr = PendingHoldManager(ttl_seconds=300)
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
                price=80000.0,
                ttl_seconds=1  # 1 second TTL
            )
            intent_id = intent["intent_id"]

            # Force expiry
            intent["expires_at"] = time.time() - 10

            ok, _, reason = await mgr.consume_pending_intent(intent_id, 1)
            self.assertFalse(ok)
            self.assertEqual(reason, "pending_intent_expired")
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 6: Production Fail-Closed Enforcement
    # -------------------------------------------------------------------------
    def test_06_production_fail_closed_enforcement(self):
        """6. Trong môi trường production, nếu Redis mất kết nối thì fail-closed, không dùng in-memory."""
        async def _test():
            original_env = settings.NODE_ENV
            try:
                settings.NODE_ENV = "production"
                self.assertTrue(is_production())

                # With redis_client = None in production, acquire must raise ConnectionError
                with patch.object(redis_module, "redis_client", None):
                    with self.assertRaises(ConnectionError):
                        await acquire_slot_lock(slot_id=999, user_id=1, timeout_sec=600)

                    with self.assertRaises(ConnectionError):
                        await release_slot_lock(slot_id=999, user_id=1)

                    with self.assertRaises(ConnectionError):
                        await get_slot_lock_holder(slot_id=999)

                    # PendingHoldManager also fails closed
                    mgr = PendingHoldManager()
                    ok, _, reason = await mgr.consume_pending_intent("phi_fake", 1)
                    self.assertFalse(ok)
                    self.assertEqual(reason, "redis_unavailable")
            finally:
                settings.NODE_ENV = original_env
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 7: Safe Reconciliation on ambiguous timeout
    # -------------------------------------------------------------------------
    def test_07_safe_reconciliation_on_timeout(self):
        """7. Khi acquire lock gặp timeout nhưng lock thực tế đã được tạo cho user -> reconcile thành công."""
        async def _test():
            mgr = PendingHoldManager(ttl_seconds=300)
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
                price=80000.0
            )
            intent_id = intent["intent_id"]

            async with AsyncSessionLocal() as session:
                # Pre-set lock as if Redis created it just before the network timed out
                _in_memory_locks[f"slot_lock:999"] = (1, time.time() + 600)

                # Mock acquire_slot_lock to raise TimeoutError
                with patch("app.ai.tools.pending_hold_manager.acquire_slot_lock", side_effect=TimeoutError("Lock timeout")):
                    res = await execute_slot_hold(db=session, user_id=1, intent_id=intent_id)

                    # Reconciliation detected holder == '1', recovered safely!
                    self.assertEqual(res["status"], "hold_succeeded")
                    self.assertEqual(res["data"]["slot_id"], 999)
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 8: Safe Reconciliation when someone else took lock during timeout
    # -------------------------------------------------------------------------
    def test_08_safe_reconciliation_detects_competitor_lock(self):
        """8. Khi acquire lock timeout và reconciliation thấy user khác đang giữ -> slot_unavailable."""
        async def _test():
            mgr = PendingHoldManager(ttl_seconds=300)
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
                price=80000.0
            )
            intent_id = intent["intent_id"]

            async with AsyncSessionLocal() as session:
                # Someone else acquired the lock
                _in_memory_locks[f"slot_lock:999"] = (2, time.time() + 600)

                with patch("app.ai.tools.pending_hold_manager.acquire_slot_lock", side_effect=TimeoutError("Lock timeout")):
                    res = await execute_slot_hold(db=session, user_id=1, intent_id=intent_id)

                    self.assertEqual(res["status"], "slot_unavailable")
                    self.assertIn("khách hàng khác", res["message"])
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 9: Lock release cannot release another user's lock
    # -------------------------------------------------------------------------
    def test_09_cannot_release_other_user_lock(self):
        """9. Không giải phóng lock của người dùng khác."""
        async def _test():
            _in_memory_locks["slot_lock:999"] = (1, time.time() + 600)

            # User 2 tries to release user 1's lock
            released = await release_slot_lock(slot_id=999, user_id=2)
            self.assertFalse(released)

            # Lock still held by User 1
            holder = await get_slot_lock_holder(slot_id=999)
            self.assertEqual(holder, "1")

            # User 1 successfully releases
            own_released = await release_slot_lock(slot_id=999, user_id=1)
            self.assertTrue(own_released)

            holder_after = await get_slot_lock_holder(slot_id=999)
            self.assertIsNone(holder_after)
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 10: Cancellation does NOT release slot lock
    # -------------------------------------------------------------------------
    def test_10_cancellation_never_releases_slot_lock(self):
        """10. Hủy pending intent không bao giờ giải phóng slot lock trong Redis."""
        async def _test():
            mgr = PendingHoldManager(ttl_seconds=300)
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
                price=80000.0
            )
            intent_id = intent["intent_id"]

            # Another user has an active slot lock
            _in_memory_locks["slot_lock:999"] = (2, time.time() + 600)

            # User 1 cancels their pending intent
            cancelled = await mgr.cancel_pending_intent(intent_id, user_id=1)
            self.assertTrue(cancelled)

            # Slot lock must STILL belong to User 2!
            holder = await get_slot_lock_holder(slot_id=999)
            self.assertEqual(holder, "2")
        self.run_async(_test())


if __name__ == "__main__":
    unittest.main()
