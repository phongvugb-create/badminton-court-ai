from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Determine if we should use async sqlite or async postgres
db_url = settings.DATABASE_URL
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

engine_kwargs = {"echo": False, "future": True}
if "sqlite" in db_url:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs["pool_pre_ping"] = True

try:
    engine = create_async_engine(db_url, **engine_kwargs)
except Exception as e:
    logger.warning(f"Could not connect to database {db_url}: {e}. Fallback to sqlite async.")
    engine = create_async_engine(
        "sqlite+aiosqlite:///./badminton.db",
        echo=False,
        future=True,
        connect_args={"check_same_thread": False}
    )

AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
