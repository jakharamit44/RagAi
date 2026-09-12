import re
import hashlib
from typing import List, Dict, Any, Optional

class SemanticChunker:
    """
    Layout and structure-aware chunking preserving page numbers and section headers.
    Target chunk size: ~500-800 tokens with 100 token overlap.
    Reference: Phase 2 of technical plan.
    """

    def __init__(self, target_chars: int = 1500, overlap_chars: int = 200):
        self.target_chars = target_chars
        self.overlap_chars = overlap_chars

    def chunk_document(
        self,
        pages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        pages: list of dicts with keys: {'page_number': int, 'text': str, 'section': Optional[str]}
        returns list of chunks with metadata and SHA-256 hash.
        """
        chunks = []

        for page in pages:
            page_num = page.get("page_number", 1)
            section = page.get("section")
            text = page.get("text", "")

            # Split paragraphs by double newlines
            raw_paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
            paragraphs = []
            for p in raw_paragraphs:
                if len(p) > self.target_chars:
                    # Sub-split long blocks by single newline
                    sub_lines = [l.strip() for l in p.split("\n") if l.strip()]
                    cur_block = ""
                    for sl in sub_lines:
                        if len(cur_block) + len(sl) <= self.target_chars:
                            cur_block += ("\n" if cur_block else "") + sl
                        else:
                            if cur_block:
                                paragraphs.append(cur_block)
                            while len(sl) > self.target_chars:
                                paragraphs.append(sl[:self.target_chars])
                                sl = sl[self.target_chars - self.overlap_chars:]
                            cur_block = sl
                    if cur_block:
                        paragraphs.append(cur_block)
                else:
                    paragraphs.append(p)

            current_chunk = ""
            for p in paragraphs:
                if len(current_chunk) + len(p) <= self.target_chars:
                    current_chunk += ("\n\n" if current_chunk else "") + p
                else:
                    if current_chunk:
                        chunk_hash = hashlib.sha256(current_chunk.encode("utf-8")).hexdigest()
                        chunks.append({
                            "page_number": page_num,
                            "section": section,
                            "text": current_chunk,
                            "content_hash": chunk_hash,
                        })
                    current_chunk = p

            if current_chunk:
                chunk_hash = hashlib.sha256(current_chunk.encode("utf-8")).hexdigest()
                chunks.append({
                    "page_number": page_num,
                    "section": section,
                    "text": current_chunk,
                    "content_hash": chunk_hash,
                })

        return chunks

chunker = SemanticChunker()
