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

"""PDF sub-document splitter.

This module provides lightweight heuristics to split long PDF files into
sub-documents based on page-level title signals.
"""

from __future__ import annotations

import re
from typing import Any

_DEFAULT_CONFIDENCE = 0.45
_HIGH_CONFIDENCE = 0.85

_TITLE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"起诉书|起诉意见书"), "indictment"),
    (re.compile(r"讯问笔录|询问笔录"), "interrogation"),
    (re.compile(r"判决书|裁定书|决定书"), "judgment"),
    (re.compile(r"证据目录|证据材料"), "evidence"),
]

_PAGE_PREFIX_PATTERN = re.compile(r"^\s*(第[一二三四五六七八九十百千\d]+[页章节卷]|[（(][一二三四五六七八九十\d]+[)）])")


def _extract_title_hint(page_text: str) -> str:
    if not page_text:
        return ""

    lines = [line.strip() for line in page_text.splitlines() if line.strip()]
    if not lines:
        return ""

    candidates = lines[:3]
    for line in candidates:
        normalized = re.sub(r"\s+", "", line)
        if len(normalized) >= 4 and len(normalized) <= 60:
            return line[:255]

    return candidates[0][:255]


def _infer_doc_type_hint(text: str) -> tuple[str, float]:
    normalized = re.sub(r"\s+", "", text or "")
    for pattern, hint in _TITLE_PATTERNS:
        if pattern.search(normalized):
            return hint, _HIGH_CONFIDENCE
    return "unknown", _DEFAULT_CONFIDENCE


def split_pdf_into_subdocs(
    page_texts: list[str],
    total_pages: int | None = None,
    max_scan_pages: int = 30,
) -> list[dict[str, Any]]:
    """Split a PDF into sub-document page ranges.

    Args:
        page_texts: Page-level texts. Index is 0-based page number.
        total_pages: Total pages in PDF. If omitted, infer from page_texts.
        max_scan_pages: Max number of pages to use for boundary detection.

    Returns:
        A list of subdoc descriptors:
        [{start_page,end_page,doc_type_hint,confidence,title_hint}]
        where page ranges are 0-based and end_page is exclusive.
    """
    page_count = total_pages if total_pages is not None else len(page_texts)
    if page_count <= 0:
        return []

    clipped_texts = page_texts[: min(len(page_texts), max_scan_pages)]
    boundaries = [0]

    for idx in range(1, len(clipped_texts)):
        text = clipped_texts[idx] or ""
        short_text = re.sub(r"\s+", "", text[:120])
        if not short_text:
            continue

        if _PAGE_PREFIX_PATTERN.search(text[:60]):
            continue

        title_hint = _extract_title_hint(text)
        is_large_title = len(title_hint) >= 4 and len(title_hint) <= 40
        mostly_short_page = len(short_text) <= 90
        if is_large_title and mostly_short_page:
            boundaries.append(idx)

    boundaries = sorted(set([b for b in boundaries if 0 <= b < page_count]))
    if not boundaries:
        boundaries = [0]

    if boundaries[-1] != page_count:
        boundaries.append(page_count)

    subdocs: list[dict[str, Any]] = []
    for i in range(len(boundaries) - 1):
        start = boundaries[i]
        end = boundaries[i + 1]
        if end <= start:
            continue

        header_text = "\n".join(page_texts[start : min(start + 2, len(page_texts))])
        doc_type_hint, confidence = _infer_doc_type_hint(header_text)
        title_hint = _extract_title_hint(page_texts[start] if start < len(page_texts) else "")

        subdocs.append(
            {
                "start_page": start,
                "end_page": end,
                "doc_type_hint": doc_type_hint,
                "confidence": round(confidence, 4),
                "title_hint": title_hint,
            }
        )

    return subdocs
