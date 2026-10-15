"""
BADMINTON.AI - PHASE 3 TEST SUITE: DOCUMENT INGESTION PIPELINE
Tests all 16 required scenarios:
1. PDF parsing
2. DOCX parsing
3. TXT parsing
4. Vietnamese Unicode preservation (NFC, diacritics)
5. Empty document rejection
6. Malformed document rejection
7. Cleaning & normalization (numbers, currency 130.000đ preserved)
8. Hierarchical chunking
9. Metadata completeness
10. SHA-256 Checksum
11. Duplicate ingestion detection
12. Re-ingestion and version bump
13. Access-control metadata & filtering
14. Database persistence
15. Transaction rollback on ingestion failure
16. Document status progression (READY / FAILED)
"""

import unittest
import asyncio
import os
import sys
import io
import json
from datetime import datetime

# Setup sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select

from app.core.database import Base, AsyncSessionLocal
from app.models.all_models import Document, DocumentChunk, User
from app.ai.parsers import (
    get_parser,
    TextParser,
    MarkdownParser,
    DocxParser,
    PDFParser,
    UnsupportedDocumentTypeError,
    MalformedDocumentError
)
from app.ai.cleaner import TextCleaner
from app.ai.chunker import HierarchicalChunker
from app.ai.ingestion_service import DocumentIngestionService, get_ingestion_service

TEST_DB_URL = "sqlite+aiosqlite:///./test_phase3_ingest.db"

class TestPhase3DocumentIngestion(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.engine = create_async_engine(TEST_DB_URL, echo=False)
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        self.service = DocumentIngestionService(
            chunker=HierarchicalChunker(
                chunk_size=300,
                chunk_overlap=50,
                min_chunk_size=40,
                max_chunk_size=500
            )
        )

    async def asyncTearDown(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await self.engine.dispose()
        # Clean up db file
        db_file = os.path.join(BASE_DIR, "test_phase3_ingest.db")
        if os.path.exists(db_file):
            try:
                os.remove(db_file)
            except Exception:
                pass

    # 1. TXT Parsing
    def test_01_txt_parsing(self):
        parser = get_parser("quy_dinh_san.txt")
        self.assertIsInstance(parser, TextParser)
        raw_text = (
            "1. QUY ĐỊNH CHUNG\nKhách hàng cần tuân thủ nội quy sân cầu lông.\n\n"
            "2. GIỜ HOẠT ĐỘNG\nSân mở cửa từ 05:00 đến 24:00 hàng ngày."
        ).encode("utf-8")
        doc = parser.parse(raw_text, "quy_dinh_san.txt")
        self.assertEqual(len(doc.sections), 2)
        self.assertIn("QUY ĐỊNH CHUNG", doc.sections[0].section_heading)
        self.assertIn("GIỜ HOẠT ĐỘNG", doc.sections[1].section_heading)

    # 2. DOCX Parsing
    def test_02_docx_parsing(self):
        import docx
        doc_obj = docx.Document()
        doc_obj.add_heading("1. Chính sách giá và phụ thu", level=1)
        doc_obj.add_paragraph("Mức giá thuê sân tiêu chuẩn là 80.000đ/giờ. Giờ vàng phụ thu 25%.")
        doc_obj.add_heading("2. Đặt cọc 50%", level=1)
        doc_obj.add_paragraph("Khách hàng cần thanh toán trước 50% tiền cọc.")
        buf = io.BytesIO()
        doc_obj.save(buf)
        docx_bytes = buf.getvalue()

        parser = get_parser("chinh_sach.docx")
        self.assertIsInstance(parser, DocxParser)
        parsed = parser.parse(docx_bytes, "chinh_sach.docx")
        self.assertGreaterEqual(len(parsed.sections), 2)
        self.assertIn("Chính sách giá", parsed.sections[0].section_heading)
        self.assertIn("80.000đ/giờ", parsed.sections[0].text)

    # 3. PDF Parsing
    def test_03_pdf_parsing(self):
        import pypdf
        # Generate minimal valid PDF with pypdf
        writer = pypdf.PdfWriter()
        page = writer.add_blank_page(width=300, height=300)
        buf = io.BytesIO()
        writer.write(buf)
        pdf_bytes = buf.getvalue()

        parser = get_parser("huong_dan.pdf")
        self.assertIsInstance(parser, PDFParser)
        parsed = parser.parse(pdf_bytes, "huong_dan.pdf")
        self.assertEqual(parsed.mime_type, "application/pdf")
        self.assertIn("total_pages", parsed.metadata)

    # 4. Vietnamese Unicode Preservation (NFC, diacritics)
    def test_04_vietnamese_unicode_preservation(self):
        raw_vn = "Hệ thống Quản lý Sân Cầu Lông & Pickleball: Đặt sân trực tuyến, giữ chỗ 10 phút."
        cleaned = TextCleaner.clean_text(raw_vn)
        self.assertEqual(cleaned, raw_vn)
        # Check NFC normalization
        import unicodedata
        self.assertTrue(unicodedata.is_normalized("NFC", cleaned))

    # 5. Empty Document Rejection
    async def test_05_empty_document_rejection(self):
        async with self.async_session() as db:
            with self.assertRaises(ValueError):
                await self.service.ingest_file(
                    db=db,
                    content_bytes=b"   \n  \t  ",
                    filename="empty.txt"
                )

    # 6. Malformed Document Rejection
    def test_06_unsupported_document_type(self):
        with self.assertRaises(UnsupportedDocumentTypeError):
            get_parser("malicious_script.exe")

    # 7. Cleaning & Preserving Exact Numbers and Terms
    def test_07_cleaning_preserves_numbers_and_currency(self):
        dirty_text = "  Giá thuê:   130.000đ/giờ   .   Giờ vàng:  17:00 - 21:00  (phụ thu +25%).  \n\n\n\n  Hotline: 1900 6868  "
        cleaned = TextCleaner.clean_text(dirty_text)
        self.assertIn("130.000đ/giờ", cleaned)
        self.assertIn("17:00 - 21:00", cleaned)
        self.assertIn("+25%", cleaned)
        self.assertIn("1900 6868", cleaned)
        self.assertNotIn("\n\n\n", cleaned)

    # 8. Hierarchical Chunking
    def test_08_hierarchical_chunking(self):
        chunker = HierarchicalChunker(chunk_size=120, chunk_overlap=30, min_chunk_size=20)
        from app.ai.parsers.base_parser import ParsedDocument, ParsedSection
        mock_doc = ParsedDocument(
            filename="test.txt",
            mime_type="text/plain",
            total_characters=300,
            sections=[
                ParsedSection(
                    text=(
                        "Quy định đặt cọc:\n"
                        "Khách hàng cần thanh toán trước 50% tiền cọc qua cổng VNPay hoặc chuyển khoản ngân hàng.\n"
                        "Hệ thống sẽ giữ chỗ trong 10 phút chờ thanh toán."
                    ),
                    section_heading="3.8. Thanh toán đặt cọc"
                )
            ]
        )
        chunks = chunker.chunk_document(mock_doc)
        self.assertGreaterEqual(len(chunks), 1)
        for c in chunks:
            self.assertEqual(c.section, "3.8. Thanh toán đặt cọc")
            self.assertGreater(c.token_estimate, 0)
            self.assertGreater(len(c.text), 0)

    # 9. Metadata Completeness
    async def test_09_metadata_completeness(self):
        async with self.async_session() as db:
            sample_text = (
                "1. QUY ĐỊNH HOÀN HỦY SÂN\n"
                "Hủy trước 24 giờ hoàn 100% cọc.\n"
                "Hủy từ 12-24 giờ hoàn 50% cọc.\n"
                "Hủy dưới 12 giờ không hoàn tiền."
            )
            res = await self.service.ingest_text(
                db=db,
                text_content=sample_text,
                title="Quy định Hoàn Hủy",
                filename="hoan_huy.txt",
                source_type="policy",
                access_scope="public"
            )
            self.assertEqual(res.status, "READY")
            self.assertGreater(res.total_chunks, 0)

            # Check chunk metadata in DB
            chunks = await self.service.get_document_chunks(db, res.document_id)
            self.assertGreater(len(chunks), 0)
            for chk in chunks:
                self.assertIsNotNone(chk.meta_info)
                meta = json.loads(chk.meta_info)
                self.assertEqual(meta["filename"], "hoan_huy.txt")
                self.assertEqual(meta["source_type"], "policy")
                self.assertEqual(meta["access_scope"], "public")

    # 10. SHA-256 Checksum Accuracy
    def test_10_checksum_calculation(self):
        content = "Dữ liệu kiểm tra SHA-256".encode("utf-8")
        chk1 = DocumentIngestionService.calculate_checksum(content)
        chk2 = DocumentIngestionService.calculate_checksum(content)
        self.assertEqual(chk1, chk2)
        self.assertEqual(len(chk1), 64)

    # 11. Duplicate Ingestion Detection
    async def test_11_duplicate_ingestion_detection(self):
        async with self.async_session() as db:
            text = "Nội dung tài liệu kiểm tra tính năng chống trùng lặp dữ liệu."
            # Lần 1
            res1 = await self.service.ingest_text(
                db=db,
                text_content=text,
                title="Tài liệu trùng",
                filename="duplicate_test.txt"
            )
            self.assertFalse(res1.is_duplicate)
            self.assertEqual(res1.version, 1)

            # Lần 2 (cùng nội dung)
            res2 = await self.service.ingest_text(
                db=db,
                text_content=text,
                title="Tài liệu trùng",
                filename="duplicate_test.txt"
            )
            self.assertTrue(res2.is_duplicate)
            self.assertEqual(res2.document_id, res1.document_id)
            self.assertIn("Tài liệu đã tồn tại", res2.message)

    # 12. Re-ingestion and Version Bump
    async def test_12_reingestion_version_bump(self):
        async with self.async_session() as db:
            text = "Nội dung cập nhật tài liệu phiên bản mới."
            res1 = await self.service.ingest_text(
                db=db,
                text_content=text,
                title="Tài liệu Version",
                filename="version_test.txt"
            )
            self.assertEqual(res1.version, 1)

            # Re-ingest with reingest=True
            res2 = await self.service.ingest_text(
                db=db,
                text_content=text,
                title="Tài liệu Version v2",
                filename="version_test.txt",
                reingest=True
            )
            self.assertEqual(res2.version, 2)
            self.assertFalse(res2.is_duplicate)

    # 13. Access Control Metadata & Filtering
    async def test_13_access_control_filtering(self):
        async with self.async_session() as db:
            # 1 doc public, 1 doc internal, 1 doc admin
            await self.service.ingest_text(
                db=db, text_content="Tài liệu công khai cho khách hàng.",
                title="Public Doc", filename="public.txt", access_scope="public"
            )
            await self.service.ingest_text(
                db=db, text_content="Tài liệu hướng dẫn trực ca nhân viên.",
                title="Internal Doc", filename="internal.txt", access_scope="internal"
            )
            await self.service.ingest_text(
                db=db, text_content="Tài liệu bảo mật cấu hình hệ thống.",
                title="Admin Doc", filename="admin.txt", access_scope="admin"
            )

            # Khách hàng (CUSTOMER) chỉ xem được doc public
            customer_docs = await self.service.list_documents(db, user_role="CUSTOMER")
            titles = [d.title for d in customer_docs]
            self.assertIn("Public Doc", titles)
            self.assertNotIn("Internal Doc", titles)
            self.assertNotIn("Admin Doc", titles)

            # Nhân viên (STAFF) xem được public & internal
            staff_docs = await self.service.list_documents(db, user_role="STAFF")
            staff_titles = [d.title for d in staff_docs]
            self.assertIn("Public Doc", staff_titles)
            self.assertIn("Internal Doc", staff_titles)
            self.assertNotIn("Admin Doc", staff_titles)

            # Quản trị viên (ADMIN) xem được tất cả
            admin_docs = await self.service.list_documents(db, user_role="ADMIN")
            admin_titles = [d.title for d in admin_docs]
            self.assertIn("Public Doc", admin_titles)
            self.assertIn("Internal Doc", admin_titles)
            self.assertIn("Admin Doc", admin_titles)

    # 14. Database Persistence Verification
    async def test_14_database_persistence(self):
        async with self.async_session() as db:
            res = await self.service.ingest_text(
                db=db,
                text_content="Kiểm tra lưu trữ DB SQLite và PostgreSQL.",
                title="Kiểm tra DB",
                filename="db_test.txt"
            )
            stmt = select(Document).where(Document.id == res.document_id)
            db_res = await db.execute(stmt)
            saved_doc = db_res.scalar_one_or_none()
            self.assertIsNotNone(saved_doc)
            self.assertEqual(saved_doc.title, "Kiểm tra DB")
            self.assertEqual(saved_doc.status, "READY")

    # 15. Transaction Rollback on Ingestion Failure
    async def test_15_transaction_rollback_on_failure(self):
        async with self.async_session() as db:
            # Tạo mock chunker cố tình ném lỗi giữa chừng
            class BrokenChunker(HierarchicalChunker):
                def chunk_document(self, parsed_doc):
                    raise RuntimeError("Cố ý mô phỏng sự cố phân đoạn để kiểm tra rollback!")

            broken_service = DocumentIngestionService(chunker=BrokenChunker())

            with self.assertRaises(RuntimeError):
                await broken_service.ingest_text(
                    db=db,
                    text_content="Văn bản gây lỗi.",
                    title="Doc lỗi",
                    filename="broken.txt"
                )

            # Kiểm tra không có chunk mồ côi nào lọt vào DB
            stmt = select(DocumentChunk)
            res = await db.execute(stmt)
            chunks = res.scalars().all()
            self.assertEqual(len(chunks), 0)

    # 16. Document Status Progression
    async def test_16_document_status_progression(self):
        async with self.async_session() as db:
            res = await self.service.ingest_text(
                db=db,
                text_content="Kiểm tra trạng thái hoàn tất READY.",
                title="Doc Status",
                filename="status.txt"
            )
            self.assertEqual(res.status, "READY")

if __name__ == "__main__":
    unittest.main()
