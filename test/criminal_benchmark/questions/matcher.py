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
"""Answer matcher for criminal benchmark."""

import re
from typing import Optional

import sys
from pathlib import Path
# Add project root to path
_project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(_project_root))

from test.criminal_benchmark.models import QuestionCategory, MatchResult


class AnswerMatcher:
    """Matcher for comparing expected and actual answers."""

    def __init__(
        self,
        coverage_threshold: float = 0.8,
        negative_keywords: Optional[list[str]] = None,
    ):
        """
        Initialize the matcher.

        Args:
            coverage_threshold: Minimum coverage for evidence questions
            negative_keywords: Keywords indicating missing information
        """
        self.coverage_threshold = coverage_threshold
        self.negative_keywords = negative_keywords or [
            "材料未显示", "文档未提及", "无法确定", "未记载",
            "没有信息", "未找到", "无法从材料中得知", "材料中没有", "未提供",
        ]

    def match(
        self,
        category: QuestionCategory,
        expected: str,
        actual: str,
    ) -> MatchResult:
        """
        Match actual answer against expected answer.

        Args:
            category: Question category
            expected: Expected answer
            actual: Actual answer from LLM

        Returns:
            MatchResult with matched status and score
        """
        if category == QuestionCategory.FACTUAL:
            return self._match_factual(expected, actual)
        elif category == QuestionCategory.EVIDENCE:
            return self._match_evidence(expected, actual)
        elif category == QuestionCategory.GAP:
            return self._match_gap(expected, actual)
        else:
            return MatchResult(matched=False, score=0.0, reason="Unknown category")

    def _normalize(self, text: str) -> str:
        """Normalize text for comparison."""
        # Remove extra whitespace
        text = re.sub(r"\s+", "", text)
        # Normalize punctuation
        text = text.replace("：", ":").replace("，", ",").replace("。", ".")
        # Lowercase
        text = text.lower()
        return text

    def _match_factual(self, expected: str, actual: str) -> MatchResult:
        """Match factual question answer."""
        norm_expected = self._normalize(expected)
        norm_actual = self._normalize(actual)

        # Special handling for boolean questions
        if expected in ["是", "否"]:
            return self._match_boolean(expected, actual, norm_actual)

        # Special handling for numeric answers
        if re.search(r"\d", expected):
            return self._match_numeric(expected, actual, norm_expected, norm_actual)

        # Standard containment check
        if norm_expected in norm_actual:
            return MatchResult(
                matched=True,
                score=1.0,
                reason="Exact match after normalization",
                expected_normalized=norm_expected,
                actual_normalized=norm_actual,
            )

        # Try partial match (expected might be substring of actual answer)
        if len(norm_expected) >= 2:
            # Check if any significant part matches
            for i in range(len(norm_expected) - 1):
                substr = norm_expected[i:i+min(3, len(norm_expected)-i)]
                if len(substr) >= 2 and substr in norm_actual:
                    # Partial match found, but not confident
                    pass

        return MatchResult(
            matched=False,
            score=0.0,
            reason=f"Expected '{expected}' not found in actual answer",
            expected_normalized=norm_expected,
            actual_normalized=norm_actual,
        )

    def _match_boolean(self, expected: str, actual: str, norm_actual: str) -> MatchResult:
        """Match boolean (是/否) answers."""
        if expected == "是":
            positive_patterns = ["是", "有", "已", "认罪", "承认", "同意"]
            if any(p in norm_actual for p in positive_patterns):
                # Check for negation
                negation_patterns = ["不是", "没有", "未", "不认罪", "不承认"]
                if any(n in norm_actual for n in negation_patterns):
                    return MatchResult(
                        matched=False,
                        score=0.0,
                        reason="Negation detected",
                        expected_normalized=expected,
                        actual_normalized=norm_actual,
                    )
                return MatchResult(
                    matched=True,
                    score=1.0,
                    reason="Positive boolean match",
                    expected_normalized=expected,
                    actual_normalized=norm_actual,
                )
        elif expected == "否":
            negative_patterns = ["否", "不是", "没有", "未", "不认罪", "不承认", "不"]
            if any(p in norm_actual for p in negative_patterns):
                return MatchResult(
                    matched=True,
                    score=1.0,
                    reason="Negative boolean match",
                    expected_normalized=expected,
                    actual_normalized=norm_actual,
                )

        return MatchResult(
            matched=False,
            score=0.0,
            reason=f"Boolean mismatch: expected '{expected}'",
            expected_normalized=expected,
            actual_normalized=norm_actual,
        )

    def _match_numeric(self, expected: str, actual: str, norm_expected: str, norm_actual: str) -> MatchResult:
        """Match numeric answers with tolerance for formatting."""
        # Extract numeric values
        expected_numbers = re.findall(r"[\d,]+\.?\d*", expected)
        actual_numbers = re.findall(r"[\d,]+\.?\d*", actual)

        if not expected_numbers:
            return MatchResult(
                matched=False,
                score=0.0,
                reason="No numeric value in expected answer",
                expected_normalized=norm_expected,
                actual_normalized=norm_actual,
            )

        # Normalize numbers (remove commas)
        expected_nums_normalized = [n.replace(",", "") for n in expected_numbers]
        actual_nums_normalized = [n.replace(",", "") for n in actual_numbers]

        # Check if all expected numbers are in actual
        matched_count = 0
        for exp_num in expected_nums_normalized:
            if exp_num in actual_nums_normalized:
                matched_count += 1

        if matched_count == len(expected_nums_normalized):
            return MatchResult(
                matched=True,
                score=1.0,
                reason="All numeric values matched",
                expected_normalized=norm_expected,
                actual_normalized=norm_actual,
            )

        # Partial match
        score = matched_count / len(expected_nums_normalized) if expected_nums_normalized else 0
        return MatchResult(
            matched=score >= 0.5,
            score=score,
            reason=f"Partial numeric match: {matched_count}/{len(expected_nums_normalized)}",
            expected_normalized=norm_expected,
            actual_normalized=norm_actual,
        )

    def _match_evidence(self, expected: str, actual: str) -> MatchResult:
        """Match evidence collection answers using coverage."""
        expected_items = self._extract_items(expected)
        actual_items = self._extract_items(actual)

        if not expected_items:
            return MatchResult(
                matched=False,
                score=0.0,
                reason="No items found in expected answer",
            )

        # Calculate coverage
        matched_items = expected_items & actual_items
        coverage = len(matched_items) / len(expected_items)

        return MatchResult(
            matched=coverage >= self.coverage_threshold,
            score=coverage,
            reason=f"Coverage: {len(matched_items)}/{len(expected_items)} = {coverage:.2%}",
            expected_normalized=str(expected_items),
            actual_normalized=str(actual_items),
        )

    def _extract_items(self, text: str) -> set[str]:
        """Extract items from a list-style answer."""
        items = set()

        # Split by common delimiters
        # Try numbered list first
        numbered = re.split(r"\d+[\.、）]\s*", text)
        if len(numbered) > 1:
            for item in numbered[1:]:  # Skip first empty match
                item = item.strip()
                if item:
                    # Take first significant part
                    item = re.split(r"[，,\n]", item)[0].strip()
                    items.add(self._normalize(item))

        # Try comma/semicolon separation
        if len(items) <= 1:
            parts = re.split(r"[，,；;\n]+", text)
            for part in parts:
                part = part.strip()
                if len(part) >= 2:
                    items.add(self._normalize(part))

        return items

    def _match_gap(self, expected: str, actual: str) -> MatchResult:
        """Match gap (missing information) answers."""
        norm_actual = self._normalize(actual)

        # Check for negative keywords
        for keyword in self.negative_keywords:
            if self._normalize(keyword) in norm_actual:
                return MatchResult(
                    matched=True,
                    score=1.0,
                    reason=f"Found negative keyword: {keyword}",
                    expected_normalized=expected,
                    actual_normalized=norm_actual,
                )

        # If LLM tried to answer, it's wrong
        return MatchResult(
            matched=False,
            score=0.0,
            reason="No negative keyword found - LLM may have hallucinated",
            expected_normalized=expected,
            actual_normalized=norm_actual,
        )


if __name__ == "__main__":
    # Test the matcher
    matcher = AnswerMatcher()

    # Test factual
    print("=== Factual Tests ===")
    tests = [
        ("曾庆成", "犯罪嫌疑人是曾庆成", True),
        ("202mg/100ml", "血液酒精浓度为202mg/100ml", True),
        ("202mg/100ml", "202 mg/100ml", True),
        ("是", "嫌疑人认罪认罚", True),
        ("否", "我不认罪认罚", True),
    ]
    for expected, actual, should_match in tests:
        result = matcher.match(QuestionCategory.FACTUAL, expected, actual)
        status = "✓" if result.matched == should_match else "✗"
        print(f"  {status} '{expected}' in '{actual[:30]}...' => {result.matched} ({result.reason})")

    # Test gap
    print("\n=== Gap Tests ===")
    tests = [
        ("材料未显示", "根据材料未显示该信息", True),
        ("材料未显示", "犯罪嫌疑人的血液酒精浓度是202mg/100ml", False),
    ]
    for expected, actual, should_match in tests:
        result = matcher.match(QuestionCategory.GAP, expected, actual)
        status = "✓" if result.matched == should_match else "✗"
        print(f"  {status} '{actual[:30]}...' => {result.matched} ({result.reason})")
