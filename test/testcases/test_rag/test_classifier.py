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
Unit tests for document classifier.

Tests the rule-based and LLM-based classification logic.
"""

import pytest
from unittest.mock import patch, MagicMock

from common.constants import ParserType
from rag.app.classifier import (
    DocumentClassifier,
    extract_text_sample,
    DOCUMENT_PATTERNS,
    MAX_TEXT_SAMPLE_CHARS,
    MIN_TEXT_THRESHOLD,
)


@pytest.mark.p2
class TestExtractTextSample:
    """Tests for text extraction from various file formats."""

    def test_extract_from_text_file(self):
        """Test extracting text from a plain text file."""
        content = b"This is a test document content for classification."
        result = extract_text_sample(content, "test.txt")
        assert result == "This is a test document content for classification."

    def test_extract_from_text_file_with_limit(self):
        """Test that text extraction respects max_chars limit."""
        content = b"A" * 5000
        result = extract_text_sample(content, "test.txt", max_chars=100)
        assert len(result) == 100

    def test_extract_from_empty_content(self):
        """Test handling of empty content."""
        result = extract_text_sample(b"", "test.txt")
        assert result == ""

    def test_extract_from_none_content(self):
        """Test handling of None content."""
        result = extract_text_sample(None, "test.txt")
        assert result == ""

    def test_extract_from_pdf_with_pypdf(self):
        """Test extracting text from a PDF using pypdf."""
        # Create a minimal PDF content (just text extraction test)
        # This test verifies the function handles PDF files without crashing
        with patch("rag.app.classifier._extract_pdf_text") as mock_extract:
            mock_extract.return_value = "Extracted PDF text content"
            result = extract_text_sample(b"fake pdf content", "test.pdf")
            assert result == "Extracted PDF text content"

    def test_extract_from_docx(self):
        """Test extracting text from a DOCX file."""
        with patch("rag.app.classifier._extract_docx_text") as mock_extract:
            mock_extract.return_value = "Extracted DOCX text content"
            result = extract_text_sample(b"fake docx content", "test.docx")
            assert result == "Extracted DOCX text content"

    def test_extract_handles_exceptions_gracefully(self):
        """Test that extraction handles exceptions without crashing."""
        with patch("rag.app.classifier._extract_text_file") as mock_extract:
            mock_extract.side_effect = Exception("Test error")
            result = extract_text_sample(b"content", "test.txt")
            assert result == ""


@pytest.mark.p2
class TestRuleBasedClassification:
    """Tests for rule-based document classification."""

    def test_classify_interrogation_record(self):
        """Test classification of interrogation records (讯问笔录)."""
        text = "这是讯问笔录的内容，记录了犯罪嫌疑人的供述。"
        parser_id, method, confidence = DocumentClassifier._rule_classify(text)
        assert parser_id == ParserType.INTERROGATION.value
        assert method == "rule"
        assert confidence == 1.0

    def test_classify_inquiry_record(self):
        """Test classification of inquiry records (询问笔录)."""
        text = "询问笔录\n时间：2024年1月1日\n地点：公安局"
        parser_id, method, confidence = DocumentClassifier._rule_classify(text)
        assert parser_id == ParserType.INTERROGATION.value
        assert method == "rule"
        assert confidence == 1.0

    def test_classify_indictment_opinion(self):
        """Test classification of indictment opinions (起诉意见书)."""
        text = "起诉意见书\n某某公安局\n关于张三涉嫌盗窃案"
        parser_id, method, confidence = DocumentClassifier._rule_classify(text)
        assert parser_id == ParserType.INDICTMENT.value
        assert method == "rule"
        assert confidence == 1.0

    def test_classify_indictment(self):
        """Test classification of indictments (起诉书)."""
        text = "某某市人民检察院起诉书\n被告人李四"
        parser_id, method, confidence = DocumentClassifier._rule_classify(text)
        assert parser_id == ParserType.INDICTMENT.value
        assert method == "rule"
        assert confidence == 1.0

    def test_classify_judgment(self):
        """Test classification of court judgments (判决书)."""
        text = "某某市人民法院刑事判决书\n(2024)某某刑初字第1号"
        parser_id, method, confidence = DocumentClassifier._rule_classify(text)
        assert parser_id == ParserType.LAWS.value
        assert method == "rule"
        assert confidence == 1.0

    def test_classify_ruling(self):
        """Test classification of court rulings (裁定书)."""
        text = "某某市人民法院民事裁定书"
        parser_id, method, confidence = DocumentClassifier._rule_classify(text)
        assert parser_id == ParserType.LAWS.value
        assert method == "rule"
        assert confidence == 1.0

    def test_classify_legal_regulation(self):
        """Test classification of legal regulations (法规)."""
        text = "本条例适用于所有企业"
        parser_id, method, confidence = DocumentClassifier._rule_classify(text)
        assert parser_id == ParserType.LAWS.value
        assert method == "rule"
        assert confidence == 1.0

    def test_classify_unknown_document(self):
        """Test classification of unknown document types."""
        text = "这是一份普通的文档，不包含任何特定类型的内容。"
        parser_id, method, confidence = DocumentClassifier._rule_classify(text)
        assert parser_id == ""
        assert method == "rule"
        assert confidence == 0.0

    def test_case_insensitive_matching(self):
        """Test that pattern matching is case insensitive."""
        text = "讯问笔录".lower()  # lowercase Chinese characters
        parser_id, method, confidence = DocumentClassifier._rule_classify(text)
        # Note: Chinese characters don't have case, but the regex uses IGNORECASE
        assert parser_id == ParserType.INTERROGATION.value


@pytest.mark.p2
class TestFallbackClassification:
    """Tests for fallback classification."""

    def test_fallback_returns_naive(self):
        """Test that fallback returns naive parser."""
        parser_id, method, confidence = DocumentClassifier._fallback_classify("unknown.pdf")
        assert parser_id == ParserType.NAIVE.value
        assert method == "fallback"
        assert confidence == 0.0

    def test_fallback_ignores_filename(self):
        """Test that fallback ignores filename for classification."""
        # Fallback always returns naive, regardless of filename
        parser_id1, _, _ = DocumentClassifier._fallback_classify("interrogation.pdf")
        parser_id2, _, _ = DocumentClassifier._fallback_classify("indictment.pdf")
        assert parser_id1 == ParserType.NAIVE.value
        assert parser_id2 == ParserType.NAIVE.value


@pytest.mark.p2
class TestLLMClassification:
    """Tests for LLM-based classification.

    Note: LLM classification tests require the full LLM infrastructure to be available.
    These tests focus on edge cases that don't require LLM calls.
    """

    def test_llm_classify_empty_text_returns_naive(self):
        """Test LLM classification with empty text returns naive."""
        parser_id, method, confidence = DocumentClassifier._classify_by_llm(
            "", "tenant-123"
        )
        assert parser_id == ParserType.NAIVE.value
        assert method == "llm"
        assert confidence == 0.0

    def test_llm_classify_short_text_returns_naive(self):
        """Test LLM classification with short text returns naive."""
        parser_id, method, confidence = DocumentClassifier._classify_by_llm(
            "短文本", "tenant-123"
        )
        assert parser_id == ParserType.NAIVE.value
        assert method == "llm"
        assert confidence == 0.0

    def test_llm_classify_handles_import_error(self):
        """Test LLM classification handles import errors gracefully."""
        # When LLMBundle cannot be imported, it should return naive
        parser_id, method, confidence = DocumentClassifier._classify_by_llm(
            "这是一段足够长的文本内容用于测试LLM分类功能", "tenant-123"
        )
        # Since LLMBundle is not available in test environment, it should fallback to naive
        assert parser_id == ParserType.NAIVE.value
        assert method == "llm"
        assert confidence == 0.0


@pytest.mark.p2
class TestDocumentClassifier:
    """Tests for the main DocumentClassifier.classify method."""

    def test_classify_uses_rule_first(self):
        """Test that classify uses rule-based classification first."""
        # Use a .txt file to avoid PDF parsing issues
        binary = "讯问笔录\n这是讯问笔录的内容".encode("utf-8")
        parser_id, method, confidence = DocumentClassifier.classify(
            binary, "interrogation.txt"
        )
        assert parser_id == ParserType.INTERROGATION.value
        assert method == "rule"
        assert confidence == 1.0

    def test_classify_uses_llm_when_rule_fails(self):
        """Test that classify attempts LLM when rule-based fails (then falls back to naive)."""
        # Text that doesn't match any rule and is long enough for LLM
        binary = "这是一个非标准文档类型的测试文本，内容足够长以触发LLM分类" * 3
        binary = binary.encode("utf-8")
        parser_id, method, confidence = DocumentClassifier.classify(
            binary, "unknown.txt", tenant_id="tenant-123"
        )
        # Since LLM infrastructure is not available in test env, it falls back to naive
        assert parser_id == ParserType.NAIVE.value
        # When LLM fails, it goes to fallback
        assert method in ("llm", "fallback")
        assert confidence == 0.0

    def test_classify_uses_fallback_when_all_fail(self):
        """Test that classify uses fallback when both rule and LLM fail."""
        # Short text that doesn't match rules and can't use LLM
        binary = "短文本".encode("utf-8")
        parser_id, method, confidence = DocumentClassifier.classify(
            binary, "unknown.txt"
        )
        assert parser_id == ParserType.NAIVE.value
        assert method == "fallback"
        assert confidence == 0.0

    def test_classify_without_tenant_id_skips_llm(self):
        """Test that classify skips LLM when no tenant_id is provided."""
        # Text long enough for LLM but no tenant_id
        binary = "这是一个非标准文档类型的测试文本，内容足够长但缺少tenant_id" * 3
        binary = binary.encode("utf-8")
        parser_id, method, confidence = DocumentClassifier.classify(
            binary, "unknown.pdf"
        )
        assert parser_id == ParserType.NAIVE.value
        assert method == "fallback"
        assert confidence == 0.0


@pytest.mark.p2
class TestDocumentPatterns:
    """Tests for document pattern configuration."""

    def test_patterns_are_valid_regex(self):
        """Test that all patterns in DOCUMENT_PATTERNS are valid regex."""
        import re
        for pattern, parser_id, description in DOCUMENT_PATTERNS:
            # Should not raise exception
            re.compile(pattern)

    def test_patterns_have_valid_parser_ids(self):
        """Test that all parser IDs in patterns are valid ParserType values."""
        valid_parsers = [e.value for e in ParserType]
        for pattern, parser_id, description in DOCUMENT_PATTERNS:
            assert parser_id in valid_parsers, f"Invalid parser_id: {parser_id}"
