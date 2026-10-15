"""
Migration Revision 005: Add idempotency_key to bookings table.
Supports PostgreSQL and SQLite. Ensures robust at-most-once booking creation.
"""

REVISION = "005_phase7_3_booking_idempotency"
DESCRIPTION = "Add idempotency_key column and unique index to bookings table"

SQL_UPGRADE_POSTGRES = [
    """
    ALTER TABLE bookings ADD COLUMN IF NOT EXISTS idempotency_key VARCHAR(100);
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS ix_bookings_idempotency_key ON bookings(idempotency_key);
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_bookings_slot_payment ON bookings(slot_id, payment_status);
    """
]

SQL_DOWNGRADE_POSTGRES = [
    "DROP INDEX IF EXISTS ix_bookings_slot_payment;",
    "DROP INDEX IF EXISTS ix_bookings_idempotency_key;",
    "ALTER TABLE bookings DROP COLUMN IF EXISTS idempotency_key;"
]

SQL_UPGRADE_SQLITE = [
    """
    ALTER TABLE bookings ADD COLUMN idempotency_key TEXT;
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS ix_bookings_idempotency_key ON bookings(idempotency_key);
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_bookings_slot_payment ON bookings(slot_id, payment_status);
    """
]

SQL_DOWNGRADE_SQLITE = [
    "DROP INDEX IF EXISTS ix_bookings_slot_payment;",
    "DROP INDEX IF EXISTS ix_bookings_idempotency_key;"
]


def upgrade(connection_or_cursor, dialect_name: str = "sqlite"):
    if "postgres" in dialect_name.lower():
        for sql in SQL_UPGRADE_POSTGRES:
            connection_or_cursor.execute(sql.strip())
    else:
        for sql in SQL_UPGRADE_SQLITE:
            try:
                connection_or_cursor.execute(sql.strip())
            except Exception:
                # Column might already exist in SQLite
                pass


def downgrade(connection_or_cursor, dialect_name: str = "sqlite"):
    if "postgres" in dialect_name.lower():
        for sql in SQL_DOWNGRADE_POSTGRES:
            connection_or_cursor.execute(sql.strip())
    else:
        for sql in SQL_DOWNGRADE_SQLITE:
            try:
                connection_or_cursor.execute(sql.strip())
            except Exception:
                pass
