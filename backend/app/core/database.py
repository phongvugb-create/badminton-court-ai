from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Determine if we should use async sqlite or async postgres
db_url = settings.DATABASE_URL
# Both server.py and uvicorn must use the same local knowledge/booking database,
# regardless of the directory from which the process was started.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
LOCAL_DATABASE_URL = "sqlite+aiosqlite:///" + (PROJECT_ROOT / "badminton.db").as_posix()
if db_url.startswith("sqlite+aiosqlite:///"):
    local_path = db_url[len("sqlite+aiosqlite:///"):]
    if local_path != ":memory:" and not Path(local_path).is_absolute():
        db_url = "sqlite+aiosqlite:///" + (PROJECT_ROOT / local_path).resolve().as_posix()
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

engine_kwargs = {"echo": False, "future": True}
if "sqlite" in db_url:
    engine_kwargs["connect_args"] = {"check_same_thread": False, "timeout": 30}
else:
    engine_kwargs["pool_pre_ping"] = True

import socket
from urllib.parse import urlparse


def is_db_reachable(url_str: str) -> bool:
    if "sqlite" in url_str:
        return True
    try:
        parsed = urlparse(url_str.replace("postgresql+asyncpg://", "http://").replace("postgresql://", "http://"))
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 5432
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.5)
        s.connect((host, port))
        s.close()
        return True
    except Exception:
        return False


if "sqlite" in db_url or is_db_reachable(db_url):
    try:
        engine = create_async_engine(db_url, **engine_kwargs)
    except Exception as e:
        logger.warning(f"Could not initialize database engine for {db_url}: {e}. Fallback to sqlite async.")
        engine = create_async_engine(
            LOCAL_DATABASE_URL,
            echo=False,
            future=True,
            connect_args={"check_same_thread": False, "timeout": 30}
        )
else:
    logger.info(f"Target PostgreSQL at {db_url} is unreachable. Fallback to sqlite async active.")
    engine = create_async_engine(
        LOCAL_DATABASE_URL,
        echo=False,
        future=True,
        connect_args={"check_same_thread": False, "timeout": 30}
    )

AsyncSessionLocal = async_sessionmaker(
    engine, expire_on_commit=False
)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
