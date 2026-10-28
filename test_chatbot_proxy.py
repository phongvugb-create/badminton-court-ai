"""Exercise the website /api/chat handler without a socket or external LLM."""
import io
import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
import server


class ChatProxyTests(unittest.TestCase):
    def request(self, result=None, error=None):
        handler = object.__new__(server.BadmintonServerHandler)
        body = json.dumps({"message": "Đặt sân"}).encode()
        handler.path = "/api/chat"
        handler.headers = {"Content-Length": str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler.wfile = io.BytesIO()
        handler.send_response = Mock()
        handler.send_header = Mock()
        handler.end_headers = Mock()
        handler._parse_auth_cookie = Mock(return_value=None)
        handler._authenticate_request = Mock(return_value=None)
        service = SimpleNamespace(handle_message=AsyncMock(return_value=result, side_effect=error))
        with patch.object(server, "get_chatbot_service", return_value=service):
            handler.do_POST()
        return json.loads(handler.wfile.getvalue())

    def test_preview_metadata_reaches_browser(self):
        result = {"answer": "Xem trước", "reply": "Xem trước", "conversation_id": "conv1", "message_id": "msg1", "status": "success", "action_type": "booking_preview", "booking_intent_id": "intent1", "preview_data": {"slot_id": 12}}
        response = self.request(result)
        for field in ["action_type", "booking_intent_id", "preview_data"]:
            self.assertEqual(response[field], result[field])

    def test_hold_metadata_reaches_browser(self):
        result = {"answer": "Giữ sân", "reply": "Giữ sân", "conversation_id": "conv1", "message_id": "msg1", "status": "success", "action_type": "slot_hold_preview", "pending_intent_id": "hold1"}
        response = self.request(result)
        self.assertEqual(response["pending_intent_id"], "hold1")

    def test_error_does_not_expose_internal_details(self):
        response = self.request(error=RuntimeError("PRIVATE_CONNECTION_STRING"))
        self.assertEqual(response["retrieval_status"], "data_unavailable")
        self.assertNotIn("PRIVATE_CONNECTION_STRING", json.dumps(response))


if __name__ == "__main__":
    unittest.main()
