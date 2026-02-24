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

"""Unit tests for InterrogationPlugin."""

import pytest
from rag.app.criminal.plugins.interrogation_plugin import InterrogationPlugin
from rag.app.naive import UniversalBlock, BlockType


def make_block(text: str, block_type: BlockType = BlockType.QA_PAIR,
               page_no: int = 0, bbox: tuple = (0, 0, 100, 50)) -> UniversalBlock:
    """Helper to create a UniversalBlock for testing."""
    return UniversalBlock(block_type=block_type, text=text, page_no=page_no, bbox=bbox)


class TestInterrogationPlugin:
    """Tests for InterrogationPlugin."""

    def test_doc_type(self):
        """Plugin should handle interrogation_record type."""
        plugin = InterrogationPlugin()
        assert plugin.doc_type == "interrogation_record"

    def test_single_qa_pair(self):
        """Single Q/A pair should generate one qa_pair chunk."""
        plugin = InterrogationPlugin()
        blocks = [
            make_block("问：你叫什么名字？"),
            make_block("答：我叫张三。"),
        ]
        chunks = plugin.transform(blocks)
        assert len(chunks) == 1
        assert chunks[0].chunk_type == "qa_pair"
        assert "问：你叫什么名字？" in chunks[0].text
        assert "答：我叫张三。" in chunks[0].text

    def test_multiple_qa_pairs(self):
        """Multiple Q/A pairs should generate multiple qa_pair chunks."""
        plugin = InterrogationPlugin()
        blocks = [
            make_block("问：你叫什么名字？"),
            make_block("答：我叫张三。"),
            make_block("问：你住在哪里？"),
            make_block("答：我住在北京。"),
        ]
        chunks = plugin.transform(blocks)
        assert len(chunks) == 2
        assert all(c.chunk_type == "qa_pair" for c in chunks)

    def test_question_with_multiple_answers(self):
        """One question with multiple answers should merge into one qa_pair."""
        plugin = InterrogationPlugin()
        blocks = [
            make_block("问：描述一下经过？"),
            make_block("答：那天我在路上走着，"),
            make_block("答：然后看到了一个钱包。"),
        ]
        chunks = plugin.transform(blocks)
        assert len(chunks) == 1
        assert chunks[0].chunk_type == "qa_pair"
        assert "走着" in chunks[0].text
        assert "钱包" in chunks[0].text

    def test_header_block_as_metadata(self):
        """HEADER block should be metadata, not a separate chunk."""
        plugin = InterrogationPlugin()
        blocks = [
            make_block("讯问笔录", BlockType.HEADER),
            make_block("问：你是谁？"),
            make_block("答：我是证人。"),
        ]
        chunks = plugin.transform(blocks)
        qa_chunks = [c for c in chunks if c.chunk_type == "qa_pair"]
        assert len(qa_chunks) == 1

    def test_empty_blocks(self):
        """Empty block list should return empty chunk list."""
        plugin = InterrogationPlugin()
        chunks = plugin.transform([])
        assert chunks == []
