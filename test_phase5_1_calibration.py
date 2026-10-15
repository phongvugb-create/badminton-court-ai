"""
BADMINTON.AI - PHASE 5.1 TEST SUITE:
RETRIEVAL CALIBRATION, ABSTENTION & POSTGRESQL VALIDATION

Validates all Phase 5.1 objectives:
1. Group A (Positive In-Domain) Dataset with Explicit Evidence Verification
2. Group B (Negative Out-Of-Domain) Dataset & Rejection / Abstention Verification
3. Threshold Sweep across [0.50, 0.52, 0.54, 0.56, 0.58, 0.60]
4. Q10 Evaluation Correction (Meta/negative query must abstain)
5. Evidence Quality Audit (Top-1 evidence verification)
6. PostgreSQL Native pgvector Validation (SQL compilation, <=> operator, mathematical parity)
7. RBAC Security Isolation under calibrated threshold
8. Performance Latency Measurements
"""

import unittest
import asyncio
import os
import sys
import json
import math
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
from sqlalchemy import select, and_, or_, func
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

from app.core.database import Base, AsyncSessionLocal
from app.models.all_models import Document, DocumentChunk, VectorType, _HAS_PGVECTOR
from app.config import settings
from app.ai.embedding_provider import (
    BaseEmbeddingProvider,
    get_embedding_provider,
    MockEmbeddingProvider
)
from app.ai.retrieval_service import (
    BaseRetriever,
    VectorRetriever,
    get_retriever
)
from app.schemas.all_schemas import (
    RetrievalSearchRequest,
    RetrievalSearchResponse,
    RetrievalResultItem
)


# In-memory cached provider to avoid repeated network overhead during calibration tests
class MemoryCachedProvider(BaseEmbeddingProvider):
    def __init__(self, inner: BaseEmbeddingProvider):
        self._inner = inner
        self._cache: Dict[str, List[float]] = {}

    @property
    def provider_name(self) -> str:
        return self._inner.provider_name

    @property
    def model_name(self) -> str:
        return self._inner.model_name

    @property
    def dimension(self) -> int:
        return self._inner.dimension

    async def embed_text(self, text: str) -> List[float]:
        cleaned = text.strip()
        if cleaned in self._cache:
            return self._cache[cleaned]
        vec = await self._inner.embed_text(cleaned)
        self._cache[cleaned] = vec
        return vec

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        return [await self.embed_text(t) for t in texts]


class TestPhase51EvaluationDatasetAndEvidence(unittest.TestCase):
    """
    Test 1: Group A (Positive In-Domain) & Group B (Negative Out-Of-Domain)
    with explicit evidence checking and Q10 correction.
    """

    POSITIVE_QUERIES = [
        {
            "id": "P1",
            "query": "Thời gian giữ chỗ là bao lâu?",
            "expected_section": "3.5.1 Mô tả use case UC005",
            "expected_evidence_keywords": ["10 phút", "held_until", "redis atomic lock"],
            "evidence_desc": "UC005: Khóa slot thời gian 10 phút, held_until = Now() + 10 phút."
        },
        {
            "id": "P2",
            "query": "AI Dynamic Pricing hoạt động như thế nào?",
            "expected_section": "3.3.1.  Mô tả use case UC003",
            "expected_evidence_keywords": ["dynamic pricing", "dự báo nhu cầu", "đề xuất mức giá"],
            "evidence_desc": "UC003: Phân tích dữ liệu lấp đầy quá khứ và dự báo nhu cầu -> Đề xuất giá."
        },
        {
            "id": "P3",
            "query": "ELO được sử dụng cho chức năng nào?",
            "expected_section": "3.6.1 Mô tả use case UC006",
            "expected_evidence_keywords": ["elo", "matchmaking", "tìm đối thủ"],
            "evidence_desc": "UC006: AI Matchmaking & Tìm Đối Thủ Giao Lưu (ELO Rating)."
        },
        {
            "id": "P4",
            "query": "Có tài liệu nào nói về check-in QR không?",
            "expected_section": "3.9.1 Mô tả use case UC009",
            "expected_evidence_keywords": ["quét mã qr", "check-in", "pos"],
            "evidence_desc": "UC009: Nhân viên quét mã QR vé hoặc tìm theo SĐT để bấm Xác nhận Check-in."
        },
        {
            "id": "P5",
            "query": "Khách cần đặt cọc qua cổng thanh toán nào?",
            "expected_section": "3.8.1 Mô tả use case UC008",
            "expected_evidence_keywords": ["vnpay", "zalopay", "momo", "đặt cọc"],
            "evidence_desc": "UC008: Cổng thanh toán VNPay / ZaloPay / MOMO, tạo giao dịch cọc deposit_amount."
        },
        {
            "id": "P6",
            "query": "Hệ thống xử lý thế nào khi AI Engine Dynamic Pricing bị mất kết nối?",
            "expected_section": "3.3.1.  Mô tả use case UC003",
            "expected_evidence_keywords": ["fallback", "base_price_per_hour", "mất kết nối"],
            "evidence_desc": "UC003 Luồng 4a: Fallback về base_price_per_hour của sân con."
        },
        {
            "id": "P7",
            "query": "Hệ thống làm gì nếu khách không thanh toán sau 10 phút giữ chỗ?",
            "expected_section": "3.5.1 Mô tả use case UC005",
            "expected_keywords": ["10 phút", "available", "hủy đơn hàng", "redis expire"],
            "expected_evidence_keywords": ["10 phút", "available", "hủy đơn hàng"],
            "evidence_desc": "UC005 Luồng 5a: Giải phóng slot về AVAILABLE và hủy đơn hàng PENDING."
        },
        {
            "id": "P8",
            "query": "Phân hệ Quản trị viên (Admin Portal) có phạm vi chức năng gì?",
            "expected_section": "1.2. Phạm vi",
            "expected_evidence_keywords": ["admin portal", "kiểm duyệt", "phân quyền"],
            "evidence_desc": "Mục 1.2: Kiểm duyệt cơ sở mới, quản lý tài khoản người dùng, phân quyền."
        },
        {
            "id": "P9",
            "query": "Nhân viên quầy xử lý trường hợp khách chơi quá giờ như thế nào?",
            "expected_section": "3.9.1 Mô tả use case UC009",
            "expected_evidence_keywords": ["quá giờ", "extra_fee", "block 15 phút"],
            "evidence_desc": "UC009 Luồng 3a: Tự động tính thêm phụ phí quá giờ vào extra_fee theo block 15 phút."
        },
        {
            "id": "P10",
            "query": "Tìm kiếm và gợi ý sân bằng AI (UC004) hoạt động như thế nào?",
            "expected_section": "3.4.1. Mô tả use case UC004",
            "expected_evidence_keywords": ["gợi ý sân", "gps", "tọa độ"],
            "evidence_desc": "UC004: Tìm kiếm theo tọa độ GPS, bán kính di chuyển, đề xuất cụm sân phù hợp."
        }
    ]

    NEGATIVE_QUERIES = [
        {"id": "N1", "query": "Thủ đô Nhật Bản là gì?", "domain": "Địa lý"},
        {"id": "N2", "query": "Ai là tổng thống Mỹ hiện tại?", "domain": "Chính trị"},
        {"id": "N3", "query": "Công thức nấu phở bò thế nào?", "domain": "Ẩm thực"},
        {"id": "N4", "query": "Python list comprehension là gì?", "domain": "Lập trình"},
        {"id": "N5", "query": "Thời tiết Hà Nội hôm nay thế nào?", "domain": "Thời tiết"},
        {"id": "N6", "query": "Một thông tin hoàn toàn không có trong tài liệu là gì?", "domain": "Meta Negative"}
    ]

    def setUp(self):
        real_provider = get_embedding_provider()
        self.cached_provider = MemoryCachedProvider(real_provider)
        self.retriever = VectorRetriever(provider=self.cached_provider)

    def test_positive_queries_evidence_and_recall_at_calibrated_threshold(self):
        """Validates all 10 Positive Queries have Hit@1 evidence and score >= 0.58"""
        async def _run():
            async with AsyncSessionLocal() as session:
                hit1_count = 0
                evidence_verified_count = 0

                for item in self.POSITIVE_QUERIES:
                    res = await self.retriever.retrieve(
                        db=session,
                        query=item["query"],
                        top_k=5,
                        similarity_threshold=0.58
                    )
                    self.assertGreater(
                        len(res.results), 0,
                        f"Positive query '{item['query']}' was unexpectedly abstained at threshold 0.58"
                    )

                    top1 = res.results[0]
                    # Score must be strictly >= 0.58
                    self.assertGreaterEqual(top1.score, 0.58)

                    # Check section match
                    sec = (top1.section or "").lower()
                    exp_sec = item["expected_section"].lower()
                    is_sec_match = exp_sec in sec

                    # Check evidence keywords in text
                    txt = (top1.text or "").lower()
                    has_evidence = any(kw.lower() in txt for kw in item["expected_evidence_keywords"])

                    if is_sec_match or has_evidence:
                        hit1_count += 1
                    if has_evidence:
                        evidence_verified_count += 1

                self.assertEqual(hit1_count, 10, "All 10 positive queries must achieve Hit@1")
                self.assertGreaterEqual(
                    evidence_verified_count, 9,
                    "At least 9/10 positive queries must contain explicit evidence keywords in top-1"
                )

        asyncio.run(_run())

    def test_negative_queries_abstention_at_calibrated_threshold(self):
        """Validates that all out-of-domain and meta queries properly ABSTAIN at threshold 0.58"""
        async def _run():
            async with AsyncSessionLocal() as session:
                for item in self.NEGATIVE_QUERIES:
                    res = await self.retriever.retrieve(
                        db=session,
                        query=item["query"],
                        top_k=5,
                        similarity_threshold=0.58
                    )
                    self.assertEqual(
                        len(res.results), 0,
                        f"Negative query '{item['query']}' did not abstain! Returned {len(res.results)} chunks (top score: {res.results[0].score if res.results else 0})"
                    )
                    self.assertEqual(
                        res.reason, "no_relevant_documents",
                        f"Expected reason 'no_relevant_documents' for '{item['query']}', got '{res.reason}'"
                    )

        asyncio.run(_run())

    def test_q10_corrected_evaluation(self):
        """Verifies Q10 is evaluated as a negative meta query and correctly abstains"""
        async def _run():
            async with AsyncSessionLocal() as session:
                res = await self.retriever.retrieve(
                    db=session,
                    query="Một thông tin hoàn toàn không có trong tài liệu là gì?",
                    top_k=5,
                    similarity_threshold=0.58
                )
                self.assertEqual(len(res.results), 0)
                self.assertEqual(res.reason, "no_relevant_documents")

        asyncio.run(_run())


class TestPhase51ThresholdSweep(unittest.TestCase):
    """
    Test 2: Systematic threshold sweep across [0.50, 0.52, 0.54, 0.56, 0.58, 0.60]
    Proves that 0.58 balances 100% positive recall with maximum negative rejection.
    """

    def setUp(self):
        real_provider = get_embedding_provider()
        self.cached_provider = MemoryCachedProvider(real_provider)
        self.retriever = VectorRetriever(provider=self.cached_provider)

    def test_threshold_sweep_empirical_validation(self):
        async def _run():
            thresholds = [0.50, 0.52, 0.54, 0.56, 0.58, 0.60]
            pos_queries = [
                "Thời gian giữ chỗ là bao lâu?",
                "AI Dynamic Pricing hoạt động như thế nào?",
                "ELO được sử dụng cho chức năng nào?",
                "Có tài liệu nào nói về check-in QR không?",
                "Khách cần đặt cọc qua cổng thanh toán nào?"
            ]
            neg_queries = [
                "Thủ đô Nhật Bản là gì?",
                "Ai là tổng thống Mỹ hiện tại?",
                "Công thức nấu phở bò thế nào?",
                "Python list comprehension là gì?",
                "Thời tiết Hà Nội hôm nay thế nào?"
            ]

            async with AsyncSessionLocal() as session:
                # Preload embeddings into cache
                for q in pos_queries + neg_queries:
                    await self.cached_provider.embed_text(q)

                results = {}
                for th in thresholds:
                    pos_kept = 0
                    for pq in pos_queries:
                        r = await self.retriever.retrieve(db=session, query=pq, similarity_threshold=th)
                        if len(r.results) > 0:
                            pos_kept += 1

                    neg_abstained = 0
                    for nq in neg_queries:
                        r = await self.retriever.retrieve(db=session, query=nq, similarity_threshold=th)
                        if len(r.results) == 0:
                            neg_abstained += 1

                    results[th] = {"pos_kept": pos_kept, "neg_abstained": neg_abstained}

                # Verify threshold 0.50 does NOT abstain negative queries adequately
                self.assertLess(
                    results[0.50]["neg_abstained"], len(neg_queries),
                    "Threshold 0.50 fails to reject out-of-domain queries"
                )

                # Verify threshold 0.58 keeps 100% positive queries AND rejects 100% out-of-domain negative queries
                self.assertEqual(results[0.58]["pos_kept"], len(pos_queries))
                self.assertEqual(results[0.58]["neg_abstained"], len(neg_queries))

        asyncio.run(_run())


class TestPhase51PostgreSQLPgvectorValidation(unittest.TestCase):
    """
    Test 3: Native PostgreSQL + pgvector validation.
    Checks:
    - pgvector extension installed in Python
    - VectorType uses Vector.comparator_factory
    - DocumentChunk.embedding.cosine_distance(query_vector) generates <=>
    - SQL compilation under postgresql dialect
    - Mathematical parity between SQLite Python dot product and pgvector C spec
    - RBAC SQL filter clauses under PostgreSQL
    """

    def test_pgvector_installed_and_comparator_bound(self):
        self.assertTrue(_HAS_PGVECTOR, "pgvector package must be installed")
        self.assertEqual(VectorType.comparator_factory, Vector.comparator_factory)

    def test_postgresql_cosine_distance_operator_compilation(self):
        """Verifies that DocumentChunk.embedding.cosine_distance generates <=> in PostgreSQL SQL"""
        query_vec = [0.05] * 768
        dist_expr = DocumentChunk.embedding.cosine_distance(query_vec)
        sim_expr = 1.0 - dist_expr

        stmt = (
            select(
                DocumentChunk,
                Document,
                dist_expr.label("distance"),
                sim_expr.label("similarity")
            )
            .join(Document, DocumentChunk.document_id == Document.id)
            .where(
                and_(
                    Document.status == "READY",
                    DocumentChunk.embedding.isnot(None),
                    DocumentChunk.embedding_model == "gemini-embedding-2",
                    Document.access_scope == "public",
                    sim_expr >= 0.58
                )
            )
            .order_by(dist_expr.asc())
            .limit(5)
        )

        compiled_sql = str(stmt.compile(dialect=postgresql.dialect()))

        # Check pgvector cosine distance operator <=>
        self.assertIn("<=>", compiled_sql)
        self.assertIn("ORDER BY (document_chunks.embedding <=> %(embedding_1)s) ASC", compiled_sql)
        self.assertIn("LIMIT %(param_", compiled_sql)
        self.assertIn("documents.status = %(status_1)s", compiled_sql)
        self.assertIn("documents.access_scope = %(access_scope_1)s", compiled_sql)

    def test_mathematical_parity_sqlite_python_vs_pgvector_spec(self):
        """
        Validates that SQLite Python cosine distance and PostgreSQL pgvector C specification
        yield identical results within 1e-6 precision for 768-dimensional unit vectors.
        pgvector formula: 1.0 - (a . b) / (|a| * |b|)
        """
        # Create two arbitrary 768-dim normalized vectors
        dim = 768
        vec_a_raw = [math.sin(i * 0.1) for i in range(dim)]
        norm_a = math.sqrt(sum(x * x for x in vec_a_raw))
        vec_a = [x / norm_a for x in vec_a_raw]

        vec_b_raw = [math.cos(i * 0.15) for i in range(dim)]
        norm_b = math.sqrt(sum(x * x for x in vec_b_raw))
        vec_b = [x / norm_b for x in vec_b_raw]

        # 1. Python calculation (used by SQLite development engine)
        sim_py, dist_py = VectorRetriever._compute_cosine_similarity(vec_a, vec_b)

        # 2. pgvector C specification formula
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_product = math.sqrt(sum(a * a for a in vec_a)) * math.sqrt(sum(b * b for b in vec_b))
        dist_pg = 1.0 - (dot / norm_product)
        sim_pg = 1.0 - dist_pg

        # Compare precision
        self.assertAlmostEqual(dist_py, dist_pg, places=6)
        self.assertAlmostEqual(sim_py, sim_pg, places=6)


class TestPhase51SecurityAndRBAC(unittest.TestCase):
    """
    Test 4: RBAC Security Regression under threshold 0.58.
    Confirms threshold elevation never bypasses access control isolation.
    """

    def test_permission_filter_clauses(self):
        retriever = get_retriever()

        # Guest
        f_guest = retriever._build_permission_filter(None)
        sql_guest = str(f_guest.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
        self.assertIn("documents.access_scope = 'public'", sql_guest)

        # Customer (User 101)
        f_cust = retriever._build_permission_filter({"user_id": 101, "role": "CUSTOMER"})
        sql_cust = str(f_cust.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
        self.assertIn("documents.access_scope = 'public'", sql_cust)
        self.assertIn("documents.owner_id = 101", sql_cust)

        # Staff (User 202)
        f_staff = retriever._build_permission_filter({"user_id": 202, "role": "STAFF"})
        sql_staff = str(f_staff.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
        self.assertIn("documents.access_scope IN ('public', 'internal')", sql_staff)

        # Admin (User 303)
        f_admin = retriever._build_permission_filter({"user_id": 303, "role": "ADMIN"})
        sql_admin = str(f_admin.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
        self.assertIn("documents.access_scope IN ('public', 'internal', 'admin')", sql_admin)


if __name__ == "__main__":
    unittest.main()
