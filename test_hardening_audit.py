import os
import sys
import json
import asyncio
import unittest
from unittest.mock import patch

# Setup path
BACKEND_DIR = os.path.join(os.path.dirname(__file__), "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.ai.llm_provider import BaseLLMProvider, GeminiLLMProvider
from app.ai.chatbot_service import ChatbotService
from app.api.v1.ai import chat_with_ai, get_chat_user
from app.schemas.all_schemas import AIChatRequest, AIChatResponse
from app.core.security import create_access_token, decode_token
from fastapi import HTTPException

DUMMY_SECRET_KEY = "AIzaSySecretApiKey123456789TestKey"

class TimeoutMockProvider(BaseLLMProvider):
    @property
    def provider_name(self) -> str:
        return "TimeoutMockProvider"

    @property
    def model_name(self) -> str:
        return "mock-timeout"

    async def generate_text(self, system_instruction: str, user_message: str, history=None, timeout=10.0) -> str:
        raise TimeoutError(f"Request to https://generativelanguage.googleapis.com?key={DUMMY_SECRET_KEY} timed out")


class UnavailableMockProvider(BaseLLMProvider):
    @property
    def provider_name(self) -> str:
        return "UnavailableMockProvider"

    @property
    def model_name(self) -> str:
        return "mock-503"

    async def generate_text(self, system_instruction: str, user_message: str, history=None, timeout=10.0) -> str:
        raise ConnectionError(f"HTTP 503 Service Unavailable on https://generativelanguage.googleapis.com?key={DUMMY_SECRET_KEY}")


class TestHardeningAndAudit(unittest.TestCase):
    def setUp(self):
        self.service = ChatbotService(llm_provider=TimeoutMockProvider())

    def test_01_safe_fallback_no_fake_business_numbers(self):
        """KIỂM TRA 1: Fallback không chứa số liệu giá tiền hay chính sách bịa đặt"""
        res = asyncio.run(self.service.handle_message(
            message="Bảng giá thuê sân giờ vàng là bao nhiêu?",
            conversation_id="conv_safe_1"
        ))

        self.assertEqual(res["status"], "fallback")
        answer = res["answer"]
        # Phải thông báo gián đoạn kết nối trung thực
        self.assertIn("gián đoạn tạm thời", answer)
        self.assertIn("1900 6868", answer)

        # KHÔNG được chứa các số liệu/chính sách giả mạo hard-code
        banned_phrases = ["70.000", "130.000", "giảm 15%", "phụ thu 25%", "cọc 50%", "hoàn cọc 100%"]
        for phrase in banned_phrases:
            self.assertNotIn(phrase, answer, f"Phát hiện dữ liệu hard-code bị cấm: {phrase}")

    def test_02_api_key_not_leaked_in_response_or_error(self):
        """KIỂM TRA 2: API Key không bị rò rỉ trong câu trả lời hay log khi có ngoại lệ"""
        res = asyncio.run(self.service.handle_message(
            message="Test prompt",
            conversation_id="conv_secret_test"
        ))
        # API key tuyệt đối không xuất hiện trong answer hoặc reply
        self.assertNotIn(DUMMY_SECRET_KEY, json.dumps(res))

    def test_03_unauthorized_request(self):
        """KIỂM TRA 5: Token không hợp lệ bị từ chối 401 Unauthorized"""
        # Test giải mã token hỏng
        payload = decode_token("malformed.jwt.token")
        self.assertIsNone(payload)

        # Test dependency get_chat_user từ chối token hỏng
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(get_chat_user(token="invalid_token", db=None))
        self.assertEqual(ctx.exception.status_code, 401)
        self.assertIn("Token không hợp lệ", ctx.exception.detail)

    def test_04_empty_message_rejected(self):
        """KIỂM TRA: Tin nhắn rỗng hoặc chỉ chứa khoảng trắng phải bị từ chối 400"""
        req_empty = AIChatRequest(message="")
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(chat_with_ai(req_empty, current_user=None))
        self.assertEqual(ctx.exception.status_code, 400)

        req_spaces = AIChatRequest(message="   \n\t  ")
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(chat_with_ai(req_spaces, current_user=None))
        self.assertEqual(ctx.exception.status_code, 400)

    def test_05_llm_timeout_handled_gracefully(self):
        """KIỂM TRA 3: Timeout của LLM được bọc an toàn và chuyển sang fallback"""
        timeout_svc = ChatbotService(llm_provider=TimeoutMockProvider())
        res = asyncio.run(timeout_svc.handle_message(
            message="Hỏi câu hỏi bất kỳ",
            conversation_id="conv_timeout"
        ))
        self.assertEqual(res["status"], "fallback")
        self.assertTrue(len(res["answer"]) > 0)
        self.assertEqual(res["conversation_id"], "conv_timeout")
        self.assertTrue(res["message_id"].startswith("msg_"))

    def test_06_llm_unavailable_handled_gracefully(self):
        """KIỂM TRA 3: LLM mất kết nối/503 được xử lý êm thấm không gây crash 500"""
        unavail_svc = ChatbotService(llm_provider=UnavailableMockProvider())
        res = asyncio.run(unavail_svc.handle_message(
            message="Hỏi câu hỏi khi máy chủ sập",
            conversation_id="conv_503"
        ))
        self.assertEqual(res["status"], "fallback")
        self.assertIn("gián đoạn", res["answer"])

    def test_07_conversation_id_sanitization(self):
        """KIỂM TRA 2: conversation_id chứa ký tự độc hại được làm sạch an toàn"""
        malicious_id = "../../etc/passwd; DROP TABLE users; -- <script>"
        res = asyncio.run(self.service.handle_message(
            message="Kiểm tra chống injection ID",
            conversation_id=malicious_id
        ))
        # Chỉ giữ lại a-zA-Z0-9_-
        self.assertNotIn("..", res["conversation_id"])
        self.assertNotIn("/", res["conversation_id"])
        self.assertNotIn(";", res["conversation_id"])
        self.assertNotIn("<", res["conversation_id"])
        self.assertTrue(res["conversation_id"].startswith("etcpasswdDROPTABLEusers"))

    def test_08_user_identity_tracking(self):
        """KIỂM TRA 5: Danh tính user_id được ghi nhận và truyền tải cho kiểm toán/phân quyền"""
        user_info = {
            "id": 999,
            "name": "Nguyễn Văn Test",
            "phone": "0988888888",
            "role": "MEMBER"
        }
        res = asyncio.run(self.service.handle_message(
            message="Xin chào từ thành viên",
            conversation_id="conv_member_1",
            user_info=user_info
        ))
        self.assertEqual(res.get("user_id"), "999")


if __name__ == "__main__":
    unittest.main()
