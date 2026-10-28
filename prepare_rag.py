"""Ingest and embed an official document using the application's RAG pipeline.

Run from the project root: python prepare_rag.py [path-to-document]
Unchanged documents and embeddings are reused on subsequent runs.
"""

import argparse
import asyncio
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backend"))


async def prepare(path: Path, force: bool = False) -> int:
    from app.ai.ingestion_service import get_ingestion_service
    from app.ai.embedding_ingestion_service import get_embedding_ingestion_service
    from app.core.database import AsyncSessionLocal, engine

    try:
        async with AsyncSessionLocal() as db:
            document = await get_ingestion_service().ingest_file(
                db=db,
                content_bytes=path.read_bytes(),
                filename=path.name,
                title="Đặc tả nghiệp vụ BADMINTON.AI (SRS)",
                source_type="srs",
                access_scope="public",
                reingest=False,
            )
            report = await get_embedding_ingestion_service().embed_document_chunks(
                db=db,
                document_id=document.document_id,
                force_reembed=force,
            )
            print(f"Document: {document.document_id}; chunks: {document.total_chunks}")
            print(f"Embedding: {report.status}; model: {report.embedding_model}")
            print(f"Embedded: {report.embedded_chunks}; skipped: {report.skipped_chunks}; failed: {report.failed_chunks}")
            return 0 if report.status in {"COMPLETED", "ALREADY_UP_TO_DATE"} else 1
    finally:
        await engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("document", nargs="?", type=Path, default=ROOT / "extracted_doc.txt")
    parser.add_argument("--force", action="store_true", help="Regenerate existing embeddings")
    args = parser.parse_args()
    if not args.document.is_file():
        parser.error("Document does not exist")
    return asyncio.run(prepare(args.document.resolve(), args.force))


if __name__ == "__main__":
    raise SystemExit(main())
