"""
BADMINTON.AI - DOCX PARSER
Parses Microsoft Word (.docx) documents into structured sections.
Extracts headings, paragraphs, and tabular data while preserving formatting.
"""

import io
import re
from typing import List
from .base_parser import BaseDocumentParser, ParsedDocument, ParsedSection

class DocxParser(BaseDocumentParser):
    """Parser for Microsoft Word (.docx) files."""

    def parse(self, content_bytes: bytes, filename: str) -> ParsedDocument:
        import docx

        doc = docx.Document(io.BytesIO(content_bytes))
        sections: List[ParsedSection] = []
        current_heading = "Phần mở đầu"
        current_paragraphs: List[str] = []

        heading_regex = re.compile(
            r"^(\d+(\.\d+)*\.?\s+[A-ZÀ-Ỹ0-9\s_]{3,}|Mục\s+\d+|Điều\s+\d+|UC\d{3}[_\s].+)",
            re.IGNORECASE
        )

        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue

            is_heading_style = (
                para.style and (
                    "Heading" in para.style.name or
                    "Title" in para.style.name
                )
            )
            is_heading_text = bool(heading_regex.match(text) and len(text) < 120)

            if is_heading_style or is_heading_text:
                if current_paragraphs:
                    sec_text = "\n".join(current_paragraphs).strip()
                    if sec_text:
                        sections.append(ParsedSection(
                            text=sec_text,
                            section_heading=current_heading,
                            page_number=1
                        ))
                    current_paragraphs = []
                current_heading = text
                current_paragraphs.append(text)
            else:
                current_paragraphs.append(text)

        # Also extract text from docx tables if any
        table_texts: List[str] = []
        for table in doc.tables:
            for row in table.rows:
                row_cells = [c.text.strip() for c in row.cells if c.text.strip()]
                if row_cells:
                    table_texts.append(" | ".join(row_cells))

        if table_texts:
            current_paragraphs.append("\n[Bảng dữ liệu trích xuất]:\n" + "\n".join(table_texts))

        # Flush final section
        if current_paragraphs:
            sec_text = "\n".join(current_paragraphs).strip()
            if sec_text:
                sections.append(ParsedSection(
                    text=sec_text,
                    section_heading=current_heading,
                    page_number=1
                ))

        if not sections and doc.paragraphs:
            raw_text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
            if raw_text:
                sections.append(ParsedSection(
                    text=raw_text,
                    section_heading="Toàn văn tài liệu",
                    page_number=1
                ))

        total_chars = sum(len(s.text) for s in sections)
        return ParsedDocument(
            filename=filename,
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            total_characters=total_chars,
            sections=sections
        )
