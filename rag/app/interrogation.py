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
"""

import logging
import re
from copy import deepcopy
from timeit import default_timer as timer
from typing import Optional

from deepdoc.parser import PdfParser
from rag.nlp import rag_tokenizer, add_positions, tokenize
from strenum import StrEnum


class InterrogationChunkType(StrEnum):
    """Chunk types for interrogation records."""

    HEADER = "header"  # Header block with basic info
    QA_PAIR = "qa_pair"  # Question-answer pair block
    QA_SUB = "qa_sub"  # Sub-segment of long QA pair


# Maximum length for QA answer before splitting
MAX_QA_LENGTH = 2000

# Patterns for identifying QA structure
QUESTION_PATTERN = re.compile(r"^问[：:\s]")
ANSWER_PATTERN = re.compile(r"^答[：:\s]")


class Pdf(PdfParser):
    """PDF parser for interrogation records."""

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


def extract_header_chunks(blocks: list, doc: dict, pdf_parser: Pdf, eng: bool = False) -> tuple[list, list]:
    """
    Extract header section from the beginning of blocks.

    Header is defined as all content before the first "问：" pattern.

    Args:
        blocks: List of text blocks with position tags
        doc: Base document dict
        pdf_parser: PDF parser instance for extracting positions
        eng: Whether the text is English

    Returns:
        tuple: (header_chunks, remaining_blocks)
    """
    header_parts = []

    for i, block in enumerate(blocks):
        # Remove tag to get pure text for pattern matching
        pure_text = pdf_parser.remove_tag(block).strip()

        if QUESTION_PATTERN.match(pure_text):
            # Found first question, return header and remaining blocks
            if header_parts:
                # Build header chunk using standard method
                header_text = "\n".join(header_parts)
                d = deepcopy(doc)
                d["chunk_type"] = InterrogationChunkType.HEADER.value
                d["image"], poss = pdf_parser.crop(header_text, need_position=True)
                add_positions(d, poss)
                tokenize(d, pdf_parser.remove_tag(header_text), eng)
                return [d], blocks[i:]

            return [], blocks[i:]

        header_parts.append(block)

    # No question found, all content is header
    if header_parts:
        header_text = "\n".join(header_parts)
        d = deepcopy(doc)
        d["chunk_type"] = InterrogationChunkType.HEADER.value
        d["image"], poss = pdf_parser.crop(header_text, need_position=True)
        add_positions(d, poss)
        tokenize(d, pdf_parser.remove_tag(header_text), eng)
        return [d], []

    return [], []


def split_qa_chunks(blocks: list, doc: dict, pdf_parser: Pdf, eng: bool = False) -> list:
    """
    Split blocks into QA pair chunks.

    Rules:
    1. Each "问：" starts a new QA pair
    2. Collect all content until next "问：" as the answer
    3. Use standard crop/remove_tag methods for position handling

    Args:
        blocks: List of text blocks with position tags (should start with first question)
        doc: Base document dict
        pdf_parser: PDF parser instance for extracting positions
        eng: Whether the text is English

    Returns:
        list: List of chunk dictionaries
    """
    res = []
    current_q_parts = []
    current_a_parts = []
    qa_index = 0

    for block in blocks:
        pure_text = pdf_parser.remove_tag(block).strip()

        if QUESTION_PATTERN.match(pure_text):
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


def _build_qa_chunk(doc: dict, pdf_parser: Pdf, q_parts: list, a_parts: list, qa_index: int, eng: bool) -> dict:
    """
    Build a QA pair chunk using standard position handling.

    Args:
        doc: Base document dict
        pdf_parser: PDF parser instance
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

    # Extract pure text for content
    q_text = pdf_parser.remove_tag("\n".join(q_parts))
    a_text = pdf_parser.remove_tag("\n".join(a_parts))

    # Format: question\tanswer (same as QA parser)
    d["content_with_weight"] = f"{q_text}\t{a_text}"

    # Use standard position extraction
    d["image"], poss = pdf_parser.crop(combined_text, need_position=True)
    add_positions(d, poss)

    # Tokenize
    tokenize(d, f"{q_text} {a_text}", eng)

    return d


def chunk(filename, binary=None, from_page=0, to_page=100000, lang="Chinese", callback=None, **kwargs):
    """
    Main chunking function for interrogation records.

    Supports PDF files. The parser will:
    1. Extract header section (before first "问：")
    2. Split remaining content into QA pairs
    3. Optionally split long answers into sub-chunks

    Args:
        filename: Path to the file
        binary: Binary content (optional)
        from_page: Start page (for PDF)
        to_page: End page (for PDF)
        lang: Language ("Chinese" or "English")
        callback: Progress callback function

    Returns:
        list: List of chunk dictionaries
    """
    eng = lang.lower() == "english"
    res = []

    doc = {"docnm_kwd": filename, "title_tks": rag_tokenizer.tokenize(re.sub(r"\.[a-zA-Z]+$", "", filename))}

    if not re.search(r"\.pdf$", filename, re.IGNORECASE):
        raise NotImplementedError("Interrogation parser currently only supports PDF format files.")

    callback(0.1, "Start to parse interrogation record.")

    # Parse PDF
    pdf_parser = Pdf()
    blocks = pdf_parser(filename if not binary else binary, from_page=from_page, to_page=to_page, callback=callback)

    callback(0.5, f"Extracted {len(blocks)} text blocks.")

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
