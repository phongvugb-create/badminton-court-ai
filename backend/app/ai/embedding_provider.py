"""
BADMINTON.AI - EMBEDDING PROVIDER ABSTRACTION & IMPLEMENTATION
Independent provider module for vector embeddings.
Separated strictly from LLM text generation provider.
Supports Google Gemini gemini-embedding-2 with MRL (output_dimensionality = 768).
Supports both embedContent (single) and batchEmbedContents (batch).
STRICT: NO silent mock/fallback vectors in production. API failures raise typed errors.
SECURITY: Never logs or exposes raw API keys.
"""

import os
import math
import json
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import hashlib
import urllib.request
import urllib.error

logger = logging.getLogger("embedding_provider")

# ==============================================================================
# TYPED EMBEDDING EXCEPTIONS (Phase 4.2 Error Handling Specification)
# ==============================================================================

class EmbeddingError(RuntimeError):
    """Base class cho toàn bộ lỗi trong hệ thống Embedding."""
    pass

class CredentialInvalidError(EmbeddingError):
    """HTTP 401: Credential/API key không hợp lệ hoặc không đúng loại (OAuth vs API Key)."""
    pass

class PermissionDeniedError(EmbeddingError):
    """HTTP 403: Quyền truy cập bị từ chối hoặc model bị giới hạn quyền."""
    pass

class InvalidRequestError(EmbeddingError):
    """HTTP 400: Cấu trúc request, model name hoặc output_dimensionality không hợp lệ."""
    pass

class RateLimitExceededError(EmbeddingError):
    """HTTP 429: Quá giới hạn quota/rate limit của Google API."""
    pass

class ProviderServerError(EmbeddingError):
    """HTTP 5xx: Sự cố máy chủ nội bộ từ phía Google Gemini."""
    pass

class NetworkTimeoutError(EmbeddingError):
    """Timeout mạng khi kết nối tới Google API."""
    pass


# ==============================================================================
# BASE ABSTRACT PROVIDER
# ==============================================================================

class BaseEmbeddingProvider(ABC):
    """
    Abstract Base Class for Vector Embedding Providers.
    Allows easy swapping (Gemini, OpenAI, Cohere, HuggingFace)
    without touching downstream ingestion or storage services.
    """

    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding vector for a single string."""
        pass

    @abstractmethod
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embedding vectors for a batch of strings."""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        pass

    @property
    def embedding_version(self) -> str:
        return os.getenv("EMBEDDING_VERSION", "v1")

    def validate_vector(self, vector: List[float]) -> None:
        """
        Validates embedding vector:
        1. Not None / empty
        2. Exact dimension match (768)
        3. All numeric floats
        4. No NaN, no Infinity
        5. Not all zeros (non-trivial vector)
        """
        if vector is None or not isinstance(vector, (list, tuple)):
            raise ValueError("Vector nhúng phải là danh sách số (list of floats).")

        if len(vector) != self.dimension:
            raise ValueError(
                f"Kích thước vector không khớp: mong đợi {self.dimension}, nhận được {len(vector)}."
            )

        has_non_zero = False
        for i, val in enumerate(vector):
            if not isinstance(val, (int, float)):
                raise ValueError(f"Giá trị tại vị trí {i} không phải kiểu số: {type(val)}.")
            if math.isnan(val) or math.isinf(val):
                raise ValueError(f"Vector chứa giá trị không hợp lệ (NaN hoặc Infinity) tại vị trí {i}.")
            if abs(val) > 1e-9:
                has_non_zero = True

        if not has_non_zero:
            raise ValueError("Vector nhúng trả về là zero-vector (tất cả phần tử đều bằng 0), không hợp lệ.")

    @staticmethod
    def normalize_l2(vector: List[float]) -> List[float]:
        """Performs L2 unit normalization on vector."""
        norm = math.sqrt(sum(x * x for x in vector))
        if norm > 0.0:
            return [x / norm for x in vector]
        return vector


# ==============================================================================
# GEMINI EMBEDDING PROVIDER (PRODUCTION)
# ==============================================================================

class GeminiEmbeddingProvider(BaseEmbeddingProvider):
    """
    Google Gemini Embedding Provider implementing gemini-embedding-2 (768-dim via MRL).
    Supports:
      - embedContent (single text endpoint)
      - batchEmbedContents (batch processing endpoint)
      - x-goog-api-key HTTP header (secure authentication)
      - output_dimensionality = 768
    CRITICAL POLICY:
      - NO fake/fallback vectors in production under any circumstance.
      - Typed exceptions on HTTP errors with explicit categorization.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        dimension: Optional[int] = None,
        timeout: float = 10.0,
        max_retries: int = 3
    ):
        self._api_key = api_key if api_key is not None else self._resolve_api_key()
        self._model = model or os.getenv("EMBEDDING_MODEL", "gemini-embedding-2")
        self._dimension = dimension or int(os.getenv("EMBEDDING_DIMENSION", "768"))
        self._timeout = timeout
        self._max_retries = max_retries
        self._base_url = "https://generativelanguage.googleapis.com/v1beta"

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimension(self) -> int:
        return self._dimension

    @staticmethod
    def _resolve_api_key() -> str:
        key = os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", "")
        if key and not key.startswith("YOUR_"):
            return key.strip()

        # Check root .env
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        env_file = os.path.join(base_dir, ".env")
        if os.path.exists(env_file):
            try:
                with open(env_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("GEMINI_API_KEY=") or line.startswith("GOOGLE_API_KEY="):
                            val = line.split("=", 1)[1].strip().strip('"').strip("'")
                            if val and not val.startswith("YOUR_"):
                                return val
            except Exception:
                pass
        return ""

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "BadmintonAI-EmbeddingClient/1.0"
        }
        if self._api_key:
            if self._api_key.startswith("ya29."):
                headers["Authorization"] = f"Bearer {self._api_key}"
            else:
                headers["x-goog-api-key"] = self._api_key
        return headers

    def _sanitize_error_body(self, raw_body: str) -> str:
        """Parses and formats API error JSON message cleanly without leaking secrets."""
        try:
            parsed = json.loads(raw_body)
            err = parsed.get("error", {})
            msg = err.get("message", raw_body)
            status = err.get("status", "")
            return f"[{status}] {msg}" if status else msg
        except Exception:
            return raw_body[:300]

    async def embed_text(self, text: str) -> List[float]:
        """
        Generates embedding for a single text using the dedicated embedContent endpoint.
        Uses output_dimensionality = 768.
        """
        if not text or not text.strip():
            raise ValueError("Văn bản đầu vào không được để trống khi tạo embedding.")

        if not self._api_key:
            raise CredentialInvalidError(
                "GEMINI_API_KEY chưa được cấu hình. "
                "Production cấm sử dụng vector giả lập. Vui lòng cung cấp Google API Key chính xác trong .env."
            )

        url = f"{self._base_url}/models/{self._model}:embedContent"
        payload = {
            "model": f"models/{self._model}",
            "content": {
                "parts": [{"text": text.strip()[:2048]}]
            },
            "output_dimensionality": self._dimension
        }
        json_data = json.dumps(payload).encode("utf-8")
        headers = self._get_headers()

        for attempt in range(self._max_retries):
            try:
                def _do_request():
                    req = urllib.request.Request(url, data=json_data, headers=headers)
                    with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                        return json.loads(resp.read().decode("utf-8"))

                resp_data = await asyncio.to_thread(_do_request)
                emb_obj = resp_data.get("embedding", {})
                values = emb_obj.get("values", [])

                if len(values) != self._dimension:
                    raise ValueError(
                        f"Kích thước vector trả về ({len(values)}) không khớp với cấu hình dimension ({self._dimension})."
                    )

                norm_vec = self.normalize_l2(values)
                self.validate_vector(norm_vec)
                return norm_vec

            except urllib.error.HTTPError as e:
                status_code = e.code
                error_body = self._sanitize_error_body(e.read().decode("utf-8", errors="ignore"))

                if status_code in [429, 503] and attempt < self._max_retries - 1:
                    wait_time = 1.5 * (2 ** attempt)
                    logger.warning(f"[GeminiEmbeddingProvider] HTTP {status_code}. Thử lại sau {wait_time:.1f}s...")
                    await asyncio.sleep(wait_time)
                    continue

                if status_code == 401:
                    raise CredentialInvalidError(
                        f"HTTP 401 Unauthorized: Credential không hợp lệ hoặc đã bị khóa. Chi tiết: {error_body}"
                    )
                elif status_code == 403:
                    raise PermissionDeniedError(
                        f"HTTP 403 Forbidden: Quyền truy cập bị từ chối với model '{self._model}'. Chi tiết: {error_body}"
                    )
                elif status_code == 400:
                    raise InvalidRequestError(
                        f"HTTP 400 Bad Request: Request không hợp lệ với model '{self._model}'. Chi tiết: {error_body}"
                    )
                elif status_code == 429:
                    raise RateLimitExceededError(
                        f"HTTP 429 Too Many Requests: Vượt quá giới hạn quota Gemini API. Chi tiết: {error_body}"
                    )
                elif status_code >= 500:
                    raise ProviderServerError(
                        f"HTTP {status_code} Server Error: Máy chủ Google gặp sự cố. Chi tiết: {error_body}"
                    )
                else:
                    raise EmbeddingError(f"HTTP {status_code} Error: {error_body}")

            except (TimeoutError, urllib.error.URLError) as e:
                if attempt < self._max_retries - 1:
                    wait_time = 1.0 * (2 ** attempt)
                    logger.warning(f"[GeminiEmbeddingProvider] Lỗi kết nối: {e}. Thử lại sau {wait_time:.1f}s...")
                    await asyncio.sleep(wait_time)
                    continue
                raise NetworkTimeoutError(f"Không thể kết nối đến Google Gemini API sau {self._max_retries} lần thử: {e}")
            except Exception as e:
                if isinstance(e, EmbeddingError):
                    raise
                raise EmbeddingError(f"Lỗi không xác định khi gọi Gemini API: {e}")

        raise EmbeddingError("Google Gemini Embedding API không phản hồi kết quả hợp lệ.")

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Embeds a batch of strings using Gemini batchEmbedContents API.
        Enforces output_dimensionality = 768 per request part.
        CRITICAL: Never generates fake or fallback vectors. Fails explicitly on API error.
        """
        if not texts:
            return []

        cleaned_texts = [t.strip() if t else "" for t in texts]
        non_empty_indices = [i for i, t in enumerate(cleaned_texts) if len(t) > 0]

        if not non_empty_indices:
            raise ValueError("Không có đoạn văn bản hợp lệ để vector hóa trong batch.")

        if not self._api_key:
            raise CredentialInvalidError(
                "GEMINI_API_KEY chưa được cấu hình. "
                "Production cấm sử dụng vector giả lập. Vui lòng cung cấp Google API Key chính xác trong .env."
            )

        url = f"{self._base_url}/models/{self._model}:batchEmbedContents"
        requests_payload = []
        for t in cleaned_texts:
            item: Dict[str, Any] = {
                "model": f"models/{self._model}",
                "content": {
                    "parts": [{"text": t[:2048]}]
                },
                "output_dimensionality": self._dimension
            }
            requests_payload.append(item)

        payload = {"requests": requests_payload}
        json_data = json.dumps(payload).encode("utf-8")
        headers = self._get_headers()

        for attempt in range(self._max_retries):
            try:
                def _do_request():
                    req = urllib.request.Request(url, data=json_data, headers=headers)
                    with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                        return json.loads(resp.read().decode("utf-8"))

                resp_data = await asyncio.to_thread(_do_request)
                raw_embeddings = resp_data.get("embeddings", [])

                if len(raw_embeddings) != len(texts):
                    raise InvalidRequestError(
                        f"Số lượng vector trả về từ Gemini API ({len(raw_embeddings)}) "
                        f"không khớp với số văn bản gửi đi ({len(texts)})."
                    )

                vectors: List[List[float]] = []
                for emb in raw_embeddings:
                    values = emb.get("values", [])
                    if len(values) != self._dimension:
                        raise ValueError(
                            f"Kích thước vector trả về ({len(values)}) không khớp với cấu hình dimension ({self._dimension})."
                        )
                    norm_vec = self.normalize_l2(values)
                    self.validate_vector(norm_vec)
                    vectors.append(norm_vec)
                return vectors

            except urllib.error.HTTPError as e:
                status_code = e.code
                error_body = self._sanitize_error_body(e.read().decode("utf-8", errors="ignore"))

                if status_code in [429, 503] and attempt < self._max_retries - 1:
                    wait_time = 1.5 * (2 ** attempt)
                    logger.warning(f"[GeminiEmbeddingProvider] HTTP {status_code}. Thử lại sau {wait_time:.1f}s...")
                    await asyncio.sleep(wait_time)
                    continue

                if status_code == 401:
                    raise CredentialInvalidError(
                        f"HTTP 401 Unauthorized: Credential không hợp lệ hoặc đã bị khóa. Chi tiết: {error_body}"
                    )
                elif status_code == 403:
                    raise PermissionDeniedError(
                        f"HTTP 403 Forbidden: Quyền truy cập bị từ chối với model '{self._model}'. Chi tiết: {error_body}"
                    )
                elif status_code == 400:
                    raise InvalidRequestError(
                        f"HTTP 400 Bad Request: Request không hợp lệ với model '{self._model}'. Chi tiết: {error_body}"
                    )
                elif status_code == 429:
                    raise RateLimitExceededError(
                        f"HTTP 429 Too Many Requests: Vượt quá giới hạn quota Gemini API. Chi tiết: {error_body}"
                    )
                elif status_code >= 500:
                    raise ProviderServerError(
                        f"HTTP {status_code} Server Error: Máy chủ Google gặp sự cố. Chi tiết: {error_body}"
                    )
                else:
                    raise EmbeddingError(f"HTTP {status_code} Error: {error_body}")

            except (TimeoutError, urllib.error.URLError) as e:
                if attempt < self._max_retries - 1:
                    wait_time = 1.0 * (2 ** attempt)
                    logger.warning(f"[GeminiEmbeddingProvider] Lỗi kết nối: {e}. Thử lại sau {wait_time:.1f}s...")
                    await asyncio.sleep(wait_time)
                    continue
                raise NetworkTimeoutError(f"Không thể kết nối đến Google Gemini API sau {self._max_retries} lần thử: {e}")
            except Exception as e:
                if isinstance(e, EmbeddingError):
                    raise
                raise EmbeddingError(f"Lỗi không xác định khi gọi Gemini API: {e}")

        raise EmbeddingError("Google Gemini Embedding API không phản hồi kết quả hợp lệ.")


# ==============================================================================
# MOCK EMBEDDING PROVIDER (UNIT TEST ONLY)
# ==============================================================================

class MockEmbeddingProvider(BaseEmbeddingProvider):
    """
    Mock Embedding Provider for isolated unit tests ONLY.
    Produces deterministic vectors with zero network overhead.
    """

    def __init__(self, dimension: int = 768, model: str = "mock-embedding-v1"):
        self._dim = dimension
        self._model = model

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimension(self) -> int:
        return self._dim

    async def embed_text(self, text: str) -> List[float]:
        vec = [0.0] * self._dim
        words = text.split()
        for w in words:
            idx = int(hashlib.md5(w.lower().encode("utf-8")).hexdigest(), 16) % self._dim
            vec[idx] += 1.0
        # Ensure not pure zeros
        if all(abs(x) < 1e-9 for x in vec):
            vec[0] = 1.0
        return self.normalize_l2(vec)

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        return [await self.embed_text(t) for t in texts]


# ==============================================================================
# PROVIDER FACTORY
# ==============================================================================

_embedding_provider_instance: Optional[BaseEmbeddingProvider] = None

def get_embedding_provider() -> BaseEmbeddingProvider:
    global _embedding_provider_instance
    if _embedding_provider_instance is None:
        provider_type = os.getenv("EMBEDDING_PROVIDER", "gemini").lower()
        if provider_type == "mock":
            _embedding_provider_instance = MockEmbeddingProvider()
        else:
            _embedding_provider_instance = GeminiEmbeddingProvider()
    return _embedding_provider_instance
