"""
BADMINTON.AI - RETRIEVAL & VECTOR SEARCH SERVICE (PHASE 5)
Independent retrieval pipeline:
User Query -> Query Embedding -> Permission Filtering (RBAC) -> Vector Search (pgvector / SQLite candidate) -> Top-K Results -> Source Metadata.
STRICT: Does NOT call LLM, does NOT construct RAG prompts, does NOT modify ChatbotService.
"""

import os
import math
import time
import json
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, or_, func, text

from app.config import settings
from app.models.all_models import Document, DocumentChunk, UserRole, _HAS_PGVECTOR
from app.schemas.all_schemas import (
    RetrievalSearchRequest,
    RetrievalSearchResponse,
    RetrievalResultItem
)
from .embedding_provider import (
    BaseEmbeddingProvider,
    get_embedding_provider
)
from .evidence_gate import (
    BaseEvidenceGate,
    get_evidence_gate
)

logger = logging.getLogger("retrieval_service")


# ==============================================================================
# BASE RETRIEVER ABSTRACTION
# ==============================================================================

class BaseRetriever(ABC):
    """
    Abstract Base Class for Document Retrieval Services.
    Allows easy extension (Dense Vector, Sparse BM25, Hybrid, Graph).
    """

    @abstractmethod
    async def retrieve(
        self,
        db: AsyncSession,
        query: str,
        user_context: Optional[Dict[str, Any]] = None,
        top_k: Optional[int] = None,
        similarity_threshold: Optional[float] = None,
        apply_evidence_gate: Optional[bool] = None
    ) -> RetrievalSearchResponse:
        """
        Executes search given a natural language query and user authorization context.
        """
        pass


_pgvector_db_cache: Dict[str, bool] = {}


async def _is_pgvector_native(db: AsyncSession) -> bool:
    """
    Checks if the connected PostgreSQL instance actually has the 'vector' extension installed.
    Prevents runtime 'operator does not exist: text <=> unknown' errors when pgvector Python
    library is installed but PostgreSQL runs on minimal/alpine without the pgvector extension.
    """
    if not _HAS_PGVECTOR:
        return False
    bind = db.bind or getattr(db, "sync_session", db).bind
    if not bind or "postgres" not in bind.dialect.name.lower():
        return False

    url_key = str(bind.url)
    if url_key in _pgvector_db_cache:
        return _pgvector_db_cache[url_key]

    try:
        res = await db.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'vector';"))
        has_ext = res.first() is not None
        _pgvector_db_cache[url_key] = has_ext
        return has_ext
    except Exception:
        _pgvector_db_cache[url_key] = False
        return False


class VectorRetriever(BaseRetriever):
    """
    Production-grade Vector Retriever with:
    1. Query embedding generation via configured EmbeddingProvider (gemini-embedding-2, 768-dim).
    2. Enforced RBAC Access Control filtering at query level (public, internal, admin, owner).
    3. Hybrid dialect engine:
       - PostgreSQL: database-side pgvector cosine distance operator `<=>`.
       - SQLite (dev/test): loads candidate chunks matching auth & model, computes Python dot product.
    4. Strict Top-K and Similarity Threshold filtering.
    5. Post-retrieval Evidence Gate (Phase 5.2): lexical & semantic constraint evaluation.
    6. Complete source traceability (chunk, doc, filename, page, section).
    """

    def __init__(
        self,
        provider: Optional[BaseEmbeddingProvider] = None,
        evidence_gate: Optional[BaseEvidenceGate] = None,
        default_top_k: Optional[int] = None,
        default_threshold: Optional[float] = None
    ):
        self.provider = provider or get_embedding_provider()
        self.evidence_gate = evidence_gate or get_evidence_gate()
        self.default_top_k = default_top_k or getattr(settings, "RETRIEVAL_TOP_K", 5)
        self.default_threshold = default_threshold if default_threshold is not None else getattr(settings, "RETRIEVAL_SIMILARITY_THRESHOLD", 0.58)

    def _build_permission_filter(self, user_context: Optional[Dict[str, Any]] = None):
        """
        Constructs SQLAlchemy filter clause based on Document access_scope and User role/identity.
        RBAC Rules:
        - ADMIN: public, internal, admin (all READY docs).
        - STAFF / OWNER: public, internal, OR (owner_id == user_id).
        - CUSTOMER: public, OR (owner_id == user_id).
        - GUEST / Anonymous: public ONLY.
        """
        if not user_context:
            return Document.access_scope == "public"

        user_id = user_context.get("user_id")
        raw_role = user_context.get("role", "GUEST")
        role = str(raw_role).upper() if raw_role else "GUEST"

        # ADMIN role: unrestricted access across scopes
        if role == "ADMIN":
            return Document.access_scope.in_(["public", "internal", "admin"])

        # STAFF or OWNER role: public, internal, plus owned documents
        if role in ["STAFF", "OWNER"]:
            conditions = [Document.access_scope.in_(["public", "internal"])]
            if user_id:
                conditions.append(Document.owner_id == user_id)
            return or_(*conditions)

        # CUSTOMER role: public, plus owned documents
        if role == "CUSTOMER":
            conditions = [Document.access_scope == "public"]
            if user_id:
                conditions.append(Document.owner_id == user_id)
            return or_(*conditions)

        # GUEST / Default
        return Document.access_scope == "public"

    @staticmethod
    def _compute_cosine_similarity(vec_a: List[float], vec_b: List[float]) -> Tuple[float, float]:
        """
        Computes cosine similarity and distance between two vectors.
        Assumes both vectors are L2-normalized unit vectors.
        Returns: (similarity, distance) where similarity in [-1, 1], distance = 1 - similarity.
        """
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        # Clamp to avoid floating point precision edge cases
        dot = max(-1.0, min(1.0, dot))
        similarity = dot
        distance = max(0.0, 1.0 - dot)
        return similarity, distance

    async def retrieve(
        self,
        db: AsyncSession,
        query: str,
        user_context: Optional[Dict[str, Any]] = None,
        top_k: Optional[int] = None,
        similarity_threshold: Optional[float] = None,
        apply_evidence_gate: Optional[bool] = None
    ) -> RetrievalSearchResponse:
        t_start = time.time()
        k = top_k if top_k is not None and top_k > 0 else self.default_top_k
        threshold = similarity_threshold if similarity_threshold is not None else self.default_threshold

        # 1. Handle Empty or Whitespace Query
        cleaned_query = query.strip() if query else ""
        if not cleaned_query:
            return RetrievalSearchResponse(
                query=query,
                total_candidates=0,
                returned_results=0,
                top_k=k,
                similarity_threshold=threshold,
                results=[],
                reason="empty_query",
                latency_ms={"embedding_ms": 0.0, "search_ms": 0.0, "total_ms": 0.0}
            )

        # 2. Query Embedding Generation
        t_embed_start = time.time()
        query_vector = await self.provider.embed_text(cleaned_query)
        embedding_ms = (time.time() - t_embed_start) * 1000

        # Validate query vector
        self.provider.validate_vector(query_vector)
        if len(query_vector) != self.provider.dimension:
            raise ValueError(
                f"Kích thước query embedding ({len(query_vector)}) không khớp dimension mong đợi ({self.provider.dimension})."
            )

        # 3. Detect Database Dialect (PostgreSQL vs SQLite)
        t_search_start = time.time()
        bind = db.bind or getattr(db, "sync_session", db).bind
        is_postgres = bool(bind and "postgres" in bind.dialect.name.lower())

        perm_filter = self._build_permission_filter(user_context)

        candidate_results: List[RetrievalResultItem] = []
        total_candidates = 0

        # 4. Search Execution
        use_native_pgvector = False
        if is_postgres and _HAS_PGVECTOR:
            use_native_pgvector = await _is_pgvector_native(db)

        if use_native_pgvector:
            # Native PostgreSQL pgvector cosine distance: `<=>`
            # Note: cosine_similarity = 1.0 - cosine_distance
            cosine_dist_expr = DocumentChunk.embedding.cosine_distance(query_vector)
            cosine_sim_expr = 1.0 - cosine_dist_expr

            stmt = (
                select(
                    DocumentChunk,
                    Document,
                    cosine_dist_expr.label("distance"),
                    cosine_sim_expr.label("similarity")
                )
                .join(Document, DocumentChunk.document_id == Document.id)
                .where(
                    and_(
                        Document.status == "READY",
                        DocumentChunk.embedding.isnot(None),
                        DocumentChunk.embedding_model == self.provider.model_name,
                        perm_filter,
                        cosine_sim_expr >= threshold
                    )
                )
                .order_by(cosine_dist_expr.asc())
                .limit(k)
            )

            res = await db.execute(stmt)
            rows = res.all()
            total_candidates = len(rows)

            for chunk, doc, dist, sim in rows:
                candidate_results.append(
                    RetrievalResultItem(
                        chunk_id=chunk.id,
                        document_id=doc.id,
                        text=chunk.text,
                        score=round(float(sim), 4),
                        distance=round(float(dist), 4),
                        similarity=round(float(sim), 4),
                        filename=doc.filename,
                        page_number=chunk.page_number,
                        section=chunk.section,
                        source_type=doc.source_type,
                        access_scope=doc.access_scope
                    )
                )

        else:
            # SQLite Development / Testing Engine
            # Loads authorized candidates and computes exact cosine similarity in Python
            stmt = (
                select(DocumentChunk, Document)
                .join(Document, DocumentChunk.document_id == Document.id)
                .where(
                    and_(
                        Document.status == "READY",
                        DocumentChunk.embedding.isnot(None),
                        DocumentChunk.embedding_model == self.provider.model_name,
                        perm_filter
                    )
                )
            )

            res = await db.execute(stmt)
            candidates = res.all()
            total_candidates = len(candidates)

            scored_candidates: List[Tuple[float, float, DocumentChunk, Document]] = []

            for chunk, doc in candidates:
                raw_vec = chunk.embedding
                if isinstance(raw_vec, str):
                    try:
                        raw_vec = json.loads(raw_vec)
                        if isinstance(raw_vec, str):
                            raw_vec = json.loads(raw_vec)
                    except Exception:
                        continue
                if not raw_vec or not isinstance(raw_vec, (list, tuple)) or len(raw_vec) != self.provider.dimension:
                    continue

                sim, dist = self._compute_cosine_similarity(query_vector, raw_vec)
                if sim >= threshold:
                    scored_candidates.append((sim, dist, chunk, doc))

            # Sort descending by similarity (ascending by distance)
            scored_candidates.sort(key=lambda item: item[0], reverse=True)

            # Take Top-K
            top_scored = scored_candidates[:k]

            for sim, dist, chunk, doc in top_scored:
                candidate_results.append(
                    RetrievalResultItem(
                        chunk_id=chunk.id,
                        document_id=doc.id,
                        text=chunk.text,
                        score=round(float(sim), 4),
                        distance=round(float(dist), 4),
                        similarity=round(float(sim), 4),
                        filename=doc.filename,
                        page_number=chunk.page_number,
                        section=chunk.section,
                        source_type=doc.source_type,
                        access_scope=doc.access_scope
                    )
                )

        search_ms = (time.time() - t_search_start) * 1000
        total_ms = (time.time() - t_start) * 1000

        initial_candidate_count = len(candidate_results)

        # 5. Evidence Gate Post-Processing (Phase 5.2)
        valid_items, rejected_items = self.evidence_gate.evaluate_results(cleaned_query, candidate_results)

        # Determine whether to enforce evidence gate filtering
        # Default: True when similarity_threshold > 0.0, False when similarity_threshold <= 0.0 (raw/debug mode)
        should_filter = apply_evidence_gate if apply_evidence_gate is not None else (threshold > 0.0)

        if should_filter:
            final_results = valid_items
            reason = None
            if not final_results:
                if initial_candidate_count > 0:
                    reason = "insufficient_evidence"
                elif total_candidates == 0:
                    reason = "no_authorized_documents"
                else:
                    reason = "no_relevant_documents"
        else:
            final_results = candidate_results
            reason = None
            if not final_results:
                if total_candidates == 0:
                    reason = "no_authorized_documents"
                else:
                    reason = "no_relevant_documents"

        return RetrievalSearchResponse(
            query=cleaned_query,
            total_candidates=total_candidates,
            returned_results=len(final_results),
            top_k=k,
            similarity_threshold=threshold,
            results=final_results,
            reason=reason,
            latency_ms={
                "embedding_ms": round(embedding_ms, 2),
                "search_ms": round(search_ms, 2),
                "total_ms": round(total_ms, 2)
            }
        )


# ==============================================================================
# RETRIEVAL SERVICE FACTORY
# ==============================================================================

_retriever_instance: Optional[VectorRetriever] = None

def get_retriever() -> VectorRetriever:
    global _retriever_instance
    if _retriever_instance is None:
        _retriever_instance = VectorRetriever()
    return _retriever_instance

def get_retrieval_service() -> VectorRetriever:
    return get_retriever()
