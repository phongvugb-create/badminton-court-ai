import os
import sys
import asyncio
import unittest
from datetime import datetime

# Setup path
BACKEND_DIR = os.path.join(os.path.dirname(__file__), "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.core.database import engine, AsyncSessionLocal, Base
from app.models.all_models import User, Conversation, ChatMessage
from app.ai.conversation_service import ConversationService, get_conversation_service
from app.ai.context_manager import SlidingWindowContextManager
from app.ai.llm_provider import BaseLLMProvider
from app.ai.chatbot_service import ChatbotService, get_chatbot_service
from app.core.security import create_access_token, get_password_hash
from app.api.v1.ai import (
    create_conversation,
    list_conversations,
    get_conversation_detail,
    send_message_in_conversation,
    chat_with_ai
)
from app.schemas.all_schemas import (
    ConversationCreate,
    ChatMessageCreate,
    AIChatRequest
)
from fastapi import HTTPException
from sqlalchemy.future import select

class MockPhase2LLMProvider(BaseLLMProvider):
    @property
    def provider_name(self) -> str:
        return "MockPhase2LLMProvider"

    @property
    def model_name(self) -> str:
        return "mock-phase2"

    async def generate_text(self, system_instruction: str, user_message: str, history=None, timeout=10.0) -> str:
        history_len = len(history) if history else 0
        return f"Trợ lý AI phản hồi: '{user_message}' (Số tin nhắn ngữ cảnh trước: {history_len})"


class TestPhase2ConversationMemory(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Thiết lập mock provider cho chatbot service
        chatbot_svc = get_chatbot_service()
        chatbot_svc.llm_provider = MockPhase2LLMProvider()

        # Đảm bảo bảng cơ sở dữ liệu đã sẵn sàng
        async def init_tables():
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            # Tạo 2 user test
            async with AsyncSessionLocal() as session:
                # User 1
                res1 = await session.execute(select(User).where(User.phone == "0911111111"))
                u1 = res1.scalar_one_or_none()
                if not u1:
                    u1 = User(
                        id=1001,
                        full_name="Nguyễn Văn A (User 1)",
                        phone="0911111111",
                        password_hash=get_password_hash("pass123"),
                        role="CUSTOMER"
                    )
                    session.add(u1)

                # User 2
                res2 = await session.execute(select(User).where(User.phone == "0922222222"))
                u2 = res2.scalar_one_or_none()
                if not u2:
                    u2 = User(
                        id=1002,
                        full_name="Trần Thị B (User 2)",
                        phone="0922222222",
                        password_hash=get_password_hash("pass123"),
                        role="CUSTOMER"
                    )
                    session.add(u2)

                await session.commit()

        asyncio.run(init_tables())

    def test_01_create_conversation(self):
        """PHẦN 2 & 4: Tạo conversation cho User 1"""
        async def run_test():
            async with AsyncSessionLocal() as session:
                user1 = await session.get(User, 1001)
                payload = ConversationCreate(title="Hội thoại tư vấn sân")
                conv = await create_conversation(payload=payload, current_user=user1, db=session)
                
                self.assertIsNotNone(conv.id)
                self.assertEqual(conv.user_id, 1001)
                self.assertEqual(conv.title, "Hội thoại tư vấn sân")
                self.assertEqual(conv.status, "ACTIVE")
                return conv.id

        conv_id = asyncio.run(run_test())
        self.assertTrue(conv_id.startswith("conv_"))

    def test_02_send_message_in_conversation_flow(self):
        """PHẦN 3 & 5: Gửi tin nhắn, lưu user message, gọi LLM, lưu assistant message"""
        async def run_test():
            async with AsyncSessionLocal() as session:
                user1 = await session.get(User, 1001)
                # Tạo conversation
                conv_svc = get_conversation_service()
                conv = await conv_svc.create_conversation(db=session, user_id=1001, title="Test Chat Flow")

                # Gửi tin nhắn đầu tiên
                payload = ChatMessageCreate(message="Xin chào! Có sân nào gần Cầu Giấy không?")
                res = await send_message_in_conversation(
                    conversation_id=conv.id,
                    payload=payload,
                    current_user=user1,
                    db=session
                )

                self.assertIn("Xin chào!", res.answer)
                self.assertEqual(res.conversation_id, conv.id)
                self.assertEqual(res.user_id, "1001")
                self.assertTrue(res.message_id.startswith("msg_"))

                # Kiểm tra cả 2 tin nhắn đã được ghi vào DB
                history = await conv_svc.get_recent_messages(db=session, conversation_id=conv.id)
                self.assertEqual(len(history), 2)
                self.assertEqual(history[0].role, "user")
                self.assertIn("Cầu Giấy", history[0].content)
                self.assertEqual(history[1].role, "assistant")
                self.assertIn("Trợ lý AI phản hồi", history[1].content)
                return conv.id

        asyncio.run(run_test())

    def test_03_load_conversation_history(self):
        """PHẦN 4: Lấy lịch sử hội thoại"""
        async def run_test():
            async with AsyncSessionLocal() as session:
                user1 = await session.get(User, 1001)
                conv_svc = get_conversation_service()
                conv = await conv_svc.create_conversation(db=session, user_id=1001, title="Test History")

                await conv_svc.add_message(session, conv.id, "user", "Tin nhắn 1")
                await conv_svc.add_message(session, conv.id, "assistant", "Phản hồi 1")

                detail = await get_conversation_detail(conv.id, current_user=user1, db=session)
                self.assertEqual(detail.id, conv.id)
                self.assertEqual(len(detail.messages), 2)
                self.assertEqual(detail.messages[0].content, "Tin nhắn 1")
                self.assertEqual(detail.messages[1].content, "Phản hồi 1")

        asyncio.run(run_test())

    def test_04_ownership_isolation_user_b_cannot_read_user_a(self):
        """PHẦN 7: User B không được đọc conversation của User A (HTTP 403)"""
        async def run_test():
            async with AsyncSessionLocal() as session:
                user1 = await session.get(User, 1001)
                user2 = await session.get(User, 1002)

                # User 1 tạo conversation
                conv_svc = get_conversation_service()
                conv_a = await conv_svc.create_conversation(db=session, user_id=user1.id, title="Bí mật User A")

                # User 2 cố tình đọc conversation của User 1
                with self.assertRaises(HTTPException) as ctx:
                    await get_conversation_detail(conversation_id=conv_a.id, current_user=user2, db=session)
                
                self.assertEqual(ctx.exception.status_code, 403)
                self.assertIn("không có quyền truy cập", ctx.exception.detail)

        asyncio.run(run_test())

    def test_05_ownership_isolation_user_b_cannot_send_to_user_a(self):
        """PHẦN 7: User B không được gửi message vào conversation của User A (HTTP 403)"""
        async def run_test():
            async with AsyncSessionLocal() as session:
                user1 = await session.get(User, 1001)
                user2 = await session.get(User, 1002)

                # User 1 tạo conversation
                conv_svc = get_conversation_service()
                conv_a = await conv_svc.create_conversation(db=session, user_id=user1.id, title="Conv User A")

                # User 2 cố tình gửi tin nhắn vào conversation của User 1
                payload = ChatMessageCreate(message="User B tấn công giả mạo")
                with self.assertRaises(HTTPException) as ctx:
                    await send_message_in_conversation(
                        conversation_id=conv_a.id,
                        payload=payload,
                        current_user=user2,
                        db=session
                    )

                self.assertEqual(ctx.exception.status_code, 403)
                self.assertIn("không có quyền truy cập", ctx.exception.detail)

        asyncio.run(run_test())

    def test_06_non_existent_conversation_404(self):
        """PHẦN 5 & 7: Conversation không tồn tại trả về 404"""
        async def run_test():
            async with AsyncSessionLocal() as session:
                user1 = await session.get(User, 1001)
                with self.assertRaises(HTTPException) as ctx:
                    await get_conversation_detail(conversation_id="conv_non_existent_9999", current_user=user1, db=session)
                self.assertEqual(ctx.exception.status_code, 404)

        asyncio.run(run_test())

    def test_07_context_management_sliding_window(self):
        """PHẦN 6: Sliding window context management cắt tỉa đúng limit"""
        mgr = SlidingWindowContextManager(max_recent_messages=4)
        mock_messages = [
            {"role": "user", "content": f"Message {i}"} for i in range(1, 11) # 10 tin nhắn
        ]
        context = mgr.select_context_messages(mock_messages, max_count=4)
        self.assertEqual(len(context), 4)
        self.assertEqual(context[0]["content"], "Message 7")
        self.assertEqual(context[3]["content"], "Message 10")

    def test_08_backward_compatibility_chat_endpoint(self):
        """PHẦN 4 & 5: Backward compatibility POST /api/v1/ai/chat tự động lưu hội thoại"""
        async def run_test():
            async with AsyncSessionLocal() as session:
                user1 = await session.get(User, 1001)

                # Test 1: Đăng nhập -> Tự động sinh conversation và lưu DB
                req = AIChatRequest(message="Hỏi giá qua endpoint cũ")
                res = await chat_with_ai(req=req, current_user=user1, db=session)
                self.assertIsNotNone(res.conversation_id)
                self.assertEqual(res.user_id, "1001")
                self.assertIn("Hỏi giá", res.answer)

                # Kiểm tra DB đã lưu
                conv_svc = get_conversation_service()
                saved_msgs = await conv_svc.get_recent_messages(session, res.conversation_id)
                self.assertEqual(len(saved_msgs), 2)

                # Test 2: Khách vãng lai (Guest) -> Vẫn hoạt động trơn tru không lỗi
                guest_req = AIChatRequest(message="Khách vãng lai hỏi")
                guest_res = await chat_with_ai(req=guest_req, current_user=None, db=session)
                self.assertIsNone(guest_res.user_id)
                self.assertIn("Khách vãng lai", guest_res.answer)

        asyncio.run(run_test())

    def test_09_chat_endpoint_cross_user_forbidden(self):
        """PHẦN 7: User 2 gửi message tới endpoint /chat với conversation_id của User 1 -> 403 Forbidden"""
        async def run_test():
            async with AsyncSessionLocal() as session:
                user1 = await session.get(User, 1001)
                user2 = await session.get(User, 1002)

                conv_svc = get_conversation_service()
                conv_a = await conv_svc.create_conversation(session, user_id=user1.id, title="Conv User 1")

                # User 2 gọi /chat kèm conversation_id của User 1
                req = AIChatRequest(
                    message="User 2 muốn chen ngang hội thoại của User 1",
                    conversation_id=conv_a.id
                )
                with self.assertRaises(HTTPException) as ctx:
                    await chat_with_ai(req=req, current_user=user2, db=session)

                self.assertEqual(ctx.exception.status_code, 403)
                self.assertIn("không có quyền truy cập", ctx.exception.detail)

        asyncio.run(run_test())

    def test_10_empty_message_in_conversation_rejected(self):
        """PHẦN 4: Gửi tin nhắn rỗng vào conversation trả về 400"""
        async def run_test():
            async with AsyncSessionLocal() as session:
                user1 = await session.get(User, 1001)
                conv_svc = get_conversation_service()
                conv = await conv_svc.create_conversation(session, user_id=user1.id)

                payload = ChatMessageCreate(message="   ")
                with self.assertRaises(HTTPException) as ctx:
                    await send_message_in_conversation(conv.id, payload, current_user=user1, db=session)
                self.assertEqual(ctx.exception.status_code, 400)

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
