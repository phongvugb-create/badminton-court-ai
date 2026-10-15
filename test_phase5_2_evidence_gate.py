"""
BADMINTON.AI - PHASE 5.2 TEST SUITE: EVIDENCE GATE
Validates post-retrieval evidence evaluation:
1. Valid factual evidence (P1: 10 phút, P5: VNPay/ZaloPay/MOMO)
2. Valid numeric evidence (P1: time duration 10 phút)
3. Valid procedural / policy evidence (P2: Dynamic Pricing, P3: ELO, P4: QR check-in)
4. Topical but insufficient evidence
5. Negative out-of-domain query ("no_relevant_documents")
6. Negative test N7 ("Hủy sân trước 24 giờ được hoàn bao nhiêu phần trăm?" -> "insufficient_evidence")
7. Empty query handling ("empty_query")
8. No retrieval result above high threshold ("no_relevant_documents")
9. RBAC permission preservation (Permission filter runs before Evidence Gate)
10. Source metadata preservation (document_id, chunk_id, filename, section, score, distance)
11. Optional apply_evidence_gate=False audit mode
12. PostgreSQL pgvector SQL compilation validation
"""

import os
import sys
import json
import asyncio
import unittest

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from sqlalchemy.future import select
from sqlalchemy import and_, or_

from app.core.database import AsyncSessionLocal
from app.models.all_models import Document, DocumentChunk, _HAS_PGVECTOR
from app.ai.retrieval_service import get_retriever, VectorRetriever
from app.ai.evidence_gate import get_evidence_gate, RuleBasedEvidenceGate, QueryType
from app.schemas.all_schemas import RetrievalResultItem


class TestPhase52EvidenceGate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(cls.loop)
        cls.retriever = get_retriever()
        cls.evidence_gate = get_evidence_gate()

    @classmethod
    def tearDownClass(cls):
        cls.loop.close()

    def run_async(self, coro):
        return self.loop.run_until_complete(coro)

    # -------------------------------------------------------------------------
    # TEST 1: VALID FACTUAL EVIDENCE (P1 & P5)
    # -------------------------------------------------------------------------
    def test_01_valid_factual_evidence(self):
        """P1 & P5: Factual queries must match valid evidence chunks with positive matches."""
        async def _test():
            async with AsyncSessionLocal() as session:
                # P1: Giữ chỗ bao lâu
                res_p1 = await self.retriever.retrieve(session, "Thời gian giữ chỗ là bao lâu?")
                self.assertGreater(res_p1.returned_results, 0, "P1 should return valid results")
                self.assertIsNone(res_p1.reason)
                for item in res_p1.results:
                    self.assertTrue(item.evidence_match, "P1 results must have evidence_match=True")
                    self.assertIn("10 phút", item.text.lower(), "P1 text must contain '10 phút'")
                    self.assertTrue(len(item.evidence_reason) > 5, "P1 evidence_reason must be populated")

                # P5: Khách đặt cọc qua cổng nào
                res_p5 = await self.retriever.retrieve(session, "Khách đặt cọc qua cổng nào?")
                self.assertGreater(res_p5.returned_results, 0, "P5 should return valid results")
                self.assertIsNone(res_p5.reason)
                has_gateway = any(
                    any(gw in item.text.lower() for gw in ["vnpay", "zalopay", "momo"])
                    for item in res_p5.results
                )
                self.assertTrue(has_gateway, "P5 results must mention VNPay, ZaloPay, or MOMO")
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 2: VALID NUMERIC EVIDENCE
    # -------------------------------------------------------------------------
    def test_02_valid_numeric_evidence(self):
        """Questions requiring numeric duration must match chunks with actual numeric quantities."""
        async def _test():
            async with AsyncSessionLocal() as session:
                res = await self.retriever.retrieve(session, "Thời gian giữ chỗ là bao lâu?")
                self.assertGreater(len(res.results), 0)
                top_item = res.results[0]
                self.assertTrue(top_item.evidence_match)
                self.assertIn("10 phút", top_item.text.lower())
                self.assertIn("10 phút", top_item.evidence_reason)
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 3: VALID PROCEDURAL EVIDENCE (P2, P3, P4)
    # -------------------------------------------------------------------------
    def test_03_valid_procedural_evidence(self):
        """Procedural queries P2 (Dynamic Pricing), P3 (ELO), P4 (QR check-in) must find mechanism evidence."""
        async def _test():
            async with AsyncSessionLocal() as session:
                # P2: AI Dynamic Pricing
                res_p2 = await self.retriever.retrieve(session, "AI Dynamic Pricing hoạt động như thế nào?")
                self.assertGreater(res_p2.returned_results, 0)
                p2_top = res_p2.results[0]
                self.assertTrue(p2_top.evidence_match)
                self.assertTrue(
                    any(term in p2_top.text.lower() for term in ["dự báo nhu cầu", "lấp đầy", "đề xuất", "giá"]),
                    "P2 must contain operational mechanism terms"
                )

                # P3: ELO Rating
                res_p3 = await self.retriever.retrieve(session, "ELO được sử dụng cho chức năng nào?")
                self.assertGreater(res_p3.returned_results, 0)
                p3_top = res_p3.results[0]
                self.assertTrue(p3_top.evidence_match)
                self.assertTrue(
                    any(term in p3_top.text.lower() for term in ["matchmaking", "đối thủ", "ghép", "trình độ"]),
                    "P3 must state matchmaking purpose"
                )

                # P4: Check-in QR
                res_p4 = await self.retriever.retrieve(session, "Check-in QR hoạt động như thế nào?")
                self.assertGreater(res_p4.returned_results, 0)
                p4_top = res_p4.results[0]
                self.assertTrue(p4_top.evidence_match)
                self.assertTrue(
                    any(term in p4_top.text.lower() for term in ["quét mã qr", "quét", "xác nhận check-in", "vào sân"]),
                    "P4 must contain QR check-in procedure"
                )
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 4: TOPICAL BUT INSUFFICIENT EVIDENCE
    # -------------------------------------------------------------------------
    def test_04_topical_but_insufficient_evidence(self):
        """Queries matching court/booking topics but lacking specific policy facts must be marked insufficient."""
        async def _test():
            async with AsyncSessionLocal() as session:
                query = "Khách được đền bù bao nhiêu tiền nếu chủ sân tự ý hủy sân?"
                res = await self.retriever.retrieve(session, query)
                # May match booking chunks on similarity, but none contains monetary compensation rules
                self.assertEqual(res.returned_results, 0)
                self.assertIn(res.reason, ["insufficient_evidence", "no_relevant_documents"])
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 5: NEGATIVE OUT-OF-DOMAIN QUERY
    # -------------------------------------------------------------------------
    def test_05_negative_out_of_domain_query(self):
        """Out-of-domain query fails similarity threshold -> reason='no_relevant_documents'."""
        async def _test():
            async with AsyncSessionLocal() as session:
                res = await self.retriever.retrieve(session, "Thủ đô Nhật Bản là gì?")
                self.assertEqual(res.returned_results, 0)
                self.assertEqual(res.reason, "no_relevant_documents")
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 6: MANDATORY NEGATIVE TEST N7
    # -------------------------------------------------------------------------
    def test_06_n7_cancellation_24h_refund(self):
        """
        N7: 'Hủy sân trước 24 giờ được hoàn bao nhiêu phần trăm?'
        Similarity can be high (~0.7216), but chunk lacks 24-hour refund rule.
        System MUST reject it: evidence_match=False, returned_results=0, reason='insufficient_evidence'.
        """
        async def _test():
            async with AsyncSessionLocal() as session:
                # 1. Test with Evidence Gate applied (default)
                res = await self.retriever.retrieve(session, "Hủy sân trước 24 giờ được hoàn bao nhiêu phần trăm?")
                self.assertEqual(res.returned_results, 0, "N7 must return 0 valid evidence chunks")
                self.assertEqual(res.reason, "insufficient_evidence", "Reason must be 'insufficient_evidence'")
                self.assertEqual(len(res.results), 0)

                # 2. Test with apply_evidence_gate=False to verify raw candidate evaluation
                res_raw = await self.retriever.retrieve(
                    session,
                    "Hủy sân trước 24 giờ được hoàn bao nhiêu phần trăm?",
                    apply_evidence_gate=False
                )
                self.assertGreater(res_raw.returned_results, 0, "Raw candidates exist with similarity >= 0.58")
                top_raw = res_raw.results[0]
                self.assertGreaterEqual(top_raw.score, 0.70, "Raw top candidate similarity is ~0.72")
                self.assertFalse(top_raw.evidence_match, "Top candidate must fail evidence_match")
                self.assertIn("24 giờ", top_raw.evidence_reason, "Reason must mention missing 24-hour condition")
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 7: EMPTY QUERY
    # -------------------------------------------------------------------------
    def test_07_empty_query(self):
        """Empty or whitespace-only queries must return reason='empty_query'."""
        async def _test():
            async with AsyncSessionLocal() as session:
                res1 = await self.retriever.retrieve(session, "")
                self.assertEqual(res1.returned_results, 0)
                self.assertEqual(res1.reason, "empty_query")

                res2 = await self.retriever.retrieve(session, "   ")
                self.assertEqual(res2.returned_results, 0)
                self.assertEqual(res2.reason, "empty_query")
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 8: NO RETRIEVAL RESULT (HIGH THRESHOLD)
    # -------------------------------------------------------------------------
    def test_08_no_retrieval_result_high_threshold(self):
        """When similarity threshold is impossibly high (0.999), reason='no_relevant_documents'."""
        async def _test():
            async with AsyncSessionLocal() as session:
                res = await self.retriever.retrieve(
                    session,
                    "Thời gian giữ chỗ là bao lâu?",
                    similarity_threshold=0.999
                )
                self.assertEqual(res.returned_results, 0)
                self.assertEqual(res.reason, "no_relevant_documents")
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 9: RBAC PRESERVATION
    # -------------------------------------------------------------------------
    def test_09_rbac_preservation(self):
        """Evidence Gate does NOT bypass RBAC. Permission filtering runs first at DB query level."""
        async def _test():
            async with AsyncSessionLocal() as session:
                # Guest context: only public documents
                guest_res = await self.retriever.retrieve(
                    session,
                    "Cấu hình hệ thống server",
                    user_context={"role": "GUEST"}
                )
                for item in guest_res.results:
                    self.assertEqual(item.access_scope, "public", "Guest can only see public documents")

                # Admin context: can see all
                admin_res = await self.retriever.retrieve(
                    session,
                    "Cấu hình hệ thống server",
                    user_context={"role": "ADMIN"}
                )
                self.assertIsNotNone(admin_res)
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 10: SOURCE TRACEABILITY PRESERVATION
    # -------------------------------------------------------------------------
    def test_10_source_preservation(self):
        """Valid evidence items must retain complete provenance metadata."""
        async def _test():
            async with AsyncSessionLocal() as session:
                res = await self.retriever.retrieve(session, "Thời gian giữ chỗ là bao lâu?")
                self.assertGreater(len(res.results), 0)
                for item in res.results:
                    self.assertTrue(item.chunk_id.startswith("chunk_"), f"Invalid chunk_id: {item.chunk_id}")
                    self.assertTrue(len(item.document_id) > 0, "Missing document_id")
                    self.assertTrue(item.filename.endswith((".docx", ".txt", ".pdf")), f"Invalid filename: {item.filename}")
                    self.assertIsNotNone(item.score)
                    self.assertIsNotNone(item.distance)
                    self.assertIsNotNone(item.similarity)
                    self.assertIsNotNone(item.section)
                    self.assertIsNotNone(item.evidence_match)
                    self.assertIsNotNone(item.evidence_reason)
        self.run_async(_test())

    # -------------------------------------------------------------------------
    # TEST 11: DIRECT EVIDENCE GATE UNIT TESTS
    # -------------------------------------------------------------------------
    def test_11_evidence_gate_unit_evaluation(self):
        """Direct unit evaluation of RuleBasedEvidenceGate methods."""
        gate = RuleBasedEvidenceGate()

        # Classify queries
        c1 = gate.classify_query("Thời gian giữ chỗ là bao lâu?")
        self.assertEqual(c1.query_type, QueryType.FACTUAL)
        self.assertTrue(c1.requires_duration)

        c2 = gate.classify_query("Hủy sân trước 24 giờ được hoàn bao nhiêu phần trăm?")
        self.assertEqual(c2.query_type, QueryType.POLICY)
        self.assertTrue(c2.requires_percentage)
        self.assertIn("24 giờ", c2.specific_time_conditions)

        c3 = gate.classify_query("AI Dynamic Pricing hoạt động như thế nào?")
        self.assertEqual(c3.query_type, QueryType.PROCEDURAL)

        # Mock item without 24 hours
        fake_item = RetrievalResultItem(
            chunk_id="chunk_test_1",
            document_id="doc_test_1",
            text="Bảng courts và time_slots: Quản lý đặt sân thể thao cầu lông.",
            score=0.72,
            distance=0.28,
            filename="test.docx"
        )
        eval_n7 = gate.evaluate_item("Hủy sân trước 24 giờ được hoàn bao nhiêu phần trăm?", fake_item, c2)
        self.assertFalse(eval_n7.evidence_match)
        self.assertIn("24 giờ", eval_n7.evidence_reason)

    # -------------------------------------------------------------------------
    # TEST 12: POSTGRESQL PGVECTOR SQL COMPILATION
    # -------------------------------------------------------------------------
    def test_12_pgvector_sql_compilation(self):
        """Validates that PostgreSQL pgvector <=> SQL queries compile without dialect errors."""
        from sqlalchemy.dialects import postgresql
        vec = [0.0] * 768
        dist_expr = DocumentChunk.embedding.cosine_distance(vec)
        sim_expr = 1.0 - dist_expr

        stmt = (
            select(DocumentChunk, dist_expr.label("distance"), sim_expr.label("similarity"))
            .where(sim_expr >= 0.58)
            .order_by(dist_expr.asc())
        )

        compiled = str(stmt.compile(dialect=postgresql.dialect()))
        self.assertIn("<=>", compiled, "PostgreSQL dialect must compile native pgvector <=> operator")


if __name__ == "__main__":
    unittest.main()
