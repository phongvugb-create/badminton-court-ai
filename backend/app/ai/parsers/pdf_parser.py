"""
BADMINTON.AI - PDF PARSER
Parses Adobe PDF (.pdf) documents into structured sections with page tracking.
Uses pypdf with robust error handling.
"""

import io
import re
from typing import List
from .base_parser import BaseDocumentParser, ParsedDocument, ParsedSection

class PDFParser(BaseDocumentParser):
    """Parser for Adobe PDF (.pdf) documents."""

    def parse(self, content_bytes: bytes, filename: str) -> ParsedDocument:
        import pypdf

        reader = pypdf.PdfReader(io.BytesIO(content_bytes))
        sections: List[ParsedSection] = []

        heading_regex = re.compile(
            r"^(\d+(\.\d+)*\.?\s+[A-ZÀ-Ỹ0-9\s_]{3,}|Mục\s+\d+|Điều\s+\d+|UC\d{3}[_\s].+)",
            re.IGNORECASE
        )

        for page_idx, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            text = text.strip()
            if not text:
                continue

            lines = text.splitlines()
            current_heading = f"Trang {page_idx}"
            current_lines: List[str] = []

            for line in lines:
                s = line.strip()
                if not s:
                    continue
                if heading_regex.match(s) and len(s) < 120:
                    if current_lines:
                        sec_text = "\n".join(current_lines).strip()
                        if sec_text:
                            sections.append(ParsedSection(
                                text=sec_text,
                                section_heading=current_heading,
                                page_number=page_idx
                            ))
                        current_lines = []
                    current_heading = s
                    current_lines.append(s)
                else:
                    current_lines.append(s)

            if current_lines:
                sec_text = "\n".join(current_lines).strip()
                if sec_text:
                    sections.append(ParsedSection(
                        text=sec_text,
                        section_heading=current_heading,
                        page_number=page_idx
                    ))

        total_chars = sum(len(s.text) for s in sections)
        return ParsedDocument(
            filename=filename,
            mime_type="application/pdf",
            total_characters=total_chars,
            sections=sections,
            metadata={"total_pages": len(reader.pages)}
        )
