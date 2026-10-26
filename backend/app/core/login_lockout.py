"""Shared persistent lockout policy for all login entry points."""

import hashlib
import math
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.future import select

from app.core.database import AsyncSessionLocal, engine
from app.models.all_models import LoginAttempt

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_SECONDS = 5 * 60
_table_ready = False


def _login_key(identifier: str) -> str:
    normalized = (identifier or "").strip().casefold()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


async def _ensure_table() -> None:
    global _table_ready
    if _table_ready:
        return
    async with engine.begin() as connection:
        await connection.run_sync(LoginAttempt.__table__.create, checkfirst=True)
    _table_ready = True


async def remaining_lock_seconds(identifier: str) -> int:
    """Return remaining lock time, or zero when the account may try again."""
    await _ensure_table()
    key = _login_key(identifier)
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(LoginAttempt).where(LoginAttempt.login_key == key).with_for_update()
        )
        attempt = result.scalar_one_or_none()
        if attempt is None:
            return 0
        locked_until = attempt.locked_until
        if locked_until is None:
            return 0
        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=timezone.utc)
        remaining = math.ceil((locked_until - now).total_seconds())
        if remaining > 0:
            return remaining
        attempt.failed_attempts = 0
        attempt.locked_until = None
        await db.commit()
        return 0


async def record_failed_login(identifier: str) -> int:
    """Increment failures and return seconds to wait (0 until threshold reached)."""
    await _ensure_table()
    key = _login_key(identifier)
    now = datetime.now(timezone.utc)

    # A concurrent first failure can race to create the unique account row.
    for _ in range(3):
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(LoginAttempt).where(LoginAttempt.login_key == key).with_for_update()
            )
            attempt = result.scalar_one_or_none()
            if attempt is None:
                attempt = LoginAttempt(login_key=key, failed_attempts=0)
                db.add(attempt)
                try:
                    await db.flush()
                except IntegrityError:
                    await db.rollback()
                    continue

            locked_until = attempt.locked_until
            if locked_until is not None:
                if locked_until.tzinfo is None:
                    locked_until = locked_until.replace(tzinfo=timezone.utc)
                if locked_until > now:
                    return math.ceil((locked_until - now).total_seconds())
                attempt.failed_attempts = 0
                attempt.locked_until = None

            attempt.failed_attempts = (attempt.failed_attempts or 0) + 1
            if attempt.failed_attempts >= MAX_FAILED_ATTEMPTS:
                attempt.failed_attempts = MAX_FAILED_ATTEMPTS
                attempt.locked_until = now + timedelta(seconds=LOCKOUT_SECONDS)
                await db.commit()
                return LOCKOUT_SECONDS

            await db.commit()
            return 0

    # If the database was contended beyond retries, fail closed for authentication.
    return LOCKOUT_SECONDS


async def clear_failed_logins(identifier: str) -> None:
    """Clear the counter after successful authentication."""
    await _ensure_table()
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(LoginAttempt).where(LoginAttempt.login_key == _login_key(identifier))
        )
        attempt = result.scalar_one_or_none()
        if attempt is not None:
            await db.delete(attempt)
            await db.commit()
