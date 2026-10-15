"""
BADMINTON.AI - EMBEDDING SERVICE
Chịu trách nhiệm tạo vector nhúng (embeddings) cho RAG pipeline sử dụng mô hình Google Gemini text-embedding-004.
Được thiết kế native (urllib.request), không phụ thuộc thư viện nặng, an toàn và có cơ chế fallback offline.
"""

import os
import json
import math
import hashlib
import logging
import urllib.request
import urllib.error
from typing import List, Optional, Dict, Any

logger = logging.getLogger("embedding_service")

EMBEDDING_MODEL = "text-embedding-004"
EMBEDDING_DIM = 768

def get_api_key() -> str:
    """Lấy API key từ biến môi trường hoặc file .env mà không để lộ secret ra ngoài."""
    key = os.environ.get("GEMINI_API_KEY", "")
    if key and not key.startswith("YOUR_"):
        return key.strip()
    
    # Đọc từ .env tại thư mục gốc nếu biến môi trường chưa được set
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    env_file = os.path.join(base_dir, ".env")
    if os.path.exists(env_file):
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("GEMINI_API_KEY="):
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if val and not val.startswith("YOUR_"):
                            return val
        except Exception:
            pass
    return ""

def generate_fallback_embedding(text: str, dim: int = EMBEDDING_DIM) -> List[float]:
    """
    Cơ chế dự phòng: Sinh vector đặc trưng từ chuỗi văn bản bằng thuật toán băm phân tán chuẩn hóa.
    Đảm bảo tính tất định (deterministic) và tính tương đồng từ khóa cơ bản khi offline.
    """
    words = text.lower().split()
    vector = [0.0] * dim
    
    for word in words:
        h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        val = ((h >> 8) % 1000) / 1000.0 - 0.5
        vector[idx] += val

    # Chuẩn hóa L2 norm về độ dài đơn vị 1.0
    norm = math.sqrt(sum(x * x for x in vector))
    if norm > 0:
        vector = [x / norm for x in vector]
    else:
        vector[0] = 1.0
    return vector

def get_text_embedding(text: str, api_key: Optional[str] = None) -> List[float]:
    """
    Gọi Google Gemini API để lấy vector nhúng 768 chiều cho một đoạn văn bản.
    """
    key = api_key or get_api_key()
    cleaned_text = (text or "").strip()
    if not cleaned_text:
        return [0.0] * EMBEDDING_DIM

    if not key:
        return generate_fallback_embedding(cleaned_text)

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{EMBEDDING_MODEL}:embedContent?key={key}"
    payload = {
        "model": f"models/{EMBEDDING_MODEL}",
        "content": {
            "parts": [{"text": cleaned_text[:2048]}] # Giới hạn an toàn độ dài token
        }
    }

    try:
        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=req_data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=5.0) as response:
            if response.status == 200:
                res_body = json.loads(response.read().decode("utf-8"))
                values = res_body.get("embedding", {}).get("values", [])
                if values and len(values) == EMBEDDING_DIM:
                    return values
    except Exception as e:
        logger.warning(f"Không thể kết nối Gemini Embedding API ({e}), kích hoạt fallback embedding.")

    return generate_fallback_embedding(cleaned_text)

def batch_get_embeddings(texts: List[str], api_key: Optional[str] = None) -> List[List[float]]:
    """
    Lấy vector nhúng cho một danh sách văn bản.
    """
    key = api_key or get_api_key()
    results = []
    for text in texts:
        results.append(get_text_embedding(text, key))
    return results

def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """
    Tính độ tương đồng Cosine giữa 2 vector [-1.0, 1.0].
    """
    if len(vec_a) != len(vec_b) or not vec_a:
        return 0.0
    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot_product / (norm_a * norm_b)
