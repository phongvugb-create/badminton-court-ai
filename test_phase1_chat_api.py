import os
import sys
import unittest
import asyncio

# Setup path to backend
BACKEND_DIR = os.path.join(os.path.dirname(__file__), "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.ai.llm_provider import BaseLLMProvider, GeminiLLMProvider
from app.ai.chatbot_service import ChatbotService, get_chatbot_service
from app.core.security import create_access_token, decode_token
from app.schemas.all_schemas import AIChatRequest, AIChatResponse

class MockLLMProvider(BaseLLMProvider):
    def __init__(self, reply_text="Chào bạn! Tôi là Trợ lý AI test."):
        self._reply_text = reply_text
        self._called_count = 0

    @property
    def provider_name(self) -> str:
        return "MockLLMProvider"

    @property
    def model_name(self) -> str:
        return "mock-model-v1"

    async def generate_text(self, system_instruction: str, user_message: str, history=None, timeout=8.0) -> str:
        self._called_count += 1
        if "error_trigger" in user_message:
            raise RuntimeError("Simulated network timeout/error")
        return f"{self._reply_text} (Echo: {user_message})"


class FailingLLMProvider(BaseLLMProvider):
    @property
    def provider_name(self) -> str:
        return "FailingLLMProvider"

    @property
    def model_name(self) -> str:
        return "failing-model"

    async def generate_text(self, system_instruction: str, user_message: str, history=None, timeout=8.0) -> str:
        raise TimeoutError("LLM API timed out after 8.0s")


class TestPhase1Chatbot(unittest.TestCase):
    def setUp(self):
        self.mock_provider = MockLLMProvider()
        self.service = ChatbotService(llm_provider=self.mock_provider)

    def test_01_llm_provider_abstraction(self):
        """Test 1: LLM Provider abstraction works properly"""
        self.assertEqual(self.mock_provider.provider_name, "MockLLMProvider")
        self.assertEqual(self.mock_provider.model_name, "mock-model-v1")

    def test_02_chatbot_service_flow(self):
        """Test 2: Chatbot service processes user message and standardizes output"""
        res = asyncio.run(self.service.handle_message(
            message="Xin chào",
            conversation_id="conv_test_123"
        ))

        self.assertIn("answer", res)
        self.assertIn("reply", res)
        self.assertEqual(res["conversation_id"], "conv_test_123")
        self.assertTrue(res["message_id"].startswith("msg_"))
        self.assertEqual(res["status"], "success")
        self.assertIn("Xin chào", res["answer"])

    def test_03_conversation_id_generation(self):
        """Test 3: Auto-generate conversation_id when None or empty is provided"""
        res = asyncio.run(self.service.handle_message(
            message="Tìm sân Cầu Giấy",
            conversation_id=None
        ))
        self.assertTrue(res["conversation_id"].startswith("conv_"))
        self.assertTrue(len(res["conversation_id"]) > 10)

    def test_04_fallback_handling_on_failure(self):
        """Test 4: Graceful fallback when LLM provider fails"""
        failing_service = ChatbotService(llm_provider=FailingLLMProvider())
        res = asyncio.run(failing_service.handle_message(
            message="Bảng giá sân giờ vàng thế nào?",
            conversation_id="conv_fail_1"
        ))

        self.assertEqual(res["status"], "fallback")
        self.assertIn("answer", res)
        # Verify fallback contains helpful domain information
        self.assertTrue(len(res["answer"]) > 20)

    def test_05_schema_validation(self):
        """Test 5: Pydantic schemas AIChatRequest & AIChatResponse"""
        req = AIChatRequest(
            message="Xin chào",
            conversation_id="conv_abc",
            context="home_page"
        )
        self.assertEqual(req.message, "Xin chào")
        self.assertEqual(req.conversation_id, "conv_abc")

        resp = AIChatResponse(
            answer="Phản hồi từ AI",
            reply="Phản hồi từ AI",
            conversation_id="conv_abc",
            message_id="msg_xyz"
        )
        self.assertEqual(resp.answer, "Phản hồi từ AI")
        self.assertEqual(resp.reply, "Phản hồi từ AI")
        self.assertEqual(resp.conversation_id, "conv_abc")
        self.assertEqual(resp.message_id, "msg_xyz")

    def test_06_auth_token_integration(self):
        """Test 6: Existing system authentication tokens can be decoded and verified"""
        token = create_access_token(subject=1, role="CUSTOMER")
        payload = decode_token(token)
        self.assertIsNotNone(payload)
        self.assertEqual(payload.get("sub"), "1")
        self.assertEqual(payload.get("role"), "CUSTOMER")

        # Invalid token rejection
        invalid_payload = decode_token("invalid.token.here")
        self.assertIsNone(invalid_payload)


if __name__ == "__main__":
    unittest.main()
