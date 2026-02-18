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
"""Question parser for RAG evaluation framework."""

import re
from pathlib import Path

import sys

# Add project root to path
_project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(_project_root))

from test.eval.models import Question, QuestionCategory, DocType
from test.eval.questions.types import (
    parse_category_from_filename,
    parse_doc_type_from_path,
    extract_case_name,
)


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
