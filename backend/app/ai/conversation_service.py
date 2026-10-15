import uuid
import logging
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status

from app.models.all_models import Conversation, ChatMessage

logger = logging.getLogger(__name__)

class ConversationService:
    """
    Quản lý vòng đời cuộc hội thoại và lịch sử tin nhắn trong cơ sở dữ liệu.
    Đảm bảo chặt chẽ nguyên tắc bảo mật: Phân quyền sở hữu (ownership isolation).
    """

    async def create_conversation(
        self,
        db: AsyncSession,
        user_id: int,
        title: Optional[str] = None,
        conv_id: Optional[str] = None
    ) -> Conversation:
        clean_title = (title or "Cuộc trò chuyện mới").strip()[:200]
        c_id = conv_id or f"conv_{uuid.uuid4().hex[:12]}"

        conversation = Conversation(
            id=c_id,
            user_id=user_id,
            title=clean_title,
            status="ACTIVE"
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        logger.info(f"[Conversation] Đã tạo cuộc hội thoại mới id={c_id} cho user_id={user_id}")
        return conversation

    async def get_conversation(
        self,
        db: AsyncSession,
        conversation_id: str,
        user_id: int,
        load_messages: bool = False
    ) -> Conversation:
        stmt = select(Conversation).where(Conversation.id == conversation_id)
        if load_messages:
            stmt = stmt.options(selectinload(Conversation.messages))

        res = await db.execute(stmt)
        conversation = res.scalar_one_or_none()

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy cuộc hội thoại"
            )

        # Kiểm tra quyền sở hữu (Ownership check)
        if conversation.user_id != user_id:
            logger.warning(
                f"[Security] User {user_id} cố tình truy cập trái phép conversation {conversation_id} thuộc quyền sở hữu của user {conversation.user_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền truy cập cuộc hội thoại này"
            )

        return conversation

    async def get_or_create_conversation(
        self,
        db: AsyncSession,
        conversation_id: Optional[str],
        user_id: int,
        default_title: Optional[str] = None
    ) -> Conversation:
        """
        Lấy conversation nếu có sẵn và kiểm tra quyền sở hữu.
        Nếu conversation_id chưa có hoặc chưa tồn tại trong DB, tự động tạo mới cho user_id.
        """
        if conversation_id:
            stmt = select(Conversation).where(Conversation.id == conversation_id)
            res = await db.execute(stmt)
            existing = res.scalar_one_or_none()
            if existing:
                if existing.user_id != user_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Bạn không có quyền truy cập cuộc hội thoại này"
                    )
                return existing

        return await self.create_conversation(
            db=db,
            user_id=user_id,
            title=default_title or "Cuộc trò chuyện mới",
            conv_id=conversation_id
        )

    async def list_conversations(
        self,
        db: AsyncSession,
        user_id: int,
        limit: int = 20
    ) -> List[Conversation]:
        stmt = (
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
            .limit(limit)
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    async def add_message(
        self,
        db: AsyncSession,
        conversation_id: str,
        role: str,
        content: str,
        msg_id: Optional[str] = None
    ) -> ChatMessage:
        from datetime import datetime
        m_id = msg_id or f"msg_{uuid.uuid4().hex[:12]}"
        message = ChatMessage(
            id=m_id,
            conversation_id=conversation_id,
            role=role,
            content=content.strip(),
            created_at=datetime.utcnow()
        )
        db.add(message)
        await db.commit()
        await db.refresh(message)
        return message

    async def get_recent_messages(
        self,
        db: AsyncSession,
        conversation_id: str,
        limit: int = 10
    ) -> List[ChatMessage]:
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.conversation_id == conversation_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
        )
        res = await db.execute(stmt)
        messages = list(res.scalars().all())
        # Đảo ngược lại theo thứ tự thời gian tăng dần
        messages.reverse()
        return messages


_conversation_service_instance: Optional[ConversationService] = None

def get_conversation_service() -> ConversationService:
    global _conversation_service_instance
    if _conversation_service_instance is None:
        _conversation_service_instance = ConversationService()
    return _conversation_service_instance
