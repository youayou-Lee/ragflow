#
#  Copyright 2025 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

"""
Indictment Parser (起诉意见书解析器)

This parser is designed for Chinese indictment documents (起诉意见书).
It automatically identifies:
1. Sections based on legal trigger phrases
2. Paragraphs within long sections
3. Evidence items (optional)

Features:
- Section-based chunking with trigger phrases
- Paragraph splitting for long sections (>800 chars)
- Optional evidence item extraction
- Preserves position information for frontend highlighting
- Layer A + Layer B architecture using extract_universal_blocks and IndictmentPlugin
"""

import logging
import re
from copy import deepcopy
from timeit import default_timer as timer
from typing import Optional

from deepdoc.parser import PdfParser
from rag.nlp import rag_tokenizer, add_positions, tokenize, add_bbox_union, add_page_range, add_block_refs
from rag.app.criminal.blocks import extract_universal_blocks
from rag.app.criminal.plugins.indictment import IndictmentPlugin
from strenum import StrEnum


class IndictmentChunkType(StrEnum):
    """Chunk types for indictment documents."""

    SECTION = "section"  # Main section chunk
    PARAGRAPH = "paragraph"  # Sub-segment of long section
    EVIDENCE_ITEM = "evidence_item"  # Individual evidence item


# Maximum length for section before splitting into paragraphs
MAX_SECTION_LENGTH = 800

# Section trigger phrases (in order of typical appearance)
SECTION_TRIGGERS = [
    r"经依法侦查查明",
    r"经依法审查查明",
    r"现查明",
    r"认定上述犯罪事实的证据如下",
    r"上述犯罪事实(?:，|，\s*)有(?:以下|下列)证据(?:予以)?证实",
    r"综上所述",
    r"本院认为",
    r"此致",
]

# Compiled pattern for section triggers
SECTION_TRIGGER_PATTERN = re.compile("|".join(f"({t})" for t in SECTION_TRIGGERS))

# Evidence item patterns
EVIDENCE_ITEM_PATTERN = re.compile(
    r"^[（(][一二三四五六七八九十]+[)）]\s*|"
    r"^\d+[\.、]\s*|"
    r"^[（(]\d+[)）]\s*"
)


class Pdf(PdfParser):
    """PDF parser for indictment documents."""

    def __call__(self, filename, binary=None, from_page=0, to_page=100000, zoomin=3, callback=None):
        """
        Parse PDF and extract blocks.

        Returns:
            list: List of blocks with text and position info (same format as naive parser)
        """
        start = timer()
        callback(msg="OCR started")
        self.__images__(filename if not binary else binary, zoomin, from_page, to_page, callback)
        callback(msg="OCR finished ({:.2f}s)".format(timer() - start))
        logging.debug("OCR({}~{}): {:.2f}s".format(from_page, to_page, timer() - start))

        start = timer()
        self._layouts_rec(zoomin, drop=False)
        callback(0.63, "Layout analysis ({:.2f}s)".format(timer() - start))

        start = timer()
        self._table_transformer_job(zoomin)
        callback(0.65, "Table analysis ({:.2f}s)".format(timer() - start))

        start = timer()
        self._text_merge()
        callback(0.67, "Text merged ({:.2f}s)".format(timer() - start))

        logging.debug("layouts: {}".format(timer() - start))

        # Return blocks in the same format as naive parser
        blocks = []
        for box in self.boxes:
            line_tag = self._line_tag(box, zoomin)
            text_with_tag = f"{line_tag}{box['text']}"
            blocks.append(text_with_tag)

        return blocks


def find_section_boundaries(blocks: list, pdf_parser: Pdf) -> list[tuple[int, int, str]]:
    """
    Find section boundaries based on trigger phrases.

    Args:
        blocks: List of text blocks with position tags
        pdf_parser: PDF parser instance

    Returns:
        list: List of (start_index, end_index, trigger_phrase) tuples
    """
    sections = []
    current_start = 0
    current_trigger = "header"  # First section is header

    for i, block in enumerate(blocks):
        pure_text = pdf_parser.remove_tag(block).strip()

        # Check for section trigger
        match = SECTION_TRIGGER_PATTERN.search(pure_text)
        if match:
            # Save previous section
            if i > current_start:
                sections.append((current_start, i, current_trigger))

            # Start new section
            current_start = i
            current_trigger = match.group(0)

    # Save last section
    if current_start < len(blocks):
        sections.append((current_start, len(blocks), current_trigger))

    return sections


def extract_evidence_items(blocks: list, doc: dict, pdf_parser: Pdf, eng: bool = False) -> list:
    """
    Extract evidence items from blocks.

    Evidence items are identified by patterns like:
    - （一）xxx
    - 1. xxx
    - (1) xxx

    Args:
        blocks: List of text blocks with position tags
        doc: Base document dict
        pdf_parser: PDF parser instance
        eng: Whether the text is English

    Returns:
        list: List of evidence item chunks
    """
    res = []
    current_item_parts = []
    item_index = 0

    for block in blocks:
        pure_text = pdf_parser.remove_tag(block).strip()

        if EVIDENCE_ITEM_PATTERN.match(pure_text):
            # Save previous item if exists
            if current_item_parts:
                chunk = _build_evidence_chunk(doc, pdf_parser, current_item_parts, item_index, eng)
                if chunk:
                    res.append(chunk)
                    item_index += 1

            # Start new item
            current_item_parts = [block]
        elif current_item_parts:
            # Continue current item
            current_item_parts.append(block)

    # Save last item
    if current_item_parts:
        chunk = _build_evidence_chunk(doc, pdf_parser, current_item_parts, item_index, eng)
        if chunk:
            res.append(chunk)

    return res


def _build_evidence_chunk(doc: dict, pdf_parser: Pdf, parts: list, item_index: int, eng: bool) -> dict:
    """Build an evidence item chunk."""
    d = deepcopy(doc)
    d["chunk_type"] = IndictmentChunkType.EVIDENCE_ITEM.value
    d["evidence_index"] = item_index

    combined_text = "\n".join(parts)
    pure_text = pdf_parser.remove_tag(combined_text)

    d["content_with_weight"] = pure_text
    d["image"], poss = pdf_parser.crop(combined_text, need_position=True)
    add_positions(d, poss)
    tokenize(d, pure_text, eng)

    # Add block_refs for criminal case RAG extension
    add_block_refs(d)

    return d


def build_section_chunks(
    blocks: list,
    doc: dict,
    pdf_parser: Pdf,
    sections: list[tuple[int, int, str]],
    eng: bool = False,
    extract_evidence: bool = False
) -> list:
    """
    Build chunks from section boundaries.

    Args:
        blocks: List of text blocks with position tags
        doc: Base document dict
        pdf_parser: PDF parser instance
        sections: List of (start, end, trigger) tuples
        eng: Whether the text is English
        extract_evidence: Whether to extract evidence items

    Returns:
        list: List of chunk dictionaries
    """
    res = []

    for start_idx, end_idx, trigger in sections:
        section_blocks = blocks[start_idx:end_idx]

        # Combine text for length check
        combined_text = "\n".join(section_blocks)
        pure_text = pdf_parser.remove_tag(combined_text)

        # Check if we should extract evidence items from this section
        if extract_evidence and "证据" in trigger:
            evidence_chunks = extract_evidence_items(section_blocks, doc, pdf_parser, eng)
            if evidence_chunks:
                res.extend(evidence_chunks)
                continue

        # Check if section needs to be split into paragraphs
        if len(pure_text) > MAX_SECTION_LENGTH:
            # Split into paragraphs
            para_chunks = _split_into_paragraphs(
                section_blocks, doc, pdf_parser, trigger, eng
            )
            res.extend(para_chunks)
        else:
            # Single section chunk
            chunk = _build_section_chunk(doc, pdf_parser, section_blocks, trigger, eng)
            res.append(chunk)

    return res


def _build_section_chunk(
    doc: dict,
    pdf_parser: Pdf,
    blocks: list,
    trigger: str,
    eng: bool,
    chunk_type: str = None
) -> dict:
    """Build a section or paragraph chunk."""
    d = deepcopy(doc)
    d["chunk_type"] = chunk_type or IndictmentChunkType.SECTION.value
    d["section_trigger"] = trigger

    combined_text = "\n".join(blocks)
    pure_text = pdf_parser.remove_tag(combined_text)

    d["content_with_weight"] = pure_text
    d["image"], poss = pdf_parser.crop(combined_text, need_position=True)
    add_positions(d, poss)
    tokenize(d, pure_text, eng)

    # Add block_refs for criminal case RAG extension
    add_block_refs(d)

    return d


def _split_into_paragraphs(
    blocks: list,
    doc: dict,
    pdf_parser: Pdf,
    trigger: str,
    eng: bool
) -> list:
    """
    Split a long section into paragraph chunks.

    Splits by natural paragraph boundaries while trying to keep
    each chunk under MAX_SECTION_LENGTH.
    """
    res = []
    current_parts = []
    current_length = 0

    for block in blocks:
        pure_text = pdf_parser.remove_tag(block).strip()
        block_length = len(pure_text)

        # Check if adding this block would exceed the limit
        if current_length + block_length > MAX_SECTION_LENGTH and current_parts:
            # Build chunk for current parts
            chunk = _build_section_chunk(
                doc, pdf_parser, current_parts, trigger, eng,
                chunk_type=IndictmentChunkType.PARAGRAPH.value
            )
            res.append(chunk)

            # Start new paragraph
            current_parts = [block]
            current_length = block_length
        else:
            current_parts.append(block)
            current_length += block_length

    # Add remaining parts
    if current_parts:
        chunk = _build_section_chunk(
            doc, pdf_parser, current_parts, trigger, eng,
            chunk_type=IndictmentChunkType.PARAGRAPH.value if len(res) > 0 else IndictmentChunkType.SECTION.value
        )
        res.append(chunk)

    return res


def chunk(
    filename,
    binary=None,
    from_page=0,
    to_page=100000,
    lang="Chinese",
    callback=None,
    extract_evidence=False,
    **kwargs
):
    """
    Main chunking function for indictment documents using Layer A + Layer B architecture.

    Layer A: extract_universal_blocks - Universal block extraction
    Layer B: IndictmentPlugin - Specialized indictment processing

    Supports PDF files. The parser will:
    1. OCR the document using PaddleOCR (with fallback to local OCR)
    2. Extract universal blocks (Layer A)
    3. Process with indictment plugin (Layer B)
    4. Add required fields for RAG

    Args:
        filename: Path to the file
        binary: Binary content (optional)
        from_page: Start page (for PDF)
        to_page: End page (for PDF)
        lang: Language ("Chinese" or "English")
        callback: Progress callback function
        extract_evidence: Whether to extract evidence items (default: False)
        **kwargs: Additional arguments including:
            - parser_config: Parser configuration dict
            - tenant_id: Tenant ID for LLMBundle
            - kb_id: Knowledge base ID for OCR caching
            - doc_id: Document ID for OCR caching (extracted from parser_config)
            - chat_mdl: Chat model for LLM processing

    Returns:
        list: List of chunk dictionaries
    """
    eng = lang.lower() == "english"

    doc = {"docnm_kwd": filename, "title_tks": rag_tokenizer.tokenize(re.sub(r"\.[a-zA-Z]+$", "", filename))}

    if not re.search(r"\.pdf$", filename, re.IGNORECASE):
        raise NotImplementedError("Indictment parser currently only supports PDF format files.")

    callback(0.1, "Start to parse indictment document.")

    parser_config = kwargs.get("parser_config", {})
    tenant_id = kwargs.get("tenant_id")
    kb_id = kwargs.get("kb_id")
    doc_id = parser_config.get("doc_id", "")

    # Step 1: Try PaddleOCR first (same as interrogation)
    from rag.app.naive import by_paddleocr
    sections, tables, pdf_parser = by_paddleocr(
        filename=filename,
        binary=binary,
        from_page=from_page,
        to_page=to_page,
        lang=lang,
        callback=callback,
        parser_config=parser_config,
        tenant_id=tenant_id,
        kb_id=kb_id,
        doc_id=doc_id,
    )

    # Fallback to local OCR if PaddleOCR fails
    if sections is None:
        logging.info("PaddleOCR not available, falling back to local OCR")
        pdf_parser = Pdf()
        blocks_raw = pdf_parser(filename if not binary else binary, from_page=from_page, to_page=to_page, callback=callback)
        # Convert raw blocks to sections format: (content, tag)
        sections = [(b, "") for b in blocks_raw]

    callback(0.4, "OCR completed.")

    # Step 2: Layer A - Extract universal blocks
    blocks = extract_universal_blocks(sections, "indictment")
    callback(0.6, f"Extracted {len(blocks)} blocks.")

    # Step 3: Layer B - Plugin processing
    plugin = IndictmentPlugin()
    chunks = plugin.process(blocks, doc, chat_mdl=kwargs.get("chat_mdl"))
    callback(0.8, f"Generated {len(chunks)} chunks.")

    # Step 4: Add required fields for RAG
    for c in chunks:
        content = c.get("content_with_weight", "")
        tokenize(c, content, eng)
        add_bbox_union(c)
        add_page_range(c)
        add_block_refs(c)

    callback(1.0, f"Completed. Total chunks: {len(chunks)}")
    return chunks


if __name__ == "__main__":
    import sys

    def dummy(prog=None, msg=""):
        if msg:
            print(f"[{prog:.0%}] {msg}" if prog else msg)

    if len(sys.argv) < 2:
        print("Usage: python indictment.py <pdf_file>")
        sys.exit(1)

    result = chunk(sys.argv[1], callback=dummy)
    print(f"\nTotal chunks: {len(result)}")

    for i, chunk_item in enumerate(result):
        chunk_type = chunk_item.get("chunk_type", "unknown")
        content_preview = chunk_item.get("content_with_weight", "")[:100]
        print(f"\n[{i}] Type: {chunk_type}")
        print(f"    Trigger: {chunk_item.get('section_trigger', 'N/A')}")
        print(f"    Content: {content_preview}...")
