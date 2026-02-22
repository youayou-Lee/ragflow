# test/unit/test_plugins_base.py
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
Tests for ParserPlugin base class.
"""

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
