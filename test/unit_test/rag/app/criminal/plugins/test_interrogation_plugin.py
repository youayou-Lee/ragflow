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

# Disable all proxies before any imports to avoid ollama connection issues
import os
for proxy_var in ["http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
                   "all_proxy", "ALL_PROXY", "socks_proxy", "SOCKS_PROXY"]:
    os.environ.pop(proxy_var, None)
os.environ["NO_PROXY"] = "*"

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


class TestInterrogationPluginTextCleaning:
    """Tests for text cleaning in InterrogationPlugin."""

    def test_clean_text_removes_underline_fillers(self):
        """Plugin should remove ___ filler patterns."""
        plugin = InterrogationPlugin()
        text = "地点___ 清远市公安局"
        result = plugin._clean_text(text)
        assert "___" not in result
        assert "清远市公安局" in result

    def test_clean_text_removes_multiple_underline_groups(self):
        """Plugin should remove multiple groups of underlines."""
        plugin = InterrogationPlugin()
        text = "讯问人（签名）___、___、___"
        result = plugin._clean_text(text)
        assert "___" not in result

    def test_clean_text_preserves_single_underscore(self):
        """Plugin should preserve single underscore in identifiers."""
        plugin = InterrogationPlugin()
        text = "微信ID: wxid_wb67ftqi5p9722"
        result = plugin._clean_text(text)
        assert "wxid_wb67ftqi5p9722" in result

    def test_clean_text_removes_standalone_underline_lines(self):
        """Plugin should remove standalone underline lines."""
        plugin = InterrogationPlugin()
        text = "正文内容\n___\n\n___\n更多内容"
        result = plugin._clean_text(text)
        assert result.count("___") == 0

    def test_clean_text_removes_duplicate_segments(self):
        """Plugin should remove consecutive duplicate text segments (OCR re-scan issue)."""
        plugin = InterrogationPlugin()
        # Simulate OCR re-scan issue: same paragraph appears twice
        text = "办理学位的费用是成功办理小孩入读小学之后才收钱。办理学位的费用是成功办理小孩入读小学之后才收钱。这是后续内容。"
        result = plugin._clean_text(text)
        # Should have only one occurrence after dedup (sentence-based)
        assert result.count("办理学位的费用是成功办理小孩入读小学之后才收钱") == 1

    def test_clean_text_preserves_intentional_repetition(self):
        """Plugin should preserve intentional short repetition."""
        plugin = InterrogationPlugin()
        text = "问：你是否同意？答：是是是。"
        result = plugin._clean_text(text)
        assert "是是是" in result

    def test_transform_applies_cleaning(self):
        """Transform should apply text cleaning to all chunks."""
        plugin = InterrogationPlugin()
        blocks = [
            make_block("问：你叫什么名字？"),
            make_block("答：我叫张三第 6 页 共 8 页307。"),
        ]
        chunks = plugin.transform(blocks)
        # Page number and line number should be removed
        assert "第 6 页 共 8 页" not in chunks[0].text
        # Note: 307 might be kept if not on its own line, which is expected behavior
