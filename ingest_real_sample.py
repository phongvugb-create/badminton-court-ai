"""
Ingest real project documents and inspect chunk quality.
"""

import os
import sys
import asyncio
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.core.database import AsyncSessionLocal
from app.ai.ingestion_service import get_ingestion_service

async def main():
    service = get_ingestion_service()
    doc_path = os.path.join(BASE_DIR, "extracted_doc.txt")
    if not os.path.exists(doc_path):
        print(f"File not found: {doc_path}")
        return

    with open(doc_path, "rb") as f:
        content_bytes = f.read()

    async with AsyncSessionLocal() as db:
        print(f"=== Đang nạp tài liệu thực tế: {doc_path} ({len(content_bytes)} bytes) ===")
        res = await service.ingest_file(
            db=db,
            content_bytes=content_bytes,
            filename="extracted_doc.txt",
            title="Đặc tả Nghiệp vụ Hệ thống BADMINTON.AI (SRS v1.0)",
            source_type="srs",
            access_scope="public",
            reingest=True
        )

        print(f"Kết quả Ingest:")
        print(f"- Document ID: {res.document_id}")
        print(f"- Trạng thái: {res.status}")
        print(f"- Checksum: {res.checksum}")
        print(f"- Tổng số Chunks: {res.total_chunks}")
        print(f"- Phiên bản: {res.version}")

        chunks = await service.get_document_chunks(db, res.document_id)
        print(f"\n=== MẪU 6 CHUNKS ĐẦU TIÊN TỪ TÀI LIỆU THỰC TẾ ===")
        for i, chk in enumerate(chunks[:6], start=1):
            print(f"\n------------------------------------------------------------")
            print(f"CHUNK #{i}")
            print(f"document_id : {chk.document_id}")
            print(f"chunk_id    : {chk.id}")
            print(f"chunk_index : {chk.chunk_index}")
            print(f"page        : {chk.page_number}")
            print(f"section     : {chk.section}")
            print(f"token_est   : {chk.token_estimate}")
            print(f"meta_info   : {chk.meta_info}")
            print(f"text length : {len(chk.text)} ký tự")
            print(f"text preview:\n{chk.text}")

if __name__ == "__main__":
    asyncio.run(main())
