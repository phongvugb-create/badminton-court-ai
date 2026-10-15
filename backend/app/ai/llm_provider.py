import os
import json
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)

class BaseLLMProvider(ABC):
    """
    Abstract Base Class cho LLM Provider.
    Cho phép mở rộng hoặc thay thế nhà cung cấp (Gemini, OpenAI, Claude, Local LLM)
    mà không làm thay đổi các tầng trên (ChatbotService, Controller).
    """

    @abstractmethod
    async def generate_text(
        self,
        system_instruction: str,
        user_message: str,
        history: Optional[List[Dict[str, str]]] = None,
        timeout: float = 8.0
    ) -> str:
        """
        Gửi yêu cầu tới LLM Provider và nhận phản hồi văn bản.
        """
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        pass


class GeminiLLMProvider(BaseLLMProvider):
    """
    Triển khai LLM Service độc lập sử dụng Google Gemini API.
    - Lấy API Key từ biến môi trường GEMINI_API_KEY (không hard-code).
    - Hỗ trợ timeout, error handling, không làm lộ API key trong logs/errors.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        # API key được nạp an toàn từ biến môi trường, app.config, hoặc .env
        self._api_key = api_key or self._resolve_api_key()
        self._model = model or os.getenv("LLM_MODEL", "gemini-3.5-flash-lite")

    @staticmethod
    def _resolve_api_key() -> str:
        key = os.environ.get("GEMINI_API_KEY", "")
        if key and not key.startswith("YOUR_"):
            return key.strip()

        # Thử đọc từ settings nếu có
        try:
            from app.config import settings
            if settings.GEMINI_API_KEY and not settings.GEMINI_API_KEY.startswith("YOUR_"):
                return settings.GEMINI_API_KEY.strip()
        except Exception:
            pass

        # Thử tìm file .env ở thư mục gốc hoặc thư mục hiện tại
        candidate_paths = [
            os.path.join(os.getcwd(), ".env"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), ".env"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
        ]
        for p in candidate_paths:
            if os.path.exists(p):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        for line in f:
                            s = line.strip()
                            if s.startswith("GEMINI_API_KEY="):
                                val = s.split("=", 1)[1].strip().strip('"').strip("'")
                                if val and not val.startswith("YOUR_"):
                                    return val
                except Exception:
                    pass
        return ""

    @property
    def provider_name(self) -> str:
        return "Google Gemini"

    @property
    def model_name(self) -> str:
        return self._model

    def is_configured(self) -> bool:
        return bool(self._api_key and self._api_key.strip())

    async def generate_text(
        self,
        system_instruction: str,
        user_message: str,
        history: Optional[List[Dict[str, str]]] = None,
        timeout: float = 8.0
    ) -> str:
        if not self.is_configured():
            logger.warning("[LLM Service] GEMINI_API_KEY chưa được cấu hình trong environment variables.")
            raise ValueError("GEMINI_API_KEY is not configured in environment variables.")

        # Chuẩn bị contents format của Gemini API
        contents = []
        if history and isinstance(history, list):
            for item in history:
                role = "user" if item.get("role") in ["user", "customer"] or item.get("sender") == "user" else "model"
                text = item.get("text") or item.get("content") or item.get("message") or ""
                if text:
                    contents.append({
                        "role": role,
                        "parts": [{"text": str(text)}]
                    })

        contents.append({
            "role": "user",
            "parts": [{"text": user_message}]
        })

        models_to_attempt = [self._model, "gemini-3.5-flash-lite", "gemini-flash-latest", "gemini-3.8-flash", "gemini-3.7-flash"]
        # Loại bỏ trùng lặp giữ nguyên thứ tự
        seen = set()
        dedup_models = [m for m in models_to_attempt if not (m in seen or seen.add(m))]

        last_error = None
        for model in dedup_models:
            try:
                reply = await asyncio.to_thread(
                    self._call_gemini_api_sync,
                    model=model,
                    system_instruction=system_instruction,
                    contents=contents,
                    timeout=timeout
                )
                if reply:
                    return reply
            except Exception as e:
                # Không log API key, chỉ log model và thông báo lỗi
                logger.warning(f"[LLM Service] Model {model} call failed: {type(e).__name__}")
                last_error = e
                continue

        if last_error:
            raise last_error
        raise RuntimeError("Không thể nhận câu trả lời từ LLM Provider.")

    def _call_gemini_api_sync(
        self,
        model: str,
        system_instruction: str,
        contents: list,
        timeout: float
    ) -> str:
        # Sử dụng header x-goog-api-key hoặc Bearer token thay vì truyền key trên URL query parameter
        # để đảm bảo tuyệt đối không lộ API key khi có ngoại lệ URLError / HTTPError
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 1024
            }
        }
        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        headers = {
            "Content-Type": "application/json"
        }
        if self._api_key:
            if self._api_key.startswith("ya29."):
                headers["Authorization"] = f"Bearer {self._api_key}"
            else:
                headers["x-goog-api-key"] = self._api_key

        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=req_data,
            headers=headers
        )

        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status == 200:
                res_body = response.read().decode("utf-8")
                res_json = json.loads(res_body)
                candidates = res_json.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "").strip()
        return ""


def get_default_llm_provider() -> BaseLLMProvider:
    """Factory helper cung cấp singleton/instance của LLM Provider mặc định"""
    return GeminiLLMProvider()
