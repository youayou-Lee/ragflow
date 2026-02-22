# Universal Block Parser Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement Layer A (Universal Block extraction) for criminal document parsing, enabling all document types to share a common block structure.

**Architecture:** Two-layer parsing: Layer A extracts UniversalBlocks from OCR output (block_type, text, bbox, entities). Layer B plugins process blocks into semantic chunks. This plan covers Phase 1: Layer A implementation.

**Tech Stack:** Python 3.12, dataclasses, re (regex), pytest

---

## Task 1: Create Directory Structure

**Files:**
- Create: `rag/app/criminal/__init__.py`
- Create: `rag/app/criminal/plugins/__init__.py`

**Step 1: Create criminal directory with __init__.py**

```python
# rag/app/criminal/__init__.py
"""
Criminal document parsing module.

Architecture:
- Layer A: Universal Block extraction (blocks.py, ner.py)
- Layer B: Document-type specific plugins (plugins/)
"""

from .blocks import UniversalBlock, BlockType, extract_universal_blocks

__all__ = ["UniversalBlock", "BlockType", "extract_universal_blocks"]
```

**Step 2: Create plugins subdirectory with __init__.py**

```python
# rag/app/criminal/plugins/__init__.py
"""
Layer B plugins for document-type specific parsing.
"""

from .base import ParserPlugin

__all__ = ["ParserPlugin"]
```

**Step 3: Commit**

```bash
git add rag/app/criminal/__init__.py rag/app/criminal/plugins/__init__.py
git commit -m "feat(criminal): create criminal parser module structure"
```

---

## Task 2: Implement BlockType Enum and UniversalBlock Dataclass

**Files:**
- Create: `rag/app/criminal/blocks.py`

**Step 1: Write the failing test**

```python
# test/unit/test_blocks.py

import pytest
from rag.app.criminal.blocks import BlockType, UniversalBlock


class TestBlockType:
    """Test BlockType enum."""

    def test_block_type_values(self):
        """Test that all expected block types exist."""
        assert BlockType.HEADER.value == "header"
        assert BlockType.PARAGRAPH.value == "paragraph"
        assert BlockType.QA_PAIR.value == "qa_pair"
        assert BlockType.TABLE.value == "table"
        assert BlockType.LIST.value == "list"
        assert BlockType.SEAL.value == "seal"
        assert BlockType.FOOTER.value == "footer"


class TestUniversalBlock:
    """Test UniversalBlock dataclass."""

    def test_required_fields(self):
        """Test creating block with required fields only."""
        block = UniversalBlock(
            block_type=BlockType.PARAGRAPH,
            text="Test content",
            page_no=0,
            bbox=(0.0, 0.0, 100.0, 50.0),
        )
        assert block.block_type == BlockType.PARAGRAPH
        assert block.text == "Test content"
        assert block.page_no == 0
        assert block.bbox == (0.0, 0.0, 100.0, 50.0)
        assert block.doc_type_hint is None
        assert block.entities is None

    def test_optional_fields(self):
        """Test creating block with all fields."""
        block = UniversalBlock(
            block_type=BlockType.QA_PAIR,
            text="问：你叫什么名字？",
            page_no=1,
            bbox=(10.0, 20.0, 200.0, 40.0),
            doc_type_hint="interrogation",
            entities={"amounts": ["42000"], "dates": ["2024-01-15"]},
        )
        assert block.doc_type_hint == "interrogation"
        assert block.entities["amounts"] == ["42000"]
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest test/unit/test_blocks.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'rag.app.criminal.blocks'"

**Step 3: Write minimal implementation**

```python
# rag/app/criminal/blocks.py
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
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest test/unit/test_blocks.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add rag/app/criminal/blocks.py test/unit/test_blocks.py
git commit -m "feat(criminal): add BlockType enum and UniversalBlock dataclass"
```

---

## Task 3: Implement Position Tag Parsing

**Files:**
- Modify: `rag/app/criminal/blocks.py`

**Step 1: Write the failing test**

```python
# test/unit/test_blocks.py (add to existing file)

class TestParsePositionTag:
    """Test position tag parsing."""

    def test_parse_single_page_tag(self):
        """Test parsing a single page position tag."""
        from rag.app.criminal.blocks import parse_position_tag

        text = "@@1\t10.0\t200.0\t50.0\t80.0##Hello World"
        page_no, bbox, content = parse_position_tag(text)

        assert page_no == 0  # 0-indexed
        assert bbox == (10.0, 50.0, 200.0, 80.0)  # (x0, y0, x1, y1)
        assert content == "Hello World"

    def test_parse_page_range_tag(self):
        """Test parsing a page range position tag."""
        from rag.app.criminal.blocks import parse_position_tag

        text = "@@1-2\t10.0\t200.0\t50.0\t80.0##Multi-page content"
        page_no, bbox, content = parse_position_tag(text)

        assert page_no == 0  # Uses first page, 0-indexed
        assert content == "Multi-page content"

    def test_parse_no_tag(self):
        """Test parsing text without position tag."""
        from rag.app.criminal.blocks import parse_position_tag

        text = "Plain text without tag"
        page_no, bbox, content = parse_position_tag(text)

        assert page_no == 0
        assert bbox is None
        assert content == "Plain text without tag"

    def test_parse_tag_format_variations(self):
        """Test various tag formats from OCR output."""
        from rag.app.criminal.blocks import parse_position_tag

        # Format from by_paddleocr: (content, tag) -> tag + content
        text = "@@2\t15.5\t180.3\t30.2\t60.8##答：我是张三"
        page_no, bbox, content = parse_position_tag(text)

        assert page_no == 1  # Page 2 -> index 1
        assert bbox == (15.5, 30.2, 180.3, 60.8)
        assert content == "答：我是张三"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest test/unit/test_blocks.py::TestParsePositionTag -v`
Expected: FAIL with "cannot import name 'parse_position_tag'"

**Step 3: Write minimal implementation**

```python
# rag/app/criminal/blocks.py (add after UniversalBlock class)

import re
import logging

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
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest test/unit/test_blocks.py::TestParsePositionTag -v`
Expected: PASS

**Step 5: Commit**

```bash
git add rag/app/criminal/blocks.py test/unit/test_blocks.py
git commit -m "feat(criminal): add parse_position_tag function"
```

---

## Task 4: Implement Block Type Inference

**Files:**
- Modify: `rag/app/criminal/blocks.py`

**Step 1: Write the failing test**

```python
# test/unit/test_blocks.py (add to existing file)

class TestInferBlockType:
    """Test block type inference from text content."""

    def test_infer_seal(self):
        """Test seal/stamp detection."""
        from rag.app.criminal.blocks import infer_block_type

        assert infer_block_type("（印章）", "middle") == BlockType.SEAL
        assert infer_block_type("章", "middle") == BlockType.SEAL

    def test_infer_qa_pair(self):
        """Test Q/A pair detection."""
        from rag.app.criminal.blocks import infer_block_type

        assert infer_block_type("问：你叫什么名字？", "middle") == BlockType.QA_PAIR
        assert infer_block_type("答：我叫张三", "middle") == BlockType.QA_PAIR
        assert infer_block_type("问:今天几号?", "middle") == BlockType.QA_PAIR

    def test_infer_list(self):
        """Test list item detection."""
        from rag.app.criminal.blocks import infer_block_type

        assert infer_block_type("1. 第一项内容", "middle") == BlockType.LIST
        assert infer_block_type("2、第二项内容", "middle") == BlockType.LIST
        assert infer_block_type("一、基本情况", "middle") == BlockType.LIST

    def test_infer_header(self):
        """Test header detection based on position."""
        from rag.app.criminal.blocks import infer_block_type

        short_text = "讯问笔录"
        assert infer_block_type(short_text, "first") == BlockType.HEADER

        # Long text at first position is not header
        long_text = "这是一段很长的内容" * 100
        assert infer_block_type(long_text, "first") == BlockType.PARAGRAPH

    def test_infer_footer(self):
        """Test footer detection based on position."""
        from rag.app.criminal.blocks import infer_block_type

        short_text = "第 1 页 共 3 页"
        assert infer_block_type(short_text, "last") == BlockType.FOOTER

        # Long text at last position is not footer
        long_text = "这是一段很长的内容" * 10
        assert infer_block_type(long_text, "last") == BlockType.PARAGRAPH

    def test_infer_paragraph_default(self):
        """Test default paragraph type."""
        from rag.app.criminal.blocks import infer_block_type

        assert infer_block_type("这是一段普通文本。", "middle") == BlockType.PARAGRAPH
        assert infer_block_type("普通内容", "middle") == BlockType.PARAGRAPH
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest test/unit/test_blocks.py::TestInferBlockType -v`
Expected: FAIL with "cannot import name 'infer_block_type'"

**Step 3: Write minimal implementation**

```python
# rag/app/criminal/blocks.py (add after parse_position_tag function)

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
    if re.match(r'^\s*[\d一二三四五六七八九十]+[\.、）]\s', text):
        return BlockType.LIST

    # 4. Header detection (first position, relatively short)
    if position == "first" and len(text) < 500:
        return BlockType.HEADER

    # 5. Footer detection (last position, relatively short)
    if position == "last" and len(text) < 100:
        return BlockType.FOOTER

    # 6. Default: regular paragraph
    return BlockType.PARAGRAPH
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest test/unit/test_blocks.py::TestInferBlockType -v`
Expected: PASS

**Step 5: Commit**

```bash
git add rag/app/criminal/blocks.py test/unit/test_blocks.py
git commit -m "feat(criminal): add infer_block_type function with rule-based classification"
```

---

## Task 5: Implement LightWeight NER

**Files:**
- Create: `rag/app/criminal/ner.py`

**Step 1: Write the failing test**

```python
# test/unit/test_ner.py

import pytest
from rag.app.criminal.ner import extract_lightweight_entities


class TestExtractLightweightEntities:
    """Test lightweight NER extraction (amounts and dates only)."""

    def test_extract_amounts_numeric(self):
        """Test numeric amount extraction."""
        text = "涉案金额42000元，已退还1500.50元"
        entities = extract_lightweight_entities(text)

        assert entities is not None
        assert "42000" in entities["amounts"]
        assert "1500.50" in entities["amounts"]

    def test_extract_amounts_chinese(self):
        """Test Chinese numeral amount extraction."""
        text = "诈骗金额三万元，退赔一万元"
        entities = extract_lightweight_entities(text)

        assert entities is not None
        assert "三万" in entities["amounts"]
        assert "一万" in entities["amounts"]

    def test_extract_amounts_with_comma(self):
        """Test amount with comma separators."""
        text = "总计42,000.00元"
        entities = extract_lightweight_entities(text)

        assert entities is not None
        assert "42,000.00" in entities["amounts"]

    def test_extract_dates_iso_format(self):
        """Test ISO format date extraction."""
        text = "案发时间为2024-01-15，2024/03/20又作案"
        entities = extract_lightweight_entities(text)

        assert entities is not None
        assert "2024-01-15" in entities["dates"]
        assert "2024/03/20" in entities["dates"]

    def test_extract_dates_chinese_format(self):
        """Test Chinese format date extraction."""
        text = "2024年1月15日实施诈骗"
        entities = extract_lightweight_entities(text)

        assert entities is not None
        assert "2024年1月15日" in entities["dates"]

    def test_extract_dates_partial(self):
        """Test partial date extraction (month-day only)."""
        text = "1月15日当天"
        entities = extract_lightweight_entities(text)

        assert entities is not None
        assert "1月15日" in entities["dates"]

    def test_no_entities(self):
        """Test text without amounts or dates."""
        text = "这是一段普通文本，没有金额和日期"
        entities = extract_lightweight_entities(text)

        assert entities is None

    def test_deduplication(self):
        """Test that duplicate entities are removed."""
        text = "42000元和42000元是同一笔"
        entities = extract_lightweight_entities(text)

        assert entities is not None
        assert entities["amounts"].count("42000") == 1

    def test_combined_entities(self):
        """Test extraction of both amounts and dates."""
        text = "2024年3月15日收到42000元"
        entities = extract_lightweight_entities(text)

        assert entities is not None
        assert "42000" in entities["amounts"]
        assert "2024年3月15日" in entities["dates"]
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest test/unit/test_ner.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'rag.app.criminal.ner'"

**Step 3: Write minimal implementation**

```python
# rag/app/criminal/ner.py
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
Lightweight NER for Layer A block extraction.

Extracts only amounts and dates to satisfy PRD constraints:
- "精确定位引用" (Precise citation)
- "禁止无证据断言" (No assertion without evidence)
"""

import re
from typing import Optional


def extract_lightweight_entities(text: str) -> Optional[dict]:
    """
    Extract amounts and dates from text.

    This is a lightweight NER that only extracts:
    - Amounts: numeric and Chinese numerals with currency units
    - Dates: ISO and Chinese date formats

    Args:
        text: Text content to extract entities from

    Returns:
        dict with "amounts" and "dates" lists, or None if no entities found
    """
    entities = {
        "amounts": [],
        "dates": []
    }

    # Amount patterns
    amount_patterns = [
        # Numeric with optional comma separators and decimals: 42000, 42,000.00
        r'(\d+(?:,\d{3})*(?:\.\d{1,2})?)\s*[元万]',
        # Chinese numerals with currency: 三万元, 一万
        r'([一二三四五六七八九十百千万亿]+)\s*[元万]',
    ]

    for pattern in amount_patterns:
        entities["amounts"].extend(re.findall(pattern, text))

    # Date patterns
    date_patterns = [
        # ISO format: 2024-01-15, 2024/03/20
        r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})',
        # Chinese format: 2024年1月15日, 2024年3月
        r'(\d{4}年\d{1,2}月\d{1,2}日?)',
        # Partial date: 1月15日
        r'(\d{1,2}月\d{1,2}日)',
    ]

    for pattern in date_patterns:
        entities["dates"].extend(re.findall(pattern, text))

    # Deduplicate
    entities["amounts"] = list(set(entities["amounts"]))
    entities["dates"] = list(set(entities["dates"]))

    # Return None if no entities found
    if not entities["amounts"] and not entities["dates"]:
        return None

    return entities
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest test/unit/test_ner.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add rag/app/criminal/ner.py test/unit/test_ner.py
git commit -m "feat(criminal): add lightweight NER for amounts and dates"
```

---

## Task 6: Implement extract_universal_blocks Main Function

**Files:**
- Modify: `rag/app/criminal/blocks.py`

**Step 1: Write the failing test**

```python
# test/unit/test_blocks.py (add to existing file)

class TestExtractUniversalBlocks:
    """Test main block extraction function."""

    def test_extract_from_simple_sections(self):
        """Test extraction from simple OCR sections."""
        from rag.app.criminal.blocks import extract_universal_blocks

        # Simulate OCR output format from by_paddleocr
        sections = [
            ("讯问笔录", "@@1\t10.0\t200.0\t20.0\t40.0##"),
            ("问：你叫什么名字？", "@@1\t10.0\t200.0\t50.0\t70.0##"),
            ("答：我叫张三", "@@1\t10.0\t200.0\t80.0\t100.0##"),
        ]

        blocks = extract_universal_blocks(sections, "interrogation")

        assert len(blocks) == 3
        assert blocks[0].block_type == BlockType.HEADER
        assert blocks[1].block_type == BlockType.QA_PAIR
        assert blocks[2].block_type == BlockType.QA_PAIR

    def test_extract_with_entities(self):
        """Test that entities are extracted."""
        from rag.app.criminal.blocks import extract_universal_blocks

        sections = [
            ("2024年1月15日收到42000元", "@@1\t10.0\t200.0\t20.0\t40.0##"),
        ]

        blocks = extract_universal_blocks(sections)

        assert len(blocks) == 1
        assert blocks[0].entities is not None
        assert "42000" in blocks[0].entities["amounts"]
        assert "2024年1月15日" in blocks[0].entities["dates"]

    def test_extract_positions(self):
        """Test that positions are correctly extracted."""
        from rag.app.criminal.blocks import extract_universal_blocks

        sections = [
            ("Test content", "@@2\t15.0\t180.0\t30.0\t50.0##"),
        ]

        blocks = extract_universal_blocks(sections)

        assert blocks[0].page_no == 1  # Page 2 -> 0-indexed
        assert blocks[0].bbox == (15.0, 30.0, 180.0, 50.0)

    def test_extract_empty_sections(self):
        """Test handling of empty sections."""
        from rag.app.criminal.blocks import extract_universal_blocks

        blocks = extract_universal_blocks([])
        assert blocks == []

    def test_doc_type_hint_propagated(self):
        """Test that doc_type_hint is propagated to blocks."""
        from rag.app.criminal.blocks import extract_universal_blocks

        sections = [
            ("内容", "@@1\t10.0\t200.0\t20.0\t40.0##"),
        ]

        blocks = extract_universal_blocks(sections, "indictment")

        assert blocks[0].doc_type_hint == "indictment"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest test/unit/test_blocks.py::TestExtractUniversalBlocks -v`
Expected: FAIL with "cannot import name 'extract_universal_blocks'"

**Step 3: Write minimal implementation**

```python
# rag/app/criminal/blocks.py (add after infer_block_type function)

from typing import List
from .ner import extract_lightweight_entities


def _get_relative_position(index: int, total: int) -> str:
    """Determine relative position in document."""
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
) -> List["UniversalBlock"]:
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
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest test/unit/test_blocks.py::TestExtractUniversalBlocks -v`
Expected: PASS

**Step 5: Commit**

```bash
git add rag/app/criminal/blocks.py test/unit/test_blocks.py
git commit -m "feat(criminal): add extract_universal_blocks main function"
```

---

## Task 7: Implement ParserPlugin Base Class

**Files:**
- Create: `rag/app/criminal/plugins/base.py`

**Step 1: Write the failing test**

```python
# test/unit/test_plugins_base.py

import pytest
from abc import ABC
from rag.app.criminal.plugins.base import ParserPlugin
from rag.app.criminal.blocks import UniversalBlock, BlockType


class TestParserPlugin:
    """Test ParserPlugin base class."""

    def test_is_abstract(self):
        """Test that ParserPlugin cannot be instantiated directly."""
        with pytest.raises(TypeError):
            ParserPlugin()

    def test_concrete_implementation_required(self):
        """Test that subclasses must implement abstract methods."""
        class IncompletePlugin(ParserPlugin):
            pass

        with pytest.raises(TypeError):
            IncompletePlugin()

    def test_concrete_implementation(self):
        """Test a complete plugin implementation."""
        class TestPlugin(ParserPlugin):
            @property
            def doc_type(self) -> str:
                return "test"

            def process(self, blocks, doc, chat_mdl=None, **kwargs):
                return [{"content": b.text} for b in blocks]

        plugin = TestPlugin()
        assert plugin.doc_type == "test"

    def test_helper_get_header_blocks(self):
        """Test get_header_blocks helper."""
        class TestPlugin(ParserPlugin):
            @property
            def doc_type(self) -> str:
                return "test"

            def process(self, blocks, doc, chat_mdl=None, **kwargs):
                return []

        plugin = TestPlugin()
        blocks = [
            UniversalBlock(BlockType.HEADER, "Header", 0, (0, 0, 100, 50)),
            UniversalBlock(BlockType.PARAGRAPH, "Para", 0, (0, 0, 100, 50)),
            UniversalBlock(BlockType.HEADER, "Header2", 0, (0, 0, 100, 50)),
        ]

        headers = plugin.get_header_blocks(blocks)
        assert len(headers) == 2
        assert all(b.block_type == BlockType.HEADER for b in headers)

    def test_helper_get_qa_blocks(self):
        """Test get_qa_blocks helper."""
        class TestPlugin(ParserPlugin):
            @property
            def doc_type(self) -> str:
                return "test"

            def process(self, blocks, doc, chat_mdl=None, **kwargs):
                return []

        plugin = TestPlugin()
        blocks = [
            UniversalBlock(BlockType.QA_PAIR, "问：测试", 0, (0, 0, 100, 50)),
            UniversalBlock(BlockType.PARAGRAPH, "普通", 0, (0, 0, 100, 50)),
            UniversalBlock(BlockType.QA_PAIR, "答：回答", 0, (0, 0, 100, 50)),
        ]

        qa_blocks = plugin.get_qa_blocks(blocks)
        assert len(qa_blocks) == 2
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest test/unit/test_plugins_base.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'rag.app.criminal.plugins.base'"

**Step 3: Write minimal implementation**

```python
# rag/app/criminal/plugins/base.py
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
Base class for Layer B parser plugins.

Plugins receive UniversalBlock sequences and output semantic chunks.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from ..blocks import UniversalBlock, BlockType


class ParserPlugin(ABC):
    """
    Abstract base class for document-type specific parser plugins.

    Layer B plugins receive UniversalBlock sequences from Layer A
    and produce semantic chunks for indexing and retrieval.

    Attributes:
        doc_type: Document type identifier (e.g., "interrogation", "indictment")
    """

    @property
    @abstractmethod
    def doc_type(self) -> str:
        """
        Return document type identifier.

        Returns:
            str: Document type (e.g., "interrogation", "indictment")
        """
        pass

    @abstractmethod
    def process(
        self,
        blocks: List[UniversalBlock],
        doc: dict,
        chat_mdl=None,
        **kwargs
    ) -> List[dict]:
        """
        Process block sequence and generate chunks.

        Args:
            blocks: UniversalBlock list from Layer A
            doc: Document metadata (filename, etc.)
            chat_mdl: Optional LLM model for metadata enhancement
            **kwargs: Additional arguments

        Returns:
            List of chunk dictionaries with keys:
            - content_with_weight: Text content
            - chunk_type: Semantic chunk type
            - page_no: Page number
            - bbox: Bounding box
            - entities: Extracted entities (optional)
            - metadata: Additional metadata (optional)
        """
        pass

    def get_header_blocks(self, blocks: List[UniversalBlock]) -> List[UniversalBlock]:
        """
        Helper: Get all header blocks.

        Args:
            blocks: Block list

        Returns:
            List of blocks with HEADER type
        """
        return [b for b in blocks if b.block_type == BlockType.HEADER]

    def get_qa_blocks(self, blocks: List[UniversalBlock]) -> List[UniversalBlock]:
        """
        Helper: Get all Q/A pair blocks.

        Args:
            blocks: Block list

        Returns:
            List of blocks with QA_PAIR type
        """
        return [b for b in blocks if b.block_type == BlockType.QA_PAIR]

    def get_paragraph_blocks(self, blocks: List[UniversalBlock]) -> List[UniversalBlock]:
        """
        Helper: Get all paragraph blocks.

        Args:
            blocks: Block list

        Returns:
            List of blocks with PARAGRAPH type
        """
        return [b for b in blocks if b.block_type == BlockType.PARAGRAPH]

    def get_list_blocks(self, blocks: List[UniversalBlock]) -> List[UniversalBlock]:
        """
        Helper: Get all list blocks.

        Args:
            blocks: Block list

        Returns:
            List of blocks with LIST type
        """
        return [b for b in blocks if b.block_type == BlockType.LIST]
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest test/unit/test_plugins_base.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add rag/app/criminal/plugins/base.py test/unit/test_plugins_base.py
git commit -m "feat(criminal): add ParserPlugin abstract base class"
```

---

## Task 8: Run Full Test Suite

**Step 1: Run all criminal module tests**

Run: `uv run pytest test/unit/test_blocks.py test/unit/test_ner.py test/unit/test_plugins_base.py -v`
Expected: All tests PASS

**Step 2: Run with coverage**

Run: `uv run pytest test/unit/test_blocks.py test/unit/test_ner.py test/unit/test_plugins_base.py --cov=rag/app/criminal --cov-report=term-missing`
Expected: High coverage (>90%)

**Step 3: Final commit**

```bash
git add -A
git commit -m "feat(criminal): complete Phase 1 - Layer A universal block extraction

- Add UniversalBlock dataclass and BlockType enum
- Implement parse_position_tag for OCR tag parsing
- Implement infer_block_type for rule-based classification
- Implement extract_lightweight_entities for amounts/dates NER
- Implement extract_universal_blocks main function
- Add ParserPlugin abstract base class for Layer B"
```

---

## Summary

**Phase 1 Complete:** Layer A (Universal Block Extraction) is now implemented and tested.

**Files Created:**
- `rag/app/criminal/__init__.py`
- `rag/app/criminal/blocks.py`
- `rag/app/criminal/ner.py`
- `rag/app/criminal/plugins/__init__.py`
- `rag/app/criminal/plugins/base.py`
- `test/unit/test_blocks.py`
- `test/unit/test_ner.py`
- `test/unit/test_plugins_base.py`

**Next Steps (Future Phases):**
- Phase 2: Migrate interrogation.py to use Layer A
- Phase 3: Migrate indictment.py to use Layer A
- Phase 4: Implement InterrogationPlugin and IndictmentPlugin
