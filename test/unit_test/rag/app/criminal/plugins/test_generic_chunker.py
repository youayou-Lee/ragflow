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

"""Unit tests for GenericChunker plugin."""

import sys
from dataclasses import dataclass
from enum import Enum
from unittest.mock import MagicMock

import pytest


# Define BlockType and UniversalBlock locally to avoid heavy imports
class BlockType(str, Enum):
    """Layout element types for universal blocks."""
    HEADER = "header"
    PARAGRAPH = "paragraph"
    QA_PAIR = "qa_pair"
    TABLE = "table"
    LIST = "list"
    SEAL = "seal"
    FOOTER = "footer"


@dataclass
class UniversalBlock:
    """Universal block structure for testing."""
    block_type: BlockType
    text: str
    page_no: int
    bbox: tuple
    doc_type_hint: str = None
    entities: dict = None


# Mock the rag.app.naive module before importing GenericChunker
mock_naive = MagicMock()
mock_naive.BlockType = BlockType
mock_naive.UniversalBlock = UniversalBlock
sys.modules['rag.app.naive'] = mock_naive

# Now we can import the GenericChunker
from rag.app.criminal.plugins.generic_chunker import GenericChunker

# Use the same BlockType that the chunker module sees (from the mock)
# This ensures our test blocks use the same BlockType enum instances


def make_block(text: str, block_type: BlockType = None,
               page_no: int = 0, bbox: tuple = (0, 0, 100, 50)) -> UniversalBlock:
    """Helper to create a UniversalBlock for testing."""
    if block_type is None:
        block_type = BlockType.PARAGRAPH
    return UniversalBlock(
        block_type=block_type,
        text=text,
        page_no=page_no,
        bbox=bbox,
    )


class TestGenericChunker:
    def test_chunker_doc_type_is_wildcard(self):
        """GenericChunker's doc_type should be '*'"""
        chunker = GenericChunker()
        assert chunker.doc_type == "*"

    def test_chunker_priority_is_lowest(self):
        """GenericChunker's priority should be 1000 (lowest)"""
        chunker = GenericChunker()
        assert chunker.priority == 1000

    def test_filter_ignored_blocks(self):
        """Should filter out footer and seal block types"""
        chunker = GenericChunker()
        blocks = [
            make_block("Page 1", BlockType.FOOTER),
            make_block("Main content here that is long enough for minimum size requirement", BlockType.PARAGRAPH),
            make_block("印章", BlockType.SEAL),
            make_block("Another paragraph that is also long enough for the minimum chunk size", BlockType.PARAGRAPH),
        ]
        chunks = chunker.transform(blocks)
        # Should only have chunks from PARAGRAPH blocks
        assert len(chunks) >= 1
        assert "Main content" in chunks[0].text or "Another paragraph" in chunks[0].text

    def test_merge_consecutive_text_blocks(self):
        """Consecutive text/paragraph blocks should be merged"""
        chunker = GenericChunker()
        blocks = [
            make_block("First paragraph with enough text to pass the minimum chunk size requirement. ", BlockType.PARAGRAPH),
            make_block("Second paragraph that adds more content to ensure we meet the minimum. ", BlockType.PARAGRAPH),
            make_block("Third paragraph to complete the merged chunk with sufficient length.", BlockType.PARAGRAPH),
        ]
        chunks = chunker.transform(blocks)
        assert len(chunks) == 1
        assert "First paragraph" in chunks[0].text
        assert "Second paragraph" in chunks[0].text
        assert "Third paragraph" in chunks[0].text

    def test_header_creates_boundary(self):
        """HEADER block should create a chunk boundary"""
        chunker = GenericChunker()
        blocks = [
            make_block("Content before title that is long enough for the minimum chunk size requirement", BlockType.PARAGRAPH),
            make_block("Section Title", BlockType.HEADER),
            make_block("Content after title that is also long enough for the minimum chunk size requirement", BlockType.PARAGRAPH),
        ]
        chunks = chunker.transform(blocks)
        # Should create at least 2 chunks due to title boundary
        assert len(chunks) >= 2

    def test_table_block_preserved_intact(self):
        """TABLE block should be preserved as standalone chunk"""
        chunker = GenericChunker()
        blocks = [
            make_block("Before table with enough text for minimum chunk size", BlockType.PARAGRAPH),
            make_block("Table content here that is long enough to meet the minimum chunk size requirement for tables", BlockType.TABLE),
            make_block("After table with enough text for minimum chunk size", BlockType.PARAGRAPH),
        ]
        chunks = chunker.transform(blocks)
        # Table should be its own chunk
        table_chunks = [c for c in chunks if c.chunk_type == "table"]
        assert len(table_chunks) == 1
        assert "Table content" in table_chunks[0].text

    def test_chunk_size_control(self):
        """Chunk size should be controlled (max 1500 chars)"""
        chunker = GenericChunker()
        # Create multiple blocks that together exceed max size
        # Each block is under max size individually
        long_text_1 = "这是一段很长的文本。" * 400  # ~4000 chars
        long_text_2 = "这是另一段很长的文本。" * 400  # ~4000 chars
        blocks = [
            make_block(long_text_1, BlockType.PARAGRAPH),
            make_block(long_text_2, BlockType.PARAGRAPH),
        ]
        chunks = chunker.transform(blocks)
        # First block should create a chunk, second should create another
        # Because adding second block would exceed max size
        assert len(chunks) >= 2
        for chunk in chunks:
            assert len(chunk.text) <= 1500, f"Chunk too long: {len(chunk.text)}"

    def test_empty_blocks_returns_empty_list(self):
        """Empty block list should return empty chunk list"""
        chunker = GenericChunker()
        chunks = chunker.transform([])
        assert chunks == []

    def test_chunk_has_correct_metadata(self):
        """Chunks should have is_generic_chunked metadata set to True"""
        chunker = GenericChunker()
        blocks = [
            make_block("Some content here that is long enough to meet the minimum chunk size requirement", BlockType.PARAGRAPH),
        ]
        chunks = chunker.transform(blocks)
        assert len(chunks) == 1
        assert chunks[0].metadata.get("is_generic_chunked") is True

    def test_chunk_page_range_calculation(self):
        """Chunk page_range should be correctly calculated"""
        chunker = GenericChunker()
        blocks = [
            make_block("Page 0 content that is long enough for minimum chunk size requirement", BlockType.PARAGRAPH, page_no=0),
            make_block("Page 1 content that is long enough for minimum chunk size requirement", BlockType.PARAGRAPH, page_no=1),
            make_block("Page 2 content that is long enough for minimum chunk size requirement", BlockType.PARAGRAPH, page_no=2),
        ]
        chunks = chunker.transform(blocks)
        assert len(chunks) == 1
        # Page range should be 1-indexed [1, 3]
        assert chunks[0].page_range == [1, 3]

    def test_chunk_bbox_union_calculation(self):
        """Chunk bbox_union should be correctly calculated"""
        chunker = GenericChunker()
        blocks = [
            make_block("Block 1 with enough text to meet the minimum chunk size requirement", BlockType.PARAGRAPH, bbox=(10, 20, 100, 50)),
            make_block("Block 2 with enough text to meet the minimum chunk size requirement", BlockType.PARAGRAPH, bbox=(5, 30, 90, 60)),
        ]
        chunks = chunker.transform(blocks)
        assert len(chunks) == 1
        # bbox union: min x0=5, min y0=20, max x1=100, max y1=60
        assert chunks[0].bbox_union == [5, 20, 100, 60]

    def test_short_text_filtered(self):
        """Text shorter than MIN_CHUNK_SIZE should be filtered"""
        chunker = GenericChunker()
        blocks = [
            make_block("Short", BlockType.PARAGRAPH),  # Only 5 chars
        ]
        chunks = chunker.transform(blocks)
        # Should be filtered due to minimum size
        assert len(chunks) == 0

    def test_qa_pair_blocks_merged(self):
        """QA_PAIR blocks should be merged like paragraphs"""
        chunker = GenericChunker()
        blocks = [
            make_block("问：你的名字是什么？这个问题很重要需要详细回答", BlockType.QA_PAIR),
            make_block("答：我叫张三。这是我的回答内容足够长以满足最小块大小要求", BlockType.QA_PAIR),
        ]
        chunks = chunker.transform(blocks)
        assert len(chunks) == 1
        assert "问：" in chunks[0].text
        assert "答：" in chunks[0].text

    def test_list_blocks_merged(self):
        """LIST blocks should be merged like paragraphs"""
        chunker = GenericChunker()
        blocks = [
            make_block("1. 第一项这是列表的第一项内容足够长以满足最小块大小要求", BlockType.LIST),
            make_block("2. 第二项这是列表的第二项内容足够长以满足最小块大小要求", BlockType.LIST),
        ]
        chunks = chunker.transform(blocks)
        assert len(chunks) == 1
        assert "第一项" in chunks[0].text
        assert "第二项" in chunks[0].text
