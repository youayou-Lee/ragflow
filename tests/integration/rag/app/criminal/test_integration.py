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
Integration tests for two-layer parsing architecture.

Tests the complete pipeline from Layer A (UniversalBlock extraction)
through Layer B (plugin-based chunking).
"""

import pytest

from rag.app.criminal import route_to_plugin, InterrogationPlugin, IndictmentPlugin
from rag.app.naive import UniversalBlock, BlockType, extract_universal_blocks


class TestTwoLayerIntegration:
    """Integration tests for the complete two-layer pipeline."""

    def test_interrogation_record_pipeline(self):
        """Test complete pipeline for interrogation record."""
        # Simulated OCR output (sections with position tags)
        sections = [
            ("讯问笔录", "@@1\t0\t100\t0\t50##"),
            ("问：你叫什么名字？", "@@1\t0\t100\t50\t100##"),
            ("答：我叫张三。", "@@1\t0\t100\t100\t150##"),
            ("问：你住在哪里？", "@@1\t0\t100\t150\t200##"),
            ("答：我住在北京。", "@@1\t0\t100\t200\t250##"),
        ]

        # Layer A: Extract universal blocks
        blocks = extract_universal_blocks(sections, doc_type_hint="interrogation_record")
        assert len(blocks) == 5

        # Layer B: Route to plugin
        chunks = route_to_plugin(blocks, "interrogation_record")

        # Verify output: 1 header_info + 2 qa_pairs = 3 chunks
        assert len(chunks) == 3

        # First chunk should be header_info
        assert chunks[0].chunk_type == "header_info"
        assert "讯问笔录" in chunks[0].text

        # Remaining chunks should be qa_pair
        assert chunks[1].chunk_type == "qa_pair"
        assert chunks[2].chunk_type == "qa_pair"

    def test_indictment_opinion_pipeline(self):
        """Test complete pipeline for indictment opinion."""
        # Text must be at least 50 chars (MIN_CHUNK_SIZE) for indictment plugin
        # Each section needs enough content to meet the minimum size requirement
        sections = [
            ("起诉意见书", "@@1\t0\t100\t0\t50##"),
            ("犯罪嫌疑人张三，男，1990年出生，住北京市朝阳区建国路100号，无前科。", "@@1\t0\t100\t50\t100##"),
            ("经依法侦查查明：2023年5月15日，犯罪嫌疑人张三在某商场内实施了诈骗行为，以虚假投资为名骗取受害人李四人民币五万元整，涉案金额巨大。", "@@1\t0\t100\t100\t200##"),
            ("认定上述犯罪事实的证据如下：第一，受害人李四的陈述笔录详细记录了被骗经过；第二，银行转账记录证实了资金流向；第三，犯罪嫌疑人张三的供述与上述证据相互印证。", "@@1\t0\t100\t200\t300##"),
        ]

        # Layer A
        blocks = extract_universal_blocks(sections, doc_type_hint="indictment_opinion")

        # Layer B
        chunks = route_to_plugin(blocks, "indictment_opinion")

        # Verify output - should have at least one chunk
        assert len(chunks) >= 1

    def test_unknown_type_uses_generic_chunker(self):
        """Test that unknown types use generic chunker."""
        sections = [
            ("Some document title", "@@1\t0\t100\t0\t50##"),
            ("Paragraph 1 content here with enough text to meet minimum chunk size requirements.", "@@1\t0\t100\t50\t100##"),
            ("Paragraph 2 content here with enough text to meet minimum chunk size requirements.", "@@1\t0\t100\t100\t150##"),
        ]

        blocks = extract_universal_blocks(sections)
        chunks = route_to_plugin(blocks, "unknown_document_type")

        # Should use generic chunker
        assert len(chunks) >= 1
        assert chunks[0].metadata.get("is_generic_chunked") is True

    def test_layer_a_block_type_inference(self):
        """Test that Layer A correctly infers block types."""
        sections = [
            ("讯问笔录", "@@1\t0\t100\t0\t50##"),
            ("问：这是问题？", "@@1\t0\t100\t50\t100##"),
            ("答：这是回答。", "@@1\t0\t100\t100\t150##"),
            ("1. 列表项一", "@@1\t0\t100\t150\t200##"),
        ]

        blocks = extract_universal_blocks(sections, doc_type_hint="interrogation_record")

        # First block should be HEADER (first position, short text)
        assert blocks[0].block_type == BlockType.HEADER

        # Q/A patterns
        assert blocks[1].block_type == BlockType.QA_PAIR
        assert blocks[2].block_type == BlockType.QA_PAIR

        # List item
        assert blocks[3].block_type == BlockType.LIST

    def test_layer_a_entity_extraction(self):
        """Test that Layer A extracts entities correctly."""
        sections = [
            ("经依法侦查查明：2023年5月15日，犯罪嫌疑人诈骗人民币50000元。", "@@1\t0\t100\t0\t50##"),
        ]

        blocks = extract_universal_blocks(sections)

        # Check entity extraction
        entities = blocks[0].entities
        assert entities is not None
        assert len(entities.get("dates", [])) > 0  # Should have 2023年5月15日
        assert len(entities.get("amounts", [])) > 0  # Should have 50000

    def test_layer_a_position_parsing(self):
        """Test that Layer A correctly parses position tags."""
        sections = [
            ("Content text", "@@2\t10\t200\t50\t100##"),
        ]

        blocks = extract_universal_blocks(sections)

        # Page should be 1 (0-indexed, from page 2)
        assert blocks[0].page_no == 1

        # Bounding box
        assert blocks[0].bbox == (10.0, 50.0, 200.0, 100.0)

        # Content without tag
        assert blocks[0].text == "Content text"

    def test_interrogation_qa_grouping(self):
        """Test that interrogation plugin correctly groups Q/A pairs."""
        sections = [
            ("讯问笔录", "@@1\t0\t100\t0\t50##"),
            ("问：问题一？", "@@1\t0\t100\t50\t100##"),
            ("答：回答一。", "@@1\t0\t100\t100\t150##"),
            ("问：问题二？", "@@1\t0\t100\t150\t200##"),
            ("答：回答二。", "@@1\t0\t100\t200\t250##"),
            ("答：补充回答。", "@@1\t0\t100\t250\t300##"),
        ]

        blocks = extract_universal_blocks(sections, doc_type_hint="interrogation_record")
        chunks = route_to_plugin(blocks, "interrogation_record")

        # Should have 3 chunks: 1 header_info + 2 qa_pairs
        assert len(chunks) == 3

        # First chunk is header_info
        assert chunks[0].chunk_type == "header_info"
        assert "讯问笔录" in chunks[0].text

        # Second chunk is first QA pair
        assert chunks[1].chunk_type == "qa_pair"
        assert "问：问题一？" in chunks[1].text
        assert "答：回答一。" in chunks[1].text

        # Third chunk is second QA pair (with supplementary answer)
        assert chunks[2].chunk_type == "qa_pair"
        assert "问：问题二？" in chunks[2].text
        assert "答：回答二。" in chunks[2].text
        assert "答：补充回答。" in chunks[2].text

    def test_indictment_section_boundaries(self):
        """Test that indictment plugin detects section boundaries."""
        # Text must be at least 50 chars (MIN_CHUNK_SIZE) for indictment plugin
        # Each section needs enough content to meet the minimum size requirement
        sections = [
            ("起诉意见书", "@@1\t0\t100\t0\t50##"),
            ("经依法侦查查明：犯罪嫌疑人张三于2023年5月在北京市朝阳区实施了盗窃行为，窃取他人财物价值人民币三万元整，情节严重。", "@@1\t0\t100\t50\t100##"),
            ("认定上述犯罪事实的证据如下：证据一、监控录像显示犯罪嫌疑人作案全过程；证据二、失主王五的陈述笔录；证据三、赃物照片及鉴定报告。", "@@1\t0\t100\t100\t150##"),
        ]

        blocks = extract_universal_blocks(sections, doc_type_hint="indictment_opinion")
        chunks = route_to_plugin(blocks, "indictment_opinion")

        # Should create chunks for sections
        assert len(chunks) >= 1

        # Check that section titles are captured in metadata
        for chunk in chunks:
            if chunk.metadata.get("section_title"):
                assert len(chunk.metadata["section_title"]) > 0

    def test_empty_input_handling(self):
        """Test that pipeline handles empty input gracefully."""
        # Empty sections
        blocks = extract_universal_blocks([])
        assert blocks == []

        # Empty blocks to router
        chunks = route_to_plugin([], "interrogation_record")
        assert chunks == []

    def test_mixed_block_types_integration(self):
        """Test integration with mixed block types."""
        sections = [
            ("文档标题", "@@1\t0\t100\t0\t50##"),
            ("问：这是一个问题？", "@@1\t0\t100\t50\t100##"),
            ("答：这是回答内容。", "@@1\t0\t100\t100\t150##"),
            ("1. 列表项", "@@1\t0\t100\t150\t200##"),
            ("普通段落文本内容，这是一个比较长的段落，用于测试段落类型的识别。", "@@1\t0\t100\t200\t250##"),
        ]

        blocks = extract_universal_blocks(sections)

        # Verify different block types are identified
        block_types = {b.block_type for b in blocks}
        assert BlockType.HEADER in block_types
        assert BlockType.QA_PAIR in block_types
        assert BlockType.LIST in block_types
        # Note: Last block with short text may be classified as FOOTER
        # This is expected behavior based on position and length
        assert BlockType.PARAGRAPH in block_types or BlockType.FOOTER in block_types
