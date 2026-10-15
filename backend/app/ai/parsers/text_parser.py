"""
BADMINTON.AI - TEXT & MARKDOWN PARSERS
Handles parsing of raw UTF-8 plaintext and Markdown documents.
Preserves headings, sections, and structural boundaries.
"""

import re
from typing import List
from .base_parser import BaseDocumentParser, ParsedDocument, ParsedSection

class TextParser(BaseDocumentParser):
    """Parser for .txt documents."""

    def parse(self, content_bytes: bytes, filename: str) -> ParsedDocument:
        # Handle UTF-8 decoding with fallback for Vietnamese encoding (cp1258, utf-16)
        try:
            text = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = content_bytes.decode("utf-8-sig")
            except UnicodeDecodeError:
                text = content_bytes.decode("latin-1", errors="replace")

        lines = text.splitlines()
        sections: List[ParsedSection] = []
        current_heading = "Phần mở đầu"
        current_lines: List[str] = []

        # Heading regex patterns: "1. ", "3.1. ", "Mục 2", "Điều 1", "UC001"
        heading_pattern = re.compile(
            r"^(\d+(\.\d+)*\.?\s+[A-ZÀ-Ỹ0-9\s_]{3,}|#+\s+.+|Mục\s+\d+|Điều\s+\d+|UC\d{3}[_\s].+)",
            re.IGNORECASE
        )

        for line in lines:
            stripped = line.strip()
            if not stripped:
                if current_lines:
                    current_lines.append("")
                continue

            if heading_pattern.match(stripped) and len(stripped) < 120:
                # If current_lines already has substantive body text (more than just the heading), flush it
                has_body = len(current_lines) > 1 or (current_lines and len("\n".join(current_lines)) > 80)
                if current_lines and has_body:
                    sec_text = "\n".join(current_lines).strip()
                    if sec_text:
                        sections.append(ParsedSection(
                            text=sec_text,
                            section_heading=current_heading,
                            page_number=1
                        ))
                    current_lines = [stripped]
                    current_heading = stripped
                else:
                    # Consecutive headings without body (e.g. Table of Contents) - accumulate together
                    if not current_lines:
                        current_heading = stripped
                    current_lines.append(stripped)
            else:
                current_lines.append(line)

        # Flush last section
        if current_lines:
            sec_text = "\n".join(current_lines).strip()
            if sec_text:
                sections.append(ParsedSection(
                    text=sec_text,
                    section_heading=current_heading,
                    page_number=1
                ))

        if not sections and text.strip():
            sections.append(ParsedSection(
                text=text.strip(),
                section_heading="Toàn văn tài liệu",
                page_number=1
            ))

        total_chars = sum(len(s.text) for s in sections)
        return ParsedDocument(
            filename=filename,
            mime_type="text/plain",
            total_characters=total_chars,
            sections=sections
        )

class MarkdownParser(TextParser):
    """Parser for .md markdown documents with heading-aware parsing."""

    def parse(self, content_bytes: bytes, filename: str) -> ParsedDocument:
        doc = super().parse(content_bytes, filename)
        doc.mime_type = "text/markdown"
        return doc
