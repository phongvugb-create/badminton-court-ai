"""
BADMINTON.AI - BASE DOCUMENT PARSER ABSTRACTION
Defines standard contracts for parsing various document types (TXT, MD, DOCX, PDF).
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field

@dataclass
class ParsedSection:
    text: str
    section_heading: Optional[str] = None
    page_number: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ParsedDocument:
    filename: str
    mime_type: str
    total_characters: int
    sections: List[ParsedSection]
    metadata: Dict[str, Any] = field(default_factory=dict)

class BaseDocumentParser(ABC):
    """Abstract base class for all document parsers."""

    @abstractmethod
    def parse(self, content_bytes: bytes, filename: str) -> ParsedDocument:
        """Parse raw document bytes into a structured ParsedDocument."""
        pass
