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
"""Question types and utilities for RAG evaluation framework."""

from typing import Optional

import sys
from pathlib import Path

# Add project root to path
_project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(_project_root))

from test.eval.models import QuestionCategory, DocType


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
    parts = Path(path).parts
    for part in parts:
        if "案" in part:
            return part
    return parts[-2] if len(parts) >= 2 else "unknown"
