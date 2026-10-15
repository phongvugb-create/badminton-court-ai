import os
import sys
import json
import time
import socket
import threading
import unittest
import urllib.request
import urllib.error

# Ensure backend directory is in path
BACKEND_DIR = os.path.join(os.path.dirname(__file__), "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.api.v1.ai import chat_with_ai, get_chat_user
from app.schemas.all_schemas import AIChatRequest
from app.core.security import create_access_token
from server import BadmintonServerHandler
from http.server import ThreadingHTTPServer

def get_free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    return port

class TestPhase1Integration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Start server.py in background thread on ephemeral port
        cls.port = get_free_port()
        cls.server = ThreadingHTTPServer(('127.0.0.1', cls.port), BadmintonServerHandler)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        time.sleep(0.3)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_01_fastapi_route_empty_message_400(self):
        """Test FastAPI router chat_with_ai rejects empty message"""
        import asyncio
        from fastapi import HTTPException

        req = AIChatRequest(message="   ")
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(chat_with_ai(req, current_user=None))
        self.assertEqual(ctx.exception.status_code, 400)

    def test_02_fastapi_route_success(self):
        """Test FastAPI router chat_with_ai processes valid message"""
        import asyncio
        req = AIChatRequest(
            message="Xin chào Trợ lý AI",
            conversation_id="conv_fastapi_1"
        )
        res = asyncio.run(chat_with_ai(req, current_user=None))
        self.assertTrue(len(res.answer) > 0)
        self.assertEqual(res.conversation_id, "conv_fastapi_1")
        self.assertTrue(res.message_id.startswith("msg_"))

    def test_03_http_post_chat_success(self):
        """Test HTTP POST /api/chat returns 200 and valid Phase 1 JSON schema"""
        url = f"http://127.0.0.1:{self.port}/api/chat"
        payload = {
            "message": "Xin chào! Cho tôi hỏi giá thuê sân cầu lông",
            "conversation_id": "conv_http_test_1"
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=25) as response:
            self.assertEqual(response.status, 200)
            data = json.loads(response.read().decode("utf-8"))
            self.assertTrue(data.get("success"))
            self.assertIn("answer", data)
            self.assertIn("reply", data)
            self.assertEqual(data.get("conversation_id"), "conv_http_test_1")
            self.assertTrue(str(data.get("message_id")).startswith("msg_"))

    def test_04_http_post_v1_ai_chat_success(self):
        """Test HTTP POST /api/v1/ai/chat also routes properly"""
        url = f"http://127.0.0.1:{self.port}/api/v1/ai/chat"
        payload = {
            "message": "Sân Cầu Giấy có những sân nào?",
            "conversation_id": "conv_http_test_2"
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=25) as response:
            self.assertEqual(response.status, 200)
            data = json.loads(response.read().decode("utf-8"))
            self.assertIn("answer", data)
            self.assertEqual(data.get("conversation_id"), "conv_http_test_2")

    def test_05_http_invalid_auth_token_401(self):
        """Test HTTP POST with invalid token returns 401 Unauthorized"""
        url = f"http://127.0.0.1:{self.port}/api/chat"
        payload = {"message": "Xin chào"}
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer token_khong_hop_le_123"
            }
        )
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req, timeout=5)
        self.assertEqual(ctx.exception.code, 401)

    def test_06_http_valid_auth_token_200(self):
        """Test HTTP POST with valid auth token passes auth and succeeds"""
        token = create_access_token(subject=1, role="CUSTOMER")
        url = f"http://127.0.0.1:{self.port}/api/chat"
        payload = {
            "message": "Kiểm tra quyền khách hàng",
            "conversation_id": "conv_auth_test"
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}"
            }
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            self.assertEqual(response.status, 200)
            data = json.loads(response.read().decode("utf-8"))
            self.assertTrue(data.get("success"))
            self.assertIn("answer", data)


if __name__ == "__main__":
    unittest.main()
