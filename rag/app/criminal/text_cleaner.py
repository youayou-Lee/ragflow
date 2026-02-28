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

"""TextCleaner module for OCR text cleaning (Layer A)."""

import re


class TextCleaner:
    """
    OCR text cleaner for Layer A.

    Handles universal cleaning rules applicable to all document types:
    - Page numbers (第 X 页 共 Y 页)
    - OCR line numbers
    - LaTeX formatting
    - Whitespace normalization
    """

    # Page number pattern: 第 X 页 共 Y 页 (with variable spaces)
    PAGE_NUMBER_PATTERN = re.compile(
        r'第\s*\d+\s*页\s*共\s*\d+\s*页'
    )

    # OCR line number pattern: standalone 3-digit number on its own line
    # Matches numbers like 307, 012, 110, 909 at start/end of text or on own line
    LINE_NUMBER_PATTERN = re.compile(
        r'(?:^|\n)\s*\d{3}\s*(?=\n|$)'
    )

    # LaTeX underline patterns
    # Pattern 1: $ \underline{\text{content}} $
    LATEX_UNDERLINE_DOLLAR = re.compile(
        r'\$\s*\\underline\s*\{\\text\s*\{([^}]+)\}\}\s*\$'
    )
    # Pattern 2: \( \underline{\text{content}} \)
    LATEX_UNDERLINE_PAREN = re.compile(
        r'\\\(\s*\\underline\s*\{\\text\s*\{([^}]+)\}\}\s*\\\)'
    )

    def clean(self, text: str) -> str:
        """
        Apply all cleaning rules to text.

        Args:
            text: Raw OCR text

        Returns:
            Cleaned text
        """
        if not text:
            return text

        text = self._remove_page_numbers(text)
        text = self._remove_line_numbers(text)
        text = self._convert_latex(text)
        text = self._normalize_whitespace(text)

        return text.strip()

    def _remove_page_numbers(self, text: str) -> str:
        """Remove page number patterns like '第 6 页 共 8 页'."""
        return self.PAGE_NUMBER_PATTERN.sub('', text)

    def _remove_line_numbers(self, text: str) -> str:
        """
        Remove standalone OCR line numbers.

        These are 3-digit numbers that appear on their own line,
        typically at corners of scanned pages (e.g., 307, 012, 110).
        """
        return self.LINE_NUMBER_PATTERN.sub('\n', text)

    def _convert_latex(self, text: str) -> str:
        """
        Convert LaTeX formatting to plain text.

        Handles:
        - $ \\underline{\\text{content}} $ -> content
        - \\(\\underline{\\text{content}}\\) -> content
        """
        text = self.LATEX_UNDERLINE_DOLLAR.sub(r'\1', text)
        text = self.LATEX_UNDERLINE_PAREN.sub(r'\1', text)
        return text

    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace: multiple spaces to single, multiple newlines to double."""
        # Multiple spaces to single space
        text = re.sub(r'[^\S\n]+', ' ', text)
        # Multiple newlines to double newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text
