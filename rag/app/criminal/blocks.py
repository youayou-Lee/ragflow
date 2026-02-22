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
from typing import Optional
from enum import Enum


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
