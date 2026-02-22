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
