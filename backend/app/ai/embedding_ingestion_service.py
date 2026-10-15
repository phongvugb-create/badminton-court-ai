"""
BADMINTON.AI - EMBEDDING INGESTION SERVICE
Manages embedding generation for document chunks and persistence into vector store.
Handles batching, dimension validation, idempotency, re-embedding, invalidation, and error handling.
STRICT: Never accepts or saves fake fallback vectors. Atomically rolls back batches on error.
Does NOT perform retrieval or touch ChatbotService / /chat.
"""

import time
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, update

from app.models.all_models import Document, DocumentChunk
from app.schemas.all_schemas import EmbeddingJobResponse
from .embedding_provider import BaseEmbeddingProvider, get_embedding_provider

logger = logging.getLogger("embedding_ingestion_service")

class EmbeddingIngestionService:
    """Service orchestrating batch vectorization of stored document chunks."""

    def __init__(self, provider: Optional[BaseEmbeddingProvider] = None):
        self.provider = provider or get_embedding_provider()

    async def invalidate_document_embeddings(
        self,
        db: AsyncSession,
        document_id: str
    ) -> int:
        """
        Clears/invalidates all existing embeddings and vector metadata for a document.
        Guarantees that old vectors from deprecated models are NEVER mixed with new vectors.
        Preserves original document text and chunk structure.
        """
        count_stmt = select(func.count()).select_from(DocumentChunk).where(
            DocumentChunk.document_id == document_id,
            DocumentChunk.embedding.isnot(None)
        )
        res = await db.execute(count_stmt)
        count = res.scalar() or 0

        upd_stmt = (
            update(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .values(
                embedding=None,
                embedding_model=None,
                embedding_dimension=None,
                embedding_version=None,
                embedded_at=None
            )
        )
        await db.execute(upd_stmt)
        await db.commit()
        logger.info(f"[IngestionService] Đã vô hiệu hóa (invalidated) {count} vectors cũ của tài liệu '{document_id}'.")
        return count

    async def embed_document_chunks(
        self,
        db: AsyncSession,
        document_id: str,
        force_reembed: bool = False,
        batch_size: int = 20
    ) -> EmbeddingJobResponse:
        """
        Embeds chunks belonging to a READY document.
        Pipeline Flow:
          document_chunks -> clear/invalidate old embedding (if forced/changed)
          -> embedding model mới -> validate -> save new embedding.
        Idempotent: skips already embedded chunks with current model unless forced.
        """
        start_time = time.time()

        # 1. Verify Document Status
        stmt = select(Document).where(Document.id == document_id)
        res = await db.execute(stmt)
        doc = res.scalar_one_or_none()

        if not doc:
            raise ValueError(f"Tài liệu với ID '{document_id}' không tồn tại trong hệ thống.")

        if doc.status != "READY":
            raise ValueError(
                f"Tài liệu '{document_id}' chưa sẵn sàng để tạo embedding (trạng thái hiện tại: '{doc.status}'). "
                f"Chỉ tài liệu có trạng thái READY mới được phép xử lý."
            )

        # 2. Check existing chunks count & models
        count_stmt = select(func.count()).select_from(DocumentChunk).where(
            DocumentChunk.document_id == document_id
        )
        res_count = await db.execute(count_stmt)
        total_chunks = res_count.scalar() or 0

        if total_chunks == 0:
            elapsed = time.time() - start_time
            return EmbeddingJobResponse(
                document_id=document_id,
                total_chunks=0,
                embedded_chunks=0,
                skipped_chunks=0,
                failed_chunks=0,
                embedding_model=self.provider.model_name,
                embedding_dimension=self.provider.dimension,
                embedding_version=getattr(self.provider, "embedding_version", "v1"),
                elapsed_seconds=round(elapsed, 3),
                status="NO_CHUNKS",
                message="Tài liệu không có phân đoạn (chunks) nào để vector hóa."
            )

        # 3. Model migration check / Invalidation check
        # Check if any chunk has embedding from different model
        diff_model_stmt = select(DocumentChunk.id).where(
            DocumentChunk.document_id == document_id,
            DocumentChunk.embedding.isnot(None),
            DocumentChunk.embedding_model != self.provider.model_name
        ).limit(1)
        res_diff = await db.execute(diff_model_stmt)
        has_different_model = res_diff.scalar_one_or_none() is not None

        if force_reembed or has_different_model:
            await self.invalidate_document_embeddings(db, document_id)

        # 4. Query chunks and filter for embedding
        chunk_stmt = select(
            DocumentChunk.id,
            DocumentChunk.text,
            DocumentChunk.chunk_index,
            DocumentChunk.embedding,
            DocumentChunk.embedding_model
        ).where(
            DocumentChunk.document_id == document_id
        ).order_by(DocumentChunk.chunk_index.asc())
        chunk_res = await db.execute(chunk_stmt)
        all_chunk_records = chunk_res.all()

        chunks_to_embed: List[Dict[str, Any]] = []
        skipped_count = 0

        for r in all_chunk_records:
            cid, ctext, cidx, cemb, cmodel = r
            if cemb is not None and cmodel == self.provider.model_name and not force_reembed:
                skipped_count += 1
            else:
                chunks_to_embed.append({"id": cid, "text": ctext, "chunk_index": cidx})

        if not chunks_to_embed:
            elapsed = time.time() - start_time
            logger.info(f"Tất cả {total_chunks} chunks của tài liệu '{document_id}' đã có vector hợp lệ với model '{self.provider.model_name}'.")
            return EmbeddingJobResponse(
                document_id=document_id,
                total_chunks=total_chunks,
                embedded_chunks=0,
                skipped_chunks=skipped_count,
                failed_chunks=0,
                embedding_model=self.provider.model_name,
                embedding_dimension=self.provider.dimension,
                embedding_version=getattr(self.provider, "embedding_version", "v1"),
                elapsed_seconds=round(elapsed, 3),
                status="ALREADY_UP_TO_DATE",
                message=f"Tất cả {total_chunks} chunks đã được vector hóa trước đó với model '{self.provider.model_name}'."
            )

        # 5. Batch Embedding Execution
        embedded_count = 0
        failed_count = 0
        current_time = datetime.utcnow()

        logger.info(
            f"Bắt đầu vector hóa {len(chunks_to_embed)} chunks cho doc '{document_id}' "
            f"(Model: {self.provider.model_name}, Dim: {self.provider.dimension}, Batch: {batch_size})..."
        )

        for i in range(0, len(chunks_to_embed), batch_size):
            batch = chunks_to_embed[i : i + batch_size]
            texts = [c["text"] for c in batch]
            batch_ids = [c["id"] for c in batch]

            try:
                vectors = await self.provider.embed_texts(texts)

                if len(vectors) != len(batch):
                    raise ValueError(
                        f"Số lượng vector trả về ({len(vectors)}) không khớp với số chunk gửi đi ({len(batch)})."
                    )

                # Query the ORM objects for this specific batch
                orm_stmt = select(DocumentChunk).where(DocumentChunk.id.in_(batch_ids))
                orm_res = await db.execute(orm_stmt)
                orm_map = {c.id: c for c in orm_res.scalars().all()}

                # Validate and assign
                for c_data, vec in zip(batch, vectors):
                    self.provider.validate_vector(vec)
                    chunk_obj = orm_map[c_data["id"]]
                    chunk_obj.embedding = vec
                    chunk_obj.embedding_model = self.provider.model_name
                    chunk_obj.embedding_dimension = self.provider.dimension
                    chunk_obj.embedding_version = getattr(self.provider, "embedding_version", "v1")
                    chunk_obj.embedded_at = current_time
                    db.add(chunk_obj)

                await db.commit()
                embedded_count += len(batch)
                logger.info(f"  -> Batch {i // batch_size + 1}: +{len(batch)} chunks vector hóa thành công.")

            except Exception as e:
                await db.rollback()
                failed_count += len(batch)
                logger.error(f"  ❌ Lỗi khi vector hóa batch {i // batch_size + 1}: {e}")

        elapsed = time.time() - start_time
        if failed_count == 0 and embedded_count > 0:
            status = "COMPLETED"
        elif embedded_count > 0 and failed_count > 0:
            status = "PARTIAL_FAILURE"
        elif failed_count > 0 and embedded_count == 0:
            status = "FAILED"
        else:
            status = "NO_OP"

        return EmbeddingJobResponse(
            document_id=document_id,
            total_chunks=total_chunks,
            embedded_chunks=embedded_count,
            skipped_chunks=skipped_count,
            failed_chunks=failed_count,
            embedding_model=self.provider.model_name,
            embedding_dimension=self.provider.dimension,
            embedding_version=getattr(self.provider, "embedding_version", "v1"),
            elapsed_seconds=round(elapsed, 3),
            status=status,
            message=(
                f"Vector hóa: {embedded_count}/{total_chunks} chunks thành công. "
                f"Bỏ qua: {skipped_count}, Thất bại: {failed_count}. "
                f"Model: {self.provider.model_name} (Dim: {self.provider.dimension})."
            )
        )

    async def embed_all_pending_chunks(
        self,
        db: AsyncSession,
        force_reembed: bool = False,
        batch_size: int = 20
    ) -> List[EmbeddingJobResponse]:
        """
        Embeds chunks for all READY documents across the system.
        """
        stmt = select(Document).where(Document.status == "READY")
        res = await db.execute(stmt)
        ready_docs = res.scalars().all()

        reports: List[EmbeddingJobResponse] = []
        for doc in ready_docs:
            rep = await self.embed_document_chunks(
                db=db,
                document_id=doc.id,
                force_reembed=force_reembed,
                batch_size=batch_size
            )
            reports.append(rep)

        return reports

_embedding_ingestion_service_instance: Optional[EmbeddingIngestionService] = None

def get_embedding_ingestion_service() -> EmbeddingIngestionService:
    global _embedding_ingestion_service_instance
    if _embedding_ingestion_service_instance is None:
        _embedding_ingestion_service_instance = EmbeddingIngestionService()
    return _embedding_ingestion_service_instance
