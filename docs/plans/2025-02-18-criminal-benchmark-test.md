# 刑事案件 RAG Benchmark 测试方案实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 创建一个全自动的刑事案件 RAG Benchmark 测试工具，能够自动登录、创建知识库、上传文档、执行检索和聊天测试、验证答案、生成报告。

**Architecture:** 采用模块化设计，分为题目解析、测试运行器、答案匹配器、报告生成器四个核心模块。复用现有 `test/testcases/test_http_api/common.py` 的 API 封装。

**Tech Stack:** Python 3.12, PyYAML, requests, dataclasses

---

## Task 1: 创建目录结构和配置文件

**Files:**
- Create: `test/criminal_benchmark/__init__.py`
- Create: `test/criminal_benchmark/config.yaml`
- Create: `test/criminal_benchmark/.gitignore`

**Step 1: 创建目录结构**

```bash
mkdir -p test/criminal_benchmark/questions
mkdir -p test/criminal_benchmark/runner
mkdir -p test/criminal_benchmark/report
mkdir -p test/criminal_benchmark/reports
```

**Step 2: 创建 `__init__.py` 文件**

```bash
touch test/criminal_benchmark/__init__.py
touch test/criminal_benchmark/questions/__init__.py
touch test/criminal_benchmark/runner/__init__.py
touch test/criminal_benchmark/report/__init__.py
```

**Step 3: 创建配置文件 `test/criminal_benchmark/config.yaml`**

```yaml
# 刑事案件 RAG Benchmark 测试配置

server:
  base_url: "http://127.0.0.1:9380"
  api_version: "v1"

auth:
  email: "qa@infiniflow.org"
  # password 是 "123" 加密后的值
  password: "ctAseGvejiaSWWZ88T/m4FQVOpQyUvP+x7sXtdv3feqZACiQleuewkUi35E16wSd5C5QcnkkcV9cYc8TKPTRZlxappDuirxghxoOvFcJxFU4ixLsDfN33jCHRoDUW81IH9zjij/vaw8IbVyb6vuwg6MX6inOEBRRzVbRYxXOu1wkWY6SsI8X70oF9aeLFp/PzQpjoe/YbSqpTq8qqrmHzn9vO+yvyYyvmDsphXeX8f7fp9c7vUsfOCkM+gHY3PadG+QHa7KI7mzTKgUTZImK6BZtfRBATDTthEUbbaTewY4H0MnWiCeeDhcbeQao6cFy1To8pE3RpmxnGnS8BsBn8w=="

dataset:
  name_prefix: "criminal_benchmark"
  embedding_model: "BAAI/bge-large-zh-v1.5@Builtin"
  chunk_method: "naive"

chat:
  llm_model: "glm-4-flash@ZHIPU-AI"

test:
  parse_timeout: 300
  parse_interval: 5
  top_k: 10
  score_threshold: 0.0

documents:
  - name: "曾庆成危险驾驶案"
    doc_type: "indictment"
    path: "benchmark/起诉意见书/曾庆成危险驾驶案/原始数据/起诉意见书_sample.pdf"
    question_dir: "benchmark/起诉意见书/曾庆成危险驾驶案"
  - name: "陈明飞诈骗案"
    doc_type: "interrogation"
    path: "benchmark/讯问笔录/陈明飞诈骗案/原始数据/讯问笔录_sample.pdf"
    question_dir: "benchmark/讯问笔录/陈明飞诈骗案"

# 答案匹配配置
matching:
  factual:
    # 事实型题目：标准化后包含匹配
    normalize_whitespace: true
    case_sensitive: false
  evidence:
    # 证据集合型：覆盖率阈值
    coverage_threshold: 0.8
  gap:
    # 冲突缺口型：否定关键词
    negative_keywords:
      - "材料未显示"
      - "文档未提及"
      - "无法确定"
      - "未记载"
      - "没有信息"
      - "未找到"
      - "无法从材料中得知"
      - "材料中没有"
      - "未提供"
```

**Step 4: 创建 `.gitignore`**

```
# 忽略生成的报告
reports/

# 忽略缓存
__pycache__/
*.pyc
.pytest_cache/

# 忽略临时文件
*.tmp
*.log
```

**Step 5: Commit**

```bash
git add test/criminal_benchmark/
git commit -m "feat(criminal-benchmark): add project structure and config"
```

---

## Task 2: 实现数据模型

**Files:**
- Create: `test/criminal_benchmark/models.py`

**Step 1: 创建数据模型文件**

```python
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
"""Data models for criminal benchmark testing."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class QuestionCategory(Enum):
    """Question category types."""
    FACTUAL = "factual"
    EVIDENCE = "evidence"
    GAP = "gap"


class DocType(Enum):
    """Document types."""
    INDICTMENT = "indictment"
    INTERROGATION = "interrogation"


class GateStatus(Enum):
    """Answer Gate validation status."""
    VALID = "valid"
    NO_EVIDENCE = "no_evidence"
    CITATION_INSUFFICIENT = "citation_insufficient"


@dataclass
class Question:
    """A benchmark question with expected answer."""
    id: str
    case: str
    doc_type: DocType
    category: QuestionCategory
    question: str
    expected_answer: str
    evidence_text: str = ""
    position: str = ""
    title: str = ""

    def __post_init__(self):
        """Convert string enums to proper types."""
        if isinstance(self.doc_type, str):
            self.doc_type = DocType(self.doc_type)
        if isinstance(self.category, str):
            self.category = QuestionCategory(self.category)


@dataclass
class ChunkInfo:
    """Information about a retrieved chunk."""
    chunk_id: str
    content: str
    score: float
    document_id: str
    document_name: str
    page_num: Optional[int] = None
    bbox: Optional[list] = None


@dataclass
class Citation:
    """Citation information from LLM answer."""
    chunk_id: str
    excerpt: str
    page_index: Optional[int] = None
    bbox: Optional[list] = None


@dataclass
class MatchResult:
    """Result of answer matching."""
    matched: bool
    score: float
    reason: str = ""
    expected_normalized: str = ""
    actual_normalized: str = ""


@dataclass
class TestResult:
    """Result of a single test case."""
    question_id: str
    question: str
    expected_answer: str
    actual_answer: str
    matched: bool
    score: float
    category: QuestionCategory
    case: str

    # Retrieval info
    retrieved_chunks: list[ChunkInfo] = field(default_factory=list)
    retrieval_count: int = 0

    # Citation info
    citations: list[Citation] = field(default_factory=list)

    # Answer Gate info
    gate_status: Optional[GateStatus] = None
    gate_errors: list[str] = field(default_factory=list)

    # Timing
    retrieval_time_ms: float = 0.0
    chat_time_ms: float = 0.0
    total_time_ms: float = 0.0

    # Error info
    error: Optional[str] = None


@dataclass
class BenchmarkSummary:
    """Summary of benchmark test results."""
    total: int = 0
    passed: int = 0
    failed: int = 0
    score: float = 0.0

    # By category
    factual_total: int = 0
    factual_passed: int = 0
    evidence_total: int = 0
    evidence_passed: int = 0
    gap_total: int = 0
    gap_passed: int = 0

    # By case
    case_stats: dict = field(default_factory=dict)

    # Timing
    total_time_ms: float = 0.0
    avg_time_ms: float = 0.0

    def calculate(self, results: list[TestResult]):
        """Calculate summary statistics from results."""
        self.total = len(results)
        self.passed = sum(1 for r in results if r.matched)
        self.failed = self.total - self.passed
        self.score = self.passed / self.total if self.total > 0 else 0.0

        # By category
        for r in results:
            if r.category == QuestionCategory.FACTUAL:
                self.factual_total += 1
                if r.matched:
                    self.factual_passed += 1
            elif r.category == QuestionCategory.EVIDENCE:
                self.evidence_total += 1
                if r.matched:
                    self.evidence_passed += 1
            elif r.category == QuestionCategory.GAP:
                self.gap_total += 1
                if r.matched:
                    self.gap_passed += 1

        # By case
        case_results = {}
        for r in results:
            if r.case not in case_results:
                case_results[r.case] = {"total": 0, "passed": 0}
            case_results[r.case]["total"] += 1
            if r.matched:
                case_results[r.case]["passed"] += 1
        self.case_stats = case_results

        # Timing
        self.total_time_ms = sum(r.total_time_ms for r in results)
        self.avg_time_ms = self.total_time_ms / self.total if self.total > 0 else 0.0


@dataclass
class BenchmarkReport:
    """Full benchmark report."""
    timestamp: str
    config: dict
    summary: BenchmarkSummary
    results: list[TestResult]

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "meta": {
                "timestamp": self.timestamp,
                "config": self.config,
            },
            "summary": {
                "total": self.summary.total,
                "passed": self.summary.passed,
                "failed": self.summary.failed,
                "score": round(self.summary.score, 4),
                "by_category": {
                    "factual": {
                        "total": self.summary.factual_total,
                        "passed": self.summary.factual_passed,
                        "score": round(self.summary.factual_passed / self.summary.factual_total, 4) if self.summary.factual_total > 0 else 0,
                    },
                    "evidence": {
                        "total": self.summary.evidence_total,
                        "passed": self.summary.evidence_passed,
                        "score": round(self.summary.evidence_passed / self.summary.evidence_total, 4) if self.summary.evidence_total > 0 else 0,
                    },
                    "gap": {
                        "total": self.summary.gap_total,
                        "passed": self.summary.gap_passed,
                        "score": round(self.summary.gap_passed / self.summary.gap_total, 4) if self.summary.gap_total > 0 else 0,
                    },
                },
                "by_case": {
                    case: {
                        "total": stats["total"],
                        "passed": stats["passed"],
                        "score": round(stats["passed"] / stats["total"], 4) if stats["total"] > 0 else 0,
                    }
                    for case, stats in self.summary.case_stats.items()
                },
                "timing": {
                    "total_ms": round(self.summary.total_time_ms, 2),
                    "avg_ms": round(self.summary.avg_time_ms, 2),
                },
            },
            "results": [
                {
                    "question_id": r.question_id,
                    "question": r.question,
                    "expected_answer": r.expected_answer,
                    "actual_answer": r.actual_answer,
                    "matched": r.matched,
                    "score": round(r.score, 4),
                    "category": r.category.value,
                    "case": r.case,
                    "retrieval_count": r.retrieval_count,
                    "gate_status": r.gate_status.value if r.gate_status else None,
                    "gate_errors": r.gate_errors,
                    "timing": {
                        "retrieval_ms": round(r.retrieval_time_ms, 2),
                        "chat_ms": round(r.chat_time_ms, 2),
                        "total_ms": round(r.total_time_ms, 2),
                    },
                    "error": r.error,
                }
                for r in self.results
            ],
        }
```

**Step 2: Commit**

```bash
git add test/criminal_benchmark/models.py
git commit -m "feat(criminal-benchmark): add data models"
```

---

## Task 3: 实现题目解析器

**Files:**
- Create: `test/criminal_benchmark/questions/parser.py`

**Step 1: 创建题目解析器**

```python
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
"""Question parser for criminal benchmark."""

import re
from pathlib import Path
from typing import Optional

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from test.criminal_benchmark.models import Question, QuestionCategory, DocType


def parse_category_from_filename(filename: str) -> Optional[QuestionCategory]:
    """Extract question category from filename."""
    if "01-事实型" in filename or "factual" in filename.lower():
        return QuestionCategory.FACTUAL
    elif "02-证据集合型" in filename or "evidence" in filename.lower():
        return QuestionCategory.EVIDENCE
    elif "03-冲突缺口型" in filename or "gap" in filename.lower():
        return QuestionCategory.GAP
    return None


def parse_doc_type_from_path(path: str) -> DocType:
    """Extract document type from path."""
    if "起诉意见书" in path or "indictment" in path.lower():
        return DocType.INDICTMENT
    elif "讯问笔录" in path or "interrogation" in path.lower():
        return DocType.INTERROGATION
    return DocType.INDICTMENT  # default


def extract_case_name(path: str) -> str:
    """Extract case name from path."""
    # Extract case name from path like "benchmark/起诉意见书/曾庆成危险驾驶案/..."
    parts = Path(path).parts
    for part in parts:
        if "案" in part:
            return part
    return parts[-2] if len(parts) >= 2 else "unknown"


def parse_question_file(filepath: Path, case: str, doc_type: DocType) -> list[Question]:
    """Parse a single question file and return list of Questions."""
    questions = []
    category = parse_category_from_filename(str(filepath))

    if category is None:
        return questions

    content = filepath.read_text(encoding="utf-8")

    # Split by question headers (## N. Title)
    pattern = r"##\s*(\d+)\.\s*([^\n]+)\n"
    splits = re.split(pattern, content)

    # splits: [preamble, num1, title1, body1, num2, title2, body2, ...]
    if len(splits) < 4:
        return questions

    # Process each question (skip preamble at index 0)
    i = 1
    while i + 2 < len(splits):
        num = splits[i].strip()
        title = splits[i + 1].strip()
        body = splits[i + 2].strip()

        # Extract question text
        question_match = re.search(r"\*\*问题\*\*[：:]\s*([^\n]+)", body)
        question_text = question_match.group(1).strip() if question_match else ""

        # Extract expected answer
        answer_match = re.search(r"\*\*答案\*\*[：:]\s*([^\n]+(?:\n(?!\*\*)[^\n]+)*)", body)
        expected_answer = answer_match.group(1).strip() if answer_match else ""

        # Extract evidence text
        evidence_match = re.search(r"\*\*证据原文\*\*[：:]\s*`([^`]+)`", body)
        evidence_text = evidence_match.group(1).strip() if evidence_match else ""

        # Extract position
        position_match = re.search(r"\*\*位置\*\*[：:]\s*`?([^`\n]+)`?", body)
        position = position_match.group(1).strip() if position_match else ""

        if question_text:
            question_id = f"{case}_{category.value}_{num}"
            questions.append(Question(
                id=question_id,
                case=case,
                doc_type=doc_type,
                category=category,
                question=question_text,
                expected_answer=expected_answer,
                evidence_text=evidence_text,
                position=position,
                title=title,
            ))

        i += 3

    return questions


def load_all_questions(base_path: str = "benchmark") -> list[Question]:
    """Load all questions from benchmark directory."""
    all_questions = []
    base = Path(base_path)

    # Find all question files
    for filepath in base.rglob("*.md"):
        # Skip README files
        if filepath.name.lower() == "readme.md":
            continue

        # Determine doc type and case
        doc_type = parse_doc_type_from_path(str(filepath))
        case = extract_case_name(str(filepath))

        # Parse questions
        questions = parse_question_file(filepath, case, doc_type)
        all_questions.extend(questions)

    return all_questions


def load_questions_for_case(case_name: str, base_path: str = "benchmark") -> list[Question]:
    """Load questions for a specific case."""
    all_questions = load_all_questions(base_path)
    return [q for q in all_questions if q.case == case_name]


def load_questions_for_category(category: QuestionCategory, base_path: str = "benchmark") -> list[Question]:
    """Load questions for a specific category."""
    all_questions = load_all_questions(base_path)
    return [q for q in all_questions if q.category == category]


if __name__ == "__main__":
    # Test the parser
    questions = load_all_questions()
    print(f"Total questions: {len(questions)}")

    # Stats by category
    by_category = {}
    for q in questions:
        cat = q.category.value
        by_category[cat] = by_category.get(cat, 0) + 1

    print("\nBy category:")
    for cat, count in by_category.items():
        print(f"  {cat}: {count}")

    # Stats by case
    by_case = {}
    for q in questions:
        by_case[q.case] = by_case.get(q.case, 0) + 1

    print("\nBy case:")
    for case, count in by_case.items():
        print(f"  {case}: {count}")

    # Print first 3 questions
    print("\nFirst 3 questions:")
    for q in questions[:3]:
        print(f"  [{q.id}] {q.question[:50]}...")
```

**Step 2: 测试解析器**

Run: `uv run python test/criminal_benchmark/questions/parser.py`
Expected: 输出题目统计信息

**Step 3: Commit**

```bash
git add test/criminal_benchmark/questions/parser.py
git commit -m "feat(criminal-benchmark): add question parser"
```

---

## Task 4: 实现答案匹配器

**Files:**
- Create: `test/criminal_benchmark/questions/matcher.py`

**Step 1: 创建答案匹配器**

```python
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
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

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
```

**Step 2: 测试匹配器**

Run: `uv run python test/criminal_benchmark/questions/matcher.py`
Expected: 输出测试结果

**Step 3: Commit**

```bash
git add test/criminal_benchmark/questions/matcher.py
git commit -m "feat(criminal-benchmark): add answer matcher"
```

---

## Task 5: 实现测试运行器

**Files:**
- Create: `test/criminal_benchmark/runner/setup.py`
- Create: `test/criminal_benchmark/runner/retrieval.py`
- Create: `test/criminal_benchmark/runner/chat.py`

**Step 1: 创建 setup.py（登录、知识库、文档管理）**

```python
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
"""Setup runner for criminal benchmark - login, dataset, documents."""

import time
from pathlib import Path
from typing import Optional

import requests


class BenchmarkSetup:
    """Handles setup operations for benchmark testing."""

    def __init__(self, base_url: str, email: str, password: str):
        self.base_url = base_url.rstrip("/")
        self.email = email
        self.password = password
        self.token: Optional[str] = None
        self.session = requests.Session()

    def login(self) -> bool:
        """Login and get API token."""
        url = f"{self.base_url}/api/v1/user/login"
        payload = {
            "email": self.email,
            "password": self.password,
        }

        resp = self.session.post(url, json=payload)
        data = resp.json()

        if data.get("code") != 0:
            raise RuntimeError(f"Login failed: {data.get('message')}")

        self.token = data["data"].get("authorization_token")
        if not self.token:
            # Try to get from cookies
            for cookie in self.session.cookies:
                if cookie.name == "authorization_token":
                    self.token = cookie.value
                    break

        if not self.token:
            raise RuntimeError("No token received after login")

        # Set authorization header
        self.session.headers["Authorization"] = f"Bearer {self.token}"
        return True

    def create_dataset(self, name: str, embedding_model: str, chunk_method: str = "naive") -> str:
        """Create a new dataset and return its ID."""
        url = f"{self.base_url}/api/v1/datasets"
        payload = {
            "name": name,
            "embedding_model": embedding_model,
            "chunk_method": chunk_method,
        }

        resp = self.session.post(url, json=payload)
        data = resp.json()

        if data.get("code") != 0:
            raise RuntimeError(f"Create dataset failed: {data.get('message')}")

        return data["data"]["id"]

    def upload_document(self, dataset_id: str, file_path: str) -> str:
        """Upload a document to dataset and return document ID."""
        url = f"{self.base_url}/api/v1/datasets/{dataset_id}/documents"

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Document not found: {file_path}")

        with path.open("rb") as f:
            files = {"file": (path.name, f)}
            resp = self.session.post(url, files=files)

        data = resp.json()

        if data.get("code") != 0:
            raise RuntimeError(f"Upload document failed: {data.get('message')}")

        # Return first document ID
        return data["data"][0]["id"]

    def parse_document(self, dataset_id: str, document_ids: list[str]) -> bool:
        """Trigger document parsing."""
        url = f"{self.base_url}/api/v1/datasets/{dataset_id}/chunks"
        payload = {"document_ids": document_ids}

        resp = self.session.post(url, json=payload)
        data = resp.json()

        if data.get("code") != 0:
            raise RuntimeError(f"Parse document failed: {data.get('message')}")

        return True

    def wait_for_parsing(
        self,
        dataset_id: str,
        document_ids: list[str],
        timeout: float = 300,
        interval: float = 5,
    ) -> bool:
        """Wait for all documents to finish parsing."""
        url = f"{self.base_url}/api/v1/datasets/{dataset_id}/documents"
        start_time = time.time()

        while time.time() - start_time < timeout:
            resp = self.session.get(url)
            data = resp.json()

            if data.get("code") != 0:
                raise RuntimeError(f"List documents failed: {data.get('message')}")

            docs = {d["id"]: d for d in data["data"].get("docs", [])}

            all_done = True
            for doc_id in document_ids:
                doc = docs.get(doc_id)
                if not doc or doc.get("run") != "DONE":
                    all_done = False
                    break

            if all_done:
                return True

            time.sleep(interval)

        raise TimeoutError(f"Document parsing timeout after {timeout}s")

    def create_chat_assistant(self, name: str, dataset_ids: list[str], llm_model: str) -> str:
        """Create a chat assistant and return its ID."""
        url = f"{self.base_url}/api/v1/chats"
        payload = {
            "name": name,
            "dataset_ids": dataset_ids,
            "llm": {"model_name": llm_model},
        }

        resp = self.session.post(url, json=payload)
        data = resp.json()

        if data.get("code") != 0:
            raise RuntimeError(f"Create chat assistant failed: {data.get('message')}")

        return data["data"]["id"]

    def delete_dataset(self, dataset_id: str) -> bool:
        """Delete a dataset."""
        url = f"{self.base_url}/api/v1/datasets"
        payload = {"ids": [dataset_id]}

        resp = self.session.delete(url, json=payload)
        data = resp.json()

        return data.get("code") == 0

    def delete_chat_assistant(self, chat_id: str) -> bool:
        """Delete a chat assistant."""
        url = f"{self.base_url}/api/v1/chats"
        payload = {"ids": [chat_id]}

        resp = self.session.delete(url, json=payload)
        data = resp.json()

        return data.get("code") == 0
```

**Step 2: 创建 retrieval.py（检索测试）**

```python
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
"""Retrieval runner for criminal benchmark."""

import time
from typing import Optional

import requests

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from test.criminal_benchmark.models import ChunkInfo


class RetrievalRunner:
    """Handles retrieval operations for benchmark testing."""

    def __init__(self, session: requests.Session, base_url: str):
        self.session = session
        self.base_url = base_url.rstrip("/")

    def retrieve(
        self,
        question: str,
        dataset_ids: list[str],
        document_ids: Optional[list[str]] = None,
        top_k: int = 10,
        score_threshold: float = 0.0,
    ) -> tuple[list[ChunkInfo], float]:
        """
        Perform retrieval and return chunks with timing.

        Returns:
            Tuple of (chunks, time_ms)
        """
        url = f"{self.base_url}/api/v1/retrieval"
        payload = {
            "question": question,
            "dataset_ids": dataset_ids,
            "top_k": top_k,
            "score_threshold": score_threshold,
        }

        if document_ids:
            payload["document_ids"] = document_ids

        start_time = time.perf_counter()
        resp = self.session.post(url, json=payload)
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        data = resp.json()

        if data.get("code") != 0:
            raise RuntimeError(f"Retrieval failed: {data.get('message')}")

        # Parse chunks
        chunks = []
        for item in data.get("data", {}).get("chunks", []):
            chunks.append(ChunkInfo(
                chunk_id=item.get("chunk_id", ""),
                content=item.get("content_with_weight", "") or item.get("content", ""),
                score=item.get("similarity", 0.0),
                document_id=item.get("document_id", ""),
                document_name=item.get("docnm_kwd", ""),
                page_num=item.get("page_num_int", [None])[0] if item.get("page_num_int") else None,
                bbox=item.get("bbox"),
            ))

        return chunks, elapsed_ms
```

**Step 3: 创建 chat.py（聊天测试）**

```python
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
"""Chat runner for criminal benchmark."""

import time
from typing import Optional

import requests


class ChatRunner:
    """Handles chat operations for benchmark testing."""

    def __init__(self, session: requests.Session, base_url: str):
        self.session = session
        self.base_url = base_url.rstrip("/")

    def chat(
        self,
        chat_id: str,
        question: str,
        session_id: Optional[str] = None,
        stream: bool = False,
    ) -> tuple[str, dict, float]:
        """
        Send a chat message and get response.

        Returns:
            Tuple of (answer, raw_response, time_ms)
        """
        url = f"{self.base_url}/api/v1/chats/{chat_id}/completions"
        payload = {
            "question": question,
            "stream": stream,
        }

        if session_id:
            payload["session_id"] = session_id

        start_time = time.perf_counter()
        resp = self.session.post(url, json=payload)
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        data = resp.json()

        if data.get("code") != 0:
            raise RuntimeError(f"Chat failed: {data.get('message')}")

        # Extract answer
        answer = data.get("data", {}).get("answer", "")

        return answer, data.get("data", {}), elapsed_ms

    def create_session(self, chat_id: str, name: str = "benchmark_session") -> str:
        """Create a new chat session."""
        url = f"{self.base_url}/api/v1/chats/{chat_id}/sessions"
        payload = {"name": name}

        resp = self.session.post(url, json=payload)
        data = resp.json()

        if data.get("code") != 0:
            raise RuntimeError(f"Create session failed: {data.get('message')}")

        return data["data"]["id"]
```

**Step 4: Commit**

```bash
git add test/criminal_benchmark/runner/
git commit -m "feat(criminal-benchmark): add test runners (setup, retrieval, chat)"
```

---

## Task 6: 实现报告生成器

**Files:**
- Create: `test/criminal_benchmark/report/json_report.py`
- Create: `test/criminal_benchmark/report/md_report.py`

**Step 1: 创建 json_report.py**

```python
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
"""JSON report generator for criminal benchmark."""

import json
from datetime import datetime
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from test.criminal_benchmark.models import BenchmarkReport


def save_json_report(report: BenchmarkReport, output_dir: Path) -> Path:
    """Save report as JSON file."""
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"benchmark_{timestamp}.json"
    filepath = output_dir / filename

    with filepath.open("w", encoding="utf-8") as f:
        json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)

    return filepath
```

**Step 2: 创建 md_report.py**

```python
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
"""Markdown report generator for criminal benchmark."""

from datetime import datetime
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from test.criminal_benchmark.models import BenchmarkReport, TestResult, QuestionCategory


def generate_md_report(report: BenchmarkReport) -> str:
    """Generate Markdown report content."""
    lines = []

    # Header
    lines.append("# 刑事案件 RAG Benchmark 测试报告")
    lines.append("")
    lines.append(f"**测试时间**: {report.timestamp}")
    lines.append("")

    # Summary
    lines.append("## 概要")
    lines.append("")
    lines.append(f"- **总题数**: {report.summary.total}")
    lines.append(f"- **通过**: {report.summary.passed} ({report.summary.score:.1%})")
    lines.append(f"- **失败**: {report.summary.failed}")
    lines.append(f"- **总耗时**: {report.summary.total_time_ms/1000:.1f}s")
    lines.append("")

    # By category
    lines.append("## 按题型分布")
    lines.append("")
    lines.append("| 题型 | 总数 | 通过 | 得分率 |")
    lines.append("|------|------|------|--------|")

    if report.summary.factual_total > 0:
        score = report.summary.factual_passed / report.summary.factual_total
        lines.append(f"| 事实型 | {report.summary.factual_total} | {report.summary.factual_passed} | {score:.1%} |")

    if report.summary.evidence_total > 0:
        score = report.summary.evidence_passed / report.summary.evidence_total
        lines.append(f"| 证据集合型 | {report.summary.evidence_total} | {report.summary.evidence_passed} | {score:.1%} |")

    if report.summary.gap_total > 0:
        score = report.summary.gap_passed / report.summary.gap_total
        lines.append(f"| 冲突缺口型 | {report.summary.gap_total} | {report.summary.gap_passed} | {score:.1%} |")

    lines.append("")

    # By case
    lines.append("## 按案件分布")
    lines.append("")
    lines.append("| 案件 | 总数 | 通过 | 得分率 |")
    lines.append("|------|------|------|--------|")

    for case, stats in report.summary.case_stats.items():
        score = stats["passed"] / stats["total"] if stats["total"] > 0 else 0
        lines.append(f"| {case} | {stats['total']} | {stats['passed']} | {score:.1%} |")

    lines.append("")

    # Failed questions
    failed_results = [r for r in report.results if not r.matched]
    if failed_results:
        lines.append("## 失败题目详情")
        lines.append("")

        for i, r in enumerate(failed_results, 1):
            lines.append(f"### {i}. {r.case} - {r.category.value} #{r.question_id.split('_')[-1]}")
            lines.append("")
            lines.append(f"- **问题**: {r.question}")
            lines.append(f"- **期望答案**: {r.expected_answer}")
            lines.append(f"- **实际答案**: {r.actual_answer[:200]}{'...' if len(r.actual_answer) > 200 else ''}")
            lines.append(f"- **检索数量**: {r.retrieval_count}")
            if r.error:
                lines.append(f"- **错误**: {r.error}")
            lines.append("")

    return "\n".join(lines)


def save_md_report(report: BenchmarkReport, output_dir: Path) -> Path:
    """Save report as Markdown file."""
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"benchmark_{timestamp}.md"
    filepath = output_dir / filename

    content = generate_md_report(report)

    with filepath.open("w", encoding="utf-8") as f:
        f.write(content)

    return filepath
```

**Step 3: Commit**

```bash
git add test/criminal_benchmark/report/
git commit -m "feat(criminal-benchmark): add report generators (JSON, Markdown)"
```

---

## Task 7: 实现主入口脚本

**Files:**
- Create: `test/criminal_benchmark/run_benchmark.py`

**Step 1: 创建主入口脚本**

```python
#!/usr/bin/env python3
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
"""Main entry point for criminal benchmark testing."""

import argparse
import logging
import time
from datetime import datetime
from pathlib import Path

import yaml

# Add project root to path
sys_path = Path(__file__).parent.parent.parent
import sys
sys.path.insert(0, str(sys_path))

from test.criminal_benchmark.models import (
    BenchmarkReport,
    BenchmarkSummary,
    QuestionCategory,
    TestResult,
    GateStatus,
)
from test.criminal_benchmark.questions.parser import load_all_questions, load_questions_for_case
from test.criminal_benchmark.questions.matcher import AnswerMatcher
from test.criminal_benchmark.runner.setup import BenchmarkSetup
from test.criminal_benchmark.runner.retrieval import RetrievalRunner
from test.criminal_benchmark.runner.chat import ChatRunner
from test.criminal_benchmark.report.json_report import save_json_report
from test.criminal_benchmark.report.md_report import save_md_report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def load_config(config_path: Path) -> dict:
    """Load configuration from YAML file."""
    with config_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_benchmark(
    config: dict,
    case_filter: str = None,
    category_filter: str = None,
    cleanup: bool = True,
    base_path: str = "benchmark",
) -> BenchmarkReport:
    """Run the complete benchmark test."""
    start_time = time.time()

    # Load questions
    logger.info("Loading questions...")
    if case_filter:
        questions = load_questions_for_case(case_filter, base_path)
    else:
        questions = load_all_questions(base_path)

    if category_filter:
        questions = [q for q in questions if q.category.value == category_filter]

    logger.info(f"Loaded {len(questions)} questions")

    if not questions:
        raise RuntimeError("No questions found to test")

    # Initialize components
    setup = BenchmarkSetup(
        base_url=config["server"]["base_url"],
        email=config["auth"]["email"],
        password=config["auth"]["password"],
    )
    matcher = AnswerMatcher(
        coverage_threshold=config["matching"]["evidence"]["coverage_threshold"],
        negative_keywords=config["matching"]["gap"]["negative_keywords"],
    )

    # Login
    logger.info("Logging in...")
    setup.login()

    # Create dataset
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dataset_name = f"{config['dataset']['name_prefix']}_{timestamp}"
    logger.info(f"Creating dataset: {dataset_name}")
    dataset_id = setup.create_dataset(
        name=dataset_name,
        embedding_model=config["dataset"]["embedding_model"],
        chunk_method=config["dataset"]["chunk_method"],
    )
    logger.info(f"Dataset created: {dataset_id}")

    # Upload and parse documents
    document_ids = []
    doc_case_map = {}  # Map document_id to case name

    for doc_config in config["documents"]:
        doc_path = Path(base_path).parent / doc_config["path"]
        case_name = doc_config["name"]

        logger.info(f"Uploading document: {doc_path}")
        doc_id = setup.upload_document(dataset_id, str(doc_path))
        document_ids.append(doc_id)
        doc_case_map[doc_id] = case_name
        logger.info(f"Document uploaded: {doc_id}")

    logger.info("Triggering document parsing...")
    setup.parse_document(dataset_id, document_ids)

    logger.info("Waiting for parsing to complete...")
    setup.wait_for_parsing(
        dataset_id,
        document_ids,
        timeout=config["test"]["parse_timeout"],
        interval=config["test"]["parse_interval"],
    )
    logger.info("Parsing completed")

    # Create chat assistant
    chat_name = f"benchmark_chat_{timestamp}"
    logger.info(f"Creating chat assistant: {chat_name}")
    chat_id = setup.create_chat_assistant(
        name=chat_name,
        dataset_ids=[dataset_id],
        llm_model=config["chat"]["llm_model"],
    )
    logger.info(f"Chat assistant created: {chat_id}")

    # Initialize runners
    retrieval_runner = RetrievalRunner(setup.session, config["server"]["base_url"])
    chat_runner = ChatRunner(setup.session, config["server"]["base_url"])

    # Run tests
    results: list[TestResult] = []

    for i, q in enumerate(questions, 1):
        logger.info(f"Testing question {i}/{len(questions)}: {q.question[:50]}...")

        try:
            test_start = time.time()

            # Retrieval
            chunks, retrieval_time = retrieval_runner.retrieve(
                question=q.question,
                dataset_ids=[dataset_id],
                top_k=config["test"]["top_k"],
                score_threshold=config["test"]["score_threshold"],
            )

            # Chat
            answer, chat_data, chat_time = chat_runner.chat(
                chat_id=chat_id,
                question=q.question,
            )

            total_time = (time.time() - test_start) * 1000

            # Match answer
            match_result = matcher.match(q.category, q.expected_answer, answer)

            # Create test result
            result = TestResult(
                question_id=q.id,
                question=q.question,
                expected_answer=q.expected_answer,
                actual_answer=answer,
                matched=match_result.matched,
                score=match_result.score,
                category=q.category,
                case=q.case,
                retrieved_chunks=chunks,
                retrieval_count=len(chunks),
                retrieval_time_ms=retrieval_time,
                chat_time_ms=chat_time,
                total_time_ms=total_time,
            )

            status = "✓" if result.matched else "✗"
            logger.info(f"  {status} Score: {result.score:.2f} | Time: {total_time:.0f}ms")

        except Exception as e:
            logger.error(f"  Error: {e}")
            result = TestResult(
                question_id=q.id,
                question=q.question,
                expected_answer=q.expected_answer,
                actual_answer="",
                matched=False,
                score=0.0,
                category=q.category,
                case=q.case,
                error=str(e),
            )

        results.append(result)

    # Generate summary
    summary = BenchmarkSummary()
    summary.calculate(results)

    # Create report
    report = BenchmarkReport(
        timestamp=datetime.now().isoformat(),
        config={"dataset_name": dataset_name, "chat_name": chat_name},
        summary=summary,
        results=results,
    )

    # Cleanup
    if cleanup:
        logger.info("Cleaning up resources...")
        setup.delete_chat_assistant(chat_id)
        setup.delete_dataset(dataset_id)
        logger.info("Cleanup completed")

    total_time = time.time() - start_time
    logger.info(f"Benchmark completed in {total_time:.1f}s")
    logger.info(f"Results: {summary.passed}/{summary.total} passed ({summary.score:.1%})")

    return report


def main():
    parser = argparse.ArgumentParser(description="Run criminal RAG benchmark tests")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).parent / "config.yaml",
        help="Path to config file",
    )
    parser.add_argument(
        "--case",
        type=str,
        default=None,
        help="Filter by case name",
    )
    parser.add_argument(
        "--category",
        type=str,
        choices=["factual", "evidence", "gap"],
        default=None,
        help="Filter by question category",
    )
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Don't cleanup resources after test",
    )
    parser.add_argument(
        "--base-path",
        type=str,
        default="benchmark",
        help="Base path to benchmark directory",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).parent / "reports",
        help="Output directory for reports",
    )

    args = parser.parse_args()

    # Load config
    config = load_config(args.config)

    # Run benchmark
    report = run_benchmark(
        config=config,
        case_filter=args.case,
        category_filter=args.category,
        cleanup=not args.no_cleanup,
        base_path=args.base_path,
    )

    # Save reports
    json_path = save_json_report(report, args.output_dir)
    logger.info(f"JSON report saved: {json_path}")

    md_path = save_md_report(report, args.output_dir)
    logger.info(f"Markdown report saved: {md_path}")

    # Print summary
    print("\n" + "=" * 60)
    print("BENCHMARK SUMMARY")
    print("=" * 60)
    print(f"Total:   {report.summary.total}")
    print(f"Passed:  {report.summary.passed}")
    print(f"Failed:  {report.summary.failed}")
    print(f"Score:   {report.summary.score:.1%}")
    print("=" * 60)


if __name__ == "__main__":
    main()
```

**Step 2: 测试运行**

Run: `uv run python test/criminal_benchmark/run_benchmark.py --help`
Expected: 显示帮助信息

**Step 3: Commit**

```bash
git add test/criminal_benchmark/run_benchmark.py
git commit -m "feat(criminal-benchmark): add main entry point script"
```

---

## Task 8: 最终集成测试

**Step 1: 运行完整测试**

```bash
cd /home/you/cs/proj/Superyou/ragflow
uv run python test/criminal_benchmark/run_benchmark.py
```

Expected: 完成测试并生成报告

**Step 2: 检查报告**

```bash
ls -la test/criminal_benchmark/reports/
```

**Step 3: 最终 Commit**

```bash
git add test/criminal_benchmark/
git commit -m "feat(criminal-benchmark): complete benchmark testing framework"
```

---

## 执行选择

**Plan complete and saved to `docs/plans/2025-02-18-criminal-benchmark-test.md`.**

**Two execution options:**

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?**
