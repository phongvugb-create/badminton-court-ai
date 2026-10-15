import os
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

DEFAULT_MAX_RECENT_MESSAGES = int(os.getenv("MAX_RECENT_CHAT_MESSAGES", "10"))
MAX_SINGLE_MESSAGE_CHARS = 2000

class BaseContextManager(ABC):
    """
    Abstract Base Class quản lý lịch sử hội thoại đưa vào LLM.
    Phân tách chiến lược quản lý ngữ cảnh (Sliding Window, Token Budget, Summary, RAG)
    để sau này có thể nâng cấp mà không sửa đổi LLM Provider hoặc Controller.
    """

    @abstractmethod
    def select_context_messages(
        self,
        messages: List[Any],
        max_count: Optional[int] = None
    ) -> List[Dict[str, str]]:
        pass


class SlidingWindowContextManager(BaseContextManager):
    """
    Chiến lược Sliding Window:
    - Chỉ lấy tối đa N tin nhắn gần nhất (mặc định 10).
    - Chuẩn hóa role (user, assistant).
    - Cắt tỉa tin nhắn vượt quá giới hạn ký tự để chống tràn ngữ cảnh (context flooding).
    """

    def __init__(self, max_recent_messages: int = DEFAULT_MAX_RECENT_MESSAGES):
        self.max_recent_messages = max(2, max_recent_messages)

    def select_context_messages(
        self,
        messages: List[Any],
        max_count: Optional[int] = None
    ) -> List[Dict[str, str]]:
        if not messages:
            return []

        limit = max_count or self.max_recent_messages
        recent = messages[-limit:]

        formatted_history: List[Dict[str, str]] = []
        for msg in recent:
            # Hỗ trợ cả đối tượng SQLAlchemy ChatMessage và dict từ client
            if hasattr(msg, "role") and hasattr(msg, "content"):
                role = str(msg.role).lower().strip()
                content = str(msg.content or "")
            elif isinstance(msg, dict):
                role = str(msg.get("role") or msg.get("sender") or "user").lower().strip()
                content = str(msg.get("content") or msg.get("text") or msg.get("message") or "")
            else:
                continue

            if not content.strip():
                continue

            # Chuẩn hóa role sang convention của chatbot: "user" hoặc "assistant"
            normalized_role = "assistant" if role in ["assistant", "bot", "model"] else "user"

            # Cắt tỉa nếu tin nhắn quá dài để bảo vệ budget token
            if len(content) > MAX_SINGLE_MESSAGE_CHARS:
                content = content[:MAX_SINGLE_MESSAGE_CHARS] + "... [nội dung đã được rút gọn]"

            formatted_history.append({
                "role": normalized_role,
                "content": content
            })

        return formatted_history


_context_manager_instance: Optional[BaseContextManager] = None

def get_context_manager() -> BaseContextManager:
    global _context_manager_instance
    if _context_manager_instance is None:
        _context_manager_instance = SlidingWindowContextManager()
    return _context_manager_instance
