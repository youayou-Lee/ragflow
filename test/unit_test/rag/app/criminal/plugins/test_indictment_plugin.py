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

"""Unit tests for IndictmentPlugin."""

import pytest
from rag.app.criminal.plugins.indictment_plugin import IndictmentPlugin
from rag.app.naive import UniversalBlock, BlockType


def make_block(text: str, block_type: BlockType = BlockType.PARAGRAPH,
               page_no: int = 0, bbox: tuple = (0, 0, 100, 50)) -> UniversalBlock:
    """Helper to create a UniversalBlock for testing."""
    return UniversalBlock(block_type=block_type, text=text, page_no=page_no, bbox=bbox)


class TestIndictmentPlugin:
    """Tests for IndictmentPlugin."""

    def test_doc_type(self):
        """Plugin should handle indictment_opinion type."""
        plugin = IndictmentPlugin()
        assert plugin.doc_type == "indictment_opinion"

    def test_section_detection(self):
        """Should identify key section triggers."""
        plugin = IndictmentPlugin()
        blocks = [
            make_block("起诉意见书", BlockType.HEADER),
            make_block("犯罪嫌疑人张三，男，1990年出生，住北京市朝阳区，无业。"),
            make_block("经依法侦查查明："),
            make_block("2023年5月，犯罪嫌疑人张三在北京市朝阳区实施诈骗行为，骗取受害人李四人民币5万元整。"),
            make_block("认定上述犯罪事实的证据如下："),
            make_block("1. 受害人李四的陈述，证实被张三诈骗的事实经过。"),
            make_block("2. 银行转账记录，证实李四向张三转账5万元。"),
        ]
        chunks = plugin.transform(blocks)
        # Should have multiple sections
        assert len(chunks) >= 2

    def test_paragraph_chunking(self):
        """Sections should be split by paragraphs."""
        plugin = IndictmentPlugin()
        long_text = "这是一段很长的文字。" * 200  # ~1600 chars
        blocks = [
            make_block("经依法侦查查明："),
            make_block(long_text),
        ]
        chunks = plugin.transform(blocks)
        # Should split long text into multiple chunks
        for chunk in chunks:
            if chunk.chunk_type == "paragraph":
                assert len(chunk.text) <= 1500

    def test_empty_blocks(self):
        """Empty block list should return empty chunk list."""
        plugin = IndictmentPlugin()
        chunks = plugin.transform([])
        assert chunks == []
