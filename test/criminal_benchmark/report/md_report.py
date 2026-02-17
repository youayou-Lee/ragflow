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
# Add project root to path
_project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(_project_root))

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
