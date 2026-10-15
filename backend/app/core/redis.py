# pyrefly: ignore [missing-import]
try:
    # pyrefly: ignore [missing-import]
    import redis.asyncio as redis
    _has_redis_lib = True
except ImportError:
    redis = None
    _has_redis_lib = False

import os
import time
import logging
from app.config import settings

logger = logging.getLogger(__name__)

redis_client = None
_in_memory_locks = {}


LUA_RELEASE_LOCK = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""


def is_production() -> bool:
    env = os.getenv("ENVIRONMENT") or getattr(settings, "ENVIRONMENT", None)
    node_env = getattr(settings, "NODE_ENV", None)
    return (str(env).lower() in ("production", "prod")) or (str(node_env).lower() in ("production", "prod"))


async def init_redis():
    global redis_client
    if not _has_redis_lib:
        if is_production():
            logger.error("Redis library not installed in production environment! System will fail closed.")
        else:
            logger.info("Redis library not installed. In-memory atomic lock fallback active.")
        redis_client = None
        return
    try:
        redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        await redis_client.ping()
        logger.info("Connected to Redis successfully.")
    except Exception as e:
        if is_production():
            logger.critical(f"FATAL: Failed to connect to Redis in production: {e}. In-memory fallback DISABLED.")
        else:
            logger.warning(f"Failed to connect to Redis at {settings.REDIS_URL}: {e}. Mock in-memory lock will be used.")
        redis_client = None


async def acquire_slot_lock(slot_id: int, user_id: int, timeout_sec: int = 600) -> bool:
    """
    Atomic slot lock for 10 minutes (600s).
    Redis Command: SET slot_lock:{slot_id} {user_id} EX {timeout_sec} NX
    Returns True if successfully held, False if already held by another user.
    """
    global redis_client
    lock_key = f"slot_lock:{slot_id}"

    if redis_client:
        try:
            # NX: Only set the key if it does not already exist
            # EX: Expire after timeout_sec
            res = await redis_client.set(lock_key, str(user_id), ex=timeout_sec, nx=True)
            return bool(res)
        except Exception as e:
            logger.error(f"Redis error when locking: {e}")
            raise

    # Fail closed in production: DO NOT use in-memory dictionary!
    if is_production():
        raise ConnectionError("Redis service is unavailable. Refusing operation in production environment.")

    # Fallback in-memory (dev/test only)
    current_time = time.time()
    if lock_key in _in_memory_locks:
        holder_id, expire_at = _in_memory_locks[lock_key]
        if current_time < expire_at:
            if holder_id == user_id:
                # Same user re-locking
                _in_memory_locks[lock_key] = (user_id, current_time + timeout_sec)
                return True
            return False

    _in_memory_locks[lock_key] = (user_id, current_time + timeout_sec)
    return True


async def release_slot_lock(slot_id: int, user_id: int) -> bool:
    """
    Releases lock only if held by this user.
    Uses atomic Lua script in Redis to avoid TOCTOU race conditions.
    """
    global redis_client
    lock_key = f"slot_lock:{slot_id}"

    if redis_client:
        try:
            res = await redis_client.eval(LUA_RELEASE_LOCK, 1, lock_key, str(user_id))
            return bool(res == 1)
        except Exception as e:
            logger.error(f"Redis error releasing lock: {e}")
            raise

    # Fail closed in production
    if is_production():
        raise ConnectionError("Redis service is unavailable. Refusing operation in production environment.")

    # Fallback in-memory (dev/test only)
    if lock_key in _in_memory_locks:
        holder_id, _ = _in_memory_locks[lock_key]
        if holder_id == user_id:
            del _in_memory_locks[lock_key]
            return True
    return False


async def get_slot_lock_holder(slot_id: int):
    """
    Returns holder ID if slot is locked, or None if free.
    Re-raises exception if Redis client fails to verify status.
    """
    global redis_client
    lock_key = f"slot_lock:{slot_id}"
    if redis_client:
        try:
            return await redis_client.get(lock_key)
        except Exception as e:
            logger.error(f"Redis get error for slot lock {slot_id}: {e}")
            raise

    # Fail closed in production
    if is_production():
        raise ConnectionError("Redis service is unavailable. Refusing operation in production environment.")

    if lock_key in _in_memory_locks:
        holder_id, expire_at = _in_memory_locks[lock_key]
        if time.time() < expire_at:
            return str(holder_id)
        else:
            del _in_memory_locks[lock_key]
    return None
