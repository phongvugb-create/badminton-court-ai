"""
BADMINTON.AI - TEXT NORMALIZATION & CLEANER
Normalizes text, standardizes whitespace and newlines, and strictly preserves
Vietnamese Unicode (NFC), numbers, currency (e.g. 130.000đ), percentages,
dates, headings, and legal terms without altering any factual content.
"""

import re
import unicodedata

class TextCleaner:
    """Cleans and normalizes text for RAG ingestion while preserving all facts and metrics."""

    @staticmethod
    def normalize_unicode(text: str) -> str:
        """Standardizes all Vietnamese characters to Unicode NFC composition."""
        if not text:
            return ""
        return unicodedata.normalize("NFC", text)

    @classmethod
    def clean_text(cls, text: str) -> str:
        """
        Cleans raw extracted text:
        - Normalizes Unicode to NFC
        - Strips control characters (keeping standard newlines)
        - Normalizes newlines (\r\n -> \n)
        - Strips redundant horizontal whitespace while preserving paragraph structure
        - Preserves all numbers, units, currency, dates, and technical abbreviations intact.
        """
        if not text:
            return ""

        # 1. Normalize Unicode to NFC
        text = cls.normalize_unicode(text)

        # 2. Standardize carriage returns
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # 3. Strip non-printable control characters except \n and \t
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

        # 4. Standardize horizontal whitespace on each line (preserve numbers, dots, currencies)
        cleaned_lines = []
        for line in text.split("\n"):
            # Replace multiple horizontal spaces/tabs with a single space
            cleaned_line = re.sub(r"[ \t]+", " ", line).strip()
            cleaned_lines.append(cleaned_line)

        # 5. Join lines and collapse 3+ consecutive blank lines to at most 2
        text = "\n".join(cleaned_lines)
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip()
