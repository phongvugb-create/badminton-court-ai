"""
BADMINTON.AI - PHASE 7.2.1 INTEGRATION TEST SUITE: LIVE REDIS HARDENING
Tests distributed consistency, multi-worker safety, and atomic Lua primitives
against a live Redis server instance.

MANDATORY RULES:
1. Only real Redis servers are tested here. No in-memory mocks are used to fake a live pass.
2. If live Redis is unavailable, tests are cleanly marked BLOCKED / NOT TESTED with explicit reasons.
"""

import os
import sys
import time
import json
import asyncio
import unittest
from typing import Optional

# Setup path
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ROOT_DIR = os.path.abspath(os.path.join(BACKEND_DIR, ".."))
for p in [ROOT_DIR, BACKEND_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

from app.config import settings
from app.core import redis as redis_module
from app.core.redis import acquire_slot_lock, release_slot_lock, get_slot_lock_holder
from app.ai.tools.pending_hold_manager import (
    PendingHoldManager,
    get_pending_hold_manager,
    _in_memory_intents,
    _in_memory_user_active
)

try:
    import redis.asyncio as aioredis
    _HAS_AIOREDIS = True
except ImportError:
    aioredis = None
    _HAS_AIOREDIS = False


class TestPhase721LiveRedisIntegration(unittest.TestCase):
    """
    Integration tests for distributed Redis lock and pending intent state.
    Strictly verifies live Redis behaviors without using process-local memory.
    """

    @classmethod
    def setUpClass(cls):
        cls.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(cls.loop)

        # Check if live Redis is reachable
        cls.live_redis_client = None
        cls.is_live_redis_available = False
        cls.skip_reason = ""

        if not _HAS_AIOREDIS:
            cls.skip_reason = "BLOCKED: Python 'redis' library is not installed in the environment."
            return

        configured_url = getattr(settings, "REDIS_URL", "redis://127.0.0.1:6379/0")
        candidate_urls = [configured_url]
        if "127.0.0.1" not in configured_url and "localhost" not in configured_url:
            candidate_urls.append("redis://127.0.0.1:6379/0")

        last_err = None
        for url in candidate_urls:
            try:
                client = aioredis.from_url(url, decode_responses=True)
                pong = cls.loop.run_until_complete(asyncio.wait_for(client.ping(), timeout=1.5))
                if pong:
                    cls.live_redis_client = client
                    cls.is_live_redis_available = True
                    redis_module.redis_client = client
                    break
            except Exception as e:
                last_err = e

        if not cls.is_live_redis_available:
            masked_url = configured_url
            if "@" in masked_url and ":" in masked_url.split("@")[0]:
                parts = masked_url.split("@")
                masked_url = f"{parts[0].split(':')[0]}:***@{parts[1]}"
            cls.skip_reason = (
                f"BLOCKED / NOT TESTED: Live Redis server is unreachable at {masked_url} ({last_err}). "
                "Docker Desktop Linux daemon is not running on this host."
            )

    @classmethod
    def tearDownClass(cls):
        redis_module.redis_client = None
        if cls.live_redis_client:
            async def _cleanup():
                await cls.live_redis_client.close()
            cls.loop.run_until_complete(_cleanup())
        cls.loop.close()

    def setUp(self):
        if not self.is_live_redis_available:
            self.skipTest(self.skip_reason)

    def run_async(self, coro):
        return self.loop.run_until_complete(coro)

    # -------------------------------------------------------------------------
    # TEST 1: Worker A creates pending intent -> Worker B verifies it
    # -------------------------------------------------------------------------
    def test_01_worker_a_create_worker_b_verify(self):
        """1. Pending intent được tạo bởi worker A có thể được xác minh tại worker B."""
        async def _test():
            worker_a = PendingHoldManager(ttl_seconds=300)
            worker_b = PendingHoldManager(ttl_seconds=300)

            # Worker A creates intent
            intent = await worker_a.create_pending_intent(
                user_id=101,
                slot_id=5001,
                court_id=10,
                facility_id=1,
                facility_name="Sân Test Live",
                court_number="1",
                date="2026-10-15",
                start_time="18:00",
                end_time="19:00",
                price=80000.0
            )
            intent_id = intent["intent_id"]

            # Wipe local in-memory dicts to simulate separate worker processes
            _in_memory_intents.clear()
            _in_memory_user_active.clear()

            # Worker B retrieves directly from Redis
            retrieved = await worker_b.get_pending_intent(intent_id)
            self.assertIsNotNone(retrieved, "Worker B must read pending intent from shared Redis")
            self.assertEqual(retrieved["slot_id"], 5001)
            self.assertEqual(retrieved["user_id"], 101)

            # Cleanup
            await self.live_redis_client.delete(f"pending_hold:{intent_id}")
            await self.live_redis_client.delete("user_pending_hold:101")
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 2: Concurrent confirmation requests -> only ONE consumes intent
    # -------------------------------------------------------------------------
    def test_02_concurrent_confirmations_only_one_consumes(self):
        """2. Hai confirmation request đồng thời chỉ có một request consume thành công."""
        async def _test():
            mgr = PendingHoldManager(ttl_seconds=300)
            intent = await mgr.create_pending_intent(
                user_id=102,
                slot_id=5002,
                court_id=10,
                facility_id=1,
                facility_name="Sân Test Live",
                court_number="2",
                date="2026-10-15",
                start_time="19:00",
                end_time="20:00",
                price=80000.0
            )
            intent_id = intent["intent_id"]

            # Two concurrent calls to consume_pending_intent
            res1, res2 = await asyncio.gather(
                mgr.consume_pending_intent(intent_id=intent_id, user_id=102),
                mgr.consume_pending_intent(intent_id=intent_id, user_id=102)
            )

            successes = [r for r in [res1, res2] if r[0] is True]
            failures = [r for r in [res1, res2] if r[0] is False]

            self.assertEqual(len(successes), 1, "Exactly one confirmation must succeed atomically")
            self.assertEqual(len(failures), 1, "The second confirmation must be rejected")
            self.assertEqual(failures[0][2], "already_consumed")

            # Cleanup
            await self.live_redis_client.delete(f"pending_hold:{intent_id}")
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 3: Competing users for same slot -> only ONE Redis lock granted
    # -------------------------------------------------------------------------
    def test_03_competing_users_same_slot_one_lock(self):
        """3. Hai user cạnh tranh cùng một slot chỉ có một Redis lock hợp lệ."""
        async def _test():
            slot_id = 9999
            await self.live_redis_client.delete(f"slot_lock:{slot_id}")

            lock1, lock2 = await asyncio.gather(
                acquire_slot_lock(slot_id=slot_id, user_id=201, timeout_sec=600),
                acquire_slot_lock(slot_id=slot_id, user_id=202, timeout_sec=600)
            )

            # Exactly one acquired
            self.assertTrue((lock1 and not lock2) or (lock2 and not lock1))

            holder = await get_slot_lock_holder(slot_id)
            self.assertIn(holder, ["201", "202"])

            # Cleanup
            await self.live_redis_client.delete(f"slot_lock:{slot_id}")
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 4: Lock has correct TTL
    # -------------------------------------------------------------------------
    def test_04_lock_ttl_configured_properly(self):
        """4. Lock có TTL đúng theo cấu hình (600s)."""
        async def _test():
            slot_id = 8888
            await self.live_redis_client.delete(f"slot_lock:{slot_id}")

            success = await acquire_slot_lock(slot_id=slot_id, user_id=301, timeout_sec=600)
            self.assertTrue(success)

            ttl = await self.live_redis_client.ttl(f"slot_lock:{slot_id}")
            self.assertGreater(ttl, 580)
            self.assertLessEqual(ttl, 600)

            # Cleanup
            await self.live_redis_client.delete(f"slot_lock:{slot_id}")
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 5: Cannot overwrite lock held by another user
    # -------------------------------------------------------------------------
    def test_05_cannot_overwrite_existing_lock(self):
        """5. Không ghi đè lock hiện thuộc user khác."""
        async def _test():
            slot_id = 7777
            await self.live_redis_client.delete(f"slot_lock:{slot_id}")

            first_lock = await acquire_slot_lock(slot_id=slot_id, user_id=401, timeout_sec=600)
            self.assertTrue(first_lock)

            second_lock = await acquire_slot_lock(slot_id=slot_id, user_id=402, timeout_sec=600)
            self.assertFalse(second_lock)

            holder = await get_slot_lock_holder(slot_id)
            self.assertEqual(holder, "401")

            # Cleanup
            await self.live_redis_client.delete(f"slot_lock:{slot_id}")
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 6: Cannot release lock of another user (Lua script check)
    # -------------------------------------------------------------------------
    def test_06_cannot_release_other_user_lock(self):
        """6. Không giải phóng lock của user khác."""
        async def _test():
            slot_id = 6666
            await self.live_redis_client.delete(f"slot_lock:{slot_id}")

            await acquire_slot_lock(slot_id=slot_id, user_id=501, timeout_sec=600)

            # User 502 tries to release user 501's lock
            released = await release_slot_lock(slot_id=slot_id, user_id=502)
            self.assertFalse(released)

            # Lock must still belong to 501
            holder = await get_slot_lock_holder(slot_id)
            self.assertEqual(holder, "501")

            # User 501 releases their own lock
            own_release = await release_slot_lock(slot_id=slot_id, user_id=501)
            self.assertTrue(own_release)

            holder_after = await get_slot_lock_holder(slot_id)
            self.assertIsNone(holder_after)
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 7: Redis error/disconnect not misconstrued as hold success
    # -------------------------------------------------------------------------
    def test_07_redis_error_returns_unverified(self):
        """7. Redis disconnect/timeout không bị hiểu nhầm thành thao tác thành công."""
        async def _test():
            slot_id = 5555
            # Simulate broken Redis by pointing to invalid port
            bad_client = aioredis.from_url("redis://127.0.0.1:9999/0", socket_connect_timeout=0.1)
            redis_module.redis_client = bad_client
            try:
                with self.assertRaises(Exception):
                    await acquire_slot_lock(slot_id=slot_id, user_id=601, timeout_sec=600)
            finally:
                redis_module.redis_client = self.live_redis_client
                await bad_client.close()
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 8: State does not rely on single process in-memory dict
    # -------------------------------------------------------------------------
    def test_08_no_dependency_on_single_process_dict(self):
        """8. Kết quả không phụ thuộc dictionary in-memory của một process."""
        async def _test():
            mgr = PendingHoldManager(ttl_seconds=300)
            intent = await mgr.create_pending_intent(
                user_id=701,
                slot_id=5003,
                court_id=10,
                facility_id=1,
                facility_name="Sân Test Live",
                court_number="3",
                date="2026-10-15",
                start_time="20:00",
                end_time="21:00",
                price=80000.0
            )
            intent_id = intent["intent_id"]

            # Completely clear all in-memory state
            _in_memory_intents.clear()
            _in_memory_user_active.clear()

            # Active intent lookup for user 701 still resolves from Redis!
            active = await mgr.get_active_intent_for_user(701)
            self.assertIsNotNone(active)
            self.assertEqual(active["intent_id"], intent_id)

            # Consume succeeds directly from Redis
            ok, consumed, _ = await mgr.consume_pending_intent(intent_id, 701)
            self.assertTrue(ok)
            self.assertEqual(consumed["status"], "CONSUMED")

            # Cleanup
            await self.live_redis_client.delete(f"pending_hold:{intent_id}")
        self.run_async(_test())


if __name__ == "__main__":
    unittest.main()
