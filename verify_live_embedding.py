"""
BADMINTON.AI - LIVE API EMBEDDING VERIFICATION (PHASE 4.2)
Directly tests the configured Gemini Embedding Provider against live Google API.
Test query: "Chính sách đặt sân và thời gian giữ chỗ."
CRITICAL:
- NEVER logs, prints, or exposes raw API keys.
- Accurately classifies HTTP 401 / 403 / 400 / 429 / 5xx / timeout.
- Validates 768 dimension, numeric values, non-zero, L2 norm.
"""

import os
import sys
import time
import asyncio
import math

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.ai.embedding_provider import (
    GeminiEmbeddingProvider,
    CredentialInvalidError,
    PermissionDeniedError,
    InvalidRequestError,
    RateLimitExceededError,
    ProviderServerError,
    NetworkTimeoutError,
    EmbeddingError
)

async def verify_live_api():
    test_sentence = "Chính sách đặt sân và thời gian giữ chỗ."

    print("=" * 65)
    print("PHASE 4.2: LIVE GEMINI EMBEDDING API VERIFICATION")
    print("=" * 65)
    print(f"Test Sentence     : '{test_sentence}'")

    provider = GeminiEmbeddingProvider()
    has_key = bool(provider._api_key)
    # Masked preview without leaking secret
    key_status = "CONFIGURED (Format Check Required)" if has_key else "NOT_CONFIGURED"

    print(f"Provider          : {provider.provider_name.upper()}")
    print(f"Target Model      : {provider.model_name}")
    print(f"Target Dimension  : {provider.dimension}")
    print(f"API Key Status    : {key_status}")
    print("-" * 65)

    t0 = time.time()
    try:
        vector = await provider.embed_text(test_sentence)
        elapsed_ms = (time.time() - t0) * 1000

        # Rigorous validations
        provider.validate_vector(vector)
        norm = math.sqrt(sum(x * x for x in vector))

        # Check for non-triviality / not all identical
        unique_vals = len(set(round(x, 6) for x in vector))

        print("\n✅ KẾT QUẢ KIỂM TRA LIVE API:")
        print(f"  provider        : {provider.provider_name}")
        print(f"  model           : {provider.model_name}")
        print(f"  dimension       : {len(vector)}")
        print(f"  norm            : {norm:.6f}")
        print(f"  first_5_values  : {[round(v, 6) for v in vector[:5]]}")
        print(f"  unique_vals     : {unique_vals}/768")
        print(f"  elapsed_ms      : {elapsed_ms:.2f}ms")
        print(f"  success/failure : SUCCESS")
        print("=" * 65)
        return True, vector, elapsed_ms

    except CredentialInvalidError as e:
        elapsed_ms = (time.time() - t0) * 1000
        print("\n❌ KẾT QUẢ KIỂM TRA LIVE API:")
        print(f"  provider        : {provider.provider_name}")
        print(f"  model           : {provider.model_name}")
        print(f"  dimension       : {provider.dimension}")
        print(f"  norm            : N/A")
        print(f"  first_5_values  : N/A")
        print(f"  elapsed_ms      : {elapsed_ms:.2f}ms")
        print(f"  success/failure : FAILURE")
        print(f"  error_type      : CredentialInvalidError (HTTP 401)")
        print(f"  chi_tiet        : {e}")
        print("-" * 65)
        print("KẾT LUẬN: GEMINI_API_KEY không hợp lệ hoặc không phải API Key của Google AI Studio.")
        print("YÊU CẦU: Cần cập nhật API key hợp lệ (bắt đầu bằng 'AIzaSy...') vào file .env.")
        print("=" * 65)
        return False, None, elapsed_ms

    except PermissionDeniedError as e:
        elapsed_ms = (time.time() - t0) * 1000
        print(f"\n❌ LỖI TRUY CẬP (HTTP 403): {e}")
        return False, None, elapsed_ms

    except InvalidRequestError as e:
        elapsed_ms = (time.time() - t0) * 1000
        print(f"\n❌ LỖI REQUEST (HTTP 400): {e}")
        return False, None, elapsed_ms

    except RateLimitExceededError as e:
        elapsed_ms = (time.time() - t0) * 1000
        print(f"\n❌ LỖI RATE LIMIT (HTTP 429): {e}")
        return False, None, elapsed_ms

    except ProviderServerError as e:
        elapsed_ms = (time.time() - t0) * 1000
        print(f"\n❌ LỖI MÁY CHỦ GOOGLE (HTTP 5xx): {e}")
        return False, None, elapsed_ms

    except NetworkTimeoutError as e:
        elapsed_ms = (time.time() - t0) * 1000
        print(f"\n❌ LỖI TIMEOUT: {e}")
        return False, None, elapsed_ms

    except Exception as e:
        elapsed_ms = (time.time() - t0) * 1000
        print(f"\n❌ LỖI KHÁC: {e}")
        return False, None, elapsed_ms

if __name__ == "__main__":
    success, _, _ = asyncio.run(verify_live_api())
    if not success:
        sys.exit(1)
    sys.exit(0)
