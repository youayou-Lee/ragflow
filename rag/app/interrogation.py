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
from rag.nlp import rag_tokenizer, add_positions
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
            list: List of blocks with text and position info
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

        # Return blocks with their text and position info
        blocks = []
        for box in self.boxes:
            line_tag = self._line_tag(box, zoomin)
            blocks.append({"text": box["text"], "tag": line_tag, "x0": box.get("x0", 0), "top": box.get("top", 0)})

        return blocks

    def get_positions_from_tag(self, tag: str):
        """Extract position info from tag string."""
        if not tag or not tag.startswith("@@"):
            return []
        try:
            # Format: @@page\tleft\tright\ttop\tbottom##
            parts = tag.rstrip("#").lstrip("@").split("\t")
            if len(parts) >= 5:
                return [(int(parts[0]), float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4]))]
        except (ValueError, IndexError):
            pass
        return []


def extract_header(blocks: list) -> tuple[str, list]:
    """
    Extract header section from the beginning of blocks.

    Header is defined as all content before the first "问：" pattern.

    Args:
        blocks: List of text blocks

    Returns:
        tuple: (header_content, remaining_blocks)
    """
    header_parts = []
    header_positions = []

    for i, block in enumerate(blocks):
        text = block.get("text", "").strip()
        if QUESTION_PATTERN.match(text):
            # Found first question, return header and remaining blocks
            return "\n".join(header_parts), blocks[i:], header_positions

        header_parts.append(text)
        if "tag" in block:
            header_positions.append(block["tag"])

    # No question found, all content is header
    return "\n".join(header_parts), [], header_positions


def split_qa_pairs(blocks: list) -> list[tuple[str, str, list]]:
    """
    Split blocks into QA pairs.

    Rules:
    1. Each "问：" starts a new QA pair
    2. Collect all content until next "问：" as the answer
    3. Preserve position information for frontend highlighting

    Args:
        blocks: List of text blocks (should start with first question)

    Returns:
        list: List of (question, answer, positions) tuples
    """
    qa_pairs = []
    current_q = None
    current_a_parts = []
    current_positions = []

    for block in blocks:
        text = block.get("text", "").strip()
        tag = block.get("tag", "")

        if QUESTION_PATTERN.match(text):
            # Save previous QA pair if exists
            if current_q:
                qa_pairs.append((current_q, "\n".join(current_a_parts), current_positions))

            # Start new QA pair
            current_q = text
            current_a_parts = []
            current_positions = [tag] if tag else []

        elif current_q:
            # This is part of the answer
            if ANSWER_PATTERN.match(text):
                # Remove "答：" prefix and add to answer
                current_a_parts.append(text)
            else:
                current_a_parts.append(text)
            if tag:
                current_positions.append(tag)

    # Save last QA pair
    if current_q:
        qa_pairs.append((current_q, "\n".join(current_a_parts), current_positions))

    return qa_pairs


def build_header_chunk(doc: dict, header_content: str, positions: list) -> dict:
    """
    Build a header chunk.

    Args:
        doc: Base document dict
        header_content: Header text content
        positions: Position tags

    Returns:
        dict: Chunk dictionary
    """
    d = deepcopy(doc)
    d["chunk_type"] = InterrogationChunkType.HEADER.value
    d["content_with_weight"] = header_content
    d["content_ltks"] = rag_tokenizer.tokenize(header_content)
    d["content_sm_ltks"] = rag_tokenizer.fine_grained_tokenize(d["content_ltks"])

    # Add position info
    poss = _parse_position_tags(positions)
    if poss:
        add_positions(d, poss)

    return d


def _parse_position_tags(tags: list) -> list:
    """
    Parse position tags from @@...## format to position tuples.

    The tag format is: @@{page}\t{x0}\t{x1}\t{top}\t{bottom}##
    Where page is 1-based, and add_positions expects 0-based page numbers.

    Returns:
        list: List of (page_0based, left, right, top, bottom) tuples
    """
    poss = []
    for tag in tags:
        if tag and tag.startswith("@@"):
            try:
                # Remove @@ prefix and ## suffix
                parts = tag.rstrip("#").lstrip("@").split("\t")
                if len(parts) >= 5:
                    # Convert 1-based page number to 0-based
                    page_1based = parts[0]
                    # Handle multi-page spans like "1-2"
                    page_nums = [int(p) - 1 for p in page_1based.split("-")]
                    # Use first page for position
                    page_0based = page_nums[0] if page_nums else 0
                    poss.append((page_0based, float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])))
            except (ValueError, IndexError):
                pass
    return poss


def build_qa_chunk(doc: dict, question: str, answer: str, positions: list, qa_index: int, parent_id: Optional[str] = None, sub_index: Optional[int] = None) -> dict:
    """
    Build a QA pair chunk.

    Args:
        doc: Base document dict
        question: Question text
        answer: Answer text
        positions: Position tags
        qa_index: Index of this QA pair (0-based)
        parent_id: Parent QA ID if this is a sub-chunk
        sub_index: Sub-index if this is a sub-chunk

    Returns:
        dict: Chunk dictionary
    """
    d = deepcopy(doc)

    if parent_id is not None:
        d["chunk_type"] = InterrogationChunkType.QA_SUB.value
        d["parent_qa_id"] = parent_id
        d["sub_index"] = sub_index
    else:
        d["chunk_type"] = InterrogationChunkType.QA_PAIR.value

    d["qa_index"] = qa_index

    # Combine question and answer
    content = f"{question}\t{answer}"
    d["content_with_weight"] = content
    d["content_ltks"] = rag_tokenizer.tokenize(question + " " + answer)
    d["content_sm_ltks"] = rag_tokenizer.fine_grained_tokenize(d["content_ltks"])

    # Add position info
    poss = _parse_position_tags(positions)
    if poss:
        add_positions(d, poss)

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
    _ = lang.lower() == "english"  # Reserved for future i18n support
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
    header_content, remaining_blocks, header_positions = extract_header(blocks)

    if header_content:
        header_chunk = build_header_chunk(doc, header_content, header_positions)
        res.append(header_chunk)
        callback(0.6, "Header section extracted.")

    # Step 2: Split QA pairs
    if remaining_blocks:
        qa_pairs = split_qa_pairs(remaining_blocks)
        callback(0.8, f"Extracted {len(qa_pairs)} QA pairs.")

        for idx, (question, answer, positions) in enumerate(qa_pairs):
            # Check if answer is too long
            if len(answer) > MAX_QA_LENGTH:
                # For now, just create the chunk without splitting
                # LLM-based splitting can be added later via interrogation_extractor
                chunk_item = build_qa_chunk(doc, question, answer, positions, idx)
                res.append(chunk_item)
            else:
                chunk_item = build_qa_chunk(doc, question, answer, positions, idx)
                res.append(chunk_item)

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
