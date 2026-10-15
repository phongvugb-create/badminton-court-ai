"""
BADMINTON.AI - RUN REAL EMBEDDING ON 91 CHUNKS OF SRS DOCUMENT
Vectorizes doc_fa6ecfe47d9b using EmbeddingIngestionService on badminton.db.
"""

import os
import sys
import asyncio
import json
import math
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from sqlalchemy.future import select
from sqlalchemy import func, text
from app.core.database import AsyncSessionLocal
from app.models.all_models import Document, DocumentChunk
from app.ai.embedding_ingestion_service import get_embedding_ingestion_service

async def main():
    service = get_embedding_ingestion_service()
    doc_id = "doc_fa6ecfe47d9b"

    print("=" * 65)
    print(f"BẮT ĐẦU VECTOR HÓA CHO TÀI LIỆU: {doc_id}")
    print(f"Provider: {service.provider.provider_name.upper()}")
    print(f"Model: {service.provider.model_name}")
    print(f"Dimension: {service.provider.dimension}")
    print("=" * 65)

    async with AsyncSessionLocal() as db:
        # Check doc exists
        stmt = select(Document).where(Document.id == doc_id)
        res = await db.execute(stmt)
        doc = res.scalar_one_or_none()

        if not doc:
            print(f"❌ Không tìm thấy document {doc_id} trong database!")
            return

        print(f"Tiêu đề tài liệu: {doc.title}")
        print(f"Trạng thái tài liệu: {doc.status}")
        print(f"Tổng số chunks đã nạp: {doc.total_chunks}")

        t0 = time.time()
        report = await service.embed_document_chunks(
            db=db,
            document_id=doc_id,
            force_reembed=True,
            batch_size=20
        )
        elapsed = time.time() - t0

        print("\n" + "=" * 65)
        print("KẾT QUẢ VECTORIZATION JOBS:")
        print(f"- Trạng thái: {report.status}")
        print(f"- Tổng chunks: {report.total_chunks}")
        print(f"- Chunks vector hóa thành công: {report.embedded_chunks}")
        print(f"- Chunks bỏ qua: {report.skipped_chunks}")
        print(f"- Chunks thất bại: {report.failed_chunks}")
        print(f"- Model sử dụng: {report.embedding_model}")
        print(f"- Dimension: {report.embedding_dimension}")
        print(f"- Thời gian thực hiện: {report.elapsed_seconds:.2f}s (tổng: {elapsed:.2f}s)")
        print(f"- Thông điệp: {report.message}")
        print("=" * 65)

        # SQL Database Verification
        print("\nKIỂM TRA CƠ SỞ DỮ LIỆU:")
        count_stmt = select(func.count()).select_from(DocumentChunk).where(
            DocumentChunk.document_id == doc_id,
            DocumentChunk.embedding.isnot(None)
        )
        res_count = await db.execute(count_stmt)
        embedded_db_count = res_count.scalar()

        total_stmt = select(func.count()).select_from(DocumentChunk).where(
            DocumentChunk.document_id == doc_id
        )
        res_total = await db.execute(total_stmt)
        total_db_count = res_total.scalar()

        print(f"COUNT(embedding IS NOT NULL)  : {embedded_db_count}")
        print(f"COUNT(document_id = '{doc_id}'): {total_db_count}")
        print(f"Tỷ lệ thành công: {embedded_db_count}/{total_db_count} ({embedded_db_count/total_db_count*100:.1f}%)")

        # Sample vector validation preview
        chunks_stmt = select(DocumentChunk).where(
            DocumentChunk.document_id == doc_id
        ).order_by(DocumentChunk.chunk_index.asc()).limit(3)
        res_sample = await db.execute(chunks_stmt)
        sample_chunks = res_sample.scalars().all()

        print("\nKIỂM ĐỊNH MẪU 3 VECTOR:")
        for idx, sc in enumerate(sample_chunks, 1):
            vec = sc.embedding
            if isinstance(vec, str):
                vec = json.loads(vec)
            norm = math.sqrt(sum(x * x for x in vec)) if vec else 0.0
            print(f"[{idx}] chunk_id: {sc.id} | index: {sc.chunk_index}")
            print(f"    model: {sc.embedding_model} | dimension: {sc.embedding_dimension}")
            print(f"    vector length: {len(vec) if vec else 0} | L2 norm: {norm:.4f}")
            print(f"    embedded_at: {sc.embedded_at}")
            print(f"    first 5 values: {vec[:5] if vec else None}")

if __name__ == "__main__":
    asyncio.run(main())
