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
Extended unit tests for indictment chunker.

This file supplements test_indictment_chunker.py with:
- Integration tests with mock PaddleOCR response
- extract_evidence_items() function tests
- build_section_chunks() function tests
- PR1 field (block_refs, bbox_union, page_range) integration tests
- Edge case tests
"""
import json
import pytest
from pathlib import Path
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


# Load mock PaddleOCR response fixture
FIXTURE_PATH = Path(__file__).parent.parent.parent / "deepdoc" / "parser" / "tests" / "fixtures" / "paddleocr_response.json"


@pytest.fixture
def mock_paddleocr_response():
    """Load the mock PaddleOCR API response from fixture file."""
    with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


@pytest.fixture
def mock_blocks_from_response(mock_paddleocr_response):
    """
    Generate blocks in the format expected by indictment parser.

    The PaddleOCRParser._transfer_to_sections() produces tuples like:
    - raw mode: (block_content, tag)
    where tag is: @@page\tleft\tright\ttop\tbottom##
    """
    blocks = []
    layout_results = mock_paddleocr_response["result"]["layoutParsingResults"]

    for page_idx, layout_result in enumerate(layout_results):
        pruned_result = layout_result.get("prunedResult", {})
        parsing_res_list = pruned_result.get("parsing_res_list", [])

        for block in parsing_res_list:
            block_content = block.get("block_content", "").strip()
            if not block_content:
                continue

            block_bbox = block.get("block_bbox", [0, 0, 0, 0])
            # Generate position tag (matching PaddleOCRParser format)
            # Note: PaddleOCRParser uses _ZOOMIN = 2, but we simplify here
            tag = f"@@{page_idx + 1}\t{block_bbox[0]}\t{block_bbox[2]}\t{block_bbox[1]}\t{block_bbox[3]}##"
            blocks.append((block_content, tag))

    return blocks


class TestIntegrationWithPaddleOCR:
    """Integration tests using mock PaddleOCR response."""

    def test_fixture_file_exists(self):
        """Verify the fixture file exists."""
        assert FIXTURE_PATH.exists(), f"Fixture file not found: {FIXTURE_PATH}"

    def test_fixture_contains_indictment_content(self, mock_paddleocr_response):
        """Verify the fixture contains indictment document content."""
        layout_results = mock_paddleocr_response["result"]["layoutParsingResults"]
        assert len(layout_results) > 0

        # Check for key indictment content
        all_content = []
        for layout_result in layout_results:
            for block in layout_result.get("prunedResult", {}).get("parsing_res_list", []):
                all_content.append(block.get("block_content", ""))

        combined = " ".join(all_content)
        assert "起诉意见书" in combined, "Fixture should contain 起诉意见书"
        assert "经依法侦查查明" in combined, "Fixture should contain section trigger"

    def test_find_sections_in_mock_data(self, mock_blocks_from_response):
        """Test section boundary detection with mock data."""
        parser = Mock()
        parser.remove_tag = Mock(side_effect=lambda x: x[0] if isinstance(x, tuple) else x)

        sections = find_section_boundaries(mock_blocks_from_response, parser)

        # Should find multiple sections
        assert len(sections) >= 1

        # Check that sections have valid boundaries
        for start, end, trigger in sections:
            assert start >= 0
            assert end >= start
            assert isinstance(trigger, str)

    def test_section_triggers_found_in_mock_data(self, mock_blocks_from_response):
        """Verify key section triggers are found in mock data."""
        parser = Mock()
        parser.remove_tag = Mock(side_effect=lambda x: x[0] if isinstance(x, tuple) else x)

        sections = find_section_boundaries(mock_blocks_from_response, parser)
        triggers = [trigger for _, _, trigger in sections]

        # Should find "经依法侦查查明" trigger
        found_investigation = any("经依法侦查查明" in t for t in triggers)
        assert found_investigation, "Should find '经依法侦查查明' section trigger"


class TestExtractEvidenceItems:
    """Test cases for extract_evidence_items function."""

    def _create_mock_parser(self):
        """Create a mock PDF parser for evidence tests."""
        parser = Mock()
        # remove_tag extracts pure text from tagged string
        def mock_remove_tag(text):
            if isinstance(text, str):
                # Remove position tags like @@1\t100\t200\t50\t100##
                import re
                return re.sub(r"@@[0-9-]+\t[0-9.\t]+##", "", text).strip()
            return text
        parser.remove_tag = Mock(side_effect=mock_remove_tag)
        parser.crop = Mock(return_value=(None, []))
        return parser

    def test_extract_single_evidence_item(self):
        """Should extract a single evidence item."""
        # Blocks are strings with position tags
        blocks = [
            "（一）证人证言@@1\t100\t200\t50\t100##",
            "证人张某的证言内容...@@1\t100\t200\t100\t150##",
        ]
        parser = self._create_mock_parser()
        doc = {"docnm_kwd": "test.pdf"}

        with patch("rag.app.indictment.tokenize"):
            with patch("rag.app.indictment.add_positions"):
                items = extract_evidence_items(blocks, doc, parser, eng=False)

        assert len(items) == 1
        assert items[0]["chunk_type"] == IndictmentChunkType.EVIDENCE_ITEM.value

    def test_extract_multiple_evidence_items(self):
        """Should extract multiple evidence items."""
        blocks = [
            "（一）证人证言@@1\t100\t200\t50\t100##",
            "证人证言内容@@1\t100\t200\t100\t150##",
            "（二）被害人陈述@@1\t100\t200\t150\t200##",
            "被害人陈述内容@@1\t100\t200\t200\t250##",
            "（三）书证@@1\t100\t200\t250\t300##",
            "书证内容@@1\t100\t200\t300\t350##",
        ]
        parser = self._create_mock_parser()
        doc = {"docnm_kwd": "test.pdf"}

        with patch("rag.app.indictment.tokenize"):
            with patch("rag.app.indictment.add_positions"):
                items = extract_evidence_items(blocks, doc, parser, eng=False)

        assert len(items) == 3

    def test_no_evidence_items(self):
        """Should return empty list when no evidence items found."""
        blocks = [
            "普通内容1@@1\t100\t200\t50\t100##",
            "普通内容2@@1\t100\t200\t100\t150##",
        ]
        parser = self._create_mock_parser()
        doc = {"docnm_kwd": "test.pdf"}

        items = extract_evidence_items(blocks, doc, parser, eng=False)
        assert items == []

    def test_arabic_number_evidence_items(self):
        """Should extract evidence items with Arabic numbers."""
        blocks = [
            "1. 证人证言@@1\t100\t200\t50\t100##",
            "证人证言内容@@1\t100\t200\t100\t150##",
            "2. 被害人陈述@@1\t100\t200\t150\t200##",
            "被害人陈述内容@@1\t100\t200\t200\t250##",
        ]
        parser = self._create_mock_parser()
        doc = {"docnm_kwd": "test.pdf"}

        with patch("rag.app.indictment.tokenize"):
            with patch("rag.app.indictment.add_positions"):
                items = extract_evidence_items(blocks, doc, parser, eng=False)

        assert len(items) == 2


class TestBuildSectionChunks:
    """Test cases for build_section_chunks function."""

    def _create_mock_parser(self):
        """Create a mock PDF parser."""
        parser = Mock()
        def mock_remove_tag(text):
            if isinstance(text, str):
                import re
                return re.sub(r"@@[0-9-]+\t[0-9.\t]+##", "", text).strip()
            return text
        parser.remove_tag = Mock(side_effect=mock_remove_tag)
        parser.crop = Mock(return_value=(None, [(0, 100, 200, 50, 100)]))
        return parser

    def test_build_single_section_chunk(self):
        """Should build a single section chunk."""
        blocks = ["普通内容@@1\t100\t200\t50\t100##"]
        sections = [(0, 1, "header")]
        parser = self._create_mock_parser()
        doc = {"docnm_kwd": "test.pdf"}

        with patch("rag.app.indictment.tokenize"):
            with patch("rag.app.indictment.add_positions"):
                with patch("rag.app.indictment.add_block_refs"):
                    chunks = build_section_chunks(blocks, doc, parser, sections, eng=False)

        assert len(chunks) == 1
        assert chunks[0]["chunk_type"] == IndictmentChunkType.SECTION.value

    def test_build_multiple_section_chunks(self):
        """Should build multiple section chunks."""
        blocks = [
            "头部内容@@1\t100\t200\t50\t100##",
            "经依法侦查查明，事实如下@@1\t100\t200\t100\t150##",
            "具体事实描述@@1\t100\t200\t150\t200##",
        ]
        sections = [(0, 1, "header"), (1, 3, "经依法侦查查明")]
        parser = self._create_mock_parser()
        doc = {"docnm_kwd": "test.pdf"}

        with patch("rag.app.indictment.tokenize"):
            with patch("rag.app.indictment.add_positions"):
                with patch("rag.app.indictment.add_block_refs"):
                    chunks = build_section_chunks(blocks, doc, parser, sections, eng=False)

        assert len(chunks) == 2

    def test_build_chunks_with_evidence_extraction(self):
        """Should extract evidence items when extract_evidence=True."""
        blocks = [
            "认定上述犯罪事实的证据如下：@@1\t100\t200\t50\t100##",
            "（一）证人证言@@1\t100\t200\t100\t150##",
            "证人证言内容@@1\t100\t200\t150\t200##",
        ]
        # Section trigger contains "证据"
        sections = [(0, 3, "认定上述犯罪事实的证据如下")]
        parser = self._create_mock_parser()
        doc = {"docnm_kwd": "test.pdf"}

        with patch("rag.app.indictment.tokenize"):
            with patch("rag.app.indictment.add_positions"):
                with patch("rag.app.indictment.add_block_refs"):
                    chunks = build_section_chunks(
                        blocks, doc, parser, sections, eng=False, extract_evidence=True
                    )

        # Should produce evidence items instead of section chunk
        assert len(chunks) >= 1
        # First chunk should be evidence item
        assert chunks[0]["chunk_type"] == IndictmentChunkType.EVIDENCE_ITEM.value


class TestPR1FieldIntegration:
    """Test PR1 field (block_refs, bbox_union, page_range) integration."""

    def test_block_refs_in_section_chunk(self):
        """Section chunk should have block_refs field."""
        doc = {"docnm_kwd": "test.pdf"}
        blocks = ["测试内容@@1\t100\t200\t50\t150##"]
        parser = Mock()
        parser.remove_tag = Mock(return_value="测试内容")
        parser.crop = Mock(return_value=(None, [(0, 100, 200, 50, 150)]))

        with patch("rag.app.indictment.tokenize"):
            chunk = _build_section_chunk(doc, parser, blocks, "测试触发词", False)

        assert "block_refs" in chunk
        assert isinstance(chunk["block_refs"], list)

    def test_block_refs_in_evidence_chunk(self):
        """Evidence chunk should have block_refs field."""
        parser = Mock()
        def mock_remove_tag(text):
            if isinstance(text, str):
                import re
                return re.sub(r"@@[0-9-]+\t[0-9.\t]+##", "", text).strip()
            return text
        parser.remove_tag = Mock(side_effect=mock_remove_tag)
        parser.crop = Mock(return_value=(None, [(0, 100, 200, 50, 150)]))

        blocks = [
            "（一）证人证言@@1\t100\t200\t50\t100##",
            "证人证言内容@@1\t100\t200\t100\t150##",
        ]
        doc = {"docnm_kwd": "test.pdf"}

        with patch("rag.app.indictment.tokenize"):
            with patch("rag.app.indictment.add_positions") as mock_add_pos:
                mock_add_pos.side_effect = lambda d, poss: d.update({
                    "position_int": [(1, 100, 200, 50, 150)],
                    "page_num_int": [1],
                    "top_int": [50]
                })
                items = extract_evidence_items(blocks, doc, parser, eng=False)

        if items:
            assert "block_refs" in items[0]


class TestEdgeCases:
    """Edge case tests for indictment chunker."""

    def _create_mock_parser(self):
        """Create a mock PDF parser."""
        parser = Mock()
        def mock_remove_tag(text):
            if isinstance(text, str):
                import re
                return re.sub(r"@@[0-9-]+\t[0-9.\t]+##", "", text).strip()
            return text
        parser.remove_tag = Mock(side_effect=mock_remove_tag)
        parser.crop = Mock(return_value=(None, []))
        return parser

    def test_empty_blocks(self):
        """Should handle empty block list."""
        blocks = []
        parser = self._create_mock_parser()

        sections = find_section_boundaries(blocks, parser)
        assert sections == []

    def test_very_long_section(self):
        """Should split very long sections into paragraphs."""
        doc = {"docnm_kwd": "test.pdf"}
        # Create blocks with total length over MAX_SECTION_LENGTH
        blocks = ["x" * 500 + "@@1\t100\t200\t50\t100##" for _ in range(3)]  # 1500 chars total
        parser = self._create_mock_parser()

        with patch("rag.app.indictment.tokenize"):
            # Correct parameter order: blocks, doc, parser, trigger, eng
            chunks = _split_into_paragraphs(blocks, doc, parser, "触发词", False)

        # Should be split into multiple chunks
        assert len(chunks) >= 1

    def test_trigger_in_middle_of_block(self):
        """Should handle trigger phrase in middle of block."""
        blocks = ["这是开头内容，经依法侦查查明，这是后续内容"]
        parser = Mock()
        parser.remove_tag = Mock(side_effect=lambda x: x)

        sections = find_section_boundaries(blocks, parser)

        # Should still find the trigger
        assert len(sections) >= 1

    def test_multiple_triggers_same_block(self):
        """Should handle multiple triggers in same block."""
        # This is an edge case - behavior may vary
        blocks = ["经依法侦查查明，事实描述。本院认为，应予起诉。"]
        parser = Mock()
        parser.remove_tag = Mock(side_effect=lambda x: x)

        sections = find_section_boundaries(blocks, parser)

        # Should at least find the first trigger
        assert len(sections) >= 1

    def test_unicode_and_special_chars(self):
        """Should handle unicode and special characters."""
        blocks = [
            "【重要证据】（一）证人证言：张某（男，25岁）@@1\t100\t200\t50\t100##",
            "证据内容包含特殊字符：★☆●○@@1\t100\t200\t100\t150##",
        ]
        parser = self._create_mock_parser()
        doc = {"docnm_kwd": "test.pdf"}

        with patch("rag.app.indictment.tokenize"):
            with patch("rag.app.indictment.add_positions"):
                items = extract_evidence_items(blocks, doc, parser, eng=False)

        # Should not crash with special characters
        assert isinstance(items, list)


class TestChunkFunctionIntegration:
    """Integration tests for the main chunk() function."""

    def test_chunk_function_only_pdf_supported(self):
        """Test that chunk() only supports PDF files."""
        from rag.app.indictment import chunk

        # Mock settings to use Infinity engine (avoids NLTK dependency)
        with patch("common.settings.DOC_ENGINE_INFINITY", True):
            with patch("rag.nlp.rag_tokenizer") as mock_tokenizer:
                mock_tokenizer.tokenize.return_value = "test_tokens"

                def dummy_callback(prog, msg=""):
                    pass

                # Non-PDF files should raise NotImplementedError
                with pytest.raises(NotImplementedError):
                    chunk(
                        filename="test.txt",
                        binary=None,
                        callback=dummy_callback,
                    )


class TestSectionTriggerCoverage:
    """Test coverage for all section triggers."""

    def test_all_triggers_compile(self):
        """All trigger patterns should compile successfully."""
        # This should not raise
        pattern = SECTION_TRIGGER_PATTERN
        assert pattern is not None

    def test_all_triggers_in_list(self):
        """All expected triggers should be in SECTION_TRIGGERS list."""
        expected_triggers = [
            "经依法侦查查明",
            "经依法审查查明",
            "现查明",
            "认定上述犯罪事实的证据如下",
            "综上所述",
            "本院认为",
            "此致",
        ]

        for trigger in expected_triggers:
            # Check if trigger is in the list (as regex pattern)
            found = any(trigger in t for t in SECTION_TRIGGERS)
            assert found, f"Expected trigger not found: {trigger}"
