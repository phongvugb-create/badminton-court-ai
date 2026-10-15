"""
BADMINTON.AI - LIGHTWEIGHT DATABASE MIGRATION RUNNER
Supports version tracking, upgrade, and rollback on both SQLite and PostgreSQL.
Zero heavy dependencies, fully transactional and idempotent.
Compatible with both psycopg2 and asyncpg (for environments without C-extensions).
"""

import os
import sys
import sqlite3
import logging
from urllib.parse import urlparse
from typing import List, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("migration_runner")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
backend_path = os.path.join(BASE_DIR, "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

SQLITE_PATH = os.path.join(BASE_DIR, "badminton.db")
RAW_DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL") or ""

# Asyncpg Adapter for environments without psycopg2
class AsyncpgCursor:
    def __init__(self, conn, loop):
        self.conn = conn
        self.loop = loop
        self._rows = []

    def execute(self, sql, params=None):
        stmt = sql.strip()
        if not stmt:
            return
        if params:
            converted_sql = stmt
            for i in range(1, len(params) + 1):
                if "%s" in converted_sql:
                    converted_sql = converted_sql.replace("%s", f"${i}", 1)
                elif "?" in converted_sql:
                    converted_sql = converted_sql.replace("?", f"${i}", 1)
            self._rows = self.loop.run_until_complete(self.conn.fetch(converted_sql, *params))
        else:
            self._rows = self.loop.run_until_complete(self.conn.fetch(stmt))

    def fetchall(self):
        return [tuple(r.values()) for r in self._rows]


class AsyncpgConnectionWrapper:
    def __init__(self, host, port, user, password, database):
        import asyncio
        import asyncpg
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.conn = self.loop.run_until_complete(
            asyncpg.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database
            )
        )
        self.cursor_obj = AsyncpgCursor(self.conn, self.loop)
        self.tx = None

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        pass

    def rollback(self):
        pass

    def __enter__(self):
        self.tx = self.conn.transaction()
        self.loop.run_until_complete(self.tx.start())
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.loop.run_until_complete(self.tx.rollback())
        else:
            self.loop.run_until_complete(self.tx.commit())

    def close(self):
        self.loop.run_until_complete(self.conn.close())
        self.loop.close()


def get_db_connection():
    if RAW_DATABASE_URL and ("postgres://" in RAW_DATABASE_URL or "postgresql://" in RAW_DATABASE_URL):
        # Resolve target host/port for PostgreSQL
        parsed = urlparse(RAW_DATABASE_URL.replace("postgresql+asyncpg://", "http://").replace("postgresql://", "http://").replace("postgres://", "http://"))
        host = parsed.hostname or os.environ.get("POSTGRES_HOST", "127.0.0.1")
        port = parsed.port or int(os.environ.get("POSTGRES_PORT", 5433 if host in ["127.0.0.1", "localhost"] else 5432))
        
        # If host is Docker service name and unresolvable on host, map to localhost:5433
        if host in ["badminton_ai_postgres", "badminton-ai-db"]:
            import socket
            try:
                socket.gethostbyname(host)
            except Exception:
                logger.info(f"Docker container hostname '{host}' unresolvable on host. Mapping to 127.0.0.1:{os.environ.get('POSTGRES_PORT', 5433)}")
                host = os.environ.get("POSTGRES_HOST", "127.0.0.1")
                port = int(os.environ.get("POSTGRES_PORT", 5433))

        try:
            from app.config import settings
            default_user = settings.POSTGRES_USER
            default_password = settings.POSTGRES_PASSWORD
            default_db = settings.POSTGRES_DB
        except Exception:
            default_user = "postgres"
            default_password = "postgres_secure_pass_2026"
            default_db = "badminton_ai_db"

        user = parsed.username or os.environ.get("POSTGRES_USER", default_user)
        password = parsed.password or os.environ.get("POSTGRES_PASSWORD", default_password)
        database = (parsed.path or "").lstrip("/") or os.environ.get("POSTGRES_DB", default_db)

        # Try psycopg2 first
        try:
            import psycopg2
            url = f"postgresql://{user}:{password}@{host}:{port}/{database}"
            conn = psycopg2.connect(url)
            return conn, "postgresql"
        except ImportError:
            # Fallback to asyncpg adapter
            logger.info("psycopg2 chưa được cài đặt, sử dụng asyncpg driver cho migration.")
            conn = AsyncpgConnectionWrapper(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database
            )
            return conn, "postgresql"
    else:
        conn = sqlite3.connect(SQLITE_PATH)
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn, "sqlite"


def init_migration_table(conn, dialect: str):
    sql = """
    CREATE TABLE IF NOT EXISTS schema_migrations (
        version VARCHAR(64) PRIMARY KEY,
        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        description TEXT
    );
    """
    with conn:
        cursor = conn.cursor()
        cursor.execute(sql)


def get_applied_migrations(conn) -> List[str]:
    cursor = conn.cursor()
    cursor.execute("SELECT version FROM schema_migrations ORDER BY applied_at ASC;")
    rows = cursor.fetchall()
    return [r[0] for r in rows]


def run_migrations():
    conn, dialect = get_db_connection()
    logger.info(f"Khởi động Migration Runner trên dialect: {dialect.upper()}")
    init_migration_table(conn, dialect)

    from migrations.versions import (
        v000_phase1_base_tables,
        v001_phase2_conversations,
        v002_phase3_documents,
        v003_phase4_embeddings,
        v004_phase4_1_metadata,
        v005_phase7_3_booking_idempotency,
        v006_phase7_4a_payment_foundation
    )
    registered_revisions = [
        v000_phase1_base_tables,
        v001_phase2_conversations,
        v002_phase3_documents,
        v003_phase4_embeddings,
        v004_phase4_1_metadata,
        v005_phase7_3_booking_idempotency,
        v006_phase7_4a_payment_foundation
    ]

    applied = get_applied_migrations(conn)
    logger.info(f"Các revision đã áp dụng trước đó: {applied}")

    for rev in registered_revisions:
        rev_id = rev.REVISION
        if rev_id not in applied:
            logger.info(f"--> Đang áp dụng migration: {rev_id} - {rev.DESCRIPTION}")
            try:
                with conn:
                    cursor = conn.cursor()
                    rev.upgrade(cursor, dialect_name=dialect)
                    if dialect == "sqlite":
                        cursor.execute(
                            "INSERT INTO schema_migrations (version, description) VALUES (?, ?);",
                            (rev_id, rev.DESCRIPTION)
                        )
                    else:
                        cursor.execute(
                            "INSERT INTO schema_migrations (version, description) VALUES (%s, %s);",
                            (rev_id, rev.DESCRIPTION)
                        )
                logger.info(f"✅ Hoàn tất migration: {rev_id}")
            except Exception as e:
                logger.error(f"❌ Lỗi khi áp dụng migration {rev_id}: {e}")
                raise e
        else:
            logger.info(f"==> Migration {rev_id} đã được áp dụng, bỏ qua.")

    conn.close()
    logger.info("Hoàn tất kiểm tra và đồng bộ migration.")


def rollback_latest():
    conn, dialect = get_db_connection()
    init_migration_table(conn, dialect)
    applied = get_applied_migrations(conn)
    if not applied:
        logger.warning("Không có migration nào để rollback.")
        conn.close()
        return

    latest = applied[-1]
    logger.info(f"Đang rollback migration mới nhất: {latest}")

    from migrations.versions import (
        v000_phase1_base_tables,
        v001_phase2_conversations,
        v002_phase3_documents,
        v003_phase4_embeddings,
        v004_phase4_1_metadata
    )
    rev_map = {
        v000_phase1_base_tables.REVISION: v000_phase1_base_tables,
        v001_phase2_conversations.REVISION: v001_phase2_conversations,
        v002_phase3_documents.REVISION: v002_phase3_documents,
        v003_phase4_embeddings.REVISION: v003_phase4_embeddings,
        v004_phase4_1_metadata.REVISION: v004_phase4_1_metadata
    }

    if latest in rev_map:
        rev = rev_map[latest]
        with conn:
            cursor = conn.cursor()
            rev.downgrade(cursor, dialect_name=dialect)
            if dialect == "sqlite":
                cursor.execute("DELETE FROM schema_migrations WHERE version = ?;", (latest,))
            else:
                cursor.execute("DELETE FROM schema_migrations WHERE version = %s;", (latest,))
        logger.info(f"✅ Đã rollback thành công: {latest}")
    else:
        logger.error(f"Không tìm thấy mã nguồn migration cho revision: {latest}")

    conn.close()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--rollback":
        rollback_latest()
    else:
        run_migrations()
