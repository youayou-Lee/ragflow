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
Universal Block extraction for criminal document parsing.

Layer A: Extracts unified block structure from OCR output.
"""

import re
from dataclasses import dataclass
from typing import Optional, List
from enum import Enum

from .ner import extract_lightweight_entities


class BlockType(str, Enum):
    """Layout element types for universal blocks."""

    HEADER = "header"        # Document header (title, basic info)
    PARAGRAPH = "paragraph"  # Regular paragraph
    QA_PAIR = "qa_pair"      # Question-answer pair (问：/答：)
    TABLE = "table"          # Table
    LIST = "list"            # List item
    SEAL = "seal"            # Seal/stamp
    FOOTER = "footer"        # Page footer


@dataclass
class UniversalBlock:
    """
    Universal block structure - Layer A output.

    Attributes:
        block_type: Layout element type
        text: Text content
        page_no: Page number (0-indexed)
        bbox: Bounding box (x0, y0, x1, y1)
        doc_type_hint: Optional document type hint (e.g., "interrogation")
        entities: Optional lightweight NER results (amounts, dates)
    """

    # Required fields
    block_type: BlockType
    text: str
    page_no: int
    bbox: tuple[float, float, float, float]

    # Optional fields
    doc_type_hint: Optional[str] = None
    entities: Optional[dict] = None


# Pattern for extracting position tags from text
# Format: @@page\tx0\tx1\ttop\tbottom##content
# Page can be single number (1) or range (1-2)
POSITION_TAG_PATTERN = re.compile(
    r"^@@(\d+(?:-\d+)?)\t([\d.]+)\t([\d.]+)\t([\d.]+)\t([\d.]+)##(.*)$"
)


def parse_position_tag(text: str) -> tuple[int, Optional[tuple], str]:
    """
    Parse position tag from OCR output text.

    Position tag format: @@page\tx0\tx1\ttop\tbottom##content
    - page: 1-indexed page number (can be range like "1-2")
    - x0, x1, top, bottom: bounding box coordinates
    - content: actual text content

    Args:
        text: Text with optional position tag prefix

    Returns:
        tuple: (page_no, bbox, content)
            - page_no: 0-indexed page number (uses first page for ranges)
            - bbox: (x0, y0, x1, y1) or None if no tag
            - content: Text content without tag
    """
    match = POSITION_TAG_PATTERN.match(text)

    if not match:
        # No position tag, return defaults
        return 0, None, text

    page_str, x0, x1, top, bottom, content = match.groups()

    # Handle page range: use first page, convert to 0-indexed
    first_page = int(page_str.split("-")[0]) - 1

    # bbox format: (x0, y0, x1, y1)
    bbox = (float(x0), float(top), float(x1), float(bottom))

    return first_page, bbox, content


def infer_block_type(
    text: str,
    position: str,
    doc_type_hint: Optional[str] = None
) -> BlockType:
    """
    Infer block type from text content and position.

    Uses rule-based pattern matching for layout element classification.

    Args:
        text: Text content of the block
        position: Relative position in document ("first", "middle", "last")
        doc_type_hint: Optional document type hint (not used in current rules)

    Returns:
        BlockType: Inferred block type
    """
    text = text.strip()

    # 1. Seal/stamp detection (very short text with seal keywords)
    if "印章" in text or (len(text) < 10 and "章" in text):
        return BlockType.SEAL

    # 2. Q/A pair detection (interrogation record pattern)
    if text.startswith(("问：", "问:", "答：", "答:")):
        return BlockType.QA_PAIR

    # 3. List item detection (numbered items)
    if re.match(r'^\s*[\d一二三四五六七八九十]+[\.、）]', text):
        return BlockType.LIST

    # 4. Header detection (first position, relatively short)
    if position == "first" and len(text) < 500:
        return BlockType.HEADER

    # 5. Footer detection (last position, very short - typical page numbers)
    if position == "last" and len(text) < 50:
        return BlockType.FOOTER

    # 6. Default: regular paragraph
    return BlockType.PARAGRAPH


def _get_relative_position(index: int, total: int) -> str:
    """
    Determine relative position in document.

    Args:
        index: Current section index (0-based)
        total: Total number of sections

    Returns:
        str: Position indicator ("first", "middle", or "last")
    """
    if total == 1:
        return "first"
    if index == 0:
        return "first"
    if index == total - 1:
        return "last"
    return "middle"


def extract_universal_blocks(
    sections: list,
    doc_type_hint: Optional[str] = None
) -> List[UniversalBlock]:
    """
    Extract universal blocks from OCR output sections.

    This is the main Layer A function that transforms OCR output
    into a unified block structure.

    Args:
        sections: OCR output sections, each being a tuple (content, tag)
                  where tag is "@@page\tx0\tx1\ttop\tbottom##"
        doc_type_hint: Optional document type hint (e.g., "interrogation")

    Returns:
        List of UniversalBlock objects
    """
    if not sections:
        return []

    blocks = []
    total = len(sections)

    for index, section in enumerate(sections):
        # Handle different section formats
        if isinstance(section, (list, tuple)):
            if len(section) >= 2:
                content = section[0] or ""
                tag = section[1] or ""
            else:
                content = section[0] if section else ""
                tag = ""
        else:
            content = str(section)
            tag = ""

        # Combine tag and content for parsing
        text_with_tag = f"{tag}{content}" if tag else content

        # Parse position tag
        page_no, bbox, text = parse_position_tag(text_with_tag)

        # Infer block type
        position = _get_relative_position(index, total)
        block_type = infer_block_type(text, position, doc_type_hint)

        # Extract entities
        entities = extract_lightweight_entities(text)

        # Create block
        block = UniversalBlock(
            block_type=block_type,
            text=text,
            page_no=page_no,
            bbox=bbox if bbox else (0.0, 0.0, 0.0, 0.0),
            doc_type_hint=doc_type_hint,
            entities=entities
        )
        blocks.append(block)

    return blocks
