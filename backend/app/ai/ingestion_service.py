"""
BADMINTON.AI - DOCUMENT INGESTION SERVICE
Manages the end-to-end ingestion pipeline:
Validate -> Checksum -> Parse -> Clean -> Chunk -> Metadata -> Database Persistence.
Supports deduplication, versioning, atomic transactions, and access control.
Independent of ChatbotService, zero LLM / Vector DB calls in this phase.
"""

import hashlib
import json
import uuid
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete

from app.models.all_models import Document, DocumentChunk, User
from app.schemas.all_schemas import DocumentIngestResponse
from .parsers import get_parser, UnsupportedDocumentTypeError, MalformedDocumentError
from .chunker import HierarchicalChunker, ChunkItem

logger = logging.getLogger("ingestion_service")

class DocumentIngestionService:
    """Service handling document ingestion, chunking, and database storage."""

    def __init__(self, chunker: Optional[HierarchicalChunker] = None):
        self.chunker = chunker or HierarchicalChunker(
            chunk_size=500,
            chunk_overlap=80,
            min_chunk_size=50,
            max_chunk_size=800
        )

    @staticmethod
    def calculate_checksum(content_bytes: bytes) -> str:
        """Calculates SHA-256 hash of raw document bytes."""
        return hashlib.sha256(content_bytes).hexdigest()

    async def ingest_file(
        self,
        db: AsyncSession,
        content_bytes: bytes,
        filename: str,
        title: Optional[str] = None,
        source_type: str = "policy",
        access_scope: str = "public",
        owner_id: Optional[int] = None,
        reingest: bool = False
    ) -> DocumentIngestResponse:
        """
        Executes complete ingestion pipeline from raw bytes.
        """
        # 1. Validation
        if not content_bytes or len(content_bytes.strip()) == 0:
            raise ValueError("Tài liệu rỗng. Không có nội dung để nạp vào hệ thống.")

        doc_title = title or filename
        checksum = self.calculate_checksum(content_bytes)

        # 2. Check Deduplication
        stmt = select(Document).where(Document.checksum == checksum, Document.status == "READY")
        res = await db.execute(stmt)
        existing_doc = res.scalar_one_or_none()

        if existing_doc and not reingest:
            logger.info(f"Phát hiện tài liệu trùng checksum ({checksum[:8]}...). Bỏ qua nạp mới: {existing_doc.id}")
            return DocumentIngestResponse(
                document_id=existing_doc.id,
                title=existing_doc.title,
                filename=existing_doc.filename,
                status=existing_doc.status,
                checksum=existing_doc.checksum,
                version=existing_doc.version,
                total_chunks=existing_doc.total_chunks,
                is_duplicate=True,
                access_scope=existing_doc.access_scope,
                message="Tài liệu đã tồn tại với cùng nội dung (checksum khớp). Bỏ qua việc tạo bản sao trùng lặp."
            )

        # 3. Parse Document
        parser = get_parser(filename)
        try:
            parsed_doc = parser.parse(content_bytes, filename)
        except Exception as e:
            logger.error(f"Lỗi khi bóc tách tài liệu '{filename}': {e}")
            raise MalformedDocumentError(f"Không thể đọc cấu trúc tệp '{filename}': {str(e)}")

        if not parsed_doc.sections or parsed_doc.total_characters == 0:
            raise ValueError("Tài liệu không chứa văn bản hợp lệ sau khi bóc tách.")

        # 4. Chunk Document
        chunks: List[ChunkItem] = self.chunker.chunk_document(parsed_doc)
        if not chunks:
            raise ValueError("Không tạo được phân đoạn (chunks) nào từ tài liệu.")

        # 5. Database Persistence with Transaction Safety
        target_doc: Optional[Document] = None
        try:
            if existing_doc and reingest:
                # Re-ingestion: bump version and delete previous chunks
                target_doc = existing_doc
                target_doc.version += 1
                target_doc.title = doc_title
                target_doc.status = "PROCESSING"
                target_doc.error_message = None
                target_doc.access_scope = access_scope
                target_doc.updated_at = datetime.utcnow()

                # Clean old chunks
                await db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == target_doc.id))
            else:
                doc_id = f"doc_{uuid.uuid4().hex[:12]}"
                target_doc = Document(
                    id=doc_id,
                    title=doc_title,
                    filename=filename,
                    source_type=source_type,
                    mime_type=parsed_doc.mime_type,
                    checksum=checksum,
                    version=1,
                    status="PROCESSING",
                    total_chunks=0,
                    access_scope=access_scope,
                    owner_id=owner_id,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.add(target_doc)
                await db.flush()

            # Insert chunks
            for c in chunks:
                meta = {
                    "document_id": target_doc.id,
                    "filename": filename,
                    "source_type": source_type,
                    "access_scope": access_scope,
                    "char_count": c.char_count,
                    "token_estimate": c.token_estimate
                }
                chunk_record = DocumentChunk(
                    id=f"chunk_{uuid.uuid4().hex[:12]}",
                    document_id=target_doc.id,
                    chunk_index=c.chunk_index,
                    text=c.text,
                    page_number=c.page_number,
                    section=c.section,
                    token_estimate=c.token_estimate,
                    meta_info=json.dumps(meta, ensure_ascii=False),
                    created_at=datetime.utcnow()
                )
                db.add(chunk_record)

            target_doc.status = "READY"
            target_doc.total_chunks = len(chunks)
            await db.commit()
            await db.refresh(target_doc)

            logger.info(f"✅ Đã nạp thành công tài liệu {target_doc.id} ({filename}) với {len(chunks)} chunks.")

            return DocumentIngestResponse(
                document_id=target_doc.id,
                title=target_doc.title,
                filename=target_doc.filename,
                status=target_doc.status,
                checksum=target_doc.checksum,
                version=target_doc.version,
                total_chunks=target_doc.total_chunks,
                is_duplicate=False,
                access_scope=target_doc.access_scope,
                message=f"Nạp thành công tài liệu với {len(chunks)} phân đoạn tri thức (chunks)."
            )

        except Exception as e:
            await db.rollback()
            logger.error(f"❌ Thất bại khi lưu trữ tài liệu '{filename}' vào database: {e}")
            if target_doc and target_doc.id:
                try:
                    # Update status to FAILED in a separate transaction
                    target_doc.status = "FAILED"
                    target_doc.error_message = str(e)
                    db.add(target_doc)
                    await db.commit()
                except Exception:
                    await db.rollback()
            raise e

    async def ingest_text(
        self,
        db: AsyncSession,
        text_content: str,
        title: str,
        filename: str = "manual_input.txt",
        source_type: str = "policy",
        access_scope: str = "public",
        owner_id: Optional[int] = None,
        reingest: bool = False
    ) -> DocumentIngestResponse:
        """Helper to ingest raw plaintext directly."""
        content_bytes = text_content.encode("utf-8")
        return await self.ingest_file(
            db=db,
            content_bytes=content_bytes,
            filename=filename,
            title=title,
            source_type=source_type,
            access_scope=access_scope,
            owner_id=owner_id,
            reingest=reingest
        )

    async def list_documents(
        self,
        db: AsyncSession,
        user_role: Optional[str] = "CUSTOMER",
        user_id: Optional[int] = None,
        access_scope_filter: Optional[str] = None
    ) -> List[Document]:
        """
        Lists documents with access control filtering.
        - ADMIN: sees all documents
        - STAFF / OWNER: sees 'public' and 'internal'
        - CUSTOMER / Guest: sees 'public' (plus their own uploaded documents if user_id matches)
        """
        stmt = select(Document).order_by(Document.created_at.desc())

        res = await db.execute(stmt)
        all_docs = res.scalars().all()

        allowed_docs: List[Document] = []
        for doc in all_docs:
            if access_scope_filter and doc.access_scope != access_scope_filter:
                continue

            if user_role == "ADMIN":
                allowed_docs.append(doc)
            elif user_role in ["STAFF", "OWNER"]:
                if doc.access_scope in ["public", "internal"] or (user_id and doc.owner_id == user_id):
                    allowed_docs.append(doc)
            else: # CUSTOMER or Guest
                if doc.access_scope == "public" or (user_id and doc.owner_id == user_id):
                    allowed_docs.append(doc)

        return allowed_docs

    async def get_document(
        self,
        db: AsyncSession,
        document_id: str,
        user_role: Optional[str] = "CUSTOMER",
        user_id: Optional[int] = None
    ) -> Optional[Document]:
        """Retrieves a single document verifying access permissions."""
        stmt = select(Document).where(Document.id == document_id)
        res = await db.execute(stmt)
        doc = res.scalar_one_or_none()
        if not doc:
            return None

        # Access check
        if user_role != "ADMIN":
            if doc.access_scope == "admin":
                return None
            if doc.access_scope == "internal" and user_role not in ["STAFF", "OWNER"]:
                if not (user_id and doc.owner_id == user_id):
                    return None

        return doc

    async def get_document_chunks(
        self,
        db: AsyncSession,
        document_id: str,
        user_role: Optional[str] = "CUSTOMER",
        user_id: Optional[int] = None
    ) -> List[DocumentChunk]:
        """Retrieves chunks of a document with permission verification."""
        doc = await self.get_document(db, document_id, user_role, user_id)
        if not doc:
            return []

        stmt = select(DocumentChunk).where(
            DocumentChunk.document_id == document_id
        ).order_by(DocumentChunk.chunk_index.asc())

        res = await db.execute(stmt)
        return res.scalars().all()

_ingestion_service_instance: Optional[DocumentIngestionService] = None

def get_ingestion_service() -> DocumentIngestionService:
    global _ingestion_service_instance
    if _ingestion_service_instance is None:
        _ingestion_service_instance = DocumentIngestionService()
    return _ingestion_service_instance
