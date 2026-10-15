"""
BADMINTON.AI - PENDING HOLD INTENT MANAGER (PHASE 7.2.1)
Manages ephemeral, verifiable distributed pending hold intents before user confirmation.

KEY SECURITY & DISTRIBUTED PRINCIPLES:
1. Preview generation creates ONLY a pending intent in Redis / shared storage; it NEVER creates
   a Redis slot lock, NEVER mutates TimeSlot, and NEVER creates a Booking.
2. Distributed Atomic Consistency: Transition from 'PENDING' -> 'CONSUMED' is executed via
   an atomic Redis Lua script. Concurrent requests across multiple workers cannot both consume.
3. Multi-Worker & Process Restart Resilient: State is stored in Redis with TTL 300s, accessible
   by any worker or after server restart.
4. Anti-IDOR: Intent ownership is verified inside the atomic operation against authenticated user_id.
5. Anti-Replay: Consumed intents retain a 300s tombstone state so retried/replayed requests receive
   explicit rejection.
6. Fail-Closed in Production: If Redis is unavailable in production, operations are rejected
   (availability_unverified) rather than splitting-brain into unshared in-memory dicts.
7. Safe Reconciliation: If lock acquisition fails or times out, state is reconciled via holder check.
"""

import time
import uuid
import json
import asyncio
import logging
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core import redis as redis_core
from app.core.redis import (
    acquire_slot_lock,
    release_slot_lock,
    get_slot_lock_holder,
    is_production
)
from app.models.all_models import TimeSlot, Court, Facility, SlotPricing

def _get_redis_client():
    return getattr(redis_core, "redis_client", None)

def __getattr__(name):
    if name == "redis_client":
        return getattr(redis_core, "redis_client", None)
    raise AttributeError(f"module {__name__} has no attribute {name}")


logger = logging.getLogger("pending_hold_manager")

# Lua script for distributed atomic consumption of pending hold intents
# KEYS[1]: pending_hold:{intent_id}
# KEYS[2]: user_pending_hold:{user_id}
# ARGV[1]: user_id
# ARGV[2]: now_timestamp
# ARGV[3]: consumed_retention_ttl_seconds
LUA_CONSUME_INTENT = """
local raw = redis.call("get", KEYS[1])
if not raw then
    return {0, "pending_intent_expired"}
end

local data = cjson.decode(raw)
if tostring(data.user_id) ~= tostring(ARGV[1]) then
    return {0, "permission_denied"}
end

if data.status == "CONSUMED" then
    return {0, "already_consumed"}
end

if data.status ~= "PENDING" then
    return {0, "invalid_status_" .. tostring(data.status)}
end

local now_ts = tonumber(ARGV[2])
if tonumber(data.expires_at) < now_ts then
    return {0, "pending_intent_expired"}
end

data.status = "CONSUMED"
data.consumed_at = now_ts
local new_raw = cjson.encode(data)

redis.call("set", KEYS[1], new_raw, "EX", tonumber(ARGV[3]))
redis.call("del", KEYS[2])

return {1, new_raw}
"""

# Lua script for distributed cancellation
# KEYS[1]: pending_hold:{intent_id}
# KEYS[2]: user_pending_hold:{user_id}
# ARGV[1]: user_id
LUA_CANCEL_INTENT = """
local raw = redis.call("get", KEYS[1])
if not raw then
    return 0
end
local data = cjson.decode(raw)
if tostring(data.user_id) ~= tostring(ARGV[1]) then
    return 0
end
data.status = "CANCELLED"
local new_raw = cjson.encode(data)
redis.call("set", KEYS[1], new_raw, "EX", 60)
redis.call("del", KEYS[2])
return 1
"""

# In-memory storage and mutex fallback for local development and unit tests
_in_memory_intents: Dict[str, Dict[str, Any]] = {}
_in_memory_user_active: Dict[int, str] = {}
_in_memory_mutex = asyncio.Lock()


class PendingHoldManager:
    """Manages pending hold intent lifecycle with distributed Redis and local fallback."""

    def __init__(self, ttl_seconds: int = 300):
        self.default_ttl = ttl_seconds

    async def create_pending_intent(
        self,
        user_id: int,
        slot_id: int,
        court_id: int,
        facility_id: int,
        facility_name: str,
        court_number: str,
        date: str,
        start_time: str,
        end_time: str,
        price: float,
        ttl_seconds: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Creates an ephemeral pending hold intent (PREVIEW ONLY).
        DOES NOT acquire any Redis lock or mutate DB records.
        """
        effective_ttl = ttl_seconds or self.default_ttl
        now = time.time()
        intent_id = f"phi_{uuid.uuid4().hex}"

        intent_data = {
            "intent_id": intent_id,
            "user_id": int(user_id),
            "slot_id": int(slot_id),
            "court_id": int(court_id),
            "facility_id": int(facility_id),
            "facility_name": facility_name,
            "court_number": str(court_number),
            "date": date,
            "start_time": start_time,
            "end_time": end_time,
            "price": float(price),
            "created_at": now,
            "expires_at": now + effective_ttl,
            "status": "PENDING"
        }

        # In production, require live Redis
        r_client = _get_redis_client()
        if is_production() and not r_client:
            raise ConnectionError("Redis is required in production environment.")

        # Always persist to Redis when available
        if r_client:
            try:
                await r_client.set(
                    f"pending_hold:{intent_id}",
                    json.dumps(intent_data),
                    ex=effective_ttl
                )
                await r_client.set(
                    f"user_pending_hold:{user_id}",
                    intent_id,
                    ex=effective_ttl
                )
            except Exception as e:
                logger.warning(f"[PendingHoldManager] Redis save failed: {e}")
                if is_production():
                    raise ConnectionError(f"Failed to persist intent to Redis in production: {e}")

        # In-memory storage for dev/test
        async with _in_memory_mutex:
            _in_memory_intents[intent_id] = intent_data
            _in_memory_user_active[int(user_id)] = intent_id

        logger.info(f"[PendingHoldManager] Created pending intent {intent_id} for user {user_id}, slot {slot_id}")
        return intent_data

    async def get_pending_intent(self, intent_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves pending intent by ID and validates expiry."""
        if not intent_id:
            return None

        intent = None
        r_client = _get_redis_client()
        if r_client:
            try:
                raw = await r_client.get(f"pending_hold:{intent_id}")
                if raw:
                    intent = json.loads(raw)
            except Exception as e:
                logger.warning(f"[PendingHoldManager] Redis get error: {e}")

        if not intent:
            async with _in_memory_mutex:
                intent = _in_memory_intents.get(intent_id)

        if not intent:
            return None

        # Check TTL
        if time.time() > intent.get("expires_at", 0):
            intent["status"] = "EXPIRED"
            return None

        return intent

    async def get_active_intent_for_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves currently active PENDING intent for user across workers."""
        u_id = int(user_id)
        intent_id = None
        r_client = _get_redis_client()

        if r_client:
            try:
                intent_id = await r_client.get(f"user_pending_hold:{u_id}")
            except Exception as e:
                logger.warning(f"[PendingHoldManager] Redis user active get error: {e}")

        if not intent_id:
            async with _in_memory_mutex:
                intent_id = _in_memory_user_active.get(u_id)

        if not intent_id:
            return None

        return await self.get_pending_intent(intent_id)

    async def consume_pending_intent(
        self,
        intent_id: str,
        user_id: int
    ) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Atomically validates and transitions pending intent from PENDING -> CONSUMED.
        Executes atomic Lua script in Redis for multi-worker safety, anti-replay, and anti-IDOR.
        Returns: (success: bool, intent: dict or None, reason: str)
        """
        if not intent_id:
            return False, None, "pending_intent_expired"

        now = time.time()
        key_intent = f"pending_hold:{intent_id}"
        key_user = f"user_pending_hold:{user_id}"

        # 1. Primary Distributed Execution: Redis Lua Script
        r_client = _get_redis_client()
        if r_client:
            try:
                res = await r_client.eval(
                    LUA_CONSUME_INTENT,
                    2,
                    key_intent,
                    key_user,
                    str(user_id),
                    str(now),
                    "300"
                )
                if isinstance(res, (list, tuple)) and len(res) == 2:
                    flag, payload = res[0], res[1]
                    if flag == 1 or flag == "1":
                        intent_data = json.loads(payload) if isinstance(payload, str) else payload
                        # Sync in-memory cache
                        async with _in_memory_mutex:
                            _in_memory_intents[intent_id] = intent_data
                            _in_memory_user_active.pop(int(user_id), None)
                        return True, intent_data, "ok"
                    else:
                        reason = str(payload)
                        if reason == "permission_denied":
                            logger.warning(f"[PendingHoldManager] IDOR attempt: user {user_id} tried to consume intent {intent_id}")
                        return False, None, reason
            except Exception as e:
                logger.error(f"[PendingHoldManager] Redis eval error in consume_pending_intent: {e}")
                if is_production():
                    return False, None, "redis_unavailable"

        # Fail closed in production if Redis is unavailable
        if is_production():
            return False, None, "redis_unavailable"

        # 2. Local fallback with coroutine mutex for dev/test
        async with _in_memory_mutex:
            intent = _in_memory_intents.get(intent_id)
            if not intent:
                return False, None, "pending_intent_expired"

            # Anti-IDOR
            if intent["user_id"] != int(user_id):
                logger.warning(f"[PendingHoldManager] IDOR attempt: user {user_id} tried to consume intent {intent_id} of user {intent['user_id']}")
                return False, None, "permission_denied"

            # Anti-Replay
            if intent["status"] == "CONSUMED":
                return False, None, "already_consumed"

            if intent["status"] != "PENDING":
                return False, None, f"invalid_status_{intent['status']}"

            if now > intent.get("expires_at", 0):
                intent["status"] = "EXPIRED"
                return False, None, "pending_intent_expired"

            # Atomic transition
            intent["status"] = "CONSUMED"
            intent["consumed_at"] = now
            _in_memory_intents[intent_id] = intent
            _in_memory_user_active.pop(int(user_id), None)
            return True, intent, "ok"

    async def cancel_pending_intent(self, intent_id: str, user_id: int) -> bool:
        """
        Cancels pending intent. NEVER releases slot locks as no lock was held.
        """
        r_client = _get_redis_client()
        if r_client:
            try:
                res = await r_client.eval(
                    LUA_CANCEL_INTENT,
                    2,
                    f"pending_hold:{intent_id}",
                    f"user_pending_hold:{user_id}",
                    str(user_id)
                )
                async with _in_memory_mutex:
                    _in_memory_intents.pop(intent_id, None)
                    _in_memory_user_active.pop(int(user_id), None)
                return bool(res == 1)
            except Exception as e:
                logger.warning(f"[PendingHoldManager] Redis cancel failed: {e}")

        async with _in_memory_mutex:
            intent = _in_memory_intents.get(intent_id)
            if not intent or intent["user_id"] != int(user_id):
                return False

            intent["status"] = "CANCELLED"
            _in_memory_intents[intent_id] = intent
            _in_memory_user_active.pop(int(user_id), None)
            return True



# Singleton instance
_pending_hold_manager: Optional[PendingHoldManager] = None

def get_pending_hold_manager() -> PendingHoldManager:
    global _pending_hold_manager
    if _pending_hold_manager is None:
        _pending_hold_manager = PendingHoldManager(ttl_seconds=300)
    return _pending_hold_manager


async def execute_slot_hold(
    db: AsyncSession,
    user_id: int,
    intent_id: str
) -> Dict[str, Any]:
    """
    Executes actual slot hold after explicit user confirmation:
    1. Consumes pending intent atomically (anti-IDOR & anti-replay via Redis Lua).
    2. Re-verifies slot existence and DB status (not BOOKED, not MAINTENANCE).
    3. Calls atomic acquire_slot_lock(slot.id, user.id, timeout_sec=600).
    4. Performs safe failure reconciliation if lock result is ambiguous.
    5. Returns normalized status:
       'hold_succeeded' | 'slot_unavailable' | 'pending_intent_expired' | 'availability_unverified' | 'hold_failed'
    """
    mgr = get_pending_hold_manager()

    # 1. Consume pending intent atomically
    consumed_ok, intent, reason = await mgr.consume_pending_intent(intent_id=intent_id, user_id=user_id)
    if not consumed_ok:
        if reason == "pending_intent_expired":
            return {
                "status": "pending_intent_expired",
                "message": "Bản xem trước giữ sân đã hết hạn (5 phút). Vui lòng yêu cầu kiểm tra lại sân trống nhé! 🏸",
                "data": None
            }
        elif reason == "already_consumed":
            return {
                "status": "hold_failed",
                "message": "Yêu cầu giữ sân này đã được thực hiện trước đó (chống gửi lặp thao tác). 🏸",
                "data": None
            }
        elif reason == "permission_denied":
            return {
                "status": "hold_failed",
                "message": "Bạn không có quyền xác nhận yêu cầu giữ sân của tài khoản khác.",
                "data": None
            }
        elif reason == "redis_unavailable":
            return {
                "status": "availability_unverified",
                "message": "Dịch vụ phân tán Redis hiện không khả dụng để đảm bảo giữ chỗ an toàn. Vui lòng thử lại sau!",
                "data": None
            }
        else:
            return {
                "status": "hold_failed",
                "message": f"Không thể xử lý yêu cầu giữ sân: {reason}",
                "data": None
            }

    slot_id = intent["slot_id"]

    # 2. Re-verify slot in database
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
                "status": "slot_unavailable",
                "message": "Khung giờ được yêu cầu không còn tồn tại trên hệ thống.",
                "data": None
            }

        slot, court, facility = row
        if slot.status in ("BOOKED", "MAINTENANCE"):
            return {
                "status": "slot_unavailable",
                "message": f"Khung giờ này hiện đã ở trạng thái {slot.status} và không thể giữ chỗ.",
                "data": None
            }

    except Exception as db_err:
        logger.error(f"[execute_slot_hold] DB verification error: {db_err}", exc_info=True)
        return {
            "status": "hold_failed",
            "message": "Lỗi truy vấn cơ sở dữ liệu khi xác thực khung giờ.",
            "data": None
        }

    # 3. Attempt atomic Redis hold for 10 minutes (600s) with safe reconciliation
    lock_success = False
    try:
        lock_success = await acquire_slot_lock(slot_id=slot.id, user_id=user_id, timeout_sec=600)
    except Exception as redis_err:
        logger.error(f"[execute_slot_hold] Redis atomic lock error: {redis_err}", exc_info=True)
        # Safe reconciliation: did the lock actually get created before timeout/drop?
        try:
            holder = await get_slot_lock_holder(slot.id)
            if holder == str(user_id):
                # Lock was actually acquired for this user before network dropped!
                lock_success = True
            elif holder is not None:
                return {
                    "status": "slot_unavailable",
                    "message": "Rất tiếc, khung giờ này vừa có khách hàng khác giữ chỗ thanh toán trước. Vui lòng chọn khung giờ khác nhé! 🏸",
                    "data": None
                }
            else:
                return {
                    "status": "availability_unverified",
                    "message": "Hệ thống tạm thời không thể xác minh kết quả giữ chỗ từ dịch vụ khóa Redis. Vui lòng kiểm tra lại sau!",
                    "data": None
                }
        except Exception:
            return {
                "status": "availability_unverified",
                "message": "Hệ thống tạm thời không thể kết nối tới dịch vụ khóa Redis để đảm bảo giữ chỗ tức thì. Vui lòng thử lại sau!",
                "data": None
            }

    if not lock_success:
        return {
            "status": "slot_unavailable",
            "message": "Rất tiếc, khung giờ này vừa có khách hàng khác giữ chỗ thanh toán trước. Vui lòng chọn khung giờ khác nhé! 🏸",
            "data": None
        }

    # 4. Hold Succeeded
    held_until_dt = datetime.now() + timedelta(seconds=600)
    return {
        "status": "hold_succeeded",
        "message": "Giữ chỗ thành công trong 10 phút. Vui lòng hoàn tất đặt cọc!",
        "data": {
            "slot_id": slot.id,
            "facility_id": facility.id,
            "facility_name": facility.name,
            "court_id": court.id,
            "court_number": court.court_number,
            "date": slot.date,
            "start_time": slot.start_time,
            "end_time": slot.end_time,
            "price": intent.get("price", 80000.0),
            "held_for_seconds": 600,
            "held_until": held_until_dt.strftime("%H:%M:%S")
        }
    }
