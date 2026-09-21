import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_file=".env",
        extra="ignore"
    )

    PROJECT_NAME: str = "Badminton & Pickleball AI Rental System"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Application & Environment
    PORT: int = 8085
    NODE_ENV: str = "development"

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
    
    # Google Gemini AI API Key
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    # VNPay Payment Gateway
    VNPAY_TMN_CODE: Optional[str] = "SMASHING"
    VNPAY_HASH_SECRET: Optional[str] = "SECRET_VNPAY_KEY_2026"
    VNPAY_URL: Optional[str] = "https://sandbox.vnpayment.vn/paymentv2/vpcpay.html"

settings = Settings()
