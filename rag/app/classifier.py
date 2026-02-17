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
Document classifier for automatic document type detection.

This module provides automatic classification of legal documents based on content
analysis, supporting both rule-based matching and LLM-based fallback.
"""

import logging
import re
from io import BytesIO
from typing import Tuple

from pypdf import PdfReader

from common.constants import ParserType
from rag.nlp import find_codec

# Maximum characters to extract for classification
MAX_TEXT_SAMPLE_CHARS = 2000

# Maximum pages to extract from PDFs for classification
MAX_PDF_PAGES = 3


# Rule-based classification patterns
# Each pattern maps to (parser_id, description)
DOCUMENT_PATTERNS = [
    # Legal document patterns (Chinese)
    (r"讯问笔录|询问笔录", ParserType.INTERROGATION.value, "Interrogation record"),
    (r"起诉意见书", ParserType.INDICTMENT.value, "Indictment opinion"),
    (r"起诉书", ParserType.INDICTMENT.value, "Indictment"),
    (r"判决书|裁定书", ParserType.LAWS.value, "Court judgment"),
    (r"法律|法规|条例|规定", ParserType.LAWS.value, "Legal document"),
    # Add more patterns as needed
]


def extract_text_sample(binary: bytes, filename: str, max_chars: int = MAX_TEXT_SAMPLE_CHARS) -> str:
    """
    Extract a text sample from binary content for classification.

    This function attempts to extract text from various file formats
    (PDF, TXT, DOCX, etc.) for classification purposes.

    Args:
        binary: The raw file content as bytes.
        filename: The filename (used to determine file type).
        max_chars: Maximum number of characters to extract.

    Returns:
        A text sample extracted from the file content.
    """
    if not binary:
        return ""

    ext = filename.lower().split(".")[-1] if "." in filename else ""

    try:
        # PDF files - extract text from first few pages
        if ext == "pdf":
            return _extract_pdf_text(binary, max_chars)

        # DOCX files - extract text using python-docx
        if ext == "docx":
            return _extract_docx_text(binary, max_chars)

        # Text-based files - decode directly
        return _extract_text_file(binary, max_chars)

    except Exception as e:
        logging.warning(f"Failed to extract text sample from {filename}: {e}")
        return ""


def _extract_pdf_text(binary: bytes, max_chars: int) -> str:
    """Extract text from PDF binary content."""
    try:
        reader = PdfReader(BytesIO(binary))
        text_parts = []
        total_chars = 0

        # Extract text from first few pages only
        for i, page in enumerate(reader.pages[:MAX_PDF_PAGES]):
            page_text = page.extract_text() or ""
            if total_chars + len(page_text) > max_chars:
                page_text = page_text[: max_chars - total_chars]
            text_parts.append(page_text)
            total_chars += len(page_text)
            if total_chars >= max_chars:
                break

        return " ".join(text_parts)
    except Exception as e:
        logging.debug(f"PDF text extraction failed: {e}")
        return ""


def _extract_docx_text(binary: bytes, max_chars: int) -> str:
    """Extract text from DOCX binary content."""
    try:
        from docx import Document

        doc = Document(BytesIO(binary))
        text_parts = []
        total_chars = 0

        for para in doc.paragraphs:
            para_text = para.text or ""
            if total_chars + len(para_text) > max_chars:
                para_text = para_text[: max_chars - total_chars]
            text_parts.append(para_text)
            total_chars += len(para_text)
            if total_chars >= max_chars:
                break

        return " ".join(text_parts)
    except Exception as e:
        logging.debug(f"DOCX text extraction failed: {e}")
        return ""


def _extract_text_file(binary: bytes, max_chars: int) -> str:
    """Extract text from text-based binary content."""
    try:
        encoding = find_codec(binary)
        text = binary.decode(encoding, errors="ignore")
        return text[:max_chars]
    except Exception as e:
        logging.debug(f"Text file extraction failed: {e}")
        return ""


class DocumentClassifier:
    """
    Automatic document classifier for legal documents.

    This classifier uses a two-stage approach:
    1. Rule-based matching (fast, deterministic)
    2. LLM-based fallback (for ambiguous cases)

    The classifier returns a tuple of (parser_id, method, confidence):
    - parser_id: The parser to use for the document
    - method: How the classification was done ('rule', 'llm', or 'fallback')
    - confidence: Classification confidence (0.0 to 1.0)
    """

    @staticmethod
    def classify(binary: bytes, filename: str) -> Tuple[str, str, float]:
        """
        Classify a document and return the appropriate parser.

        Args:
            binary: The raw file content as bytes.
            filename: The filename (used for extension-based hints).

        Returns:
            Tuple of (parser_id, method, confidence):
            - parser_id: The parser to use (e.g., 'interrogation', 'naive')
            - method: Classification method ('rule', 'llm', or 'fallback')
            - confidence: Classification confidence (0.0 to 1.0)
        """
        # Step 1: Rule-based classification (fast path)
        text = extract_text_sample(binary, filename)

        if text:
            parser_id, method, confidence = DocumentClassifier._rule_classify(text)
            if confidence > 0:
                return parser_id, method, confidence

        # Step 2: LLM-based fallback (optional, for ambiguous cases)
        # For now, we use naive parser as fallback
        # TODO: Implement LLM-based classification when needed
        return DocumentClassifier._fallback_classify(filename)

    @staticmethod
    def _rule_classify(text: str) -> Tuple[str, str, float]:
        """
        Apply rule-based classification using regex patterns.

        Args:
            text: The text sample to classify.

        Returns:
            Tuple of (parser_id, method, confidence).
        """
        for pattern, parser_id, description in DOCUMENT_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                logging.debug(f"Rule matched: {pattern} -> {parser_id} ({description})")
                return parser_id, "rule", 1.0

        # No rule matched
        return "", "rule", 0.0

    @staticmethod
    def _fallback_classify(filename: str) -> Tuple[str, str, float]:
        """
        Fallback classification when rules don't match.

        This uses the default 'naive' parser as a safe fallback.

        Args:
            filename: The filename (for logging purposes).

        Returns:
            Tuple of (parser_id, method, confidence).
        """
        logging.debug(f"Using fallback classifier for: {filename}")
        return ParserType.NAIVE.value, "fallback", 0.0

    @staticmethod
    def classify_with_llm(text: str, tenant_id: str, llm_id: str = None) -> Tuple[str, str, float]:
        """
        LLM-based classification for ambiguous documents.

        This is an optional enhancement that uses an LLM to classify
        documents when rule-based matching fails.

        Args:
            text: The text sample to classify.
            tenant_id: The tenant ID for LLM access.
            llm_id: Optional specific LLM ID to use.

        Returns:
            Tuple of (parser_id, method, confidence).

        Note:
            This method is currently a placeholder. Implement when needed.
        """
        # TODO: Implement LLM-based classification
        # Example prompt structure:
        # prompt = f"""请根据以下文档内容判断文档类型：
        #
        # 文档内容：
        # {text[:1000]}
        #
        # 可选类型：
        # - interrogation: 讯问笔录
        # - indictment: 起诉意见书
        # - laws: 法律法规
        # - naive: 普通文档
        #
        # 请只返回类型名称，不要返回其他内容。
        # """

        # For now, return fallback
        return ParserType.NAIVE.value, "fallback", 0.0
