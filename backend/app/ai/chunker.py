"""
BADMINTON.AI - HIERARCHICAL CHUNKER
Splits documents using hierarchical boundaries (Heading -> Section -> Paragraph -> Sentence -> Size limits).
Preserves structural context and section metadata for downstream RAG retrieval.
"""

import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from .cleaner import TextCleaner
from .parsers.base_parser import ParsedDocument, ParsedSection

@dataclass
class ChunkItem:
    chunk_index: int
    text: str
    section: Optional[str] = None
    page_number: Optional[int] = None
    token_estimate: int = 0
    char_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

class HierarchicalChunker:
    """
    Hierarchical chunker respecting document headings, paragraphs, and sentence boundaries.
    Fully configurable via parameters.
    """

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 80,
        min_chunk_size: int = 50,
        max_chunk_size: int = 800
    ):
        if min_chunk_size > chunk_size:
            min_chunk_size = chunk_size // 2
        if chunk_size > max_chunk_size:
            max_chunk_size = chunk_size * 2
        if chunk_overlap >= chunk_size:
            chunk_overlap = chunk_size // 4

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size

    def _estimate_tokens(self, text: str) -> int:
        """Estimates token count for Vietnamese/English mixed text."""
        words = text.split()
        return max(1, int(len(words) * 1.3))

    def _split_into_sentences(self, text: str) -> List[str]:
        """Splits paragraph into sentences respecting numbers and abbreviations."""
        # Don't split on dots within numbers (e.g. 130.000, 1.5)
        raw_sentences = re.split(r"(?<=[.!?])\s+(?=[A-ZÀ-Ỹ0-9])", text)
        sentences: List[str] = []
        for s in raw_sentences:
            s_clean = s.strip()
            if s_clean:
                sentences.append(s_clean)
        return sentences if sentences else [text]

    def _split_large_text(self, text: str) -> List[str]:
        """Splits an oversized paragraph into chunks with overlap at sentence boundaries."""
        sentences = self._split_into_sentences(text)
        chunks: List[str] = []
        current_sentences: List[str] = []
        current_len = 0

        for sentence in sentences:
            s_len = len(sentence)
            if current_len + s_len > self.chunk_size and current_sentences:
                chunk_str = " ".join(current_sentences).strip()
                if chunk_str:
                    chunks.append(chunk_str)

                # Overlap: keep the last sentence(s) if within overlap budget
                overlap_sentences: List[str] = []
                overlap_len = 0
                for s in reversed(current_sentences):
                    if overlap_len + len(s) <= self.chunk_overlap:
                        overlap_sentences.insert(0, s)
                        overlap_len += len(s)
                    else:
                        break
                current_sentences = overlap_sentences + [sentence]
                current_len = sum(len(s) for s in current_sentences) + len(current_sentences)
            else:
                current_sentences.append(sentence)
                current_len += s_len + 1

        if current_sentences:
            chunk_str = " ".join(current_sentences).strip()
            if chunk_str:
                chunks.append(chunk_str)

        return chunks

    def chunk_document(self, parsed_doc: ParsedDocument) -> List[ChunkItem]:
        """
        Chunks an entire parsed document across all sections.
        """
        result_chunks: List[ChunkItem] = []
        chunk_idx = 0

        for sec in parsed_doc.sections:
            cleaned_sec_text = TextCleaner.clean_text(sec.text)
            if not cleaned_sec_text:
                continue

            sec_heading = sec.section_heading or "Tổng quan"
            page_no = sec.page_number

            # If section fits within chunk_size, keep it whole
            if len(cleaned_sec_text) <= self.chunk_size:
                c_item = ChunkItem(
                    chunk_index=chunk_idx,
                    text=cleaned_sec_text,
                    section=sec_heading,
                    page_number=page_no,
                    token_estimate=self._estimate_tokens(cleaned_sec_text),
                    char_count=len(cleaned_sec_text),
                    metadata={
                        "filename": parsed_doc.filename,
                        "mime_type": parsed_doc.mime_type,
                        "section": sec_heading,
                        "page_number": page_no
                    }
                )
                result_chunks.append(c_item)
                chunk_idx += 1
                continue

            # Otherwise, split section by paragraphs
            paragraphs = [p.strip() for p in cleaned_sec_text.split("\n\n") if p.strip()]
            sec_chunks: List[str] = []
            accumulated_paras: List[str] = []
            acc_len = 0

            for para in paragraphs:
                if len(para) > self.max_chunk_size:
                    # Flush accumulated paragraphs first
                    if accumulated_paras:
                        sec_chunks.append("\n\n".join(accumulated_paras))
                        accumulated_paras = []
                        acc_len = 0
                    # Split oversized paragraph
                    sub_chunks = self._split_large_text(para)
                    sec_chunks.extend(sub_chunks)
                elif acc_len + len(para) > self.chunk_size and accumulated_paras:
                    sec_chunks.append("\n\n".join(accumulated_paras))
                    # Overlap: keep last paragraph if small
                    if len(accumulated_paras[-1]) <= self.chunk_overlap:
                        accumulated_paras = [accumulated_paras[-1], para]
                        acc_len = sum(len(p) for p in accumulated_paras) + 2
                    else:
                        accumulated_paras = [para]
                        acc_len = len(para)
                else:
                    accumulated_paras.append(para)
                    acc_len += len(para) + 2

            if accumulated_paras:
                sec_chunks.append("\n\n".join(accumulated_paras))

            # Merge any tiny trailing chunk into the previous chunk if under max_chunk_size
            merged_chunks: List[str] = []
            for text_chunk in sec_chunks:
                t = text_chunk.strip()
                if not t:
                    continue
                if (
                    merged_chunks and
                    len(t) < self.min_chunk_size and
                    len(merged_chunks[-1]) + len(t) + 2 <= self.max_chunk_size
                ):
                    merged_chunks[-1] = merged_chunks[-1] + "\n\n" + t
                else:
                    merged_chunks.append(t)

            for text_chunk in merged_chunks:
                c_item = ChunkItem(
                    chunk_index=chunk_idx,
                    text=text_chunk,
                    section=sec_heading,
                    page_number=page_no,
                    token_estimate=self._estimate_tokens(text_chunk),
                    char_count=len(text_chunk),
                    metadata={
                        "filename": parsed_doc.filename,
                        "mime_type": parsed_doc.mime_type,
                        "section": sec_heading,
                        "page_number": page_no
                    }
                )
                result_chunks.append(c_item)
                chunk_idx += 1

        # Final smoothing: merge any chunks that are smaller than min_chunk_size
        final_chunks: List[ChunkItem] = []
        for chk in result_chunks:
            if not final_chunks:
                final_chunks.append(chk)
            elif (
                len(chk.text) < self.min_chunk_size and
                len(final_chunks[-1].text) + len(chk.text) + 2 <= self.max_chunk_size
            ):
                # Merge undersized chunk into previous chunk
                prev = final_chunks[-1]
                prev.text = prev.text + "\n\n" + chk.text
                prev.char_count = len(prev.text)
                prev.token_estimate = self._estimate_tokens(prev.text)
            elif (
                len(final_chunks[-1].text) < self.min_chunk_size and
                len(final_chunks[-1].text) + len(chk.text) + 2 <= self.max_chunk_size
            ):
                # Merge previous tiny chunk into current chunk
                chk.text = final_chunks[-1].text + "\n\n" + chk.text
                chk.char_count = len(chk.text)
                chk.token_estimate = self._estimate_tokens(chk.text)
                final_chunks[-1] = chk
            else:
                final_chunks.append(chk)

        # Re-index chunks monotonically 0, 1, 2...
        for idx, item in enumerate(final_chunks):
            item.chunk_index = idx

        return final_chunks
