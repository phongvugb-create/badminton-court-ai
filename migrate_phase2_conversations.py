import os
import sys
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migration")

# Ensure backend directory is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.core.database import engine, Base
from app.models.all_models import Conversation, ChatMessage

async def migrate_phase2():
    logger.info("Bắt đầu migration tạo bảng conversations & chat_messages...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Hoàn tất migration: Bảng conversations và chat_messages đã được tạo thành công.")

if __name__ == "__main__":
    asyncio.run(migrate_phase2())
