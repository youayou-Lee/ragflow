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
"""Answer matcher for RAG evaluation.

This module provides sophisticated answer matching logic for evaluating
RAG system responses. It supports:
- Factual answers: exact and semantic matching
- Evidence collection: coverage-based evaluation
- Gap detection: negative keyword detection

Note: This is evaluation logic, NOT retrieval tuning.
"""

import re
from typing import Optional

import sys
from pathlib import Path

# Add project root to path
_project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(_project_root))

from test.eval.models import QuestionCategory, MatchResult


class AnswerMatcher:
    """Matcher for comparing expected and actual answers."""

    # Semantic equivalence mappings for evidence types
    EVIDENCE_EQUIVALENCES = {
        # Confession/Statement related
        "供述": ["供述材料", "口供", "供述笔录", "供述内容", "犯罪供述", "嫌疑人供述", "被告人供述"],
        "供述材料": ["供述", "口供", "供述笔录", "供述内容"],
        "口供": ["供述", "供述材料", "供述笔录", "供述内容"],
        # Interrogation records
        "讯问笔录": ["讯问记录", "询问笔录", "询问记录", "审讯笔录", "审讯记录"],
        "询问笔录": ["讯问笔录", "询问记录", "讯问记录"],
        # Testimony
        "证言": ["证人证言", "证词", "证人证词", "证言材料"],
        "证人证言": ["证言", "证词", "证人证词"],
        # Identification
        "辨认笔录": ["辨认记录", "辨认材料", "身份辨认"],
        # Appraisal/Expert opinion
        "鉴定意见": ["鉴定报告", "鉴定结论", "司法鉴定", "检验鉴定", "鉴定书"],
        "鉴定报告": ["鉴定意见", "鉴定结论", "司法鉴定"],
        # Physical evidence
        "物证": ["物证照片", "实物证据", "物证材料"],
        "书证": ["书证材料", "文书证据", "书面证据"],
        # Audio/Video
        "视听资料": ["录音录像", "监控录像", "视频资料", "音频资料", "视听材料"],
        "录音录像": ["视听资料", "监控录像", "视频资料"],
        # Electronic data
        "电子数据": ["电子证据", "电子记录", "数字证据"],
        # On-site records
        "现场勘验笔录": ["勘验笔录", "现场勘验", "勘验检查笔录", "现场笔录"],
        "勘验笔录": ["现场勘验笔录", "勘验检查笔录"],
        # Case materials
        "案卷材料": ["案件材料", "案卷", "卷宗"],
        "起诉意见书": ["起诉书", "公诉书"],
        # Blood/Alcohol test
        "血液酒精检测": ["血醇检测", "酒精检测报告", "血液检测", "酒精含量检测"],
        "酒精检测报告": ["血液酒精检测", "血醇检测", "酒精含量检测"],
        "血液酒精检测报告": ["血醇检测报告", "血液酒精含量检测报告", "酒精含量检测报告", "血醇检验报告"],
        "血醇检测报告": ["血液酒精检测报告", "血液酒精含量检测报告", "酒精含量检测报告"],
        # Additional factual equivalences
        "血液酒精浓度": ["血液中酒精含量", "血醇含量", "酒精含量", "血液酒精含量"],
        "酒精含量": ["血液酒精浓度", "血液中酒精含量", "血醇含量"],
    }

    # Reverse mapping for quick lookup
    EQUIVALENCE_CACHE: dict[str, set[str]] = {}

    def __init__(
        self,
        coverage_threshold: float = 0.5,
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
            "不包含", "未包含", "无相关", "无法查证", "无法核实",
            "缺乏", "缺少", "不存在", "无法回答", "无法判断",
            "暂无", "无记录", "没有记载", "没有显示", "没有提及",
        ]

        # Build reverse equivalence cache
        if not self.EQUIVALENCE_CACHE:
            for key, equivalents in self.EVIDENCE_EQUIVALENCES.items():
                all_terms = set(equivalents) | {key}
                for term in all_terms:
                    self.EQUIVALENCE_CACHE[term] = all_terms

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

    def _get_equivalent_terms(self, term: str) -> set[str]:
        """Get all semantically equivalent terms for a given term."""
        norm_term = self._normalize(term)
        if norm_term in self.EQUIVALENCE_CACHE:
            return self.EQUIVALENCE_CACHE[norm_term]
        return {norm_term}

    def _check_semantic_match(self, expected_item: str, actual_text: str) -> tuple[bool, str]:
        """
        Check if expected item matches actual text using semantic equivalence.

        Returns:
            Tuple of (matched, matched_term)
        """
        norm_actual = self._normalize(actual_text)
        norm_expected = self._normalize(expected_item)

        # Direct match
        if norm_expected in norm_actual:
            return True, norm_expected

        # Check all equivalent terms
        equivalents = self._get_equivalent_terms(expected_item)
        for eq_term in equivalents:
            if eq_term in norm_actual:
                return True, eq_term

        return False, ""

    def _match_factual(self, expected: str, actual: str) -> MatchResult:
        """Match factual question answer with enhanced matching."""
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

        # Try semantic equivalence match
        matched, matched_term = self._check_semantic_match(expected, actual)
        if matched:
            return MatchResult(
                matched=True,
                score=0.95,
                reason=f"Semantic match: '{expected}' ~ '{matched_term}'",
                expected_normalized=norm_expected,
                actual_normalized=norm_actual,
            )

        # Try partial match with confidence scoring
        if len(norm_expected) >= 2:
            partial_score = self._calculate_partial_match_score(norm_expected, norm_actual)
            if partial_score >= 0.6:
                return MatchResult(
                    matched=True,
                    score=partial_score,
                    reason=f"Partial match with score {partial_score:.2f}",
                    expected_normalized=norm_expected,
                    actual_normalized=norm_actual,
                )

        # Try organization name partial matching
        if self._is_likely_organization(expected):
            org_matched = self._match_organization(expected, actual)
            if org_matched:
                return MatchResult(
                    matched=True,
                    score=0.9,
                    reason="Organization name partial match",
                    expected_normalized=norm_expected,
                    actual_normalized=norm_actual,
                )

        return MatchResult(
            matched=False,
            score=0.0,
            reason=f"Expected '{expected}' not found in actual answer",
            expected_normalized=norm_expected,
            actual_normalized=norm_actual,
        )

    def _calculate_partial_match_score(self, expected: str, actual: str) -> float:
        """Calculate partial match score based on overlapping terms."""
        # Extract significant terms (2+ Chinese characters or alphanumeric)
        expected_terms = set(re.findall(r'[\u4e00-\u9fff]{2,}|\d+|[a-zA-Z]+', expected))
        actual_terms = set(re.findall(r'[\u4e00-\u9fff]{2,}|\d+|[a-zA-Z]+', actual))

        if not expected_terms:
            return 0.0

        # Calculate overlap
        overlapping = expected_terms & actual_terms
        if not overlapping:
            return 0.0

        # Score based on coverage of expected terms
        coverage = len(overlapping) / len(expected_terms)

        # Bonus for matching key terms (numbers, proper nouns)
        key_terms = set(re.findall(r'\d+|[A-Z][a-z]+|[\u4e00-\u9fff]{3,}', expected))
        if key_terms:
            key_overlap = key_terms & actual_terms
            key_bonus = len(key_overlap) / len(key_terms) * 0.2
            coverage = min(1.0, coverage + key_bonus)

        return coverage

    def _is_likely_organization(self, text: str) -> bool:
        """Check if text is likely an organization name."""
        org_keywords = ["公安局", "检察院", "法院", "交警", "派出所", "鉴定", "检测",
                       "医院", "公司", "机关", "部门", "大队", "支队", "分局"]
        return any(kw in text for kw in org_keywords)

    def _match_organization(self, expected: str, actual: str) -> bool:
        """Match organization names with partial matching."""
        norm_expected = self._normalize(expected)
        norm_actual = self._normalize(actual)

        # Extract key parts of organization name
        core_parts = re.split(r'[省市县区镇村]', norm_expected)
        for part in core_parts:
            if len(part) >= 2 and part in norm_actual:
                return True

        # Check for significant substring overlap
        for i in range(len(norm_expected) - 3):
            substr = norm_expected[i:i+4]
            if substr in norm_actual:
                return True

        return False

    def _match_boolean(self, expected: str, actual: str, norm_actual: str) -> MatchResult:
        """Match boolean (是/否) answers."""
        if expected == "是":
            positive_patterns = ["是", "有", "已", "认罪", "承认", "同意"]
            if any(p in norm_actual for p in positive_patterns):
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
        """Match evidence collection answers using coverage with semantic matching."""
        expected_items = self._extract_items(expected)
        actual_items = self._extract_items(actual)
        norm_actual = self._normalize(actual)

        if not expected_items:
            return MatchResult(
                matched=False,
                score=0.0,
                reason="No items found in expected answer",
            )

        # Calculate coverage with semantic matching
        matched_items = {}  # exp_item -> (matched_term, match_type)

        for exp_item in expected_items:
            # Try exact match first
            if exp_item in actual_items:
                matched_items[exp_item] = (exp_item, "exact")
                continue

            # Try substring match in actual text
            if exp_item in norm_actual:
                matched_items[exp_item] = (exp_item, "substring")
                continue

            # Try semantic equivalence match
            semantic_matched, matched_term = self._check_semantic_match(exp_item, actual)
            if semantic_matched:
                matched_items[exp_item] = (matched_term, "semantic")
                continue

            # Try fuzzy keyword match
            key_terms = [t for t in re.findall(r'[\u4e00-\u9fff\w]{2,}', exp_item) if len(t) >= 2]
            matched_terms = [term for term in key_terms if term in norm_actual]
            if matched_terms:
                if len(matched_terms) / len(key_terms) >= 0.5:
                    matched_items[exp_item] = (", ".join(matched_terms), "fuzzy")
                    continue

            # Try semantic match on key terms
            for key_term in key_terms:
                term_equivs = self._get_equivalent_terms(key_term)
                for eq_term in term_equivs:
                    if eq_term in norm_actual:
                        matched_items[exp_item] = (eq_term, "term_semantic")
                        break
                if exp_item in matched_items:
                    break

            # Try partial match with single key term (lower confidence)
            if exp_item not in matched_items and key_terms:
                if any(term in norm_actual for term in key_terms):
                    matched_items[exp_item] = (key_terms[0], "partial")

        coverage = len(matched_items) / len(expected_items)

        # Build detailed reason
        match_details = []
        for exp_item, (matched_term, match_type) in matched_items.items():
            if match_type != "exact":
                match_details.append(f"{exp_item}~{matched_term}({match_type})")

        reason = f"Coverage: {len(matched_items)}/{len(expected_items)} = {coverage:.2%}"
        if match_details:
            reason += f" [semantic: {len([d for d in match_details if 'semantic' in d])}]"

        return MatchResult(
            matched=coverage >= self.coverage_threshold,
            score=coverage,
            reason=reason,
            expected_normalized=str(expected_items),
            actual_normalized=str(actual_items),
        )

    def _extract_items(self, text: str) -> set[str]:
        """Extract items from a list-style answer."""
        items = set()

        # Try numbered list first
        numbered_pattern = r"\d+[\.、）]\s*"
        if re.search(numbered_pattern, text):
            numbered = re.split(numbered_pattern, text)
            for item in numbered[1:]:
                item = item.strip()
                if item:
                    item = re.split(r"[\n，,]", item)[0].strip()
                    if len(item) >= 2:
                        items.add(self._normalize(item))

        # Try Chinese enumeration comma (、) separation
        if "、" in text:
            parts = text.split("、")
            for part in parts:
                part = part.strip()
                part = re.sub(r'^[0-9\.、）\s]+', '', part)
                part = re.sub(r'[：:。\s]+$', '', part)
                if len(part) >= 2:
                    items.add(self._normalize(part))

        # Try comma/semicolon separation if we don't have enough items
        if len(items) <= 1:
            parts = re.split(r"[，,；;\n]+", text)
            for part in parts:
                part = part.strip()
                if len(part) >= 2:
                    items.add(self._normalize(part))

        return items

    def _match_gap(self, expected: str, actual: str) -> MatchResult:
        """Match gap (missing information) answers with enhanced detection."""
        norm_actual = self._normalize(actual)

        # Check for negative keywords
        for phrase in self.negative_keywords:
            norm_phrase = self._normalize(phrase)
            if norm_phrase in norm_actual:
                return MatchResult(
                    matched=True,
                    score=1.0,
                    reason=f"Found negative phrase: {phrase}",
                    expected_normalized=expected,
                    actual_normalized=norm_actual,
                )

        # Check for "没有" + noun patterns
        no_info_patterns = re.findall(r"没有[\u4e00-\u9fff]{1,4}|无[\u4e00-\u9fff]{1,4}|未[\u4e00-\u9fff]{1,4}", actual)
        if no_info_patterns:
            return MatchResult(
                matched=True,
                score=0.9,
                reason=f"Found negative pattern: {no_info_patterns}",
                expected_normalized=expected,
                actual_normalized=norm_actual,
            )

        # Check if answer is very short but doesn't contain substantive info
        short_negatives = ["无", "不适用", "无信息", "无记录", "未提供", "缺失"]
        if norm_actual in [self._normalize(sn) for sn in short_negatives]:
            return MatchResult(
                matched=True,
                score=1.0,
                reason=f"Found short negative: {norm_actual}",
                expected_normalized=expected,
                actual_normalized=norm_actual,
            )

        # Check for sentences starting with negation about the document
        negation_starters = [
            r"^(根据|从|在)?(材料|文档|卷宗)(中)?(没有|未|无|不)",
            r"^(无法|未能)(从|在)(材料|文档)",
            r"^材料(中)?(没有|未|无)",
            r"^文档(中)?(没有|未|无)",
        ]
        for pattern in negation_starters:
            if re.search(pattern, norm_actual):
                return MatchResult(
                    matched=True,
                    score=0.95,
                    reason=f"Found negation pattern: {pattern}",
                    expected_normalized=expected,
                    actual_normalized=norm_actual,
                )

        # Check if the answer contains specific details
        has_specific_details = bool(
            re.search(r'\d{4}年|\d{1,2}月\d{1,2}日|\d+mg|\d+元|[曾陈李王张刘赵]', actual)
        )

        if has_specific_details:
            return MatchResult(
                matched=False,
                score=0.0,
                reason="Gap question but LLM found specific information",
                expected_normalized=expected,
                actual_normalized=norm_actual,
            )

        return MatchResult(
            matched=False,
            score=0.0,
            reason="No negative indicator found - LLM may have hallucinated",
            expected_normalized=expected,
            actual_normalized=norm_actual,
        )
