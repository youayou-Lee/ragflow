# test/unit_test/rag/app/criminal/test_text_cleaner.py
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
Unit tests for TextCleaner module.

Tests Layer A universal cleaning rules:
- Page number removal
- OCR line number removal
- LaTeX format conversion
"""

import pytest
import importlib.util
import sys
from pathlib import Path

# Load text_cleaner module directly to avoid triggering the import chain
# that leads to ollama client initialization with proxy issues
# Use absolute path to the source file
_MODULE_PATH = "/home/you/cs/proj/Superyou/ragflow/rag/app/criminal/text_cleaner.py"
_spec = importlib.util.spec_from_file_location("text_cleaner", _MODULE_PATH)
_text_cleaner_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_text_cleaner_module)
TextCleaner = _text_cleaner_module.TextCleaner


class TestTextCleanerPageNumbers:
    """Test page number removal."""

    def setup_method(self):
        self.cleaner = TextCleaner()

    def test_remove_simple_page_number(self):
        """Remove '第 X 页 共 Y 页' pattern."""
        text = "这是正文内容\n第 6 页 共 8 页\n继续的内容"
        result = self.cleaner.clean(text)
        assert "第 6 页 共 8 页" not in result
        assert "这是正文内容" in result
        assert "继续的内容" in result

    def test_remove_page_number_no_spaces(self):
        """Remove '第X页共Y页' pattern without spaces."""
        text = "内容第6页共8页更多内容"
        result = self.cleaner.clean(text)
        assert "第6页共8页" not in result

    def test_remove_page_number_with_extra_spaces(self):
        """Remove '第  X  页  共  Y  页' with multiple spaces."""
        text = "内容第  6  页  共  8  页更多内容"
        result = self.cleaner.clean(text)
        assert "页  共" not in result


class TestTextCleanerLineNumbers:
    """Test OCR line number removal."""

    def setup_method(self):
        self.cleaner = TextCleaner()

    def test_remove_standalone_line_number(self):
        """Remove standalone 3-digit numbers (OCR line numbers)."""
        text = "307\n这是正文内容"
        result = self.cleaner.clean(text)
        assert result == "这是正文内容"

    def test_remove_line_number_with_leading_zero(self):
        """Remove line numbers like 012, 013."""
        text = "内容\n012\n更多内容"
        result = self.cleaner.clean(text)
        assert "012" not in result

    def test_preserve_numbers_in_text(self):
        """Preserve numbers that are part of content."""
        text = "金额42000元，电话13750173434"
        result = self.cleaner.clean(text)
        assert "42000" in result
        assert "13750173434" in result

    def test_remove_line_number_at_end(self):
        """Remove line number at end of line."""
        text = "这是正文内容\n110"
        result = self.cleaner.clean(text)
        assert result == "这是正文内容"

    def test_preserve_page_references(self):
        """Preserve meaningful page references like '第1页'."""
        text = "见第1页的证据"
        result = self.cleaner.clean(text)
        assert "第1页" in result


class TestTextCleanerLatex:
    """Test LaTeX format conversion."""

    def setup_method(self):
        self.cleaner = TextCleaner()

    def test_convert_underline_text(self):
        """Convert $ \\underline{\\text{内容}} $ to plain text."""
        text = "$ \\underline{\\text{这是下划线内容}} $"
        result = self.cleaner.clean(text)
        assert result == "这是下划线内容"

    def test_convert_underline_in_sentence(self):
        """Convert LaTeX underline within sentence."""
        text = "开始 $ \\underline{\\text{中间内容}} $ 结束"
        result = self.cleaner.clean(text)
        assert "中间内容" in result
        assert "\\underline" not in result

    def test_convert_paren_underline(self):
        """Convert \\(\\underline{\\text{...}}\\) format."""
        text = "\\(\\underline{\\text{这是内容}}\\)"
        result = self.cleaner.clean(text)
        assert "这是内容" in result

    def test_convert_multiple_latex(self):
        """Convert multiple LaTeX expressions."""
        text = "第一 $ \\underline{\\text{A}} $ 第二 $ \\underline{\\text{B}} $"
        result = self.cleaner.clean(text)
        assert "A" in result
        assert "B" in result
        assert "\\underline" not in result
