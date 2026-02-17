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
# Add project root to path
_project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(_project_root))

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
