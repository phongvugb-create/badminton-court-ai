"""
Migration Revision 006: Add payments table for Phase 7.4A Payment Foundation.
Supports PostgreSQL and SQLite.
Enables multiple payment attempts per booking, idempotent reconciliation,
and structured provider tracking (Sandbox, VNPay, MoMo, ZaloPay).
"""

REVISION = "006_phase7_4a_payment_foundation"
DESCRIPTION = "Add payments table for payment attempts, sandbox, and reconciliation"

SQL_UPGRADE_POSTGRES = [
    """
    CREATE TABLE IF NOT EXISTS payments (
        id SERIAL PRIMARY KEY,
        booking_id INTEGER NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
        user_id INTEGER NOT NULL REFERENCES users(id),
        provider VARCHAR(50) NOT NULL,
        transaction_id VARCHAR(100) NOT NULL UNIQUE,
        amount FLOAT NOT NULL,
        currency VARCHAR(10) DEFAULT 'VND',
        payment_type VARCHAR(50) DEFAULT 'DEPOSIT',
        status VARCHAR(50) DEFAULT 'PENDING',
        idempotency_key VARCHAR(100) UNIQUE,
        provider_response TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """,
    "CREATE INDEX IF NOT EXISTS ix_payments_booking_id ON payments(booking_id);",
    "CREATE INDEX IF NOT EXISTS ix_payments_user_id ON payments(user_id);",
    "CREATE INDEX IF NOT EXISTS ix_payments_status ON payments(status);",
    "CREATE INDEX IF NOT EXISTS ix_payments_transaction_id ON payments(transaction_id);",
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_payments_idempotency_key ON payments(idempotency_key);"
]

SQL_DOWNGRADE_POSTGRES = [
    "DROP TABLE IF EXISTS payments CASCADE;"
]

SQL_UPGRADE_SQLITE = [
    """
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_id INTEGER NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
        user_id INTEGER NOT NULL REFERENCES users(id),
        provider TEXT NOT NULL,
        transaction_id TEXT NOT NULL UNIQUE,
        amount REAL NOT NULL,
        currency TEXT DEFAULT 'VND',
        payment_type TEXT DEFAULT 'DEPOSIT',
        status TEXT DEFAULT 'PENDING',
        idempotency_key TEXT UNIQUE,
        provider_response TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
    "CREATE INDEX IF NOT EXISTS ix_payments_booking_id ON payments(booking_id);",
    "CREATE INDEX IF NOT EXISTS ix_payments_user_id ON payments(user_id);",
    "CREATE INDEX IF NOT EXISTS ix_payments_status ON payments(status);",
    "CREATE INDEX IF NOT EXISTS ix_payments_transaction_id ON payments(transaction_id);",
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_payments_idempotency_key ON payments(idempotency_key);"
]

SQL_DOWNGRADE_SQLITE = [
    "DROP TABLE IF EXISTS payments;"
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
