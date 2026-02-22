# test/unit/test_interrogation_integration.py
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
Integration tests for Layer A + Layer B interrogation parsing.

Tests the full pipeline from OCR sections to chunks, verifying:
1. Layer A: extract_universal_blocks correctly classifies block types
2. Layer A: entities (dates, amounts) are extracted
3. Layer B: InterrogationPlugin produces correct chunks
4. Entities are preserved through the pipeline
"""

import pytest

from rag.app.criminal.blocks import extract_universal_blocks, BlockType
from rag.app.criminal.plugins.interrogation import InterrogationPlugin


class TestInterrogationIntegration:
    """Integration tests for Layer A + Layer B."""

    def test_full_pipeline(self):
        """Test full pipeline from sections to chunks."""
        # Simulate OCR output format from by_paddleocr
        sections = [
            ("讯问笔录", "@@1\t10.0\t200.0\t20.0\t40.0##"),
            ("时间：2024年1月15日", "@@1\t10.0\t200.0\t50.0\t70.0##"),
            ("问：你叫什么名字？", "@@1\t10.0\t200.0\t80.0\t100.0##"),
            ("答：我叫张三", "@@1\t10.0\t200.0\t110.0\t130.0##"),
            ("问：收到42000元吗？", "@@1\t10.0\t200.0\t140.0\t160.0##"),
            ("答：是的，收到了42000元", "@@1\t10.0\t200.0\t170.0\t190.0##"),
        ]

        # Layer A: Extract universal blocks
        blocks = extract_universal_blocks(sections, "interrogation")

        # Verify block count
        assert len(blocks) == 6

        # Verify block types
        # - First block at position "first" is HEADER
        # - Second block at position "middle" is PARAGRAPH (default)
        # - QA blocks are QA_PAIR
        assert blocks[0].block_type == BlockType.HEADER
        assert blocks[1].block_type == BlockType.PARAGRAPH  # middle position
        assert blocks[2].block_type == BlockType.QA_PAIR
        assert blocks[3].block_type == BlockType.QA_PAIR
        assert blocks[4].block_type == BlockType.QA_PAIR
        assert blocks[5].block_type == BlockType.QA_PAIR

        # Verify entities extracted in blocks
        assert blocks[1].entities is not None
        assert "2024年1月15日" in blocks[1].entities["dates"]

        # Verify entities in QA blocks
        assert blocks[4].entities is not None
        assert "42000" in blocks[4].entities["amounts"]

        # Layer B: Process blocks into chunks
        plugin = InterrogationPlugin()
        chunks = plugin.process(blocks, {"docnm_kwd": "test.pdf"})

        # Should have 1 header + 2 QA pairs (PARAGRAPH blocks are ignored)
        assert len(chunks) == 3

        # Verify chunk types
        assert chunks[0]["chunk_type"] == "header"
        assert chunks[1]["chunk_type"] == "qa_pair"
        assert chunks[2]["chunk_type"] == "qa_pair"

        # Verify qa_index in QA chunks
        assert chunks[1]["qa_index"] == 0
        assert chunks[2]["qa_index"] == 1

    def test_entities_preserved_in_chunks(self):
        """Test that entities are preserved through the pipeline."""
        sections = [
            ("讯问时间：2024年3月20日", "@@1\t10.0\t200.0\t20.0\t40.0##"),
            ("问：你收到100000元吗？", "@@1\t10.0\t200.0\t50.0\t70.0##"),
            ("答：是的，我收到了100000元", "@@1\t10.0\t200.0\t80.0\t100.0##"),
        ]

        # Layer A
        blocks = extract_universal_blocks(sections, "interrogation")

        # Verify entities extracted
        assert blocks[0].entities is not None
        assert "2024年3月20日" in blocks[0].entities["dates"]

        # Layer B
        plugin = InterrogationPlugin()
        chunks = plugin.process(blocks, {"docnm_kwd": "test.pdf"})

        # Verify entities in header chunk
        assert chunks[0]["entities"] is not None
        assert "2024年3月20日" in chunks[0]["entities"]["dates"]

        # Verify entities in QA chunk
        assert chunks[1]["entities"] is not None
        assert "100000" in chunks[1]["entities"]["amounts"]

    def test_header_and_qa_structure(self):
        """Test that header + QA pair structure is maintained."""
        sections = [
            ("讯问笔录", "@@1\t10.0\t200.0\t20.0\t40.0##"),
            ("被讯问人：张三", "@@1\t10.0\t200.0\t50.0\t70.0##"),
            ("时间：2024年1月15日", "@@1\t10.0\t200.0\t80.0\t100.0##"),
            ("问：姓名？", "@@1\t10.0\t200.0\t110.0\t130.0##"),
            ("答：张三", "@@1\t10.0\t200.0\t140.0\t160.0##"),
            ("问：年龄？", "@@1\t10.0\t200.0\t170.0\t190.0##"),
            ("答：25岁", "@@1\t10.0\t200.0\t200.0\t220.0##"),
            ("问：住址？", "@@1\t10.0\t200.0\t230.0\t250.0##"),
            ("答：北京市朝阳区", "@@1\t10.0\t200.0\t260.0\t280.0##"),
        ]

        # Layer A
        blocks = extract_universal_blocks(sections, "interrogation")

        # Only first block at position "first" is HEADER
        # Other non-QA blocks are PARAGRAPH by default
        assert blocks[0].block_type == BlockType.HEADER
        assert blocks[1].block_type == BlockType.PARAGRAPH  # middle position
        assert blocks[2].block_type == BlockType.PARAGRAPH  # middle position

        # Verify QA pairs detected
        qa_blocks = [b for b in blocks if b.block_type == BlockType.QA_PAIR]
        assert len(qa_blocks) == 6

        # Layer B
        plugin = InterrogationPlugin()
        chunks = plugin.process(blocks, {"docnm_kwd": "test.pdf"})

        # Should have 1 header + 3 QA pairs (PARAGRAPH blocks are ignored)
        assert len(chunks) == 4
        assert chunks[0]["chunk_type"] == "header"
        assert chunks[1]["chunk_type"] == "qa_pair"
        assert chunks[2]["chunk_type"] == "qa_pair"
        assert chunks[3]["chunk_type"] == "qa_pair"

    def test_multiple_answers_merged(self):
        """Test that multiple answer blocks are merged into one QA pair."""
        sections = [
            ("问：详细描述一下经过？", "@@1\t10.0\t200.0\t20.0\t40.0##"),
            ("答：2024年1月1日", "@@1\t10.0\t200.0\t50.0\t70.0##"),
            ("答：我去了银行", "@@1\t10.0\t200.0\t80.0\t100.0##"),
            ("答：取了50000元", "@@1\t10.0\t200.0\t110.0\t130.0##"),
        ]

        # Layer A
        blocks = extract_universal_blocks(sections, "interrogation")

        # Layer B
        plugin = InterrogationPlugin()
        chunks = plugin.process(blocks, {"docnm_kwd": "test.pdf"})

        # Should merge into 1 QA pair
        assert len(chunks) == 1
        assert chunks[0]["chunk_type"] == "qa_pair"

        # Content should include all answer blocks
        content = chunks[0]["content_with_weight"]
        assert "问：详细描述一下经过？" in content
        assert "答：2024年1月1日" in content
        assert "答：我去了银行" in content
        assert "答：取了50000元" in content

        # Entities should be merged from all blocks
        assert chunks[0]["entities"] is not None
        assert "2024年1月1日" in chunks[0]["entities"]["dates"]
        assert "50000" in chunks[0]["entities"]["amounts"]

    def test_position_preserved(self):
        """Test that position information is preserved through pipeline."""
        sections = [
            ("讯问笔录", "@@2\t15.0\t180.0\t30.0\t50.0##"),
            ("问：姓名？", "@@3\t20.0\t190.0\t40.0\t60.0##"),
            ("答：张三", "@@3\t20.0\t190.0\t70.0\t90.0##"),
        ]

        # Layer A
        blocks = extract_universal_blocks(sections, "interrogation")

        # Verify positions in blocks
        assert blocks[0].page_no == 1  # Page 2 -> 0-indexed
        assert blocks[0].bbox == (15.0, 30.0, 180.0, 50.0)

        # Layer B
        plugin = InterrogationPlugin()
        chunks = plugin.process(blocks, {"docnm_kwd": "test.pdf"})

        # Verify positions in header chunk
        assert chunks[0]["page_no"] == 1
        assert chunks[0]["bbox"] == [15.0, 30.0, 180.0, 50.0]

        # Verify positions in QA chunk (from question block)
        assert chunks[1]["page_no"] == 2  # Page 3 -> 0-indexed
        assert chunks[1]["bbox"] == [20.0, 40.0, 190.0, 60.0]

    def test_empty_sections(self):
        """Test handling of empty sections."""
        sections = []

        # Layer A
        blocks = extract_universal_blocks(sections, "interrogation")
        assert blocks == []

        # Layer B
        plugin = InterrogationPlugin()
        chunks = plugin.process(blocks, {"docnm_kwd": "test.pdf"})
        assert chunks == []

    def test_only_header_blocks(self):
        """Test document with only header blocks (single block case)."""
        # When there's only one section, it gets position "first"
        # and short text becomes HEADER
        sections = [
            ("讯问笔录", "@@1\t10.0\t200.0\t20.0\t40.0##"),
        ]

        # Layer A
        blocks = extract_universal_blocks(sections, "interrogation")
        assert all(b.block_type == BlockType.HEADER for b in blocks)

        # Layer B
        plugin = InterrogationPlugin()
        chunks = plugin.process(blocks, {"docnm_kwd": "test.pdf"})

        # Should produce single header chunk
        assert len(chunks) == 1
        assert chunks[0]["chunk_type"] == "header"
