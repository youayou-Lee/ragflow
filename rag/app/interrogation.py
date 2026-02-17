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
Interrogation Record Parser (讯问笔录解析器)

This parser is designed for Chinese interrogation/transcript documents (讯问笔录/询问笔录).
It automatically identifies:
1. Header section (基础信息) - containing time, location, interrogators, suspect info
2. QA Pairs (问答对) - questions and answers in the transcript

Features:
- Protects QA boundaries during chunking
- Supports long QA sub-segment splitting
- Extracts metadata via LLM (optional)
- Preserves position information for frontend highlighting
- Supports PaddleOCR for cloud-based OCR with caching
"""

import logging
import os
import re
from copy import deepcopy
from timeit import default_timer as timer
from typing import Optional

from deepdoc.parser import PdfParser
from rag.nlp import rag_tokenizer, add_positions, tokenize, add_bbox_union, add_page_range, add_block_refs
from strenum import StrEnum


class InterrogationChunkType(StrEnum):
    """Chunk types for interrogation records."""

    HEADER = "header"  # Header block with basic info
    QA_PAIR = "qa_pair"  # Question-answer pair block
    QA_SUB = "qa_sub"  # Sub-segment of long QA pair


# Maximum length for QA answer before splitting
MAX_QA_LENGTH = 2000

# Patterns for identifying QA structure
# Using search() instead of match() for more flexible matching
# Supports: 问：, 问:, 问；, 问; (with optional spaces)
QUESTION_PATTERN = re.compile(r"问\s*[：:；;]\s*")
ANSWER_PATTERN = re.compile(r"答\s*[：:；;]\s*")

# Pattern for removing position tags from text
TAG_PATTERN = re.compile(r"@@[\t0-9.-]+?##")

# Pattern for extracting position tags from text
POSITION_TAG_PATTERN = re.compile(r"@@([0-9-]+)\t([0-9.]+)\t([0-9.]+)\t([0-9.]+)\t([0-9.]+)##")


def remove_position_tag(txt: str) -> str:
    """Remove position tag from text."""
    return TAG_PATTERN.sub("", txt)


def _extract_positions_from_text(text: str) -> list:
    """
    Extract position information directly from embedded text tags.

    Position tag format: @@page\tleft\tright\ttop\tbottom##

    Args:
        text: Text containing position tags

    Returns:
        List of position tuples: (page_num, left, right, top, bottom)
        where page_num is 0-indexed (first page for multi-page tags)
    """
    poss = []
    for match in POSITION_TAG_PATTERN.finditer(text):
        pn, left, right, top, bottom = match.groups()
        # Handle page range like "1-2" - use first page
        first_page = int(pn.split("-")[0]) - 1  # Convert to 0-indexed
        poss.append((first_page, float(left), float(right), float(top), float(bottom)))
    return poss


def _clean_latex_format(text: str) -> str:
    r"""
    Clean LaTeX formatting from PaddleOCR output.

    Handles formats like:
    - $ \underline{\text{xxx}} $ -> xxx
    - $ \textbf{xxx} $ -> xxx
    - $ \text{xxx} $ -> xxx
    - $ xxx $ -> xxx
    - \( \underline{\text{xxx}} \) -> xxx (LaTeX math mode alternative)

    Note: PaddleOCR returns LaTeX with literal backslashes.
    In Python regex, r'\\' matches a single backslash character.

    Args:
        text: Text potentially containing LaTeX formatting

    Returns:
        Cleaned text without LaTeX formatting
    """
    # $ \underline{\text{xxx}} $ -> xxx
    text = re.sub(r'\$\s*\\underline\{\\text\{([^}]+)\}\}\s*\$', r'\1', text)
    # $ \textbf{xxx} $ -> xxx
    text = re.sub(r'\$\s*\\textbf\{([^}]+)\}\s*\$', r'\1', text)
    # $ \text{xxx} $ -> xxx
    text = re.sub(r'\$\s*\\text\{([^}]+)\}\s*\$', r'\1', text)
    # $ xxx $ -> xxx (remaining dollar-wrapped content)
    text = re.sub(r'\$\s*([^$]+?)\s*\$', r'\1', text)

    # \( \underline{\text{xxx}} \) -> xxx (LaTeX math mode alternative syntax)
    text = re.sub(r'\\\(\s*\\underline\{\\text\{([^}]+)\}\}\s*\\\)', r'\1', text)
    # \( \textbf{xxx} \) -> xxx
    text = re.sub(r'\\\(\s*\\textbf\{([^}]+)\}\s*\\\)', r'\1', text)
    # \( \text{xxx} \) -> xxx
    text = re.sub(r'\\\(\s*\\text\{([^}]+)\}\s*\\\)', r'\1', text)
    # \( xxx \) -> xxx (remaining backslash-paren wrapped content)
    text = re.sub(r'\\\(\s*([^\\]+?)\s*\\\)', r'\1', text)

    return text.strip()


class Pdf(PdfParser):
    """PDF parser for interrogation records using local OCR (RAGFlowPdfParser)."""

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

        # Return blocks in the same format as naive parser: (text_with_tag, ...)
        # Format: "@@page\tx0\tx1\ttop\tbottom##text_content"
        blocks = []
        for box in self.boxes:
            line_tag = self._line_tag(box, zoomin)
            # Combine tag and text like other parsers do
            text_with_tag = f"{line_tag}{box['text']}"
            blocks.append(text_with_tag)

        return blocks


def _sections_to_blocks(sections: list) -> list:
    """
    Convert sections from naive.py's by_paddleocr format to blocks format.

    Sections from by_paddleocr are tuples: (content, tag) where tag is like "@@page\\tx0\\tx1\\ttop\\tbottom##"
    Blocks are strings: "tag + content" for position extraction compatibility.

    Args:
        sections: List of section tuples from by_paddleocr

    Returns:
        List of block strings with embedded position tags
    """
    blocks = []
    for section in sections:
        if isinstance(section, (list, tuple)):
            if len(section) >= 2:
                # Format: (content, tag)
                content = section[0] if section[0] else ""
                tag = section[1] if len(section) > 1 and section[1] else ""
                if tag:
                    # Combine tag + content for position extraction
                    blocks.append(f"{tag}{content}")
                else:
                    blocks.append(content)
            elif len(section) == 1:
                blocks.append(section[0] if section[0] else "")
        elif isinstance(section, str):
            blocks.append(section)
    return blocks


def extract_header_chunks(blocks: list, doc: dict, pdf_parser, eng: bool = False) -> tuple[list, list]:
    """
    Extract header section from the beginning of blocks.

    Header is defined as all content before the first "问：" pattern.

    Args:
        blocks: List of text blocks with position tags
        doc: Base document dict
        pdf_parser: PDF parser instance for extracting positions (RAGFlowPdfParser or PaddleOCRParser)
        eng: Whether the text is English

    Returns:
        tuple: (header_chunks, remaining_blocks)
    """
    header_parts = []

    for i, block in enumerate(blocks):
        # Remove tag to get pure text for pattern matching
        # Use our helper function for compatibility
        pure_text = remove_position_tag(block).strip()

        if QUESTION_PATTERN.search(pure_text):
            # Found first question, return header and remaining blocks
            if header_parts:
                # Build header chunk
                header_text = "\n".join(header_parts)
                d = deepcopy(doc)
                d["chunk_type"] = InterrogationChunkType.HEADER.value

                # Extract position directly from text tags
                poss = _extract_positions_from_text(header_text)
                if poss:
                    add_positions(d, poss)
                else:
                    logging.warning("No position info extracted for header chunk")

                # Clean LaTeX formatting from text
                clean_text = _clean_latex_format(remove_position_tag(header_text))
                tokenize(d, clean_text, eng)

                # Add extension fields for criminal case RAG
                add_bbox_union(d)
                add_page_range(d)
                add_block_refs(d)
                return [d], blocks[i:]

            return [], blocks[i:]

        header_parts.append(block)

    # No question found, all content is header
    if header_parts:
        header_text = "\n".join(header_parts)
        d = deepcopy(doc)
        d["chunk_type"] = InterrogationChunkType.HEADER.value

        # Extract position directly from text tags
        poss = _extract_positions_from_text(header_text)
        if poss:
            add_positions(d, poss)
        else:
            logging.warning("No position info extracted for header chunk")

        # Clean LaTeX formatting from text
        clean_text = _clean_latex_format(remove_position_tag(header_text))
        tokenize(d, clean_text, eng)

        # Add extension fields for criminal case RAG
        add_bbox_union(d)
        add_page_range(d)
        add_block_refs(d)
        return [d], []

    return [], []


def split_qa_chunks(blocks: list, doc: dict, pdf_parser, eng: bool = False) -> list:
    """
    Split blocks into QA pair chunks.

    Rules:
    1. Each "问：" starts a new QA pair
    2. Collect all content until next "问：" as the answer
    3. Use standard crop/remove_tag methods for position handling

    Args:
        blocks: List of text blocks with position tags (should start with first question)
        doc: Base document dict
        pdf_parser: PDF parser instance for extracting positions (RAGFlowPdfParser or PaddleOCRParser)
        eng: Whether the text is English

    Returns:
        list: List of chunk dictionaries
    """
    res = []
    current_q_parts = []
    current_a_parts = []
    qa_index = 0

    for block in blocks:
        pure_text = remove_position_tag(block).strip()

        if QUESTION_PATTERN.search(pure_text):
            # Save previous QA pair if exists
            if current_q_parts or current_a_parts:
                chunk = _build_qa_chunk(doc, pdf_parser, current_q_parts, current_a_parts, qa_index, eng)
                if chunk:
                    res.append(chunk)
                    qa_index += 1

            # Start new QA pair
            current_q_parts = [block]
            current_a_parts = []

        elif current_q_parts:
            # This is part of the answer
            current_a_parts.append(block)

    # Save last QA pair
    if current_q_parts or current_a_parts:
        chunk = _build_qa_chunk(doc, pdf_parser, current_q_parts, current_a_parts, qa_index, eng)
        if chunk:
            res.append(chunk)

    return res


def _build_qa_chunk(doc: dict, pdf_parser, q_parts: list, a_parts: list, qa_index: int, eng: bool) -> dict:
    """
    Build a QA pair chunk using standard position handling.

    Args:
        doc: Base document dict
        pdf_parser: PDF parser instance (RAGFlowPdfParser or PaddleOCRParser)
        q_parts: Question text blocks with tags
        a_parts: Answer text blocks with tags
        qa_index: Index of this QA pair
        eng: Whether the text is English

    Returns:
        dict: Chunk dictionary
    """
    d = deepcopy(doc)
    d["chunk_type"] = InterrogationChunkType.QA_PAIR.value
    d["qa_index"] = qa_index

    # Combine question and answer with tags for position extraction
    all_parts = q_parts + a_parts
    combined_text = "\n".join(all_parts)

    # Extract pure text for content and clean LaTeX formatting
    q_text = _clean_latex_format(remove_position_tag("\n".join(q_parts)))
    a_text = _clean_latex_format(remove_position_tag("\n".join(a_parts)))

    # Format: question\tanswer (same as QA parser)
    d["content_with_weight"] = f"{q_text}\t{a_text}"

    # Extract position directly from text tags (doesn't depend on crop())
    poss = _extract_positions_from_text(combined_text)
    if poss:
        add_positions(d, poss)
    else:
        logging.warning(f"No position info extracted for QA chunk {qa_index}")

    # Tokenize
    tokenize(d, f"{q_text} {a_text}", eng)

    # Add extension fields for criminal case RAG
    add_bbox_union(d)
    add_page_range(d)
    add_block_refs(d)

    return d


def chunk(filename, binary=None, from_page=0, to_page=100000, lang="Chinese", callback=None, **kwargs):
    """
    Main chunking function for interrogation records.

    Supports PDF files. The parser will:
    1. Extract header section (before first "问：")
    2. Split remaining content into QA pairs
    3. Optionally split long answers into sub-chunks

    OCR Backend Selection:
    - Uses PaddleOCR by default (if configured) for cloud-based OCR with caching
    - Falls back to local OCR (RAGFlowPdfParser) if PaddleOCR is not available

    Args:
        filename: Path to the file
        binary: Binary content (optional)
        from_page: Start page (for PDF)
        to_page: End page (for PDF)
        lang: Language ("Chinese" or "English")
        callback: Progress callback function
        **kwargs: Additional arguments including:
            - parser_config: Parser configuration dict
            - tenant_id: Tenant ID for LLMBundle
            - kb_id: Knowledge base ID for OCR caching
            - doc_id: Document ID for OCR caching (extracted from parser_config)

    Returns:
        list: List of chunk dictionaries
    """
    eng = lang.lower() == "english"
    res = []

    doc = {"docnm_kwd": filename, "title_tks": rag_tokenizer.tokenize(re.sub(r"\.[a-zA-Z]+$", "", filename))}

    if not re.search(r"\.pdf$", filename, re.IGNORECASE):
        raise NotImplementedError("Interrogation parser currently only supports PDF format files.")

    callback(0.1, "Start to parse interrogation record.")

    parser_config = kwargs.get("parser_config", {})
    tenant_id = kwargs.get("tenant_id")
    kb_id = kwargs.get("kb_id")
    doc_id = parser_config.get("doc_id", "")

    # Try PaddleOCR first (supports OCR caching) by reusing naive.py's by_paddleocr
    blocks = None
    pdf_parser = None

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

    # Convert sections to blocks format if PaddleOCR succeeded
    if sections is not None:
        blocks = _sections_to_blocks(sections)
        callback(0.4, f"PaddleOCR extracted {len(blocks)} text blocks.")

    # Fallback to local OCR if PaddleOCR fails
    if blocks is None:
        logging.info("PaddleOCR not available, falling back to local OCR")
        pdf_parser = Pdf()
        blocks = pdf_parser(filename if not binary else binary, from_page=from_page, to_page=to_page, callback=callback)
        callback(0.5, f"Local OCR extracted {len(blocks)} text blocks.")

    # Step 1: Extract header
    header_chunks, remaining_blocks = extract_header_chunks(blocks, doc, pdf_parser, eng)
    res.extend(header_chunks)
    callback(0.6, "Header section extracted.")

    # Step 2: Split QA pairs
    if remaining_blocks:
        qa_chunks = split_qa_chunks(remaining_blocks, doc, pdf_parser, eng)
        res.extend(qa_chunks)
        callback(0.8, f"Extracted {len(qa_chunks)} QA pairs.")

    callback(1.0, f"Completed. Total chunks: {len(res)}")

    return res


if __name__ == "__main__":
    import sys

    def dummy(prog=None, msg=""):
        if msg:
            print(f"[{prog:.0%}] {msg}" if prog else msg)

    if len(sys.argv) < 2:
        print("Usage: python interrogation.py <pdf_file>")
        sys.exit(1)

    result = chunk(sys.argv[1], callback=dummy)
    print(f"\nTotal chunks: {len(result)}")

    for i, chunk_item in enumerate(result):
        chunk_type = chunk_item.get("chunk_type", "unknown")
        content_preview = chunk_item.get("content_with_weight", "")[:100]
        print(f"\n[{i}] Type: {chunk_type}")
        print(f"    Content: {content_preview}...")
        if chunk_type == "qa_pair":
            print(f"    QA Index: {chunk_item.get('qa_index')}")
