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
