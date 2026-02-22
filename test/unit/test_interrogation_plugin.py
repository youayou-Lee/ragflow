# test/unit/test_interrogation_plugin.py
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
Tests for InterrogationPlugin.
"""

import pytest
from rag.app.criminal.plugins.interrogation import InterrogationPlugin
from rag.app.criminal.blocks import UniversalBlock, BlockType


class TestInterrogationPlugin:
    """Test InterrogationPlugin."""

    def test_doc_type(self):
        """Test doc_type property."""
        plugin = InterrogationPlugin()
        assert plugin.doc_type == "interrogation"

    def test_process_empty_blocks(self):
        """Test processing empty block list."""
        plugin = InterrogationPlugin()
        chunks = plugin.process([], {"docnm_kwd": "test.pdf"})
        assert chunks == []

    def test_process_header_blocks(self):
        """Test processing header blocks."""
        plugin = InterrogationPlugin()
        blocks = [
            UniversalBlock(BlockType.HEADER, "讯问笔录", 0, (0, 0, 100, 50)),
            UniversalBlock(BlockType.HEADER, "时间：2024年1月", 0, (0, 50, 100, 100)),
        ]
        chunks = plugin.process(blocks, {"docnm_kwd": "test.pdf"})
        assert len(chunks) == 1
        assert chunks[0]["chunk_type"] == "header"

    def test_process_qa_blocks(self):
        """Test processing QA pair blocks."""
        plugin = InterrogationPlugin()
        blocks = [
            UniversalBlock(BlockType.QA_PAIR, "问：你叫什么名字？", 0, (0, 0, 100, 50)),
            UniversalBlock(BlockType.QA_PAIR, "答：我叫张三", 0, (0, 50, 100, 100)),
            UniversalBlock(BlockType.QA_PAIR, "问：住在哪里？", 0, (0, 100, 100, 150)),
            UniversalBlock(BlockType.QA_PAIR, "答：北京", 0, (0, 150, 100, 200)),
        ]
        chunks = plugin.process(blocks, {"docnm_kwd": "test.pdf"})
        # Should merge into 2 QA pairs
        assert len(chunks) == 2
        assert all(c["chunk_type"] == "qa_pair" for c in chunks)
        assert chunks[0]["qa_index"] == 0
        assert chunks[1]["qa_index"] == 1

    def test_process_header_and_qa(self):
        """Test processing both header and QA blocks."""
        plugin = InterrogationPlugin()
        blocks = [
            UniversalBlock(BlockType.HEADER, "讯问笔录", 0, (0, 0, 100, 50)),
            UniversalBlock(BlockType.QA_PAIR, "问：姓名？", 0, (0, 50, 100, 100)),
            UniversalBlock(BlockType.QA_PAIR, "答：张三", 0, (0, 100, 100, 150)),
        ]
        chunks = plugin.process(blocks, {"docnm_kwd": "test.pdf"})
        assert len(chunks) == 2
        assert chunks[0]["chunk_type"] == "header"
        assert chunks[1]["chunk_type"] == "qa_pair"
