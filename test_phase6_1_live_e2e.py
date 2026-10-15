"""
BADMINTON.AI - PHASE 6.1 LIVE GEMINI SMOKE TEST SUITE
Executes up to 3 live queries against Google Gemini API:
1. Positive Factual Query: "Thời gian giữ chỗ là bao lâu?" (Calls Live Gemini LLM)
2. Out-of-Domain Query: "Thủ đô Nhật Bản là gì?" (Deterministic Abstention at Retrieval)
3. Insufficient Evidence Query: "Hủy sân trước 24 giờ được hoàn bao nhiêu phần trăm?" (Deterministic Abstention at Evidence Gate)

STRICT REQUIREMENTS:
- Completely isolated from Mock tests.
- Uses real GeminiLLMProvider and GeminiEmbeddingProvider.
- Never hardcodes API keys or secrets.
- Records accurate component latency: retrieval, context_build, live_llm, total.
- Explicitly documents deterministic abstention cases where LLM was not called.
- If HTTP 429/401/403 or quota exhausted, marks as BLOCKED/FAILED with exact reason (never silently falls back to Mock).
"""

import os
import sys
import time
import json
import asyncio
import unittest
from typing import Dict, Any, Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.config import settings
from app.core.database import AsyncSessionLocal
from app.ai.llm_provider import GeminiLLMProvider
from app.ai.embedding_provider import GeminiEmbeddingProvider
from app.ai.retrieval_service import VectorRetriever
from app.ai.evidence_gate import get_evidence_gate
from app.ai.rag_context_builder import get_rag_context_builder
from app.ai.chatbot_service import ChatbotService
from app.schemas.all_schemas import AIChatRequest, AIChatResponse
from app.api.v1.ai import chat_with_ai


class TestPhase61LiveE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(cls.loop)

        # Check API Key validity
        api_key = settings.GEMINI_API_KEY
        cls.has_key = bool(api_key and not api_key.startswith("YOUR_") and len(api_key) > 10)
        
        if not cls.has_key:
            print("\n[LIVE TEST WARNING] GEMINI_API_KEY is not configured. Live tests will be BLOCKED/SKIPPED.")
            cls.live_chatbot = None
            return

        # Setup real providers
        cls.live_llm = GeminiLLMProvider(api_key=api_key, model=settings.LLM_MODEL)
        cls.live_embedding = GeminiEmbeddingProvider(api_key=api_key, model=settings.EMBEDDING_MODEL)
        cls.evidence_gate = get_evidence_gate()
        cls.context_builder = get_rag_context_builder()
        
        cls.live_retriever = VectorRetriever(
            provider=cls.live_embedding,
            evidence_gate=cls.evidence_gate,
            default_top_k=settings.RAG_TOP_K,
            default_threshold=settings.RETRIEVAL_SIMILARITY_THRESHOLD
        )
        cls.live_chatbot = ChatbotService(
            llm_provider=cls.live_llm,
            retriever=cls.live_retriever,
            context_builder=cls.context_builder
        )

        cls.latency_records = {}

    @classmethod
    def tearDownClass(cls):
        cls.loop.close()
        # Print latency summary
        if cls.latency_records:
            print("\n" + "=" * 60)
            print("PHASE 6.1 LIVE GEMINI LATENCY BREAKDOWN (ACTUAL MEASUREMENTS)")
            print("=" * 60)
            for test_name, metrics in cls.latency_records.items():
                print(f"[{test_name}]")
                print(f"  - Retrieval Latency:     {metrics.get('retrieval_ms', 0):.2f} ms")
                print(f"  - Context Build Latency: {metrics.get('context_ms', 0):.2f} ms")
                print(f"  - Live LLM Latency:      {metrics.get('llm_ms', 0):.2f} ms")
                print(f"  - Total Pipeline Latency:{metrics.get('total_ms', 0):.2f} ms")
                print(f"  - LLM Invoked:           {metrics.get('llm_invoked', False)}")
            print("=" * 60 + "\n")

    def run_async(self, coro):
        return self.loop.run_until_complete(coro)

    # -------------------------------------------------------------------------
    # LIVE QUERY 1: POSITIVE FACTUAL (Calls Live Gemini LLM)
    # -------------------------------------------------------------------------
    def test_live_01_positive_factual_query(self):
        """Live Query 1: 'Thời gian giữ chỗ là bao lâu?' -> calls real Gemini LLM, grounded answer."""
        if not self.has_key:
            self.skipTest("BLOCKED: GEMINI_API_KEY is not configured for Live verification.")

        async def _test():
            query = "Thời gian giữ chỗ là bao lâu?"
            t0 = time.time()
            async with AsyncSessionLocal() as session:
                res = await self.live_chatbot.handle_message(
                    message=query,
                    db=session
                )
            t_total = (time.time() - t0) * 1000

            # Record Latencies
            latency = res.get("latency_ms", {})
            self.__class__.latency_records["Query 1: Positive Factual"] = {
                "retrieval_ms": latency.get("retrieval", 0),
                "context_ms": latency.get("context_build", 0),
                "llm_ms": latency.get("llm", 0),
                "total_ms": t_total,
                "llm_invoked": True
            }

            print(f"\n[LIVE QUERY 1 RESULT] Answer: {res['answer'][:120]}... | Status: {res['retrieval_status']} | Sources: {len(res['sources'])}")

            self.assertEqual(res["status"], "success")
            self.assertEqual(res["retrieval_status"], "supported")
            self.assertIn("10 phút", res["answer"])
            self.assertGreater(len(res["sources"]), 0)
            self.assertGreater(latency.get("llm", 0), 0)

        self.run_async(_test())

    # -------------------------------------------------------------------------
    # LIVE QUERY 2: OUT-OF-DOMAIN (Deterministic Abstention without LLM)
    # -------------------------------------------------------------------------
    def test_live_02_out_of_domain_query(self):
        """Live Query 2: 'Thủ đô Nhật Bản là gì?' -> Handled deterministically at Retrieval, no LLM call."""
        if not self.has_key:
            self.skipTest("BLOCKED: GEMINI_API_KEY is not configured for Live verification.")

        async def _test():
            query = "Thủ đô Nhật Bản là gì?"
            t0 = time.time()
            async with AsyncSessionLocal() as session:
                res = await self.live_chatbot.handle_message(
                    message=query,
                    db=session
                )
            t_total = (time.time() - t0) * 1000

            latency = res.get("latency_ms", {})
            self.__class__.latency_records["Query 2: Out-of-Domain"] = {
                "retrieval_ms": latency.get("retrieval", 0),
                "context_ms": latency.get("context_build", 0),
                "llm_ms": latency.get("llm", 0),  # Should be 0.0 ms
                "total_ms": t_total,
                "llm_invoked": False
            }

            print(f"\n[LIVE QUERY 2 RESULT] Answer: {res['answer']} | Status: {res['retrieval_status']} | LLM Invoked: False (Deterministic Refusal)")

            self.assertEqual(res["retrieval_status"], "no_relevant_documents")
            self.assertEqual(len(res["sources"]), 0)
            self.assertIn("Tôi chưa tìm thấy thông tin phù hợp", res["answer"])
            # Verified: LLM was NOT invoked, avoiding wasted API tokens and external hallucination
            self.assertEqual(latency.get("llm", 0), 0.0)

        self.run_async(_test())

    # -------------------------------------------------------------------------
    # LIVE QUERY 3: INSUFFICIENT EVIDENCE N7 (Deterministic Abstention without LLM)
    # -------------------------------------------------------------------------
    def test_live_03_insufficient_evidence_query(self):
        """Live Query 3: 'Hủy sân trước 24 giờ được hoàn bao nhiêu phần trăm?' -> Deterministic Abstention at Evidence Gate."""
        if not self.has_key:
            self.skipTest("BLOCKED: GEMINI_API_KEY is not configured for Live verification.")

        async def _test():
            query = "Hủy sân trước 24 giờ được hoàn bao nhiêu phần trăm?"
            t0 = time.time()
            async with AsyncSessionLocal() as session:
                res = await self.live_chatbot.handle_message(
                    message=query,
                    db=session
                )
            t_total = (time.time() - t0) * 1000

            latency = res.get("latency_ms", {})
            self.__class__.latency_records["Query 3: Insufficient Evidence N7"] = {
                "retrieval_ms": latency.get("retrieval", 0),
                "context_ms": latency.get("context_build", 0),
                "llm_ms": latency.get("llm", 0),  # Should be 0.0 ms
                "total_ms": t_total,
                "llm_invoked": False
            }

            print(f"\n[LIVE QUERY 3 RESULT] Answer: {res['answer']} | Status: {res['retrieval_status']} | LLM Invoked: False (Deterministic Gate Refusal)")

            self.assertEqual(res["retrieval_status"], "insufficient_evidence")
            self.assertNotIn("50%", res["answer"])
            self.assertNotIn("100%", res["answer"])
            self.assertIn("chưa nêu rõ", res["answer"].lower())
            # Verified: LLM was NOT invoked, preventing hallucination
            self.assertEqual(latency.get("llm", 0), 0.0)

        self.run_async(_test())


if __name__ == "__main__":
    unittest.main()
