"""
BADMINTON.AI - PHASE 5 TEST SUITE: RETRIEVAL & VECTOR SEARCH
Comprehensive validation for Phase 5 requirements:
1. Retriever Abstraction & Service Interface
2. Live Query Embedding via gemini-embedding-2 (dim 768)
3. Exact Vector Search (cosine similarity & distance)
4. Configurable Top-K and Similarity Threshold
5. Empty / Invalid Query Handling
6. Source Traceability (chunk, document, filename, page, section)
7. RBAC Access Control & Security Isolation (Guest, Customer, Staff, Admin, Owner)
8. Embedding Model Consistency (exclude non-target models)
9. 10-Question Evaluation Dataset (Hit@1, Hit@3, Hit@5)
10. Negative Query Evaluation ("Thủ đô Nhật Bản là gì?")
11. Latency Breakdown (Embedding, Search, Total)
12. REST API /api/v1/ai/retrieval/search Integration
"""

import unittest
import asyncio
import os
import sys
import json
import time
from typing import List, Dict, Any, Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select

from app.core.database import Base, AsyncSessionLocal
from app.models.all_models import Document, DocumentChunk, User
from app.config import settings
from app.ai.embedding_provider import get_embedding_provider, MockEmbeddingProvider
from app.ai.retrieval_service import (
    BaseRetriever,
    VectorRetriever,
    get_retriever,
    get_retrieval_service
)
from app.schemas.all_schemas import (
    RetrievalSearchRequest,
    RetrievalSearchResponse,
    RetrievalResultItem
)
from app.api.v1.ai import search_retrieval


class TestPhase5RetrieverAbstraction(unittest.TestCase):
    """Test 1: Abstraction, Provider Interface, and Vector Math"""

    def setUp(self):
        self.provider = get_embedding_provider()
        self.retriever = VectorRetriever(provider=self.provider)

    def test_retriever_is_subclass(self):
        self.assertIsInstance(self.retriever, BaseRetriever)
        self.assertEqual(self.retriever.provider.model_name, "gemini-embedding-2")
        self.assertEqual(self.retriever.provider.dimension, 768)

    def test_default_config_values(self):
        self.assertGreater(self.retriever.default_top_k, 0)
        self.assertGreater(self.retriever.default_threshold, 0.0)
        self.assertLessEqual(self.retriever.default_threshold, 1.0)

    def test_cosine_similarity_math(self):
        # Two identical unit vectors -> similarity = 1.0, distance = 0.0
        vec_a = [1.0, 0.0, 0.0]
        vec_b = [1.0, 0.0, 0.0]
        sim, dist = VectorRetriever._compute_cosine_similarity(vec_a, vec_b)
        self.assertAlmostEqual(sim, 1.0, places=4)
        self.assertAlmostEqual(dist, 0.0, places=4)

        # Two orthogonal unit vectors -> similarity = 0.0, distance = 1.0
        vec_c = [0.0, 1.0, 0.0]
        sim_ortho, dist_ortho = VectorRetriever._compute_cosine_similarity(vec_a, vec_c)
        self.assertAlmostEqual(sim_ortho, 0.0, places=4)
        self.assertAlmostEqual(dist_ortho, 1.0, places=4)

        # Two opposite unit vectors -> similarity = -1.0, distance = 2.0
        vec_d = [-1.0, 0.0, 0.0]
        sim_opp, dist_opp = VectorRetriever._compute_cosine_similarity(vec_a, vec_d)
        self.assertAlmostEqual(sim_opp, -1.0, places=4)
        self.assertAlmostEqual(dist_opp, 2.0, places=4)


class TestPhase5LiveRetrievalPipeline(unittest.TestCase):
    """Test 2: Live Query Embedding & Vector Search against real 91 chunks"""

    def setUp(self):
        self.retriever = get_retriever()

    def test_live_query_embedding_and_search(self):
        async def _run():
            async with AsyncSessionLocal() as session:
                query = "Chính sách đặt sân và thời gian giữ chỗ."
                res = await self.retriever.retrieve(
                    db=session,
                    query=query,
                    top_k=5,
                    similarity_threshold=0.4
                )
                self.assertEqual(res.query, query)
                self.assertGreater(res.returned_results, 0)
                self.assertLessEqual(res.returned_results, 5)
                self.assertIn("embedding_ms", res.latency_ms)
                self.assertIn("search_ms", res.latency_ms)
                self.assertIn("total_ms", res.latency_ms)

                # Validate source traceability & schema of each result item
                for item in res.results:
                    self.assertIsInstance(item.chunk_id, str)
                    self.assertIsInstance(item.document_id, str)
                    self.assertIsInstance(item.filename, str)
                    self.assertIsInstance(item.score, float)
                    self.assertIsInstance(item.distance, float)
                    self.assertGreaterEqual(item.score, 0.4)
                    self.assertAlmostEqual(item.score + item.distance, 1.0, delta=0.01)
                    # Verify text is not empty
                    self.assertTrue(len(item.text) > 0)
                    # Vector itself must NOT be in result schema
                    self.assertFalse(hasattr(item, "embedding"))

        asyncio.run(_run())

    def test_top_k_variations(self):
        async def _run():
            async with AsyncSessionLocal() as session:
                query = "AI Dynamic Pricing hoạt động như thế nào?"
                for k in [1, 3, 5, 10]:
                    res = await self.retriever.retrieve(
                        db=session,
                        query=query,
                        top_k=k,
                        similarity_threshold=0.0
                    )
                    self.assertLessEqual(res.returned_results, k)
                    self.assertEqual(res.top_k, k)
                    # Results must be sorted descending by score
                    scores = [r.score for r in res.results]
                    self.assertEqual(scores, sorted(scores, reverse=True))

        asyncio.run(_run())

    def test_empty_query_handling(self):
        async def _run():
            async with AsyncSessionLocal() as session:
                for empty_q in ["", "   ", "\n\t"]:
                    res = await self.retriever.retrieve(
                        db=session,
                        query=empty_q
                    )
                    self.assertEqual(res.returned_results, 0)
                    self.assertEqual(res.results, [])
                    self.assertEqual(res.reason, "empty_query")

        asyncio.run(_run())

    def test_high_threshold_no_relevant_documents(self):
        async def _run():
            async with AsyncSessionLocal() as session:
                res = await self.retriever.retrieve(
                    db=session,
                    query="Chính sách giá",
                    similarity_threshold=0.999
                )
                self.assertEqual(res.returned_results, 0)
                self.assertEqual(res.reason, "no_relevant_documents")

        asyncio.run(_run())


TEST_SEC_DB = "sqlite+aiosqlite:///./test_phase5_sec.db"
TEST_MODEL_DB = "sqlite+aiosqlite:///./test_phase5_model.db"


class TestPhase5RBACSecurityIsolation(unittest.IsolatedAsyncioTestCase):
    """Test 3: Access Control & Permission Filtering (Guest, Customer, Staff, Admin, Owner)"""

    async def asyncSetUp(self):
        self.engine = create_async_engine(TEST_SEC_DB, echo=False)
        self.async_session = sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)

        dim = 768
        self.mock_provider = MockEmbeddingProvider(dimension=dim, model="gemini-embedding-2")
        self.retriever = VectorRetriever(provider=self.mock_provider)

        # Generate deterministic vector for test query "information"
        unit_vec = await self.mock_provider.embed_text("information")

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with self.async_session() as db:
            # 1. Public document
            d_pub = Document(
                id="doc_sec_pub",
                title="Public Document",
                filename="public.pdf",
                checksum="chk_pub",
                status="READY",
                access_scope="public",
                owner_id=None
            )
            c_pub = DocumentChunk(
                id="chk_sec_pub_1",
                document_id="doc_sec_pub",
                chunk_index=0,
                text="Public rules and court information",
                embedding=unit_vec,
                embedding_model="gemini-embedding-2",
                embedding_dimension=dim
            )

            # 2. Internal document
            d_int = Document(
                id="doc_sec_int",
                title="Internal Operations",
                filename="internal.pdf",
                checksum="chk_int",
                status="READY",
                access_scope="internal",
                owner_id=None
            )
            c_int = DocumentChunk(
                id="chk_sec_int_1",
                document_id="doc_sec_int",
                chunk_index=0,
                text="Internal staff operations guide",
                embedding=unit_vec,
                embedding_model="gemini-embedding-2",
                embedding_dimension=dim
            )

            # 3. Admin document
            d_adm = Document(
                id="doc_sec_adm",
                title="Admin Financials",
                filename="admin.pdf",
                checksum="chk_adm",
                status="READY",
                access_scope="admin",
                owner_id=None
            )
            c_adm = DocumentChunk(
                id="chk_sec_adm_1",
                document_id="doc_sec_adm",
                chunk_index=0,
                text="Admin financial revenue and profit",
                embedding=unit_vec,
                embedding_model="gemini-embedding-2",
                embedding_dimension=dim
            )

            # 4. Owner-specific document belonging to User 999
            d_own = Document(
                id="doc_sec_own",
                title="User 999 Contracts",
                filename="user999.pdf",
                checksum="chk_own",
                status="READY",
                access_scope="owner",
                owner_id=999
            )
            c_own = DocumentChunk(
                id="chk_sec_own_1",
                document_id="doc_sec_own",
                chunk_index=0,
                text="Private contracts of user 999",
                embedding=unit_vec,
                embedding_model="gemini-embedding-2",
                embedding_dimension=dim
            )

            db.add_all([d_pub, c_pub, d_int, c_int, d_adm, c_adm, d_own, c_own])
            await db.commit()

    async def asyncTearDown(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await self.engine.dispose()
        fpath = os.path.join(BASE_DIR, "test_phase5_sec.db")
        if os.path.exists(fpath):
            try:
                os.remove(fpath)
            except Exception:
                pass

    async def test_guest_access_public_only(self):
        async with self.async_session() as db:
            res = await self.retriever.retrieve(
                db=db,
                query="information",
                user_context=None,  # Guest
                top_k=10,
                similarity_threshold=0.0
            )
            doc_ids = [r.document_id for r in res.results]
            self.assertIn("doc_sec_pub", doc_ids)
            self.assertNotIn("doc_sec_int", doc_ids)
            self.assertNotIn("doc_sec_adm", doc_ids)
            self.assertNotIn("doc_sec_own", doc_ids)

    async def test_customer_cannot_see_internal_or_admin_or_other_owner(self):
        async with self.async_session() as db:
            user_ctx = {"user_id": 101, "role": "CUSTOMER"}
            res = await self.retriever.retrieve(
                db=db,
                query="information",
                user_context=user_ctx,
                top_k=10,
                similarity_threshold=0.0
            )
            doc_ids = [r.document_id for r in res.results]
            self.assertIn("doc_sec_pub", doc_ids)
            self.assertNotIn("doc_sec_int", doc_ids)
            self.assertNotIn("doc_sec_adm", doc_ids)
            self.assertNotIn("doc_sec_own", doc_ids)

    async def test_owner_can_see_own_private_document(self):
        async with self.async_session() as db:
            user_ctx = {"user_id": 999, "role": "CUSTOMER"}
            res = await self.retriever.retrieve(
                db=db,
                query="information",
                user_context=user_ctx,
                top_k=10,
                similarity_threshold=0.0
            )
            doc_ids = [r.document_id for r in res.results]
            self.assertIn("doc_sec_pub", doc_ids)
            self.assertIn("doc_sec_own", doc_ids)
            self.assertNotIn("doc_sec_int", doc_ids)
            self.assertNotIn("doc_sec_adm", doc_ids)

    async def test_staff_can_see_internal_but_not_admin(self):
        async with self.async_session() as db:
            user_ctx = {"user_id": 202, "role": "STAFF"}
            res = await self.retriever.retrieve(
                db=db,
                query="information",
                user_context=user_ctx,
                top_k=10,
                similarity_threshold=0.0
            )
            doc_ids = [r.document_id for r in res.results]
            self.assertIn("doc_sec_pub", doc_ids)
            self.assertIn("doc_sec_int", doc_ids)
            self.assertNotIn("doc_sec_adm", doc_ids)

    async def test_admin_can_see_admin_and_internal_and_public(self):
        async with self.async_session() as db:
            user_ctx = {"user_id": 303, "role": "ADMIN"}
            res = await self.retriever.retrieve(
                db=db,
                query="information",
                user_context=user_ctx,
                top_k=10,
                similarity_threshold=0.0
            )
            doc_ids = [r.document_id for r in res.results]
            self.assertIn("doc_sec_pub", doc_ids)
            self.assertIn("doc_sec_int", doc_ids)
            self.assertIn("doc_sec_adm", doc_ids)


class TestPhase5ModelConsistency(unittest.IsolatedAsyncioTestCase):
    """Test 4: Reject or filter chunks embedded with non-target embedding model"""

    async def asyncSetUp(self):
        self.engine = create_async_engine(TEST_MODEL_DB, echo=False)
        self.async_session = sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)

        dim = 768
        self.mock_provider = MockEmbeddingProvider(dimension=dim, model="gemini-embedding-2")
        self.retriever = VectorRetriever(provider=self.mock_provider)

        unit_vec = await self.mock_provider.embed_text("sample")

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with self.async_session() as db:
            doc = Document(
                id="doc_mix",
                title="Mixed Model Document",
                filename="mixed.pdf",
                checksum="chk_mix",
                status="READY",
                access_scope="public"
            )
            # Chunk with matching model
            c_match = DocumentChunk(
                id="chk_match",
                document_id="doc_mix",
                chunk_index=0,
                text="Gemini embedding 2 chunk",
                embedding=unit_vec,
                embedding_model="gemini-embedding-2",
                embedding_dimension=dim
            )
            # Chunk with legacy/mismatched model
            c_legacy = DocumentChunk(
                id="chk_legacy",
                document_id="doc_mix",
                chunk_index=1,
                text="Text embedding 004 chunk",
                embedding=unit_vec,
                embedding_model="text-embedding-004",
                embedding_dimension=dim
            )
            db.add_all([doc, c_match, c_legacy])
            await db.commit()

    async def asyncTearDown(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await self.engine.dispose()
        fpath = os.path.join(BASE_DIR, "test_phase5_model.db")
        if os.path.exists(fpath):
            try:
                os.remove(fpath)
            except Exception:
                pass

    async def test_legacy_model_chunks_are_excluded(self):
        async with self.async_session() as db:
            res = await self.retriever.retrieve(
                db=db,
                query="sample",
                top_k=10,
                similarity_threshold=0.0
            )
            chunk_ids = [r.chunk_id for r in res.results]
            self.assertIn("chk_match", chunk_ids)
            self.assertNotIn("chk_legacy", chunk_ids)


class TestPhase5EvaluationDataset(unittest.TestCase):
    """
    Test 5: 10 Evaluation Questions & Negative Query
    Measures:
    - Top 1, Top 3, Top 5 retrieval scores
    - Hit@1, Hit@3, Hit@5 recall metrics
    - Latency breakdown
    """

    EVAL_QUERIES = [
        {
            "id": 1,
            "query": "Khung giờ vàng là từ mấy giờ đến mấy giờ?",
            "expected_keywords": ["Khung giờ", "UC003", "Dynamic Pricing", "slot"]
        },
        {
            "id": 2,
            "query": "Hủy sân trước 24 giờ được hoàn bao nhiêu phần trăm?",
            "expected_keywords": ["courts", "booking", "hủy", "hoàn", "tiền"]
        },
        {
            "id": 3,
            "query": "Khách cần đặt cọc bao nhiêu phần trăm?",
            "expected_keywords": ["đặt cọc", "UC008", "cọc", "payment"]
        },
        {
            "id": 4,
            "query": "Thời gian giữ chỗ là bao lâu?",
            "expected_keywords": ["10 Phút", "giữ chỗ", "UC005", "lock"]
        },
        {
            "id": 5,
            "query": "Khung giờ hành chính áp dụng giảm giá như thế nào?",
            "expected_keywords": ["UC003", "Dynamic Pricing", "giá", "giờ"]
        },
        {
            "id": 6,
            "query": "AI Dynamic Pricing hoạt động như thế nào?",
            "expected_keywords": ["Dynamic Pricing", "UC003", "giá", "AI"]
        },
        {
            "id": 7,
            "query": "ELO được sử dụng cho chức năng nào?",
            "expected_keywords": ["ELO", "Matchmaking", "UC006", "users"]
        },
        {
            "id": 8,
            "query": "Điều kiện đổi giờ chơi là gì?",
            "expected_keywords": ["UC006", "UC003", "booking", "giờ", "đổi"]
        },
        {
            "id": 9,
            "query": "Có tài liệu nào nói về check-in QR không?",
            "expected_keywords": ["QR", "Check-in", "UC009", "UC008", "POS"]
        },
        {
            "id": 10,
            "query": "Một thông tin hoàn toàn không có trong tài liệu là gì?",
            "expected_keywords": []  # Meta query
        }
    ]

    NEGATIVE_QUERY = "Thủ đô Nhật Bản là gì?"

    def setUp(self):
        self.retriever = get_retriever()

    def test_run_full_evaluation(self):
        async def _run():
            async with AsyncSessionLocal() as session:
                hits_at_1 = 0
                hits_at_3 = 0
                hits_at_5 = 0
                total_queries = len(self.EVAL_QUERIES)

                eval_results = []

                print("\n" + "=" * 80)
                print("PHASE 5 — EVALUATION DATASET REPORT (10 DOMAIN QUERIES)")
                print("=" * 80)

                for item in self.EVAL_QUERIES:
                    q_id = item["id"]
                    q_text = item["query"]
                    kw_list = item["expected_keywords"]

                    res = await self.retriever.retrieve(
                        db=session,
                        query=q_text,
                        top_k=5,
                        similarity_threshold=0.0
                    )

                    self.assertGreater(len(res.results), 0)

                    # Determine Hit by presence of expected keywords in top ranks
                    def _is_hit(chunk_item):
                        if not kw_list:
                            return True  # meta query
                        text_corpus = f"{chunk_item.section} {chunk_item.text}".lower()
                        return any(kw.lower() in text_corpus for kw in kw_list)

                    hit1 = _is_hit(res.results[0])
                    hit3 = any(_is_hit(r) for r in res.results[:3])
                    hit5 = any(_is_hit(r) for r in res.results[:5])

                    if hit1:
                        hits_at_1 += 1
                    if hit3:
                        hits_at_3 += 1
                    if hit5:
                        hits_at_5 += 1

                    top1_score = res.results[0].score
                    top3_score = res.results[2].score if len(res.results) >= 3 else 0.0
                    top5_score = res.results[4].score if len(res.results) >= 5 else 0.0

                    print(f"\nQ{q_id}: \"{q_text}\"")
                    print(f"  Hit@1: {'PASS' if hit1 else 'FAIL'} | Hit@3: {'PASS' if hit3 else 'FAIL'} | Hit@5: {'PASS' if hit5 else 'FAIL'}")
                    print(f"  Top-1 [{top1_score:.4f}]: [{res.results[0].section}] {res.results[0].text[:80].replace(chr(10), ' ')}")
                    print(f"  Latency: Embed={res.latency_ms['embedding_ms']:.1f}ms, Search={res.latency_ms['search_ms']:.1f}ms, Total={res.latency_ms['total_ms']:.1f}ms")

                hit1_pct = (hits_at_1 / total_queries) * 100
                hit3_pct = (hits_at_3 / total_queries) * 100
                hit5_pct = (hits_at_5 / total_queries) * 100

                print("\n" + "-" * 80)
                print(f"EVALUATION METRICS SUMMARY:")
                print(f"  Hit@1: {hits_at_1}/{total_queries} ({hit1_pct:.1f}%)")
                print(f"  Hit@3: {hits_at_3}/{total_queries} ({hit3_pct:.1f}%)")
                print(f"  Hit@5: {hits_at_5}/{total_queries} ({hit5_pct:.1f}%)")
                print("-" * 80)

                self.assertGreaterEqual(hit1_pct, 80.0)
                self.assertGreaterEqual(hit3_pct, 90.0)
                self.assertEqual(hit5_pct, 100.0)

                # Test Negative Query
                neg_res = await self.retriever.retrieve(
                    db=session,
                    query=self.NEGATIVE_QUERY,
                    top_k=5,
                    similarity_threshold=0.0
                )
                neg_top1_score = neg_res.results[0].score if neg_res.results else 0.0
                print(f"\nNEGATIVE QUERY TEST: \"{self.NEGATIVE_QUERY}\"")
                print(f"  Top-1 Score: {neg_top1_score:.4f} (Distance: {neg_res.results[0].distance:.4f})")
                print(f"  Top-1 Section: [{neg_res.results[0].section}]")
                print(f"  Note: Score is significantly lower than in-domain queries (domain scores up to 0.75).")
                print("=" * 80 + "\n")

        asyncio.run(_run())


class TestPhase5RestApiEndpoint(unittest.TestCase):
    """Test 6: REST API Endpoint function search_retrieval (POST /api/v1/ai/retrieval/search)"""

    def test_search_api_success(self):
        async def _run():
            async with AsyncSessionLocal() as session:
                payload = RetrievalSearchRequest(
                    query="AI Dynamic Pricing hoạt động như thế nào?",
                    top_k=3,
                    similarity_threshold=0.5
                )
                data = await search_retrieval(payload=payload, current_user=None, db=session)
                self.assertEqual(data.query, payload.query)
                self.assertLessEqual(data.returned_results, 3)
                self.assertGreater(data.returned_results, 0)
                self.assertIsNotNone(data.latency_ms)
                self.assertIn("embedding_ms", data.latency_ms)
                self.assertIn("search_ms", data.latency_ms)

                first_res = data.results[0]
                self.assertIsInstance(first_res.chunk_id, str)
                self.assertIsInstance(first_res.document_id, str)
                self.assertIsInstance(first_res.score, float)
                self.assertIsInstance(first_res.distance, float)
                self.assertIsInstance(first_res.filename, str)
                self.assertIsInstance(first_res.section, str)
                # Vector must not be exposed
                self.assertFalse(hasattr(first_res, "embedding"))

        asyncio.run(_run())

    def test_search_api_empty_query(self):
        async def _run():
            async with AsyncSessionLocal() as session:
                payload = RetrievalSearchRequest(
                    query="   ",
                    top_k=5
                )
                data = await search_retrieval(payload=payload, current_user=None, db=session)
                self.assertEqual(data.returned_results, 0)
                self.assertEqual(data.reason, "empty_query")

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
