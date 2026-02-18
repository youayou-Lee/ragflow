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
"""Markdown report generator for RAG evaluation framework."""

from datetime import datetime
from pathlib import Path

import sys

# Add project root to path
_project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(_project_root))

from test.eval.models import BenchmarkReport, QuestionCategory


def save_md_report(report: BenchmarkReport, output_dir: Path) -> Path:
    """
    Save benchmark report as Markdown file.

    Args:
        report: BenchmarkReport to save
        output_dir: Directory to save report in

    Returns:
        Path to saved Markdown file
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"eval_report_{timestamp}.md"
    filepath = output_dir / filename

    lines = []

    # Header
    lines.append("# RAG Evaluation Benchmark Report")
    lines.append("")
    lines.append(f"**Timestamp**: {report.timestamp}")
    lines.append("")

    # Summary
    lines.append("## Summary")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Total Questions | {report.summary.total} |")
    lines.append(f"| Passed | {report.summary.passed} |")
    lines.append(f"| Failed | {report.summary.failed} |")
    lines.append(f"| **Score** | **{report.summary.score:.1%}** |")
    lines.append(f"| Total Time | {report.summary.total_time_ms/1000:.1f}s |")
    lines.append(f"| Avg Time | {report.summary.avg_time_ms:.0f}ms |")
    lines.append("")

    # By Category
    lines.append("## By Category")
    lines.append("")
    lines.append(f"| Category | Total | Passed | Score |")
    lines.append(f"|----------|-------|--------|-------|")

    for cat, total, passed in [
        ("Factual", report.summary.factual_total, report.summary.factual_passed),
        ("Evidence", report.summary.evidence_total, report.summary.evidence_passed),
        ("Gap", report.summary.gap_total, report.summary.gap_passed),
    ]:
        score = passed / total if total > 0 else 0
        lines.append(f"| {cat} | {total} | {passed} | {score:.1%} |")

    lines.append("")

    # By Case
    if report.summary.case_stats:
        lines.append("## By Case")
        lines.append("")
        lines.append(f"| Case | Total | Passed | Score |")
        lines.append(f"|------|-------|--------|-------|")

        for case, stats in report.summary.case_stats.items():
            score = stats["passed"] / stats["total"] if stats["total"] > 0 else 0
            lines.append(f"| {case} | {stats['total']} | {stats['passed']} | {score:.1%} |")

        lines.append("")

    # Detailed Results
    lines.append("## Detailed Results")
    lines.append("")

    # Group by category
    for category in [QuestionCategory.FACTUAL, QuestionCategory.EVIDENCE, QuestionCategory.GAP]:
        cat_results = [r for r in report.results if r.category == category]
        if not cat_results:
            continue

        lines.append(f"### {category.value.capitalize()}")
        lines.append("")

        for r in cat_results:
            status = "✅" if r.matched else "❌"
            lines.append(f"#### {status} {r.question_id}")
            lines.append("")
            lines.append(f"**Question**: {r.question}")
            lines.append("")
            lines.append(f"**Expected**: {r.expected_answer}")
            lines.append("")
            lines.append(f"**Actual**: {r.actual_answer[:500]}{'...' if len(r.actual_answer) > 500 else ''}")
            lines.append("")
            lines.append(f"**Score**: {r.score:.2f}")
            lines.append("")

    # Write to file
    with filepath.open("w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return filepath
