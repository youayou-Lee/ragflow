# test/unit/test_scene_investigation_integration.py
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
Integration tests for Layer A + Layer B scene investigation parsing.

Tests the full pipeline from OCR sections to chunks, verifying:
1. Layer A: extract_universal_blocks correctly classifies block types
2. Layer A: entities (dates, amounts) are extracted
3. Layer B: SceneInvestigationPlugin produces correct chunks with section triggers
4. Entities are preserved through the pipeline
"""

import pytest

from rag.app.criminal.blocks import extract_universal_blocks, BlockType
from rag.app.criminal.plugins.scene_investigation import SceneInvestigationPlugin


class TestSceneInvestigationIntegration:
    """Integration tests for Layer A + Layer B."""

    def test_full_pipeline(self):
        """Test full pipeline from sections to chunks."""
        # Simulate OCR output format
        sections = [
            ("勘查号：K4418025400002021020012", "@@1\t10.0\t200.0\t20.0\t40.0##"),
            ("现场勘验检查笔录", "@@1\t10.0\t200.0\t50.0\t70.0##"),
            ("现场勘验单位：清远市公安局下廓派出所", "@@1\t10.0\t200.0\t80.0\t100.0##"),
            # Long text to avoid FOOTER classification
            ("2021年2月1日进行现场勘查，涉案金额42000元。这是具体的案件描述内容，包含了案件发生的时间、地点和相关人员信息。", "@@1\t10.0\t200.0\t110.0\t130.0##"),
        ]

        # Layer A: Extract universal blocks
        blocks = extract_universal_blocks(sections, "scene_investigation")

        # Verify block count
        assert len(blocks) == 4

        # Verify block types
        assert blocks[0].block_type == BlockType.HEADER  # First block, short
        assert blocks[1].block_type == BlockType.PARAGRAPH  # Title (classified as paragraph by layout rules)
        assert blocks[2].block_type == BlockType.PARAGRAPH
        assert blocks[3].block_type == BlockType.PARAGRAPH

        # Layer B: Process blocks into chunks
        plugin = SceneInvestigationPlugin()
        chunks = plugin.process(blocks, {"docnm_kwt": "test.pdf"})

        # Should have multiple chunks based on triggers
        assert len(chunks) >= 1
        assert "section_trigger" in chunks[0]

    def test_entities_preserved(self):
        """Test entity preservation in scene investigation chunks."""
        sections = [
            ("涉案金额42000元，案发时间2021年2月1日", "@@1\t10.0\t200.0\t20.0\t40.0##"),
        ]

        # Layer A
        blocks = extract_universal_blocks(sections, "scene_investigation")

        # Verify entities extracted
        assert blocks[0].entities is not None
        assert "42000" in blocks[0].entities["amounts"]
        assert "2021年2月1日" in blocks[0].entities["dates"]

        # Layer B
        plugin = SceneInvestigationPlugin()
        chunks = plugin.process(blocks, {"docnm_kwt": "test.pdf"})

        # Verify entities preserved
        assert len(chunks) == 1
        assert chunks[0]["entities"] is not None
        assert "42000" in chunks[0]["entities"]["amounts"]
        assert "2021年2月1日" in chunks[0]["entities"]["dates"]

    def test_section_splitting_long_content(self):
        """Test long section splitting."""
        # Create a long section that exceeds MAX_SECTION_LENGTH
        long_text = "x" * 1000
        sections = [
            (long_text, "@@1\t10.0\t200.0\t20.0\t40.0##"),
        ]

        # Layer A
        blocks = extract_universal_blocks(sections, "scene_investigation")
        assert len(blocks) == 1

        # Layer B
        plugin = SceneInvestigationPlugin()
        chunks = plugin.process(blocks, {"docnm_kwt": "test.pdf"})

        # Should be split into multiple chunks
        assert len(chunks) >= 1
        for chunk in chunks:
            assert "section_trigger" in chunk
            assert "content_with_weight" in chunk

    def test_section_triggers_create_boundaries(self):
        """Test that section triggers create proper boundaries."""
        sections = [
            ("勘查号：K4418025400002021020012", "@@1\t10.0\t200.0\t20.0\t40.0##"),
            ("现场勘验单位：清远市公安局", "@@1\t10.0\t200.0\t50.0\t70.0##"),
            ("现场勘验情况：现场方位描述", "@@1\t10.0\t200.0\t80.0\t100.0##"),
            ("案发现场情况：案件详细描述", "@@1\t10.0\t200.0\t110.0\t130.0##"),
            ("现场勘验人员：签名信息", "@@1\t10.0\t200.0\t140.0\t160.0##"),
        ]

        # Layer A
        blocks = extract_universal_blocks(sections, "scene_investigation")
        assert len(blocks) == 5

        # Layer B
        plugin = SceneInvestigationPlugin()
        chunks = plugin.process(blocks, {"docnm_kwt": "test.pdf"})

        # Should create multiple chunks based on section triggers
        assert len(chunks) >= 3

        # Verify different section triggers
        triggers = [chunk["section_trigger"] for chunk in chunks]
        assert "header" in triggers  # Initial section

    def test_empty_sections(self):
        """Test handling of empty sections."""
        sections = []

        # Layer A
        blocks = extract_universal_blocks(sections, "scene_investigation")
        assert blocks == []

        # Layer B
        plugin = SceneInvestigationPlugin()
        chunks = plugin.process(blocks, {"docnm_kwt": "test.pdf"})
        assert chunks == []

    def test_position_preserved(self):
        """Test that position information is preserved through pipeline."""
        sections = [
            ("勘查号：K123", "@@2\t15.0\t180.0\t30.0\t50.0##"),
            ("现场勘验单位：公安局", "@@3\t20.0\t190.0\t40.0\t60.0##"),
        ]

        # Layer A
        blocks = extract_universal_blocks(sections, "scene_investigation")

        # Verify positions (page is 0-indexed)
        assert blocks[0].page_no == 1  # Page 2 -> 0-indexed
        assert blocks[0].bbox == (15.0, 30.0, 180.0, 50.0)

        # Layer B
        plugin = SceneInvestigationPlugin()
        chunks = plugin.process(blocks, {"docnm_kwt": "test.pdf"})

        # Verify positions in chunks
        assert chunks[0]["page_no"] == 1
        assert chunks[0]["bbox"] == [15.0, 30.0, 180.0, 50.0]
