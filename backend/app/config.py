import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_file=str(Path(__file__).resolve().parents[2] / ".env"),
        extra="ignore"
    )

    PROJECT_NAME: str = "Badminton & Pickleball AI Rental System"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Application & Environment
    PORT: int = 8085
    NODE_ENV: str = os.getenv("NODE_ENV", "development")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "")
    PAYMENT_SANDBOX_ENABLED: bool = os.getenv("PAYMENT_SANDBOX_ENABLED", "false").lower() in ["1", "true", "yes"]
    PAYMENT_PENDING_EXPIRY_ENABLED: bool = os.getenv("PAYMENT_PENDING_EXPIRY_ENABLED", "false").lower() in ["1", "true", "yes"]
    PAYMENT_PENDING_EXPIRY_MINUTES: Optional[int] = (
        int(os.getenv("PAYMENT_PENDING_EXPIRY_MINUTES"))
        if os.getenv("PAYMENT_PENDING_EXPIRY_MINUTES") and os.getenv("PAYMENT_PENDING_EXPIRY_MINUTES").strip().isdigit()
        else None
    )
    SCHEDULER_API_SECRET: Optional[str] = os.getenv("SCHEDULER_API_SECRET", None)

    # Secret Key for JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", "badminton_super_secret_jwt_key_2026")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Database configuration
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "sqlite+aiosqlite:///./badminton.db"
    )
    SYNC_DATABASE_URL: str = os.getenv(
        "SYNC_DATABASE_URL",
        "sqlite:///./badminton.db"
    )
    POSTGRES_USER: Optional[str] = "postgres"
    POSTGRES_PASSWORD: Optional[str] = "admin123"
    POSTGRES_DB: Optional[str] = "badminton_ai_db"
    
    # Redis configuration
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
    SLOT_HOLD_TIMEOUT_SECONDS: int = 600  # 10 minutes lock
    
    # Google Gemini AI API Configuration
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", "")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini-3.5-flash-lite")
    LLM_TIMEOUT_SECONDS: float = float(os.getenv("LLM_TIMEOUT_SECONDS", "30.0"))

    # RAG Embedding Configuration (Phase 4 & Phase 4.1)
    EMBEDDING_PROVIDER: str = os.getenv("EMBEDDING_PROVIDER", "gemini")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "gemini-embedding-2")
    EMBEDDING_DIMENSION: int = int(os.getenv("EMBEDDING_DIMENSION", "768"))
    EMBEDDING_VERSION: str = os.getenv("EMBEDDING_VERSION", "v1")
    EMBEDDING_TIMEOUT_SECONDS: float = float(os.getenv("EMBEDDING_TIMEOUT_SECONDS", "10.0"))
    EMBEDDING_BATCH_SIZE: int = int(os.getenv("EMBEDDING_BATCH_SIZE", "20"))

    # RAG Retrieval Configuration (Phase 5)
    RETRIEVAL_TOP_K: int = int(os.getenv("RETRIEVAL_TOP_K", "5"))
    RETRIEVAL_SIMILARITY_THRESHOLD: float = float(os.getenv("RETRIEVAL_SIMILARITY_THRESHOLD", "0.58"))

    # RAG Generation Configuration (Phase 6)
    RAG_TOP_K: int = int(os.getenv("RAG_TOP_K", "3"))
    RAG_MAX_CONTEXT_CHARS: int = int(os.getenv("RAG_MAX_CONTEXT_CHARS", "4000"))
    RAG_MAX_CONTEXT_TOKENS: int = int(os.getenv("RAG_MAX_CONTEXT_TOKENS", "1000"))
    RAG_ENABLE_EVIDENCE_GATE: bool = os.getenv("RAG_ENABLE_EVIDENCE_GATE", "true").lower() in ["1", "true", "yes"]

    # VNPay Payment Gateway
    VNPAY_TMN_CODE: Optional[str] = "SMASHING"
    VNPAY_HASH_SECRET: Optional[str] = "SECRET_VNPAY_KEY_2026"
    VNPAY_URL: Optional[str] = "https://sandbox.vnpayment.vn/paymentv2/vpcpay.html"

    # MoMo Payment Gateway Configuration (Phase 7.4B)
    MOMO_ENVIRONMENT: str = os.getenv("MOMO_ENVIRONMENT", "sandbox").lower()
    MOMO_PARTNER_CODE: Optional[str] = os.getenv("MOMO_PARTNER_CODE", None)
    MOMO_ACCESS_KEY: Optional[str] = os.getenv("MOMO_ACCESS_KEY", None)
    MOMO_SECRET_KEY: Optional[str] = os.getenv("MOMO_SECRET_KEY", None)
    MOMO_ENDPOINT: str = os.getenv("MOMO_ENDPOINT", "https://test-payment.momo.vn")
    MOMO_REDIRECT_URL: Optional[str] = os.getenv("MOMO_REDIRECT_URL", None)
    MOMO_IPN_URL: Optional[str] = os.getenv("MOMO_IPN_URL", None)
    MOMO_PARTNER_NAME: Optional[str] = os.getenv("MOMO_PARTNER_NAME", "Badminton AI")
    MOMO_STORE_ID: Optional[str] = os.getenv("MOMO_STORE_ID", "BadmintonCourt01")
    MOMO_TIMEOUT_SECONDS: float = float(os.getenv("MOMO_TIMEOUT_SECONDS", "30.0"))

settings = Settings()
