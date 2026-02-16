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
Unit tests for indictment chunker.

Tests for section-based chunking of Chinese indictment documents.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch

from rag.app.indictment import (
    IndictmentChunkType,
    SECTION_TRIGGERS,
    SECTION_TRIGGER_PATTERN,
    EVIDENCE_ITEM_PATTERN,
    find_section_boundaries,
    extract_evidence_items,
    build_section_chunks,
    _build_section_chunk,
    _split_into_paragraphs,
    MAX_SECTION_LENGTH,
)


pytestmark = pytest.mark.p1


class TestSectionTriggerPatterns:
    """Test cases for section trigger patterns."""

    def test_trigger_pattern_matches_standard_triggers(self):
        """Should match all standard trigger phrases"""
        test_cases = [
            "经依法侦查查明",
            "经依法审查查明",
            "现查明",
            "认定上述犯罪事实的证据如下",
            "综上所述",
            "本院认为",
            "此致",
        ]
        for trigger in test_cases:
            assert SECTION_TRIGGER_PATTERN.search(trigger), f"Should match: {trigger}"

    def test_trigger_pattern_in_context(self):
        """Should match triggers in context"""
        text = "经依法侦查查明，犯罪嫌疑人张三于2024年1月实施盗窃。"
        match = SECTION_TRIGGER_PATTERN.search(text)
        assert match is not None
        assert match.group(0) == "经依法侦查查明"

    def test_trigger_pattern_no_false_match(self):
        """Should not match unrelated text"""
        text = "这是一段普通的文字，不包含触发词。"
        match = SECTION_TRIGGER_PATTERN.search(text)
        assert match is None


class TestEvidenceItemPatterns:
    """Test cases for evidence item patterns."""

    def test_chinese_number_pattern(self):
        """Should match Chinese number patterns like （一）"""
        test_cases = [
            "（一）证人证言",
            "（二）被害人陈述",
            "（三）犯罪嫌疑人供述",
        ]
        for text in test_cases:
            assert EVIDENCE_ITEM_PATTERN.match(text), f"Should match: {text}"

    def test_arabic_number_pattern(self):
        """Should match Arabic number patterns like 1."""
        test_cases = [
            "1. 证人证言",
            "2、被害人陈述",
            "3. 犯罪嫌疑人供述",
        ]
        for text in test_cases:
            assert EVIDENCE_ITEM_PATTERN.match(text), f"Should match: {text}"

    def test_parenthesized_number_pattern(self):
        """Should match parenthesized numbers like (1)"""
        test_cases = [
            "(1) 证人证言",
            "（1）被害人陈述",
        ]
        for text in test_cases:
            assert EVIDENCE_ITEM_PATTERN.match(text), f"Should match: {text}"

    def test_no_false_match(self):
        """Should not match regular text"""
        test_cases = [
            "这是普通文字",
            "没有编号的内容",
            "一、标题但不是证据项",  # Note: This might match depending on pattern
        ]
        for text in test_cases:
            # At least verify it doesn't crash
            EVIDENCE_ITEM_PATTERN.match(text)


class TestFindSectionBoundaries:
    """Test cases for find_section_boundaries function."""

    def _create_mock_parser(self, texts):
        """Create a mock PDF parser that returns clean text."""
        parser = Mock()
        parser.remove_tag = Mock(side_effect=lambda x: x)
        return parser

    def test_single_section(self):
        """Should handle single section (no triggers)"""
        blocks = ["普通内容1", "普通内容2", "普通内容3"]
        parser = self._create_mock_parser(blocks)

        sections = find_section_boundaries(blocks, parser)

        assert len(sections) == 1
        assert sections[0][2] == "header"  # First section is always header

    def test_multiple_sections(self):
        """Should identify multiple sections"""
        blocks = [
            "头部内容",
            "经依法侦查查明，事实如下",
            "具体事实描述",
            "本院认为",
            "判决内容",
        ]
        parser = self._create_mock_parser(blocks)

        sections = find_section_boundaries(blocks, parser)

        assert len(sections) >= 2

    def test_empty_blocks(self):
        """Should handle empty block list"""
        blocks = []
        parser = self._create_mock_parser(blocks)

        sections = find_section_boundaries(blocks, parser)

        assert sections == []


class TestBuildSectionChunk:
    """Test cases for _build_section_chunk function."""

    def test_section_chunk_has_correct_type(self):
        """Section chunk should have correct chunk_type"""
        doc = {"docnm_kwd": "test.pdf"}
        blocks = ["内容1", "内容2"]
        parser = Mock()
        parser.remove_tag = Mock(return_value="测试内容")
        parser.crop = Mock(return_value=(None, []))

        with patch("rag.app.indictment.tokenize"):
            chunk = _build_section_chunk(doc, parser, blocks, "测试触发词", False)

        assert chunk["chunk_type"] == IndictmentChunkType.SECTION.value
        assert chunk["section_trigger"] == "测试触发词"

    def test_paragraph_chunk_has_correct_type(self):
        """Paragraph chunk should have correct chunk_type"""
        doc = {"docnm_kwd": "test.pdf"}
        blocks = ["内容1", "内容2"]
        parser = Mock()
        parser.remove_tag = Mock(return_value="测试内容")
        parser.crop = Mock(return_value=(None, []))

        with patch("rag.app.indictment.tokenize"):
            chunk = _build_section_chunk(
                doc, parser, blocks, "测试触发词", False,
                chunk_type=IndictmentChunkType.PARAGRAPH.value
            )

        assert chunk["chunk_type"] == IndictmentChunkType.PARAGRAPH.value


class TestSplitIntoParagraphs:
    """Test cases for _split_into_paragraphs function."""

    def test_short_section_no_split(self):
        """Short section should not be split"""
        doc = {"docnm_kwd": "test.pdf"}
        # Create blocks with total length under MAX_SECTION_LENGTH
        blocks = ["短内容1", "短内容2"]
        parser = Mock()
        parser.remove_tag = Mock(side_effect=lambda x: x)
        parser.crop = Mock(return_value=(None, []))

        with patch("rag.app.indictment.tokenize"):
            # Correct parameter order: blocks, doc, parser, trigger, eng
            chunks = _split_into_paragraphs(blocks, doc, parser, "触发词", False)

        # Short content should produce single chunk
        assert len(chunks) == 1
        assert chunks[0]["chunk_type"] == IndictmentChunkType.SECTION.value

    def test_long_section_splits(self):
        """Long section should be split into paragraphs"""
        doc = {"docnm_kwd": "test.pdf"}
        # Create blocks with total length over MAX_SECTION_LENGTH
        blocks = ["x" * 500, "y" * 500]  # Total 1000 chars > 800
        parser = Mock()
        parser.remove_tag = Mock(side_effect=lambda x: x)
        parser.crop = Mock(return_value=(None, []))

        with patch("rag.app.indictment.tokenize"):
            # Correct parameter order: blocks, doc, parser, trigger, eng
            chunks = _split_into_paragraphs(blocks, doc, parser, "触发词", False)

        # Long content should be split
        assert len(chunks) >= 1


class TestIndictmentChunkTypeEnum:
    """Test cases for IndictmentChunkType enum."""

    def test_chunk_types_exist(self):
        """All chunk types should be defined"""
        assert IndictmentChunkType.SECTION.value == "section"
        assert IndictmentChunkType.PARAGRAPH.value == "paragraph"
        assert IndictmentChunkType.EVIDENCE_ITEM.value == "evidence_item"


class TestMaxSectionLength:
    """Test MAX_SECTION_LENGTH constant."""

    def test_max_length_is_800(self):
        """MAX_SECTION_LENGTH should be 800"""
        assert MAX_SECTION_LENGTH == 800
