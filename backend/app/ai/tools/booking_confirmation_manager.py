"""
BADMINTON.AI - BOOKING CONFIRMATION INTENT MANAGER (PHASE 7.3)
Manages the distributed lifecycle of confirmed booking intents (Preview -> Confirmation).
Enforces:
1. Anti-Replay: An intent cannot be confirmed multiple times to create duplicate bookings.
2. Anti-IDOR: Users cannot consume another user's booking confirmation intent.
3. Expiration/TTL: Booking preview intents expire after 5 minutes (300s).
4. Distributed consistency via Redis and atomic Lua scripts.
5. In-memory fallback for local development and mock unit test suites.
"""

import time
import uuid
import json
import asyncio
import logging
from typing import Optional, Dict, Any, Tuple, List

from app.core import redis as redis_core
from app.core.redis import is_production

logger = logging.getLogger("booking_confirmation_manager")


def _get_redis_client():
    return getattr(redis_core, "redis_client", None)


def __getattr__(name):
    if name == "redis_client":
        return getattr(redis_core, "redis_client", None)
    raise AttributeError(f"module {__name__} has no attribute {name}")


# Lua script for distributed atomic consumption of booking confirmation intents
# KEYS[1]: booking_intent:{intent_id}
# KEYS[2]: user_booking_intent:{user_id}
# ARGV[1]: user_id
# ARGV[2]: now_timestamp
# ARGV[3]: consumed_retention_ttl_seconds
LUA_CONSUME_BOOKING_INTENT = """
local raw = redis.call("get", KEYS[1])
if not raw then
    return {0, "booking_intent_expired"}
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
    return {0, "booking_intent_expired"}
end

data.status = "CONSUMED"
data.consumed_at = now_ts
local new_raw = cjson.encode(data)

redis.call("set", KEYS[1], new_raw, "EX", tonumber(ARGV[3]))
redis.call("del", KEYS[2])

return {1, new_raw}
"""

# Lua script for distributed cancellation of booking intent
LUA_CANCEL_BOOKING_INTENT = """
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
_in_memory_booking_intents: Dict[str, Dict[str, Any]] = {}
_in_memory_user_active_booking: Dict[int, str] = {}
_in_memory_booking_mutex = asyncio.Lock()


class BookingConfirmationManager:
    """Manages booking confirmation intent lifecycle with distributed Redis and local fallback."""

    def __init__(self, ttl_seconds: int = 300):
        self.default_ttl = ttl_seconds

    async def create_booking_intent(
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
        total_amount: float,
        deposit_amount: float,
        equipment_ids: Optional[List[int]] = None,
        ttl_seconds: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Creates an ephemeral booking confirmation intent (PREVIEW ONLY).
        DOES NOT create any DB Booking record or charge money.
        """
        effective_ttl = ttl_seconds or self.default_ttl
        now = time.time()
        intent_id = f"bci_{uuid.uuid4().hex}"

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
            "total_amount": float(total_amount),
            "deposit_amount": float(deposit_amount),
            "equipment_ids": list(equipment_ids or []),
            "created_at": now,
            "expires_at": now + effective_ttl,
            "status": "PENDING"
        }

        r_client = _get_redis_client()
        if is_production() and not r_client:
            raise ConnectionError("Redis is required in production environment.")

        if r_client:
            try:
                await r_client.set(
                    f"booking_intent:{intent_id}",
                    json.dumps(intent_data),
                    ex=effective_ttl
                )
                await r_client.set(
                    f"user_booking_intent:{user_id}",
                    intent_id,
                    ex=effective_ttl
                )
            except Exception as e:
                logger.warning(f"[BookingConfirmationManager] Redis save failed: {e}")
                if is_production():
                    raise ConnectionError(f"Failed to persist booking intent to Redis in production: {e}")

        # In-memory storage for dev/test
        async with _in_memory_booking_mutex:
            _in_memory_booking_intents[intent_id] = intent_data
            _in_memory_user_active_booking[int(user_id)] = intent_id

        logger.info(f"[BookingConfirmationManager] Created booking intent {intent_id} for user {user_id}, slot {slot_id}")
        return intent_data

    async def get_booking_intent(self, intent_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves booking intent by ID and validates expiry."""
        if not intent_id:
            return None

        intent = None
        r_client = _get_redis_client()
        if r_client:
            try:
                raw = await r_client.get(f"booking_intent:{intent_id}")
                if raw:
                    intent = json.loads(raw)
            except Exception as e:
                logger.warning(f"[BookingConfirmationManager] Redis get error: {e}")

        if not intent:
            async with _in_memory_booking_mutex:
                intent = _in_memory_booking_intents.get(intent_id)

        if not intent:
            return None

        # Check TTL
        if time.time() > intent.get("expires_at", 0):
            intent["status"] = "EXPIRED"
            return None

        return intent

    async def get_active_booking_intent_for_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves currently active PENDING booking intent for user across workers."""
        u_id = int(user_id)
        intent_id = None
        r_client = _get_redis_client()

        if r_client:
            try:
                intent_id = await r_client.get(f"user_booking_intent:{u_id}")
            except Exception as e:
                logger.warning(f"[BookingConfirmationManager] Redis user active get error: {e}")

        if not intent_id:
            async with _in_memory_booking_mutex:
                intent_id = _in_memory_user_active_booking.get(u_id)

        if not intent_id:
            return None

        return await self.get_booking_intent(intent_id)

    async def consume_booking_intent(
        self,
        intent_id: str,
        user_id: int
    ) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Atomically validates and transitions booking intent from PENDING -> CONSUMED.
        Executes atomic Lua script in Redis for multi-worker safety, anti-replay, and anti-IDOR.
        Returns: (success: bool, intent: dict or None, reason: str)
        """
        if not intent_id:
            return False, None, "booking_intent_expired"

        now = time.time()
        key_intent = f"booking_intent:{intent_id}"
        key_user = f"user_booking_intent:{user_id}"

        # 1. Primary Distributed Execution: Redis Lua Script
        r_client = _get_redis_client()
        if r_client:
            try:
                res = await r_client.eval(
                    LUA_CONSUME_BOOKING_INTENT,
                    2,
                    key_intent,
                    key_user,
                    str(user_id),
                    str(now),
                    "600"
                )
                if isinstance(res, (list, tuple)) and len(res) == 2:
                    flag, payload = res[0], res[1]
                    if flag == 1 or flag == "1":
                        intent_data = json.loads(payload) if isinstance(payload, str) else payload
                        async with _in_memory_booking_mutex:
                            _in_memory_booking_intents[intent_id] = intent_data
                            _in_memory_user_active_booking.pop(int(user_id), None)
                        return True, intent_data, "ok"
                    else:
                        reason = str(payload)
                        if reason == "permission_denied":
                            logger.warning(f"[BookingConfirmationManager] IDOR attempt: user {user_id} tried to consume intent {intent_id}")
                        return False, None, reason
            except Exception as e:
                logger.error(f"[BookingConfirmationManager] Redis eval error: {e}")
                if is_production():
                    return False, None, "redis_unavailable"

        if is_production():
            return False, None, "redis_unavailable"

        # 2. Local fallback with coroutine mutex for dev/test
        async with _in_memory_booking_mutex:
            intent = _in_memory_booking_intents.get(intent_id)
            if not intent:
                return False, None, "booking_intent_expired"

            if intent["user_id"] != int(user_id):
                logger.warning(f"[BookingConfirmationManager] IDOR attempt: user {user_id} tried to consume intent {intent_id}")
                return False, None, "permission_denied"

            if intent["status"] == "CONSUMED":
                return False, None, "already_consumed"

            if intent["status"] != "PENDING":
                return False, None, f"invalid_status_{intent['status']}"

            if now > intent.get("expires_at", 0):
                intent["status"] = "EXPIRED"
                return False, None, "booking_intent_expired"

            intent["status"] = "CONSUMED"
            intent["consumed_at"] = now
            _in_memory_booking_intents[intent_id] = intent
            _in_memory_user_active_booking.pop(int(user_id), None)
            return True, intent, "ok"

    async def cancel_booking_intent(self, intent_id: str, user_id: int) -> bool:
        """Cancels booking intent."""
        r_client = _get_redis_client()
        if r_client:
            try:
                res = await r_client.eval(
                    LUA_CANCEL_BOOKING_INTENT,
                    2,
                    f"booking_intent:{intent_id}",
                    f"user_booking_intent:{user_id}",
                    str(user_id)
                )
                async with _in_memory_booking_mutex:
                    _in_memory_booking_intents.pop(intent_id, None)
                    _in_memory_user_active_booking.pop(int(user_id), None)
                return bool(res == 1)
            except Exception as e:
                logger.warning(f"[BookingConfirmationManager] Redis cancel failed: {e}")

        async with _in_memory_booking_mutex:
            intent = _in_memory_booking_intents.get(intent_id)
            if not intent or intent["user_id"] != int(user_id):
                return False

            intent["status"] = "CANCELLED"
            _in_memory_booking_intents[intent_id] = intent
            _in_memory_user_active_booking.pop(int(user_id), None)
            return True


# Singleton instance
_booking_confirmation_manager: Optional[BookingConfirmationManager] = None

def get_booking_confirmation_manager() -> BookingConfirmationManager:
    global _booking_confirmation_manager
    if _booking_confirmation_manager is None:
        _booking_confirmation_manager = BookingConfirmationManager(ttl_seconds=300)
    return _booking_confirmation_manager
