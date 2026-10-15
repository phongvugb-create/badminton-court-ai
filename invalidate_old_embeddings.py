"""
BADMINTON.AI - INVALIDATE OLD VECTORS IN DATABASE
Safely resets embedding and metadata columns for doc_fa6ecfe47d9b to NULL.
Preserves original chunk text and metadata.
"""

import os
import sys
import asyncio

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.core.database import AsyncSessionLocal
from app.ai.embedding_ingestion_service import get_embedding_ingestion_service
from sqlalchemy.future import select
from sqlalchemy import func
from app.models.all_models import DocumentChunk

async def main():
    doc_id = "doc_fa6ecfe47d9b"
    service = get_embedding_ingestion_service()

    async with AsyncSessionLocal() as db:
        # Check current count
        count_stmt = select(func.count()).select_from(DocumentChunk).where(
            DocumentChunk.document_id == doc_id,
            DocumentChunk.embedding.isnot(None)
        )
        res = await db.execute(count_stmt)
        before_count = res.scalar()
        print(f"Số lượng chunk có embedding trước khi invalidate: {before_count}")

        # Invalidate
        invalidated = await service.invalidate_document_embeddings(db, doc_id)
        print(f"Đã invalidate thành công: {invalidated} chunks")

        # Check after count
        res_after = await db.execute(count_stmt)
        after_count = res_after.scalar()
        print(f"Số lượng chunk có embedding sau khi invalidate: {after_count}")

if __name__ == "__main__":
    asyncio.run(main())
