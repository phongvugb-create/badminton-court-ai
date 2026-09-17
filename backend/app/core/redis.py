import redis.asyncio as redis
from app.config import settings
import logging

logger = logging.getLogger(__name__)

redis_client = None

async def init_redis():
    global redis_client
    try:
        redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        await redis_client.ping()
        logger.info("Connected to Redis successfully.")
    except Exception as e:
        logger.warning(f"Failed to connect to Redis at {settings.REDIS_URL}: {e}. Mock in-memory lock will be used.")
        redis_client = None

# In-memory lock fallback if Redis server is not running
_in_memory_locks = {}
import time

async def acquire_slot_lock(slot_id: int, user_id: int, timeout_sec: int = 600) -> bool:
    """
    Atomic slot lock for 10 minutes (600s).
    Redis Command: SET slot:{slot_id} {user_id} EX {timeout_sec} NX
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
            
    # Fallback in-memory
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
    """
    global redis_client
    lock_key = f"slot_lock:{slot_id}"
    
    if redis_client:
        try:
            val = await redis_client.get(lock_key)
            if val == str(user_id):
                await redis_client.delete(lock_key)
                return True
            return False
        except Exception as e:
            logger.error(f"Redis error releasing lock: {e}")
            
    # Fallback in-memory
    if lock_key in _in_memory_locks:
        holder_id, _ = _in_memory_locks[lock_key]
        if holder_id == user_id:
            del _in_memory_locks[lock_key]
            return True
    return False

async def get_slot_lock_holder(slot_id: int):
    global redis_client
    lock_key = f"slot_lock:{slot_id}"
    if redis_client:
        try:
            return await redis_client.get(lock_key)
        except Exception:
            pass
    if lock_key in _in_memory_locks:
        holder_id, expire_at = _in_memory_locks[lock_key]
        if time.time() < expire_at:
            return str(holder_id)
        else:
            del _in_memory_locks[lock_key]
    return None
