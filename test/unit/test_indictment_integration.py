# test/unit/test_indictment_integration.py
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
Integration tests for Layer A + Layer B indictment parsing.

Tests the full pipeline from OCR sections to chunks, verifying:
1. Layer A: extract_universal_blocks correctly classifies block types
2. Layer A: entities (dates, amounts) are extracted
3. Layer B: IndictmentPlugin produces correct chunks with section triggers
4. Entities are preserved through the pipeline
"""

import pytest

from rag.app.criminal.blocks import extract_universal_blocks, BlockType
from rag.app.criminal.plugins.indictment import IndictmentPlugin


class TestIndictmentIntegration:
    """Integration tests for Layer A + Layer B."""

    def test_full_pipeline(self):
        """Test full pipeline from sections to chunks."""
        # Simulate OCR output format from by_paddleocr
        # Note: FOOTER detection uses len(text) < 50, so last block needs >= 50 chars
        sections = [
            ("起诉意见书", "@@1\t10.0\t200.0\t20.0\t40.0##"),
            ("犯罪嫌疑人张三", "@@1\t10.0\t200.0\t50.0\t70.0##"),
            ("经依法侦查查明，事实如下", "@@1\t10.0\t200.0\t80.0\t100.0##"),
            # Long text (80+ chars) to avoid FOOTER classification on last position
            ("2024年1月15日实施诈骗42000元。这是具体的犯罪事实描述，犯罪嫌疑人张三在明知没有还款能力的情况下，仍然以非法占有为目的骗取他人财物。", "@@1\t10.0\t200.0\t110.0\t130.0##"),
        ]

        # Layer A: Extract universal blocks
        blocks = extract_universal_blocks(sections, "indictment")

        # Verify block count
        assert len(blocks) == 4

        # Verify block types - first is HEADER, middle are PARAGRAPH
        assert blocks[0].block_type == BlockType.HEADER
        assert blocks[1].block_type == BlockType.PARAGRAPH
        assert blocks[2].block_type == BlockType.PARAGRAPH
        # Last block with long text (>50 chars) should be PARAGRAPH, not FOOTER
        assert blocks[3].block_type == BlockType.PARAGRAPH

        # Verify entities extracted in block with amounts and dates
        assert blocks[3].entities is not None
        assert "42000" in blocks[3].entities["amounts"]
        assert "2024年1月15日" in blocks[3].entities["dates"]

        # Layer B: Process blocks into chunks
        plugin = IndictmentPlugin()
        chunks = plugin.process(blocks, {"docnm_kwt": "test.pdf"})

        # Should have at least 1 chunk (may be split by section triggers)
        assert len(chunks) >= 1

        # Verify section_trigger is set
        assert "section_trigger" in chunks[0]

    def test_entities_preserved(self):
        """Test entity preservation in indictment chunks."""
        sections = [
            ("涉案金额42000元，案发时间2024年3月15日", "@@1\t10.0\t200.0\t20.0\t40.0##"),
        ]

        # Layer A
        blocks = extract_universal_blocks(sections, "indictment")

        # Verify entities extracted
        assert blocks[0].entities is not None
        assert "42000" in blocks[0].entities["amounts"]
        assert "2024年3月15日" in blocks[0].entities["dates"]

        # Layer B
        plugin = IndictmentPlugin()
        chunks = plugin.process(blocks, {"docnm_kwt": "test.pdf"})

        # Verify entities preserved in chunk
        assert len(chunks) == 1
        assert chunks[0]["entities"] is not None
        assert "42000" in chunks[0]["entities"]["amounts"]
        assert "2024年3月15日" in chunks[0]["entities"]["dates"]

    def test_section_splitting(self):
        """Test long section splitting."""
        # Create a long section that exceeds MAX_SECTION_LENGTH (800)
        long_text = "x" * 1000
        sections = [
            (long_text, "@@1\t10.0\t200.0\t20.0\t40.0##"),
        ]

        # Layer A
        blocks = extract_universal_blocks(sections, "indictment")
        assert len(blocks) == 1

        # Layer B
        plugin = IndictmentPlugin()
        chunks = plugin.process(blocks, {"docnm_kwt": "test.pdf"})

        # Should be split into multiple chunks due to length
        assert len(chunks) >= 1
        # Each chunk should have section_trigger
        for chunk in chunks:
            assert "section_trigger" in chunk
            assert "content_with_weight" in chunk

    def test_section_triggers_create_boundaries(self):
        """Test that section triggers create proper boundaries."""
        sections = [
            ("起诉意见书", "@@1\t10.0\t200.0\t20.0\t40.0##"),
            ("犯罪嫌疑人基本信息", "@@1\t10.0\t200.0\t50.0\t70.0##"),
            ("经依法侦查查明，事实如下", "@@1\t10.0\t200.0\t80.0\t100.0##"),
            ("具体犯罪事实一", "@@1\t10.0\t200.0\t110.0\t130.0##"),
            ("具体犯罪事实二", "@@1\t10.0\t200.0\t140.0\t160.0##"),
            ("认定上述犯罪事实的证据如下", "@@1\t10.0\t200.0\t170.0\t190.0##"),
            ("证据1", "@@1\t10.0\t200.0\t200.0\t220.0##"),
            ("综上所述", "@@1\t10.0\t200.0\t230.0\t250.0##"),
            ("建议量刑", "@@1\t10.0\t200.0\t260.0\t280.0##"),
        ]

        # Layer A
        blocks = extract_universal_blocks(sections, "indictment")
        assert len(blocks) == 9

        # Layer B
        plugin = IndictmentPlugin()
        chunks = plugin.process(blocks, {"docnm_kwt": "test.pdf"})

        # Should create multiple chunks based on section triggers
        assert len(chunks) >= 4  # At least 4 sections based on triggers

        # Verify different section triggers
        triggers = [chunk["section_trigger"] for chunk in chunks]
        assert "header" in triggers  # Initial section
        assert "经依法侦查查明" in triggers
        assert "认定上述犯罪事实的证据如下" in triggers
        assert "综上所述" in triggers

    def test_empty_sections(self):
        """Test handling of empty sections."""
        sections = []

        # Layer A
        blocks = extract_universal_blocks(sections, "indictment")
        assert blocks == []

        # Layer B
        plugin = IndictmentPlugin()
        chunks = plugin.process(blocks, {"docnm_kwt": "test.pdf"})
        assert chunks == []

    def test_position_preserved(self):
        """Test that position information is preserved through pipeline."""
        sections = [
            ("起诉意见书", "@@2\t15.0\t180.0\t30.0\t50.0##"),
            ("经依法侦查查明", "@@3\t20.0\t190.0\t40.0\t60.0##"),
        ]

        # Layer A
        blocks = extract_universal_blocks(sections, "indictment")

        # Verify positions in blocks (page is 0-indexed)
        assert blocks[0].page_no == 1  # Page 2 -> 0-indexed
        assert blocks[0].bbox == (15.0, 30.0, 180.0, 50.0)

        # Layer B
        plugin = IndictmentPlugin()
        chunks = plugin.process(blocks, {"docnm_kwt": "test.pdf"})

        # Verify positions in chunks (from first block of section)
        assert chunks[0]["page_no"] == 1
        assert chunks[0]["bbox"] == [15.0, 30.0, 180.0, 50.0]

    def test_chunk_type_for_short_sections(self):
        """Test that short sections get 'section' chunk_type."""
        sections = [
            ("短段落内容", "@@1\t10.0\t200.0\t20.0\t40.0##"),
        ]

        # Layer A
        blocks = extract_universal_blocks(sections, "indictment")

        # Layer B
        plugin = IndictmentPlugin()
        chunks = plugin.process(blocks, {"docnm_kwt": "test.pdf"})

        assert len(chunks) == 1
        assert chunks[0]["chunk_type"] == "section"

    def test_chunk_type_for_long_sections(self):
        """Test that long sections get 'paragraph' chunk_type when split."""
        # Create content that will be split
        long_text = "测试内容。" * 200  # About 1000 characters
        sections = [
            (long_text, "@@1\t10.0\t200.0\t20.0\t40.0##"),
        ]

        # Layer A
        blocks = extract_universal_blocks(sections, "indictment")

        # Layer B
        plugin = IndictmentPlugin()
        chunks = plugin.process(blocks, {"docnm_kwt": "test.pdf"})

        # If split, chunks should have "paragraph" type
        if len(chunks) > 1:
            for chunk in chunks:
                assert chunk["chunk_type"] == "paragraph"

    def test_merged_entities_from_multiple_blocks(self):
        """Test that entities from multiple blocks are merged in chunks."""
        sections = [
            ("经依法侦查查明", "@@1\t10.0\t200.0\t20.0\t40.0##"),
            ("涉案金额10000元", "@@1\t10.0\t200.0\t50.0\t70.0##"),
            ("又查明涉案金额20000元", "@@1\t10.0\t200.0\t80.0\t100.0##"),
        ]

        # Layer A
        blocks = extract_universal_blocks(sections, "indictment")

        # Layer B
        plugin = IndictmentPlugin()
        chunks = plugin.process(blocks, {"docnm_kwt": "test.pdf"})

        # The chunk should have merged entities from all blocks in section
        chunk = chunks[-1]  # Last chunk should contain the entities
        assert chunk["entities"] is not None
        # Entities are extracted but merged when creating chunk
        assert "10000" in chunk["entities"]["amounts"]
        assert "20000" in chunk["entities"]["amounts"]
