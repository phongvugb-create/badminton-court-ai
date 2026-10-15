"""
BADMINTON.AI - PHASE 7.2.2 INTEGRATION TEST SUITE: LIVE POSTGRESQL VERIFICATION
Verifies live PostgreSQL connectivity, schema migrations, models, and queries
using the real asyncpg driver against an active PostgreSQL instance.

MANDATORY RULES:
1. Uses real PostgreSQL database connection. SQLite is NEVER accepted as proof of PostgreSQL.
2. If PostgreSQL is unreachable, tests are strictly classified BLOCKED / NOT TESTED with exact reasons.
"""

import os
import sys
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
from app.models.all_models import Facility, Court, TimeSlot, SlotPricing, Booking, User, Document, DocumentChunk
from app.ai.retrieval_service import VectorRetriever
from app.ai.embedding_provider import get_embedding_provider

try:
    import asyncpg
    _HAS_ASYNCPG = True
except ImportError:
    asyncpg = None
    _HAS_ASYNCPG = False

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from sqlalchemy import text


class TestPhase722LivePostgresIntegration(unittest.TestCase):
    """
    Integration tests for live PostgreSQL database with asyncpg.
    Strictly verifies live database connection and queries.
    """

    @classmethod
    def setUpClass(cls):
        cls.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(cls.loop)

        cls.is_live_pg_available = False
        cls.skip_reason = ""
        cls.engine = None
        cls.session_factory = None

        if not _HAS_ASYNCPG:
            cls.skip_reason = "BLOCKED: Python 'asyncpg' driver is not installed in the environment."
            return

        # Determine target postgres url candidates
        # Supports:
        # 1. TEST_DATABASE_URL environment variable
        # 2. Configured DATABASE_URL (e.g. inside Docker network)
        # 3. Host-mapped fallback with POSTGRES_PORT (default 5433) and POSTGRES_HOST (default localhost)
        pg_host = os.getenv("POSTGRES_HOST", "localhost")
        pg_port = os.getenv("POSTGRES_PORT", "5433")

        candidate_urls = []
        if os.getenv("TEST_DATABASE_URL"):
            candidate_urls.append(os.getenv("TEST_DATABASE_URL"))

        raw_url = os.getenv("DATABASE_URL", settings.DATABASE_URL)
        if raw_url:
            if raw_url.startswith("postgresql://"):
                candidate_urls.append(raw_url.replace("postgresql://", "postgresql+asyncpg://", 1))
            elif raw_url.startswith("postgresql+asyncpg://"):
                candidate_urls.append(raw_url)

        host_fallback = f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{pg_host}:{pg_port}/{settings.POSTGRES_DB}"
        if host_fallback not in candidate_urls:
            candidate_urls.append(host_fallback)

        last_err = None
        for pg_url in candidate_urls:
            try:
                engine = create_async_engine(pg_url, connect_args={"timeout": 1.5})
                async def _check(eng):
                    async with eng.connect() as conn:
                        res = await conn.execute(text("SELECT 1"))
                        return res.scalar()

                val = cls.loop.run_until_complete(asyncio.wait_for(_check(engine), timeout=2.0))
                if val == 1:
                    cls.is_live_pg_available = True
                    cls.engine = engine
                    cls.session_factory = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
                    break
                else:
                    cls.loop.run_until_complete(engine.dispose())
            except Exception as e:
                last_err = e

        if not cls.is_live_pg_available:
            display_url = candidate_urls[0] if candidate_urls else host_fallback
            masked_url = display_url
            if "@" in masked_url and ":" in masked_url.split("@")[0]:
                parts = masked_url.split("@")
                prefix = parts[0].split(":")
                masked_url = f"{prefix[0]}:***@{parts[1]}"

            cls.skip_reason = (
                f"BLOCKED / NOT TESTED: Live PostgreSQL server is unreachable at {masked_url} ({last_err}). "
                "Ensure container 'badminton_ai_postgres' is running with host port mapped (e.g. 5433)."
            )

    @classmethod
    def tearDownClass(cls):
        if cls.engine:
            async def _dispose():
                await cls.engine.dispose()
            cls.loop.run_until_complete(_dispose())
        cls.loop.close()

    def setUp(self):
        if not self.is_live_pg_available:
            self.skipTest(self.skip_reason)

    def run_async(self, coro):
        return self.loop.run_until_complete(coro)

    # -------------------------------------------------------------------------
    # TEST 1: Live connection handshake with asyncpg
    # -------------------------------------------------------------------------
    def test_01_live_connection_handshake(self):
        """1. Xác minh kết nối thành công tới PostgreSQL bằng driver asyncpg."""
        async def _test():
            async with self.session_factory() as session:
                res = await session.execute(text("SELECT version();"))
                row = res.scalar()
                self.assertIn("PostgreSQL", row)
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 2: Schema verification for Badminton models
    # -------------------------------------------------------------------------
    def test_02_badminton_schema_tables_exist(self):
        """2. Xác minh các bảng quản lý hệ thống (Facility, Court, TimeSlot, SlotPricing, Booking) tồn tại."""
        async def _test():
            async with self.session_factory() as session:
                stmt = text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public';
                """)
                res = await session.execute(stmt)
                tables = [r[0] for r in res.fetchall()]
                expected_tables = ["facilities", "courts", "time_slots", "slot_pricing", "bookings", "users"]
                for t in expected_tables:
                    self.assertIn(t, tables, f"Table {t} must exist in PostgreSQL schema")
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 3: Slot availability query on PostgreSQL
    # -------------------------------------------------------------------------
    def test_03_availability_query_on_postgres(self):
        """3. Chạy truy vấn availability trên PostgreSQL thực tế, đảm bảo kiểu dữ liệu tương thích."""
        async def _test():
            async with self.session_factory() as session:
                stmt = (
                    select(TimeSlot, Court, Facility)
                    .join(Court, TimeSlot.court_id == Court.id)
                    .join(Facility, Court.facility_id == Facility.id)
                    .where(Facility.is_approved == True)
                    .limit(5)
                )
                res = await session.execute(stmt)
                rows = res.all()
                self.assertIsInstance(rows, list)
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 4: pgvector extension check
    # -------------------------------------------------------------------------
    def test_04_pgvector_extension_check(self):
        """4. Kiểm tra extension pgvector nếu có migration vector embedding."""
        async def _test():
            async with self.session_factory() as session:
                stmt = text("SELECT extname FROM pg_extension WHERE extname = 'vector';")
                res = await session.execute(stmt)
                ext = res.scalar_one_or_none()
                # Document presence or absence of pgvector
                if ext:
                    self.assertEqual(ext, "vector")
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 5: Live Vector Retrieval on PostgreSQL
    # -------------------------------------------------------------------------
    def test_05_live_vector_retrieval_query(self):
        """5. Xác minh truy vấn vector retrieval chạy thành công trên PostgreSQL thật với chunk & citation."""
        async def _test():
            provider = get_embedding_provider()
            retriever = VectorRetriever(provider=provider)
            test_doc_id = "doc_live_test_retrieval_01"
            test_chunk_id = "chunk_live_test_retrieval_01"

            async with self.session_factory() as session:
                try:
                    # Clean any stale records
                    await session.execute(text(f"DELETE FROM document_chunks WHERE id = '{test_chunk_id}';"))
                    await session.execute(text(f"DELETE FROM documents WHERE id = '{test_doc_id}';"))
                    await session.commit()

                    # Insert test document and chunk
                    doc = Document(
                        id=test_doc_id,
                        title="Bảng giá thuê sân test 2026",
                        filename="bang_gia_test.pdf",
                        source_type="file",
                        status="READY",
                        access_scope="public",
                        checksum="checksum_live_test_01"
                    )
                    session.add(doc)
                    await session.commit()

                    chunk_text = "Giá thuê sân cầu lông từ thứ 2 đến thứ 6 là 80.000 VNĐ một giờ vào khung giờ vàng."
                    vec = await provider.embed_text(chunk_text)

                    chunk = DocumentChunk(
                        id=test_chunk_id,
                        document_id=doc.id,
                        chunk_index=0,
                        text=chunk_text,
                        page_number=1,
                        section="Bảng giá",
                        embedding=vec,
                        embedding_model=provider.model_name,
                        embedding_dimension=len(vec)
                    )
                    session.add(chunk)
                    await session.commit()

                    # Execute retrieval query
                    res = await retriever.retrieve(
                        db=session,
                        query="Giá thuê sân cầu lông",
                        user_context={"role": "ADMIN"}
                    )

                    self.assertIsNotNone(res)
                    self.assertGreaterEqual(res.total_candidates, 1)
                    self.assertGreaterEqual(res.returned_results, 1)
                    first_match = res.results[0]
                    self.assertEqual(first_match.chunk_id, test_chunk_id)
                    self.assertEqual(first_match.filename, "bang_gia_test.pdf")
                    self.assertIn("80.000 VNĐ", first_match.text)
                    self.assertGreater(first_match.score, 0.58)

                finally:
                    # Clean up
                    await session.execute(text(f"DELETE FROM document_chunks WHERE id = '{test_chunk_id}';"))
                    await session.execute(text(f"DELETE FROM documents WHERE id = '{test_doc_id}';"))
                    await session.commit()

        self.run_async(_test())


if __name__ == "__main__":
    unittest.main()

