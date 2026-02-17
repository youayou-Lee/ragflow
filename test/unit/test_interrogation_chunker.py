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
Unit tests for interrogation record chunker.

Tests for QA-based chunking of Chinese interrogation/transcript documents.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch

from rag.app.interrogation import (
    InterrogationChunkType,
    QUESTION_PATTERN,
    ANSWER_PATTERN,
    extract_header_chunks,
    split_qa_chunks,
    _build_qa_chunk,
    MAX_QA_LENGTH,
)


pytestmark = pytest.mark.p1


class TestQuestionPatternMatching:
    """Test cases for QA pattern matching."""

    def test_standard_format(self):
        """Should match standard format: 问：xxx"""
        text = "问：你叫什么名字？"
        assert QUESTION_PATTERN.search(text) is not None

    def test_with_spaces(self):
        """Should match format with spaces: 问 ： xxx"""
        text = "问 ： 你叫什么名字？"
        assert QUESTION_PATTERN.search(text) is not None

    def test_halfwidth_colon(self):
        """Should match halfwidth colon: 问: xxx"""
        text = "问: 你叫什么名字？"
        assert QUESTION_PATTERN.search(text) is not None

    def test_colon_with_spaces(self):
        """Should match colon with spaces around it"""
        text = "问 : 你叫什么名字？"
        assert QUESTION_PATTERN.search(text) is not None

    def test_chinese_semicolon(self):
        """Should match Chinese semicolon: 问；xxx (OCR sometimes outputs this)"""
        text = "问；说说你帮助成龙飞办理锦兴小学学位的经过？"
        assert QUESTION_PATTERN.search(text) is not None

    def test_halfwidth_semicolon(self):
        """Should match halfwidth semicolon: 问; xxx"""
        text = "问; 你叫什么名字？"
        assert QUESTION_PATTERN.search(text) is not None

    def test_in_context(self):
        """Should match in context"""
        text = "这是前面的一些文字。问：你叫什么名字？"
        assert QUESTION_PATTERN.search(text) is not None

    def test_no_false_match(self):
        """Should not match unrelated text"""
        text = "这是一段普通的文字，没有问题。"
        assert QUESTION_PATTERN.search(text) is None


class TestAnswerPatternMatching:
    """Test cases for answer pattern matching."""

    def test_standard_format(self):
        """Should match standard format: 答：xxx"""
        text = "答：我叫张三。"
        assert ANSWER_PATTERN.search(text) is not None

    def test_with_spaces(self):
        """Should match format with spaces"""
        text = "答 ： 我叫张三。"
        assert ANSWER_PATTERN.search(text) is not None

    def test_halfwidth_colon(self):
        """Should match halfwidth colon"""
        text = "答: 我叫张三。"
        assert ANSWER_PATTERN.search(text) is not None

    def test_chinese_semicolon(self):
        """Should match Chinese semicolon: 答；xxx (OCR sometimes outputs this)"""
        text = "答；我叫张三。"
        assert ANSWER_PATTERN.search(text) is not None

    def test_halfwidth_semicolon(self):
        """Should match halfwidth semicolon"""
        text = "答; 我叫张三。"
        assert ANSWER_PATTERN.search(text) is not None


class TestHeaderExtraction:
    """Test cases for extract_header_chunks function."""

    def _create_mock_parser(self, texts):
        """Create a mock PDF parser."""
        parser = Mock()
        parser.remove_tag = Mock(side_effect=lambda x: x)
        parser.crop = Mock(return_value=(None, []))
        return parser

    def test_extract_header_before_question(self):
        """Should extract content before first question as header"""
        blocks = ["头部内容1", "头部内容2", "问：第一个问题", "答：回答内容"]
        doc = {"docnm_kwd": "test.pdf"}
        parser = self._create_mock_parser(blocks)

        with patch("rag.app.interrogation.tokenize"):
            header_chunks, remaining = extract_header_chunks(blocks, doc, parser, False)

        assert len(header_chunks) == 1
        assert header_chunks[0]["chunk_type"] == InterrogationChunkType.HEADER.value
        assert len(remaining) == 2  # Question and answer blocks

    def test_no_question_returns_all_as_header(self):
        """Should return all content as header when no question is found"""
        blocks = ["头部内容1", "头部内容2", "普通内容"]
        doc = {"docnm_kwd": "test.pdf"}
        parser = self._create_mock_parser(blocks)

        with patch("rag.app.interrogation.tokenize"):
            header_chunks, remaining = extract_header_chunks(blocks, doc, parser, False)

        assert len(header_chunks) == 1
        assert header_chunks[0]["chunk_type"] == InterrogationChunkType.HEADER.value
        assert remaining == []

    def test_empty_blocks(self):
        """Should handle empty block list"""
        blocks = []
        doc = {"docnm_kwd": "test.pdf"}
        parser = self._create_mock_parser(blocks)

        header_chunks, remaining = extract_header_chunks(blocks, doc, parser, False)

        assert header_chunks == []
        assert remaining == []

    def test_question_at_start(self):
        """Should handle case where question is at the start"""
        blocks = ["问：第一个问题", "答：回答内容"]
        doc = {"docnm_kwd": "test.pdf"}
        parser = self._create_mock_parser(blocks)

        with patch("rag.app.interrogation.tokenize"):
            header_chunks, remaining = extract_header_chunks(blocks, doc, parser, False)

        assert header_chunks == []
        assert len(remaining) == 2


class TestQAPairSplitting:
    """Test cases for split_qa_chunks function."""

    def _create_mock_parser(self):
        """Create a mock PDF parser."""
        parser = Mock()
        parser.remove_tag = Mock(side_effect=lambda x: x)
        parser.crop = Mock(return_value=(None, []))
        return parser

    def test_split_multiple_qa_pairs(self):
        """Should split multiple QA pairs"""
        blocks = [
            "问：第一个问题",
            "答：第一个回答",
            "问：第二个问题",
            "答：第二个回答",
        ]
        doc = {"docnm_kwd": "test.pdf"}
        parser = self._create_mock_parser()

        with patch("rag.app.interrogation.tokenize"):
            chunks = split_qa_chunks(blocks, doc, parser, False)

        assert len(chunks) == 2
        assert all(c["chunk_type"] == InterrogationChunkType.QA_PAIR.value for c in chunks)

    def test_chunk_type_is_qa_pair(self):
        """Verify chunk_type is qa_pair"""
        blocks = ["问：问题", "答：回答"]
        doc = {"docnm_kwd": "test.pdf"}
        parser = self._create_mock_parser()

        with patch("rag.app.interrogation.tokenize"):
            chunks = split_qa_chunks(blocks, doc, parser, False)

        assert len(chunks) == 1
        assert chunks[0]["chunk_type"] == InterrogationChunkType.QA_PAIR.value

    def test_qa_index_is_sequential(self):
        """Verify qa_index is sequential"""
        blocks = [
            "问：第一个问题",
            "答：第一个回答",
            "问：第二个问题",
            "答：第二个回答",
            "问：第三个问题",
            "答：第三个回答",
        ]
        doc = {"docnm_kwd": "test.pdf"}
        parser = self._create_mock_parser()

        with patch("rag.app.interrogation.tokenize"):
            chunks = split_qa_chunks(blocks, doc, parser, False)

        assert len(chunks) == 3
        for i, chunk in enumerate(chunks):
            assert chunk["qa_index"] == i

    def test_empty_blocks(self):
        """Should handle empty block list"""
        blocks = []
        doc = {"docnm_kwd": "test.pdf"}
        parser = self._create_mock_parser()

        chunks = split_qa_chunks(blocks, doc, parser, False)

        assert chunks == []


class TestBuildQAChunk:
    """Test cases for _build_qa_chunk function."""

    def test_qa_chunk_has_correct_type(self):
        """QA chunk should have correct chunk_type"""
        doc = {"docnm_kwd": "test.pdf"}
        q_parts = ["问：问题内容"]
        a_parts = ["答：回答内容"]
        parser = Mock()
        parser.remove_tag = Mock(side_effect=lambda x: x)
        parser.crop = Mock(return_value=(None, []))

        with patch("rag.app.interrogation.tokenize"):
            chunk = _build_qa_chunk(doc, parser, q_parts, a_parts, 0, False)

        assert chunk["chunk_type"] == InterrogationChunkType.QA_PAIR.value
        assert chunk["qa_index"] == 0

    def test_qa_chunk_content_format(self):
        """QA chunk content should be question\\tanswer format"""
        doc = {"docnm_kwd": "test.pdf"}
        q_parts = ["问：问题内容"]
        a_parts = ["答：回答内容"]
        parser = Mock()
        parser.remove_tag = Mock(side_effect=lambda x: x)
        parser.crop = Mock(return_value=(None, []))

        with patch("rag.app.interrogation.tokenize"):
            chunk = _build_qa_chunk(doc, parser, q_parts, a_parts, 0, False)

        # Content format is question\tanswer
        assert "问：问题内容" in chunk["content_with_weight"]
        assert "答：回答内容" in chunk["content_with_weight"]


class TestChunkExtensions:
    """Test cases for chunk extension fields."""

    def _create_mock_parser(self):
        """Create a mock PDF parser (no longer used for position extraction)."""
        parser = Mock()
        parser.remove_tag = Mock(side_effect=lambda x: x)
        parser.crop = Mock(return_value=(None, []))
        return parser

    def _create_block_with_position(self, text: str, page: int = 1, left: float = 10, right: float = 100, top: float = 20, bottom: float = 50) -> str:
        """Create a block with embedded position tag."""
        return f"@@{page}\t{left}\t{right}\t{top}\t{bottom}##{text}"

    def test_qa_chunk_has_block_refs(self):
        """QA chunk should include block_refs"""
        doc = {"docnm_kwd": "test.pdf"}
        # Use blocks with position tags
        q_parts = [self._create_block_with_position("问：问题内容")]
        a_parts = [self._create_block_with_position("答：回答内容")]
        parser = self._create_mock_parser()

        with patch("rag.app.interrogation.tokenize"):
            chunk = _build_qa_chunk(doc, parser, q_parts, a_parts, 0, False)

        assert "block_refs" in chunk
        assert isinstance(chunk["block_refs"], list)

    def test_qa_chunk_has_bbox_union(self):
        """QA chunk should include bbox_union"""
        doc = {"docnm_kwd": "test.pdf"}
        # Use blocks with position tags
        q_parts = [self._create_block_with_position("问：问题内容", left=10, right=100, top=20, bottom=50)]
        a_parts = [self._create_block_with_position("答：回答内容", left=10, right=100, top=60, bottom=90)]
        parser = self._create_mock_parser()

        with patch("rag.app.interrogation.tokenize"):
            chunk = _build_qa_chunk(doc, parser, q_parts, a_parts, 0, False)

        assert "bbox_union" in chunk
        assert isinstance(chunk["bbox_union"], list)
        assert len(chunk["bbox_union"]) == 4  # [x1, y1, x2, y2]

    def test_qa_chunk_has_page_range(self):
        """QA chunk should include page_range"""
        doc = {"docnm_kwd": "test.pdf"}
        # Use blocks with position tags
        q_parts = [self._create_block_with_position("问：问题内容", page=1)]
        a_parts = [self._create_block_with_position("答：回答内容", page=1)]
        parser = self._create_mock_parser()

        with patch("rag.app.interrogation.tokenize"):
            chunk = _build_qa_chunk(doc, parser, q_parts, a_parts, 0, False)

        assert "page_range" in chunk
        assert isinstance(chunk["page_range"], list)
        assert len(chunk["page_range"]) == 2  # [start_page, end_page]

    def test_header_chunk_has_extensions(self):
        """Header chunk should include extension fields"""
        # Use blocks with position tags
        blocks = [
            self._create_block_with_position("头部内容1"),
            self._create_block_with_position("头部内容2"),
            self._create_block_with_position("问：问题"),
        ]
        doc = {"docnm_kwd": "test.pdf"}
        parser = self._create_mock_parser()

        with patch("rag.app.interrogation.tokenize"):
            header_chunks, _ = extract_header_chunks(blocks, doc, parser, False)

        assert len(header_chunks) == 1
        chunk = header_chunks[0]
        assert "block_refs" in chunk
        assert "bbox_union" in chunk
        assert "page_range" in chunk


class TestInterrogationChunkTypeEnum:
    """Test cases for InterrogationChunkType enum."""

    def test_chunk_types_exist(self):
        """All chunk types should be defined"""
        assert InterrogationChunkType.HEADER.value == "header"
        assert InterrogationChunkType.QA_PAIR.value == "qa_pair"
        assert InterrogationChunkType.QA_SUB.value == "qa_sub"


class TestMaxQALength:
    """Test MAX_QA_LENGTH constant."""

    def test_max_length_is_2000(self):
        """MAX_QA_LENGTH should be 2000"""
        assert MAX_QA_LENGTH == 2000
