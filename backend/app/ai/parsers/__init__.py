"""
BADMINTON.AI - DOCUMENT PARSER FACTORY
Dispatches appropriate parser based on file extension and mime type.
"""

import os
from typing import Optional
from .base_parser import BaseDocumentParser, ParsedDocument, ParsedSection
from .text_parser import TextParser, MarkdownParser
from .docx_parser import DocxParser
from .pdf_parser import PDFParser

class UnsupportedDocumentTypeError(ValueError):
    """Raised when an uploaded file format is not supported."""
    pass

class MalformedDocumentError(ValueError):
    """Raised when an uploaded file cannot be parsed or is corrupted."""
    pass

def get_parser(filename: str, mime_type: Optional[str] = None) -> BaseDocumentParser:
    """
    Factory function returning the appropriate parser for the document.
    """
    ext = os.path.splitext(filename.lower())[1]

    if ext in [".txt"]:
        return TextParser()
    elif ext in [".md", ".markdown"]:
        return MarkdownParser()
    elif ext in [".docx"]:
        return DocxParser()
    elif ext in [".pdf"]:
        return PDFParser()

    # Fallback to mime-type check if extension is ambiguous
    if mime_type:
        mime = mime_type.lower()
        if "text/plain" in mime:
            return TextParser()
        elif "markdown" in mime:
            return MarkdownParser()
        elif "wordprocessingml" in mime:
            return DocxParser()
        elif "pdf" in mime:
            return PDFParser()

    raise UnsupportedDocumentTypeError(
        f"Định dạng tệp '{ext or mime_type}' không được hỗ trợ. "
        f"Hệ thống chỉ hỗ trợ: .txt, .md, .docx, .pdf"
    )

__all__ = [
    "BaseDocumentParser",
    "ParsedDocument",
    "ParsedSection",
    "TextParser",
    "MarkdownParser",
    "DocxParser",
    "PDFParser",
    "get_parser",
    "UnsupportedDocumentTypeError",
    "MalformedDocumentError"
]
