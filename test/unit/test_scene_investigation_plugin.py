# test/unit/test_scene_investigation_plugin.py
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
Unit tests for SceneInvestigationPlugin.
"""

import pytest

from rag.app.criminal.blocks import UniversalBlock, BlockType
from rag.app.criminal.plugins.scene_investigation import SceneInvestigationPlugin


class TestSceneInvestigationPlugin:
    """Tests for SceneInvestigationPlugin basic functionality."""

    def test_doc_type(self):
        """Test that doc_type returns correct identifier."""
        plugin = SceneInvestigationPlugin()
        assert plugin.doc_type == "scene_investigation"

    def test_process_empty_blocks(self):
        """Test that empty blocks return empty chunks."""
        plugin = SceneInvestigationPlugin()
        chunks = plugin.process([], {"docnm_kwt": "test.pdf"})
        assert chunks == []


class TestSceneInvestigationSectionBoundaries:
    """Tests for section boundary detection."""

    def test_find_sections_basic(self):
        """Test basic section boundary detection."""
        plugin = SceneInvestigationPlugin()
        blocks = [
            UniversalBlock(BlockType.HEADER, "勘查号：K4418025400002021020012", 0, (0, 0, 100, 50)),
            UniversalBlock(BlockType.PARAGRAPH, "现场勘验单位：清远市公安局下廓派出所", 0, (0, 50, 100, 100)),
            UniversalBlock(BlockType.PARAGRAPH, "普通内容段落", 0, (0, 100, 100, 150)),
        ]

        sections = plugin._find_sections(blocks)

        assert len(sections) >= 2
        assert sections[0][2] == "header"
        assert "现场勘验单位" in sections[1][2]

    def test_find_sections_with_multiple_triggers(self):
        """Test detection with multiple trigger patterns."""
        plugin = SceneInvestigationPlugin()
        blocks = [
            UniversalBlock(BlockType.HEADER, "勘查号：K123", 0, (0, 0, 100, 50)),
            UniversalBlock(BlockType.PARAGRAPH, "现场勘验情况：详情描述", 0, (0, 50, 100, 100)),
            UniversalBlock(BlockType.PARAGRAPH, "现场勘验人员：张三", 0, (0, 100, 100, 150)),
        ]

        sections = plugin._find_sections(blocks)

        assert len(sections) == 3
        triggers = [s[2] for s in sections]
        assert "勘查号：" in triggers[0]
        assert "现场勘验情况：" in triggers[1]
        assert "现场勘验人员：" in triggers[2]

    def test_process_creates_chunks_by_section(self):
        """Test that process creates chunks based on sections."""
        plugin = SceneInvestigationPlugin()
        blocks = [
            UniversalBlock(BlockType.HEADER, "勘查号：K4418025400002021020012", 0, (0, 0, 100, 50)),
            UniversalBlock(BlockType.PARAGRAPH, "现场勘验单位：清远市公安局", 0, (0, 50, 100, 100)),
            UniversalBlock(BlockType.PARAGRAPH, "普通内容", 0, (0, 100, 100, 150)),
        ]

        chunks = plugin.process(blocks, {"docnm_kwt": "test.pdf"})

        assert len(chunks) >= 2
        assert all("section_trigger" in chunk for chunk in chunks)
        assert all("content_with_weight" in chunk for chunk in chunks)


class TestSceneInvestigationEntities:
    """Tests for entity preservation."""

    def test_entities_preserved_in_chunk(self):
        """Test that entities are preserved in chunks."""
        plugin = SceneInvestigationPlugin()
        blocks = [
            UniversalBlock(
                BlockType.PARAGRAPH,
                "涉案金额42000元，日期2021年2月1日",
                0, (0, 0, 100, 50),
                entities={"amounts": ["42000"], "dates": ["2021年2月1日"]}
            ),
        ]

        chunks = plugin.process(blocks, {"docnm_kwt": "test.pdf"})

        assert len(chunks) == 1
        assert chunks[0]["entities"] is not None
        assert "42000" in chunks[0]["entities"]["amounts"]
        assert "2021年2月1日" in chunks[0]["entities"]["dates"]

    def test_entities_merged_from_multiple_blocks(self):
        """Test that entities from multiple blocks are merged."""
        plugin = SceneInvestigationPlugin()
        blocks = [
            UniversalBlock(
                BlockType.PARAGRAPH,
                "金额10000元",
                0, (0, 0, 100, 50),
                entities={"amounts": ["10000"], "dates": []}
            ),
            UniversalBlock(
                BlockType.PARAGRAPH,
                "金额20000元",
                0, (0, 50, 100, 100),
                entities={"amounts": ["20000"], "dates": []}
            ),
        ]

        chunks = plugin.process(blocks, {"docnm_kwt": "test.pdf"})

        # Last chunk should have merged entities
        chunk = chunks[-1]
        assert chunk["entities"] is not None
        assert "10000" in chunk["entities"]["amounts"]
        assert "20000" in chunk["entities"]["amounts"]

    def test_no_entities_when_empty(self):
        """Test that entities field is empty when no entities present."""
        plugin = SceneInvestigationPlugin()
        blocks = [
            UniversalBlock(BlockType.PARAGRAPH, "普通文本无实体", 0, (0, 0, 100, 50)),
        ]

        chunks = plugin.process(blocks, {"docnm_kwt": "test.pdf"})

        assert len(chunks) == 1
        # Entities should be empty dict when no entities
        assert chunks[0].get("entities", {}) == {}
