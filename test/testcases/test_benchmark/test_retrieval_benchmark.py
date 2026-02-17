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
Benchmark retrieval test for criminal RAG system.

This module tests the retrieval performance of the RAGFlow criminal RAG system
using benchmark question sets from real legal cases.

Test categories:
- Factual questions: Verify exact fact extraction
- Evidence collection questions: Verify multi-source information aggregation
- Conflict/missing questions: Verify system can identify missing information
"""
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import pytest

# Import benchmark utilities from test/benchmark/
import sys
# Add the test directory to the path to enable package imports
test_dir = str(Path(__file__).parent.parent.parent)
if test_dir not in sys.path:
    sys.path.insert(0, test_dir)

from benchmark.http_client import HttpClient
from benchmark.retrieval import build_payload, run_retrieval


@dataclass
class BenchmarkQuestion:
    """Represents a single benchmark question."""
    number: int
    topic: str
    question: str
    answer: str
    evidence: str
    location: str
    explanation: Optional[str] = None  # For conflict questions


@dataclass
class BenchmarkCase:
    """Represents a benchmark case with all its questions."""
    name: str
    document_type: str
    factual_questions: list[BenchmarkQuestion] = field(default_factory=list)
    evidence_questions: list[BenchmarkQuestion] = field(default_factory=list)
    conflict_questions: list[BenchmarkQuestion] = field(default_factory=list)


@dataclass
class QuestionResult:
    """Result of testing a single question."""
    question: BenchmarkQuestion
    retrieved_chunks: list[dict]
    passed: bool
    reason: str
    latency_ms: float


def parse_question_file(file_path: Path, question_type: str) -> list[BenchmarkQuestion]:
    """Parse a markdown question file and extract questions."""
    content = file_path.read_text(encoding="utf-8")
    questions = []

    # Split by question headers (## N. Topic)
    pattern = r"## (\d+)\.\s+(.+?)\n\n\*\*问题\*\*[：:]\s*(.+?)\n\n\*\*答案\*\*[：:]\s*(.+?)(?=\n\n\*\*位置\*\*)"
    matches = re.findall(pattern, content, re.DOTALL)

    for match in matches:
        number = int(match[0])
        topic = match[1].strip()
        question = match[2].strip()
        answer = match[3].strip()

        # Extract evidence
        evidence_match = re.search(r"\*\*证据原文\*\*[：:]\s*`(.+?)`", content[content.find(match[3]):content.find("---", content.find(match[3]))] if "---" in content[content.find(match[3]):] else content[content.find(match[3]):])
        evidence = evidence_match.group(1) if evidence_match else ""

        # Extract location
        location_match = re.search(r"\*\*位置\*\*[：:]\s*`?([^`\n]+)`?", content[content.find(match[3]):content.find("---", content.find(match[3]))] if "---" in content[content.find(match[3]):] else content[content.find(match[3]):])
        location = location_match.group(1).strip() if location_match else "无"

        # Extract explanation for conflict questions
        explanation = None
        if question_type == "conflict":
            explanation_match = re.search(r"\*\*说明\*\*[：:]\s*(.+?)(?=\n\n---|\n\n##|\Z)", content[content.find(match[3]):], re.DOTALL)
            if explanation_match:
                explanation = explanation_match.group(1).strip()

        questions.append(BenchmarkQuestion(
            number=number,
            topic=topic,
            question=question,
            answer=answer,
            evidence=evidence,
            location=location,
            explanation=explanation
        ))

    return questions


def load_benchmark_case(case_dir: Path) -> BenchmarkCase:
    """Load all questions for a benchmark case."""
    # Extract case info from README or directory name
    case_name = case_dir.name
    document_type = case_dir.parent.name

    case = BenchmarkCase(
        name=case_name,
        document_type=document_type
    )

    # Load factual questions
    factual_file = case_dir / "01-事实型题目.md"
    if factual_file.exists():
        case.factual_questions = parse_question_file(factual_file, "factual")

    # Load evidence collection questions
    evidence_file = case_dir / "02-证据集合型题目.md"
    if evidence_file.exists():
        case.evidence_questions = parse_question_file(evidence_file, "evidence")

    # Load conflict/missing questions
    conflict_file = case_dir / "03-冲突缺口型题目.md"
    if conflict_file.exists():
        case.conflict_questions = parse_question_file(conflict_file, "conflict")

    return case


def check_factual_answer(question: BenchmarkQuestion, chunks: list[dict]) -> tuple[bool, str]:
    """
    Check if the expected answer appears in retrieved chunks.

    For factual questions, we verify that the answer string appears
    in at least one of the retrieved chunks.
    """
    answer = question.answer.lower().strip()

    for i, chunk in enumerate(chunks):
        content = chunk.get("content", "").lower()
        if answer in content:
            return True, f"Found in chunk {i+1} (similarity: {chunk.get('similarity', 'N/A')})"

    return False, f"Answer '{question.answer}' not found in any retrieved chunk"


def check_evidence_answer(question: BenchmarkQuestion, chunks: list[dict]) -> tuple[bool, str]:
    """
    Check if evidence items are found in retrieved chunks.

    For evidence collection questions, we check if key pieces of evidence
    are present in the retrieved chunks.
    """
    # For evidence questions, we look for key terms from the answer
    answer_lines = [line.strip() for line in question.answer.split("\n") if line.strip()]

    found_count = 0
    missing_items = []

    for line in answer_lines:
        # Extract key content (remove numbering and markdown)
        key_content = re.sub(r"^\d+\.\s*", "", line)
        key_content = re.sub(r"\*\*[^*]+\*\*[：:]\s*", "", key_content)
        key_content = key_content.strip()

        if not key_content:
            continue

        found = False
        for chunk in chunks:
            content = chunk.get("content", "")
            if key_content.lower() in content.lower():
                found = True
                break

        if found:
            found_count += 1
        else:
            missing_items.append(key_content[:50])

    total_items = len([l for l in answer_lines if l.strip()])

    if found_count == total_items:
        return True, f"All {found_count} evidence items found"
    elif found_count > 0:
        return False, f"Partial: {found_count}/{total_items} items found. Missing: {missing_items[:2]}"
    else:
        return False, "No evidence items found in retrieved chunks"


def check_conflict_answer(question: BenchmarkQuestion, chunks: list[dict]) -> tuple[bool, str]:
    """
    Check if system correctly identifies missing information.

    For conflict/missing questions, the expected answer is "材料未显示".
    The retrieval should either:
    1. Return no relevant chunks (low similarity), or
    2. Return chunks that don't actually contain the answer
    """
    # Check if any retrieved chunk contains relevant information
    # that would contradict "材料未显示"

    # Key terms that might indicate the answer exists
    question_keywords = set(re.findall(r"[\u4e00-\u9fa5]+", question.question))
    question_keywords.discard("什么")
    question_keywords.discard("哪些")
    question_keywords.discard("是否")
    question_keywords.discard("多少")
    question_keywords.discard("哪里")
    question_keywords.discard("谁")

    # Check top chunks for relevant content
    relevant_content_found = False
    for chunk in chunks[:3]:  # Check top 3 chunks
        content = chunk.get("content", "")
        similarity = chunk.get("similarity", 0)

        # If high similarity and contains keywords, might be relevant
        if similarity and similarity > 0.5:
            # Check if content actually addresses the question
            keyword_matches = sum(1 for kw in question_keywords if kw in content)
            if keyword_matches >= len(question_keywords) / 2:
                relevant_content_found = True
                break

    # For conflict questions, we want to see that the system:
    # - Either returns low-similarity chunks (indicating nothing relevant)
    # - Or returns chunks that don't actually answer the question
    if not relevant_content_found:
        return True, "Correctly identified as missing information"
    else:
        return False, "May have found relevant content - verify manually"


def run_retrieval_test(
    client: HttpClient,
    dataset_ids: list[str],
    question: BenchmarkQuestion,
    question_type: str
) -> QuestionResult:
    """Run a single retrieval test and return the result."""
    payload = build_payload(
        question=question.question,
        dataset_ids=dataset_ids,
        payload={"top_k": 10, "size": 10}
    )

    sample = run_retrieval(client, payload)

    if sample.error:
        return QuestionResult(
            question=question,
            retrieved_chunks=[],
            passed=False,
            reason=f"API error: {sample.error}",
            latency_ms=0
        )

    chunks = sample.response.get("data", {}).get("chunks", [])

    # Check answer based on question type
    if question_type == "factual":
        passed, reason = check_factual_answer(question, chunks)
    elif question_type == "evidence":
        passed, reason = check_evidence_answer(question, chunks)
    elif question_type == "conflict":
        passed, reason = check_conflict_answer(question, chunks)
    else:
        passed, reason = False, f"Unknown question type: {question_type}"

    return QuestionResult(
        question=question,
        retrieved_chunks=chunks,
        passed=passed,
        reason=reason,
        latency_ms=(sample.latency or 0) * 1000
    )


class TestBenchmarkRetrieval:
    """Test class for benchmark retrieval tests."""

    @pytest.fixture(scope="class")
    def client(self):
        """Create HTTP client for API calls."""
        base_url = os.getenv("RAGFLOW_HOST", "http://127.0.0.1:9380")
        api_key = os.getenv("RAGFLOW_API_KEY", "")

        return HttpClient(
            base_url=base_url,
            api_key=api_key if api_key else None
        )

    @pytest.fixture(scope="class")
    def dataset_ids(self):
        """Get dataset IDs for benchmark testing."""
        # These should be configured based on the actual benchmark datasets
        # Format: comma-separated dataset IDs
        ids_str = os.getenv("BENCHMARK_DATASET_IDS", "")
        if ids_str:
            return [id.strip() for id in ids_str.split(",") if id.strip()]
        return []

    @pytest.fixture(scope="class")
    def benchmark_dir(self):
        """Get benchmark directory path."""
        return Path(__file__).parent.parent.parent.parent / "benchmark"

    @pytest.fixture(scope="class")
    def cases(self, benchmark_dir):
        """Load all benchmark cases."""
        cases = []
        for case_type_dir in benchmark_dir.iterdir():
            if case_type_dir.is_dir() and case_type_dir.name != "__pycache__":
                for case_dir in case_type_dir.iterdir():
                    if case_dir.is_dir():
                        cases.append(load_benchmark_case(case_dir))
        return cases

    @pytest.mark.p1
    def test_factual_questions(self, client, dataset_ids, cases):
        """Test factual question retrieval accuracy."""
        if not dataset_ids:
            pytest.skip("BENCHMARK_DATASET_IDS not configured")

        results = []
        for case in cases:
            for question in case.factual_questions:
                result = run_retrieval_test(client, dataset_ids, question, "factual")
                results.append(result)

        # Calculate pass rate
        passed = sum(1 for r in results if r.passed)
        total = len(results)

        # Generate report
        report = generate_report("事实型题目", results)
        print("\n" + report)

        # Assert minimum pass rate (e.g., 80%)
        pass_rate = passed / total if total > 0 else 0
        assert pass_rate >= 0.8, f"Factual question pass rate {pass_rate:.1%} below 80%"

    @pytest.mark.p1
    def test_evidence_questions(self, client, dataset_ids, cases):
        """Test evidence collection question completeness."""
        if not dataset_ids:
            pytest.skip("BENCHMARK_DATASET_IDS not configured")

        results = []
        for case in cases:
            for question in case.evidence_questions:
                result = run_retrieval_test(client, dataset_ids, question, "evidence")
                results.append(result)

        # Calculate pass rate
        passed = sum(1 for r in results if r.passed)
        total = len(results)

        # Generate report
        report = generate_report("证据集合型题目", results)
        print("\n" + report)

        # Assert minimum pass rate (e.g., 70%)
        pass_rate = passed / total if total > 0 else 0
        assert pass_rate >= 0.7, f"Evidence question pass rate {pass_rate:.1%} below 70%"

    @pytest.mark.p1
    def test_conflict_questions(self, client, dataset_ids, cases):
        """Test conflict/missing question handling."""
        if not dataset_ids:
            pytest.skip("BENCHMARK_DATASET_IDS not configured")

        results = []
        for case in cases:
            for question in case.conflict_questions:
                result = run_retrieval_test(client, dataset_ids, question, "conflict")
                results.append(result)

        # Calculate pass rate
        passed = sum(1 for r in results if r.passed)
        total = len(results)

        # Generate report
        report = generate_report("冲突缺口型题目", results)
        print("\n" + report)

        # Assert minimum pass rate (e.g., 70%)
        pass_rate = passed / total if total > 0 else 0
        assert pass_rate >= 0.7, f"Conflict question pass rate {pass_rate:.1%} below 70%"


def generate_report(title: str, results: list[QuestionResult]) -> str:
    """Generate a markdown report for test results."""
    lines = [
        f"# {title}测试报告",
        "",
        f"**测试时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## 测试结果",
        "",
        "| # | 问题 | 预期答案 | 状态 | 原因 |",
        "|---|------|----------|------|------|"
    ]

    passed = 0
    for result in results:
        status = "✅" if result.passed else "❌"
        if result.passed:
            passed += 1

        # Truncate for readability
        question_short = result.question.question[:30] + "..." if len(result.question.question) > 30 else result.question.question
        answer_short = result.question.answer[:20] + "..." if len(result.question.answer) > 20 else result.question.answer
        reason_short = result.reason[:40] + "..." if len(result.reason) > 40 else result.reason

        lines.append(f"| {result.question.number} | {question_short} | {answer_short} | {status} | {reason_short} |")

    total = len(results)
    pass_rate = (passed / total * 100) if total > 0 else 0

    lines.extend([
        "",
        f"## 统计",
        "",
        f"- **通过**: {passed}/{total}",
        f"- **召回率**: {pass_rate:.1f}%",
    ])

    return "\n".join(lines)


def generate_full_report(cases: list[BenchmarkCase], all_results: dict[str, list[QuestionResult]]) -> str:
    """Generate a complete benchmark test report."""
    lines = [
        "# Benchmark 检索测试报告",
        "",
        f"**测试日期**: {datetime.now().strftime('%Y-%m-%d')}",
        f"**RAGFlow 版本**: (from git)",
        f"**Embedding 模型**: (from config)",
        "",
        "---",
        ""
    ]

    for case in cases:
        lines.extend([
            f"## {case.document_type} - {case.name}",
            ""
        ])

        # Factual questions
        if case.factual_questions:
            factual_results = [r for r in all_results.get("factual", []) if r.question in case.factual_questions]
            lines.extend(generate_case_section("事实型题目", factual_results, len(case.factual_questions)))

        # Evidence questions
        if case.evidence_questions:
            evidence_results = [r for r in all_results.get("evidence", []) if r.question in case.evidence_questions]
            lines.extend(generate_case_section("证据集合型题目", evidence_results, len(case.evidence_questions)))

        # Conflict questions
        if case.conflict_questions:
            conflict_results = [r for r in all_results.get("conflict", []) if r.question in case.conflict_questions]
            lines.extend(generate_case_section("冲突缺口型题目", conflict_results, len(case.conflict_questions)))

    # Summary
    total_factual = len(all_results.get("factual", []))
    total_evidence = len(all_results.get("evidence", []))
    total_conflict = len(all_results.get("conflict", []))

    passed_factual = sum(1 for r in all_results.get("factual", []) if r.passed)
    passed_evidence = sum(1 for r in all_results.get("evidence", []) if r.passed)
    passed_conflict = sum(1 for r in all_results.get("conflict", []) if r.passed)

    lines.extend([
        "---",
        "",
        "## 总结",
        "",
        f"- **事实型召回率**: {passed_factual}/{total_factual}",
        f"- **证据集合型完整性**: {passed_evidence}/{total_evidence}",
        f"- **冲突缺口型诚实性**: {passed_conflict}/{total_conflict}",
        ""
    ])

    return "\n".join(lines)


def generate_case_section(title: str, results: list[QuestionResult], expected_count: int) -> list[str]:
    """Generate a section for a question type within a case."""
    lines = [
        f"### {title}（{expected_count}题）",
        "",
        "| # | 问题 | 预期答案 | 状态 | 原因 |",
        "|---|------|----------|------|------|"
    ]

    passed = 0
    for result in results:
        status = "✅" if result.passed else "❌"
        if result.passed:
            passed += 1

        question_short = result.question.question[:40]
        answer_short = result.question.answer[:25]
        reason_short = result.reason[:35]

        lines.append(f"| {result.question.number} | {question_short} | {answer_short} | {status} | {reason_short} |")

    lines.extend([
        "",
        f"**召回率: {passed}/{len(results)}**",
        ""
    ])

    return lines


# Standalone script execution
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run benchmark retrieval tests")
    parser.add_argument("--host", default="http://127.0.0.1:9380", help="RAGFlow host URL")
    parser.add_argument("--api-key", default="", help="RAGFlow API key")
    parser.add_argument("--dataset-ids", required=True, help="Comma-separated dataset IDs")
    parser.add_argument("--output", default="RESULTS.md", help="Output report file")

    args = parser.parse_args()

    # Setup client
    client = HttpClient(
        base_url=args.host,
        api_key=args.api_key if args.api_key else None
    )

    dataset_ids = [id.strip() for id in args.dataset_ids.split(",")]

    # Load cases
    benchmark_dir = Path(__file__).parent.parent.parent.parent / "benchmark"
    cases = []
    for case_type_dir in benchmark_dir.iterdir():
        if case_type_dir.is_dir() and case_type_dir.name != "__pycache__":
            for case_dir in case_type_dir.iterdir():
                if case_dir.is_dir():
                    cases.append(load_benchmark_case(case_dir))

    # Run tests
    all_results: dict[str, list[QuestionResult]] = {
        "factual": [],
        "evidence": [],
        "conflict": []
    }

    for case in cases:
        print(f"\nTesting case: {case.document_type} - {case.name}")

        for question in case.factual_questions:
            result = run_retrieval_test(client, dataset_ids, question, "factual")
            all_results["factual"].append(result)
            print(f"  Factual Q{question.number}: {'✅' if result.passed else '❌'}")

        for question in case.evidence_questions:
            result = run_retrieval_test(client, dataset_ids, question, "evidence")
            all_results["evidence"].append(result)
            print(f"  Evidence Q{question.number}: {'✅' if result.passed else '❌'}")

        for question in case.conflict_questions:
            result = run_retrieval_test(client, dataset_ids, question, "conflict")
            all_results["conflict"].append(result)
            print(f"  Conflict Q{question.number}: {'✅' if result.passed else '❌'}")

    # Generate report
    report = generate_full_report(cases, all_results)

    output_path = Path(__file__).parent / args.output
    output_path.write_text(report, encoding="utf-8")
    print(f"\nReport saved to: {output_path}")

    # Print summary
    total_passed = sum(1 for results in all_results.values() for r in results if r.passed)
    total_questions = sum(len(results) for results in all_results.values())
    print(f"\nOverall: {total_passed}/{total_questions} ({total_passed/total_questions*100:.1f}%)")
