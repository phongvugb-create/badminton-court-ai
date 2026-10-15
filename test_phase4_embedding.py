"""
BADMINTON.AI - PHASE 4 TEST SUITE: EMBEDDING & VECTOR DATABASE
Tests all 18 required scenarios:
1. Embedding provider abstraction
2. Embedding single text
3. Embedding batch
4. Dimension validation
5. Invalid embedding response rejection
6. Empty chunk handling
7. READY document filtering
8. Failed document filtering
9. Idempotent embedding
10. Re-embedding when force_reembed=True
11. Re-embedding when model changes
12. Vector persistence in database
13. Migration v003 upgrade
14. Migration v003 rollback
15. Access metadata preservation
16. Provider timeout handling
17. Provider failure handling
18. Partial batch failure / transaction atomicity
"""

import unittest
import asyncio
import os
import sys
import json
import math
from datetime import datetime

# Setup sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.future import select

from app.core.database import Base
from app.models.all_models import Document, DocumentChunk, User
from app.ai.embedding_provider import (
    BaseEmbeddingProvider,
    GeminiEmbeddingProvider,
    MockEmbeddingProvider,
    EmbeddingError
)
from app.ai.embedding_ingestion_service import EmbeddingIngestionService
from migrations.versions import v003_phase4_embeddings

TEST_DB_URL = "sqlite+aiosqlite:///./test_phase4_embed.db"

class TestPhase4Embedding(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.engine = create_async_engine(TEST_DB_URL, echo=False)
        self.async_session = async_sessionmaker(
            self.engine, expire_on_commit=False
        )
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        self.mock_provider = MockEmbeddingProvider(dimension=768, model="text-embedding-004")
        self.service = EmbeddingIngestionService(provider=self.mock_provider)

    async def asyncTearDown(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await self.engine.dispose()
        db_file = os.path.join(BASE_DIR, "test_phase4_embed.db")
        if os.path.exists(db_file):
            try:
                os.remove(db_file)
            except Exception:
                pass

    # 1. Provider Abstraction
    def test_01_provider_abstraction(self):
        self.assertIsInstance(self.mock_provider, BaseEmbeddingProvider)
        self.assertEqual(self.mock_provider.dimension, 768)
        self.assertEqual(self.mock_provider.model_name, "text-embedding-004")

    # 2. Embedding Single Text
    async def test_02_embed_single_text(self):
        vec = await self.mock_provider.embed_text("Hệ thống cho thuê sân cầu lông AI")
        self.assertEqual(len(vec), 768)
        self.assertIsInstance(vec[0], float)
        # Check L2 norm is ~ 1.0
        norm = math.sqrt(sum(x * x for x in vec))
        self.assertAlmostEqual(norm, 1.0, places=4)

    # 3. Embedding Batch
    async def test_03_embed_batch(self):
        texts = [
            "Bảng giá thuê sân 50.000đ - 180.000đ/giờ",
            "Cơ chế khóa giữ chỗ 10 phút chống xung đột",
            "Chính sách hoàn cọc 100% trước 24h"
        ]
        vectors = await self.mock_provider.embed_texts(texts)
        self.assertEqual(len(vectors), 3)
        for v in vectors:
            self.assertEqual(len(v), 768)

    # 4. Dimension Validation
    def test_04_dimension_validation(self):
        valid_vec = [0.1] * 768
        self.mock_provider.validate_vector(valid_vec)

        # Mismatched dimension (767 != 768)
        invalid_dim_vec = [0.1] * 767
        with self.assertRaises(ValueError):
            self.mock_provider.validate_vector(invalid_dim_vec)

    # 5. Invalid Embedding Response Rejection (NaN / Inf)
    def test_05_nan_inf_rejection(self):
        nan_vec = [0.1] * 767 + [float("nan")]
        with self.assertRaises(ValueError):
            self.mock_provider.validate_vector(nan_vec)

        inf_vec = [0.1] * 767 + [float("inf")]
        with self.assertRaises(ValueError):
            self.mock_provider.validate_vector(inf_vec)

    # 6. Empty Chunk Handling
    async def test_06_empty_chunk_handling(self):
        vec = await self.mock_provider.embed_text("")
        self.assertEqual(len(vec), 768)

    # Helper to insert test document & chunks
    async def _create_test_document(self, db, doc_id="doc_test_1", status="READY", chunk_count=3):
        doc = Document(
            id=doc_id,
            title="Tài liệu thử nghiệm",
            filename="test.txt",
            source_type="policy",
            mime_type="text/plain",
            checksum="chk_12345",
            version=1,
            status=status,
            total_chunks=chunk_count,
            access_scope="public",
            created_at=datetime.utcnow()
        )
        db.add(doc)
        await db.flush()

        for i in range(chunk_count):
            c = DocumentChunk(
                id=f"chunk_{doc_id}_{i}",
                document_id=doc_id,
                chunk_index=i,
                text=f"Nội dung phân đoạn thử nghiệm {i} về quy định thể thao.",
                section="Quy định",
                meta_info=json.dumps({"access_scope": "public"}),
                created_at=datetime.utcnow()
            )
            db.add(c)
        await db.commit()

    # 7. READY Document Filtering
    async def test_07_ready_document_filtering(self):
        async with self.async_session() as db:
            await self._create_test_document(db, doc_id="doc_ready", status="READY", chunk_count=2)
            report = await self.service.embed_document_chunks(db, "doc_ready")
            self.assertEqual(report.status, "COMPLETED")
            self.assertEqual(report.embedded_chunks, 2)

    # 8. Failed / Processing Document Filtering
    async def test_08_failed_document_filtering(self):
        async with self.async_session() as db:
            await self._create_test_document(db, doc_id="doc_failed", status="FAILED", chunk_count=2)
            with self.assertRaises(ValueError):
                await self.service.embed_document_chunks(db, "doc_failed")

            await self._create_test_document(db, doc_id="doc_proc", status="PROCESSING", chunk_count=2)
            with self.assertRaises(ValueError):
                await self.service.embed_document_chunks(db, "doc_proc")

    # 9. Idempotent Embedding (Skip already embedded chunks)
    async def test_09_idempotent_embedding(self):
        async with self.async_session() as db:
            await self._create_test_document(db, doc_id="doc_idemp", status="READY", chunk_count=3)
            # Run 1: Embeds 3 chunks
            rep1 = await self.service.embed_document_chunks(db, "doc_idemp")
            self.assertEqual(rep1.embedded_chunks, 3)

            # Run 2: Skips 3 chunks
            rep2 = await self.service.embed_document_chunks(db, "doc_idemp")
            self.assertEqual(rep2.embedded_chunks, 0)
            self.assertEqual(rep2.skipped_chunks, 3)
            self.assertEqual(rep2.status, "ALREADY_UP_TO_DATE")

    # 10. Re-embedding when force_reembed=True
    async def test_10_force_reembed(self):
        async with self.async_session() as db:
            await self._create_test_document(db, doc_id="doc_force", status="READY", chunk_count=2)
            await self.service.embed_document_chunks(db, "doc_force")

            # Force re-embed
            rep = await self.service.embed_document_chunks(db, "doc_force", force_reembed=True)
            self.assertEqual(rep.embedded_chunks, 2)
            self.assertEqual(rep.skipped_chunks, 0)

    # 11. Re-embedding when Model Changes (e.g. Model A -> Model B)
    async def test_11_reembed_on_model_change(self):
        async with self.async_session() as db:
            await self._create_test_document(db, doc_id="doc_model_change", status="READY", chunk_count=2)
            # Embed with Model A
            await self.service.embed_document_chunks(db, "doc_model_change")

            # Switch provider to Model B
            new_provider = MockEmbeddingProvider(dimension=768, model="text-embedding-005")
            new_service = EmbeddingIngestionService(provider=new_provider)

            # Should automatically detect model mismatch and re-embed without force flag
            rep = await new_service.embed_document_chunks(db, "doc_model_change")
            self.assertEqual(rep.embedded_chunks, 2)
            self.assertEqual(rep.embedding_model, "text-embedding-005")

    # 12. Vector Persistence in Database
    async def test_12_vector_persistence(self):
        async with self.async_session() as db:
            await self._create_test_document(db, doc_id="doc_persist", status="READY", chunk_count=1)
            await self.service.embed_document_chunks(db, "doc_persist")

            stmt = select(DocumentChunk).where(DocumentChunk.document_id == "doc_persist")
            res = await db.execute(stmt)
            chunk = res.scalar_one()

            self.assertIsNotNone(chunk.embedding)
            self.assertEqual(chunk.embedding_model, "text-embedding-004")
            self.assertEqual(chunk.embedding_dimension, 768)
            self.assertIsNotNone(chunk.embedded_at)

    # 13. Migration v003 Upgrade Execution
    def test_13_migration_upgrade(self):
        import sqlite3
        conn = sqlite3.connect(":memory:")
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE document_chunks (id TEXT PRIMARY KEY, document_id TEXT, text TEXT);")
        v003_phase4_embeddings.upgrade(cursor, dialect_name="sqlite")

        # Verify new columns added
        cursor.execute("PRAGMA table_info(document_chunks);")
        columns = [row[1] for row in cursor.fetchall()]
        self.assertIn("embedding", columns)
        self.assertIn("embedding_model", columns)
        self.assertIn("embedding_dimension", columns)
        self.assertIn("embedded_at", columns)
        conn.close()

    # 14. Migration v003 Rollback Execution
    def test_14_migration_rollback(self):
        import sqlite3
        conn = sqlite3.connect(":memory:")
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE document_chunks (id TEXT PRIMARY KEY, document_id TEXT, text TEXT, embedding TEXT);")
        v003_phase4_embeddings.downgrade(cursor, dialect_name="sqlite")
        conn.close()

    # 15. Access Metadata Preservation
    async def test_15_access_metadata_preservation(self):
        async with self.async_session() as db:
            await self._create_test_document(db, doc_id="doc_access", status="READY", chunk_count=1)
            await self.service.embed_document_chunks(db, "doc_access")

            # Check chunk still has intact document link and meta_info
            stmt = select(DocumentChunk, Document).join(Document, DocumentChunk.document_id == Document.id).where(
                DocumentChunk.document_id == "doc_access"
            )
            res = await db.execute(stmt)
            row = res.first()
            self.assertIsNotNone(row)
            assert row is not None
            chunk, doc = row
            self.assertEqual(doc.access_scope, "public")
            self.assertEqual(chunk.document_id, "doc_access")

    # 16. Provider Timeout Handling
    async def test_16_provider_timeout_handling(self):
        class TimingOutProvider(BaseEmbeddingProvider):
            @property
            def provider_name(self): return "timeout"
            @property
            def model_name(self): return "timeout-model"
            @property
            def dimension(self): return 768
            async def embed_text(self, text):
                raise asyncio.TimeoutError("Timeout kết nối embedding")
            async def embed_texts(self, texts):
                raise asyncio.TimeoutError("Timeout kết nối embedding")

        svc = EmbeddingIngestionService(provider=TimingOutProvider())
        async with self.async_session() as db:
            await self._create_test_document(db, doc_id="doc_timeout", status="READY", chunk_count=2)
            rep = await svc.embed_document_chunks(db, "doc_timeout")
            self.assertIn(rep.status, ["PARTIAL_FAILURE", "FAILED"])
            self.assertEqual(rep.failed_chunks, 2)

    # 17. Provider Failure Handling
    async def test_17_provider_failure_handling(self):
        class FailingProvider(BaseEmbeddingProvider):
            @property
            def provider_name(self): return "fail"
            @property
            def model_name(self): return "fail-model"
            @property
            def dimension(self): return 768
            async def embed_text(self, text):
                raise RuntimeError("API lỗi HTTP 500")
            async def embed_texts(self, texts):
                raise RuntimeError("API lỗi HTTP 500")

        svc = EmbeddingIngestionService(provider=FailingProvider())
        async with self.async_session() as db:
            await self._create_test_document(db, doc_id="doc_fail", status="READY", chunk_count=2)
            rep = await svc.embed_document_chunks(db, "doc_fail")
            self.assertEqual(rep.failed_chunks, 2)

    # 18. Partial Batch Failure & Transaction Atomicity
    async def test_18_partial_batch_failure_atomicity(self):
        call_count = 0
        class FlakyProvider(BaseEmbeddingProvider):
            @property
            def provider_name(self): return "flaky"
            @property
            def model_name(self): return "flaky-model"
            @property
            def dimension(self): return 768
            async def embed_text(self, text):
                return [0.1] * 768
            async def embed_texts(self, texts):
                nonlocal call_count
                call_count += 1
                if call_count == 2:
                    raise RuntimeError("Sự cố ở batch thứ 2")
                return [[0.1] * 768 for _ in texts]

        svc = EmbeddingIngestionService(provider=FlakyProvider())
        async with self.async_session() as db:
            # 4 chunks with batch_size=2 -> 2 batches
            await self._create_test_document(db, doc_id="doc_flaky", status="READY", chunk_count=4)
            rep = await svc.embed_document_chunks(db, "doc_flaky", batch_size=2)
            self.assertEqual(rep.embedded_chunks, 2)
            self.assertEqual(rep.failed_chunks, 2)
            self.assertEqual(rep.status, "PARTIAL_FAILURE")

    # 19. Production Fallback Disabled: Raises Error on API Failure
    async def test_19_production_fallback_disabled_raises_error(self):
        # Case A: Provider with explicitly empty API key
        gemini_provider_no_key = GeminiEmbeddingProvider(model="gemini-embedding-2", dimension=768)
        gemini_provider_no_key._api_key = ""
        with self.assertRaises(RuntimeError) as ctx:
            await gemini_provider_no_key.embed_texts(["Thử nghiệm vector không có API key"])
        self.assertIn("GEMINI_API_KEY chưa được cấu hình", str(ctx.exception))

        # Case B: Provider with invalid API key (must raise on API 401, not return fallback vector)
        gemini_provider_bad_key = GeminiEmbeddingProvider(api_key="AIza_Invalid_Key_Test_Only", model="gemini-embedding-2", dimension=768)
        with self.assertRaises((EmbeddingError, RuntimeError)) as ctx2:
            await gemini_provider_bad_key.embed_texts(["Thử nghiệm vector với invalid key"])
        self.assertTrue(
            "không hợp lệ" in str(ctx2.exception).lower()
            or "api key" in str(ctx2.exception).lower()
            or "thất bại" in str(ctx2.exception).lower()
        )

    # 20. Model & Dimension Configuration Consistency
    def test_20_model_and_dimension_consistency(self):
        prov = GeminiEmbeddingProvider(model="gemini-embedding-2", dimension=768)
        self.assertEqual(prov.model_name, "gemini-embedding-2")
        self.assertEqual(prov.dimension, 768)
        self.assertEqual(prov.provider_name, "gemini")
        self.assertEqual(prov.embedding_version, "v1")

    # 21. Vector Dimension Strict Validation
    def test_21_vector_dimension_strict_validation(self):
        # 512 dimensions instead of 768
        invalid_vec = [0.1] * 512
        with self.assertRaises(ValueError) as ctx:
            self.mock_provider.validate_vector(invalid_vec)
        self.assertIn("Kích thước vector không khớp", str(ctx.exception))

        # Vector containing NaN
        nan_vec = [0.1] * 767 + [float("nan")]
        with self.assertRaises(ValueError) as ctx:
            self.mock_provider.validate_vector(nan_vec)
        self.assertIn("NaN hoặc Infinity", str(ctx.exception))

    # 22. Invalidation and Re-Embedding Pipeline Flow
    async def test_22_invalidation_and_reembedding(self):
        async with self.async_session() as db:
            await self._create_test_document(db, doc_id="doc_reembed", status="READY", chunk_count=3)
            # Initial embed
            rep1 = await self.service.embed_document_chunks(db, "doc_reembed")
            self.assertEqual(rep1.embedded_chunks, 3)

            # Invalidate explicitly
            invalidated = await self.service.invalidate_document_embeddings(db, "doc_reembed")
            self.assertEqual(invalidated, 3)

            # Verify all vectors are None
            stmt = select(DocumentChunk).where(DocumentChunk.document_id == "doc_reembed")
            res = await db.execute(stmt)
            chunks = res.scalars().all()
            for c in chunks:
                self.assertIsNone(c.embedding)
                self.assertIsNone(c.embedding_model)

            # Force re-embed with new model
            new_provider = MockEmbeddingProvider(dimension=768, model="gemini-embedding-2")
            new_service = EmbeddingIngestionService(provider=new_provider)
            rep2 = await new_service.embed_document_chunks(db, "doc_reembed", force_reembed=True)
            self.assertEqual(rep2.embedded_chunks, 3)
            self.assertEqual(rep2.embedding_model, "gemini-embedding-2")

    # 23. No Mixed Embedding Models Guarantee
    async def test_23_no_mixed_embedding_models(self):
        async with self.async_session() as db:
            await self._create_test_document(db, doc_id="doc_nomix", status="READY", chunk_count=4)
            # Embed with model A
            old_provider = MockEmbeddingProvider(dimension=768, model="text-embedding-004")
            old_svc = EmbeddingIngestionService(provider=old_provider)
            await old_svc.embed_document_chunks(db, "doc_nomix")

            # Now switch to model B (gemini-embedding-2)
            new_provider = MockEmbeddingProvider(dimension=768, model="gemini-embedding-2")
            new_svc = EmbeddingIngestionService(provider=new_provider)
            await new_svc.embed_document_chunks(db, "doc_nomix")

            # Check all chunks have ONLY gemini-embedding-2
            stmt = select(DocumentChunk).where(DocumentChunk.document_id == "doc_nomix")
            res = await db.execute(stmt)
            chunks = res.scalars().all()
            models = {c.embedding_model for c in chunks}
            self.assertEqual(models, {"gemini-embedding-2"})
            self.assertNotIn("text-embedding-004", models)

    # 24. Migration v004 Upgrade & Downgrade
    def test_24_migration_v004_metadata(self):
        import sqlite3
        from migrations.versions import v004_phase4_1_metadata
        conn = sqlite3.connect(":memory:")
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE document_chunks (id TEXT PRIMARY KEY, embedding TEXT);")
        v004_phase4_1_metadata.upgrade(cursor, dialect_name="sqlite")

        cursor.execute("PRAGMA table_info(document_chunks);")
        columns = [row[1] for row in cursor.fetchall()]
        self.assertIn("embedding_version", columns)

        v004_phase4_1_metadata.downgrade(cursor, dialect_name="sqlite")
        conn.close()

if __name__ == "__main__":
    unittest.main()
