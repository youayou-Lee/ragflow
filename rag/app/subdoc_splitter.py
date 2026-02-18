#
#  Copyright 2026 The InfiniFlow Authors. All Rights Reserved.
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

"""Rule-based splitter for mixed legal PDFs.

This module provides a lightweight page-level boundary detector to split one PDF
into multiple sub-documents. It is intentionally heuristic and designed as an
MVP before model-based boundary detection.
"""

from __future__ import annotations

import re
from io import BytesIO
from typing import Any



TITLE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"讯问笔录|询问笔录"), "interrogation"),
    (re.compile(r"起诉意见书|起诉书"), "indictment"),
    (re.compile(r"立案决定书|拘留证|逮捕证|取保候审|监视居住"), "procedure"),
]


def _extract_pdf_page_texts(binary: bytes, max_pages: int = 300) -> list[str]:
    """Extract text per page from PDF bytes."""
    try:
        try:
            from pypdf import PdfReader  # type: ignore
        except ImportError:
            from PyPDF2 import PdfReader  # type: ignore
    except ImportError:
        return []

    reader = PdfReader(BytesIO(binary))
    pages = min(len(reader.pages), max_pages)
    return [(reader.pages[i].extract_text() or "").strip() for i in range(pages)]


def _detect_page_type(page_text: str) -> tuple[str, float, str]:
    """Detect sub-document type from one page.

    Returns:
        (doc_type, confidence, matched_pattern)
    """
    if not page_text:
        return "unknown", 0.0, ""

    head = "\n".join(page_text.splitlines()[:12])
    for pattern, doc_type in TITLE_PATTERNS:
        if pattern.search(head):
            return doc_type, 0.92, pattern.pattern

    # weak structural hints for interrogation transcript
    if re.search(r"问\s*[：:；;].{0,80}答\s*[：:；;]", page_text, re.S):
        return "interrogation", 0.65, "qa_pattern"

    return "unknown", 0.0, ""


def split_mixed_pdf(binary: bytes, filename: str = "") -> list[dict[str, Any]]:
    """Split PDF into sub-documents by page boundaries.

    The function creates a new boundary when a page has a strong title match.
    If no boundary is found, it returns one full-range sub-document.
    """
    page_texts = _extract_pdf_page_texts(binary)
    total = len(page_texts)
    if total == 0:
        return []

    boundaries: list[int] = [1]
    page_labels: dict[int, tuple[str, float, str]] = {}

    for idx, text in enumerate(page_texts, start=1):
        doc_type, confidence, matched = _detect_page_type(text)
        page_labels[idx] = (doc_type, confidence, matched)
        if idx > 1 and confidence >= 0.9:
            boundaries.append(idx)

    boundaries = sorted(set(boundaries))
    sub_docs: list[dict[str, Any]] = []

    for i, start in enumerate(boundaries):
        end = boundaries[i + 1] - 1 if i + 1 < len(boundaries) else total
        doc_type, confidence, matched = page_labels.get(start, ("unknown", 0.0, ""))
        sub_docs.append(
            {
                "index": i,
                "name": f"{filename or 'document'}#subdoc-{i + 1}",
                "start_page": start,
                "end_page": end,
                "doc_type": doc_type,
                "confidence": round(float(confidence), 3),
                "title_hint": matched,
                "status": "ready" if confidence >= 0.9 else "need_review",
            }
        )

    return sub_docs
