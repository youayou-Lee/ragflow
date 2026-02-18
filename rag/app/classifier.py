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

# Minimum text threshold for pypdf extraction (below this, use OCR fallback)
MIN_TEXT_THRESHOLD = 50


# Rule-based classification patterns
# Each pattern maps to (parser_id, description)
# Note: \s* allows for spaces between characters (common in OCR/scanned PDFs)
DOCUMENT_PATTERNS = [
    # Legal document patterns (Chinese)
    # Interrogation/Inquiry records - must match before generic "规定" pattern
    (r"讯\s*问\s*笔\s*录|询\s*问\s*笔\s*录", ParserType.INTERROGATION.value, "Interrogation record"),
    # Indictment opinion - specific document type from police
    (r"起\s*诉\s*意\s*见\s*书", ParserType.INDICTMENT.value, "Indictment opinion"),
    # Indictment - from prosecutor
    (r"起\s*诉\s*书", ParserType.INDICTMENT.value, "Indictment"),
    # Court judgments
    (r"判\s*决\s*书|裁\s*定\s*书", ParserType.LAWS.value, "Court judgment"),
    # Generic legal documents - keep last as fallback for legal content
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
            text = _extract_pdf_text(binary, max_chars)
            # OCR fallback for scanned PDFs
            if len(text.strip()) < MIN_TEXT_THRESHOLD:
                logging.debug(f"pypdf extracted only {len(text.strip())} chars, trying OCR fallback")
                ocr_text = _extract_pdf_text_with_ocr(binary, max_chars)
                if ocr_text.strip():
                    text = ocr_text
            return text

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


def _extract_pdf_text_with_ocr(binary: bytes, max_chars: int) -> str:
    """
    Extract text from scanned PDF using OCR.

    This is a fallback when pypdf fails to extract meaningful text
    from scanned PDF documents.

    Args:
        binary: The raw PDF file content as bytes.
        max_chars: Maximum number of characters to extract.

    Returns:
        Extracted text from OCR.
    """
    try:
        from deepdoc.parser.paddleocr_parser import PaddleOCRParser
        import os

        # Get OCR API configuration from environment
        api_url = os.getenv("PADDLEOCR_API_URL", "")
        access_token = os.getenv("PADDLEOCR_ACCESS_TOKEN")

        if not api_url:
            logging.debug("PADDLEOCR_API_URL not configured, skipping OCR fallback")
            return ""

        # Create parser instance
        parser = PaddleOCRParser(api_url=api_url, access_token=access_token)

        # Check if parser is properly configured
        ok, reason = parser.check_installation()
        if not ok:
            logging.debug(f"PaddleOCR not available: {reason}")
            return ""

        # Parse PDF and extract text from sections
        sections, _ = parser.parse_pdf(
            filepath="",  # Not used when binary is provided
            binary=binary,
            parse_method="raw",
        )

        # Extract text from sections
        text_parts = []
        total_chars = 0

        for section in sections[:MAX_PDF_PAGES]:
            # Section format: (content, tag) or (content, label, tag)
            section_text = section[0] if section else ""
            if total_chars + len(section_text) > max_chars:
                section_text = section_text[: max_chars - total_chars]
            text_parts.append(section_text)
            total_chars += len(section_text)
            if total_chars >= max_chars:
                break

        return " ".join(text_parts)

    except Exception as e:
        logging.warning(f"OCR fallback failed: {e}")
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
    def classify(binary: bytes, filename: str, tenant_id: str = None) -> Tuple[str, str, float]:
        """
        Classify a document and return the appropriate parser.

        Args:
            binary: The raw file content as bytes.
            filename: The filename (used for extension-based hints).
            tenant_id: Optional tenant ID for LLM-based classification fallback.

        Returns:
            Tuple of (parser_id, method, confidence):
            - parser_id: The parser to use (e.g., 'interrogation', 'naive')
            - method: Classification method ('rule', 'llm', or 'fallback')
            - confidence: Classification confidence (0.0 to 1.0)
        """
        # Step 1: Rule-based classification on extracted text (fast path)
        text = extract_text_sample(binary, filename)

        if text:
            parser_id, method, confidence = DocumentClassifier._rule_classify(text)
            if confidence > 0:
                return parser_id, method, confidence

        # Step 2: LLM-based fallback for ambiguous cases
        # Only use LLM if we have enough text and tenant_id
        if text and len(text.strip()) >= 50 and tenant_id:
            parser_id, method, confidence = DocumentClassifier._classify_by_llm(text[:500], tenant_id)
            if confidence > 0:
                return parser_id, method, confidence

        # Step 3: Filename-based classification (for scanned PDFs)
        # Try to classify based on filename when text extraction fails
        parser_id, method, confidence = DocumentClassifier._classify_by_filename(filename)
        if confidence > 0:
            return parser_id, method, confidence

        # Step 4: Final fallback
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
    def _classify_by_filename(filename: str) -> Tuple[str, str, float]:
        """
        Classify document based on filename.

        This is useful for scanned PDFs where text extraction fails.
        Many users name their files with the document type.

        Args:
            filename: The filename to classify.

        Returns:
            Tuple of (parser_id, method, confidence).
        """
        # Remove extension and common prefixes/suffixes
        name = filename.lower()
        if "." in name:
            name = name.rsplit(".", 1)[0]

        # Remove common prefixes like "sample_", "test_", etc.
        for prefix in ["sample_", "test_", "copy_of_", "副本_", "复件_"]:
            if name.startswith(prefix):
                name = name[len(prefix):]

        # Apply same patterns to filename
        for pattern, parser_id, description in DOCUMENT_PATTERNS:
            if re.search(pattern, name, re.IGNORECASE):
                logging.debug(f"Filename matched: {pattern} -> {parser_id} ({description})")
                return parser_id, "filename", 0.7

        # No filename match
        return "", "filename", 0.0

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
    def _classify_by_llm(text_sample: str, tenant_id: str) -> Tuple[str, str, float]:
        """
        Use LLM to classify document type when rule-based matching fails.

        This method sends a text sample to an LLM and asks it to identify
        the document type from a predefined list of parser types.

        Args:
            text_sample: The text sample to classify (max 500 chars recommended).
            tenant_id: The tenant ID for LLM access.

        Returns:
            Tuple of (parser_id, method, confidence).
            Returns ("naive", "llm", 0.0) if classification fails.
        """
        if not text_sample or len(text_sample.strip()) < 20:
            return ParserType.NAIVE.value, "llm", 0.0

        prompt = f"""分析以下文本片段，判断它属于哪种文档类型。

文本片段：
{text_sample}

可选类型：
1. interrogation - 讯问笔录/询问笔录（问答形式的执法记录）
2. laws - 法律文书/判决书/法规
3. resume - 简历
4. book - 书籍/教材
5. naive - 通用文档

只返回类型名称（interrogation/laws/resume/book/naive），不要其他解释。"""

        try:
            from api.db.services.llm_service import LLMBundle
            from common.constants import LLMType

            llm = LLMBundle(tenant_id=tenant_id, llm_type=LLMType.CHAT)

            # Call the chat model
            messages = [{"role": "user", "content": prompt}]
            response, _ = llm.mdl.chat("", messages, {})

            # Parse response to extract classification
            response_lower = response.lower().strip()

            # Map response to parser type
            if "interrogation" in response_lower:
                return ParserType.INTERROGATION.value, "llm", 0.8
            elif "laws" in response_lower or "法律" in response:
                return ParserType.LAWS.value, "llm", 0.8
            elif "resume" in response_lower or "简历" in response:
                return ParserType.RESUME.value, "llm", 0.8
            elif "book" in response_lower or "书" in response:
                return ParserType.BOOK.value, "llm", 0.8
            else:
                return ParserType.NAIVE.value, "llm", 0.5

        except Exception as e:
            logging.warning(f"LLM classification failed: {e}")
            return ParserType.NAIVE.value, "llm", 0.0

    @staticmethod
    def classify_with_llm(text: str, tenant_id: str, llm_id: str = None) -> Tuple[str, str, float]:
        """
        LLM-based classification for ambiguous documents.

        This is an optional enhancement that uses an LLM to classify
        documents when rule-based matching fails.

        Args:
            text: The text sample to classify.
            tenant_id: The tenant ID for LLM access.
            llm_id: Optional specific LLM ID to use (not currently used).

        Returns:
            Tuple of (parser_id, method, confidence).
        """
        return DocumentClassifier._classify_by_llm(text, tenant_id)
