#
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
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
Answer Gate Validator - PR-3

Validates LLM answer citations for the Criminal RAG system:
1. Verifies referenced chunk_id exists
2. Validates excerpt is a substring of chunk content
3. Checks numeric/date values have evidence support
4. Validates page_index/bbox coordinate provenance
"""

import logging
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from enum import Enum
from typing import Optional


class ValidationStatus(Enum):
    """Validation result status."""

    VALID = "valid"
    NO_EVIDENCE = "no_evidence"
    CITATION_INSUFFICIENT = "citation_insufficient"


@dataclass
class Evidence:
    """Evidence from a chunk supporting an answer."""

    chunk_id: str
    excerpt: str
    page_index: Optional[int] = None
    bbox: Optional[list[int]] = field(default_factory=list)


@dataclass
class ValidationResult:
    """Result of answer validation."""

    status: ValidationStatus
    conclusion: Optional[str] = None
    evidences: list[Evidence] = field(default_factory=list)
    validation_errors: list[str] = field(default_factory=list)


# Regex patterns for numeric/date extraction
NUMERIC_PATTERNS = {
    "amount": re.compile(r"[\d,]+\.?\d*\s*[万亿]?元"),
    "percentage": re.compile(r"\d+\.?\d*\s*[%％]"),
    "date": re.compile(r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?"),
    "alcohol_concentration": re.compile(r"\d+\.?\d*\s*(mg|g)/\d*\s*(ml|100ml)", re.IGNORECASE),
    "weight": re.compile(r"[\d,]+\.?\d*\s*(kg|克|斤|吨)"),
    "count": re.compile(r"\d+\s*(次|个|件|份|笔|人|名|起)"),
}


class AnswerGate:
    """
    Answer Gate Validator for Criminal RAG.

    Validates that LLM answers have proper citation support:
    - chunk_id existence
    - excerpt substring matching (with fuzzy matching for OCR errors)
    - numeric/date grounding
    - coordinate provenance
    """

    def __init__(
        self,
        fuzzy_match_threshold: float = 0.95,
        strict_numeric_validation: bool = True,
        enable_coordinate_validation: bool = True,
    ):
        """
        Initialize the Answer Gate validator.

        Args:
            fuzzy_match_threshold: Similarity threshold for excerpt matching (0-1)
            strict_numeric_validation: Whether to require numeric grounding
            enable_coordinate_validation: Whether to validate page_index/bbox
        """
        self.fuzzy_match_threshold = fuzzy_match_threshold
        self.strict_numeric_validation = strict_numeric_validation
        self.enable_coordinate_validation = enable_coordinate_validation

    def validate(
        self,
        answer: str,
        evidences: list[dict],
        raw_chunks: list[dict],
        conclusion: Optional[str] = None,
    ) -> ValidationResult:
        """
        Validate an answer against provided evidences and raw chunks.

        Args:
            answer: The LLM-generated answer text
            evidences: List of evidence dicts with chunk_id, excerpt, page_index, bbox
            raw_chunks: List of raw chunk dicts with chunk_id and content
            conclusion: Optional conclusion statement to validate

        Returns:
            ValidationResult with status, evidences, and any validation errors
        """
        errors: list[str] = []
        validated_evidences: list[Evidence] = []

        # Task 3.6: No evidence case
        if not evidences or not raw_chunks:
            return ValidationResult(
                status=ValidationStatus.NO_EVIDENCE,
                conclusion=conclusion,
                evidences=[],
                validation_errors=["No evidences or chunks provided"],
            )

        # Build chunk lookup by chunk_id
        chunk_lookup = {c.get("chunk_id"): c for c in raw_chunks if c.get("chunk_id")}

        # Task 3.2: Validate chunk existence
        chunk_errors = self._validate_chunk_existence(evidences, chunk_lookup)
        errors.extend(chunk_errors)

        # Task 3.3: Validate excerpt substring matching
        excerpt_errors, validated = self._validate_excerpt_substring(evidences, chunk_lookup)
        errors.extend(excerpt_errors)
        validated_evidences.extend(validated)

        # Task 3.4: Validate numeric grounding
        if self.strict_numeric_validation:
            numeric_errors = self._validate_numeric_grounding(answer, evidences, chunk_lookup)
            errors.extend(numeric_errors)

        # Task 3.5: Validate coordinate provenance
        if self.enable_coordinate_validation:
            coord_errors = self._validate_coordinate_provenance(evidences, chunk_lookup)
            errors.extend(coord_errors)

        # Determine final status
        if errors:
            status = ValidationStatus.CITATION_INSUFFICIENT
            logging.warning(f"Answer Gate: validation errors - {errors}")
        else:
            status = ValidationStatus.VALID

        return ValidationResult(
            status=status,
            conclusion=conclusion,
            evidences=validated_evidences,
            validation_errors=errors,
        )

    def _validate_chunk_existence(
        self,
        evidences: list[dict],
        chunk_lookup: dict,
    ) -> list[str]:
        """Task 3.2: Validate that chunk_ids exist in raw chunks."""
        errors = []
        for ev in evidences:
            chunk_id = ev.get("chunk_id")
            if not chunk_id:
                errors.append(f"Evidence missing chunk_id")
            elif chunk_id not in chunk_lookup:
                errors.append(f"chunk_id '{chunk_id}' not found in raw chunks")
        return errors

    def _validate_excerpt_substring(
        self,
        evidences: list[dict],
        chunk_lookup: dict,
    ) -> tuple[list[str], list[Evidence]]:
        """
        Task 3.3: Validate that excerpts are substrings of chunk content.

        Uses fuzzy matching with configurable threshold for OCR errors.
        """
        errors = []
        validated = []

        for ev in evidences:
            chunk_id = ev.get("chunk_id")
            excerpt = ev.get("excerpt", "")
            chunk = chunk_lookup.get(chunk_id, {})
            content = chunk.get("content_with_weight", "") or chunk.get("content", "")

            if not excerpt:
                # Empty excerpt is acceptable
                validated.append(Evidence(
                    chunk_id=chunk_id,
                    excerpt="",
                    page_index=ev.get("page_index"),
                    bbox=ev.get("bbox"),
                ))
                continue

            if not content:
                errors.append(f"chunk_id '{chunk_id}' has no content to match excerpt")
                continue

            # Try exact substring match first
            if excerpt in content:
                validated.append(Evidence(
                    chunk_id=chunk_id,
                    excerpt=excerpt,
                    page_index=ev.get("page_index"),
                    bbox=ev.get("bbox"),
                ))
                continue

            # Try fuzzy match for OCR errors
            best_ratio = 0
            best_match = None

            # Slide through content looking for best match
            excerpt_len = len(excerpt)
            for i in range(len(content) - excerpt_len + 1):
                candidate = content[i:i + excerpt_len]
                ratio = SequenceMatcher(None, excerpt, candidate).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_match = candidate

            if best_ratio >= self.fuzzy_match_threshold:
                logging.debug(
                    f"Fuzzy match for excerpt in chunk '{chunk_id}': "
                    f"ratio={best_ratio:.2f}, excerpt='{excerpt[:50]}...'"
                )
                validated.append(Evidence(
                    chunk_id=chunk_id,
                    excerpt=excerpt,
                    page_index=ev.get("page_index"),
                    bbox=ev.get("bbox"),
                ))
            else:
                errors.append(
                    f"Excerpt not found in chunk '{chunk_id}' "
                    f"(best match ratio: {best_ratio:.2f}): '{excerpt[:50]}...'"
                )

        return errors, validated

    def _validate_numeric_grounding(
        self,
        answer: str,
        evidences: list[dict],
        chunk_lookup: dict,
    ) -> list[str]:
        """
        Task 3.4: Validate that numeric values in answer have evidence support.

        Extracts amounts, percentages, dates, etc. from answer and checks
        if they appear in the evidence excerpts.
        """
        errors = []

        # Extract all numeric values from answer
        answer_numerics: dict[str, list[str]] = {}
        for pattern_name, pattern in NUMERIC_PATTERNS.items():
            matches = pattern.findall(answer)
            if matches:
                answer_numerics[pattern_name] = matches

        if not answer_numerics:
            return errors  # No numeric values to validate

        # Collect all evidence content
        evidence_content = ""
        for ev in evidences:
            chunk_id = ev.get("chunk_id")
            chunk = chunk_lookup.get(chunk_id, {})
            content = chunk.get("content_with_weight", "") or chunk.get("content", "")
            evidence_content += " " + content

        # Check each numeric value has grounding
        for pattern_name, values in answer_numerics.items():
            for value in values:
                # Try exact match first
                if value in evidence_content:
                    continue

                # Try normalized match (remove spaces, standardize)
                normalized_value = re.sub(r"\s+", "", value)
                normalized_content = re.sub(r"\s+", "", evidence_content)

                if normalized_value in normalized_content:
                    continue

                errors.append(
                    f"Numeric value '{value}' ({pattern_name}) in answer "
                    f"not found in evidence chunks"
                )

        return errors

    def _validate_coordinate_provenance(
        self,
        evidences: list[dict],
        chunk_lookup: dict,
    ) -> list[str]:
        """
        Task 3.5: Validate page_index and bbox coordinate provenance.

        Ensures that cited coordinates match the actual chunk's coordinates.
        """
        errors = []

        for ev in evidences:
            chunk_id = ev.get("chunk_id")
            if not chunk_id:
                continue

            chunk = chunk_lookup.get(chunk_id)
            if not chunk:
                continue  # Already reported in chunk existence check

            cited_page = ev.get("page_index")
            cited_bbox = ev.get("bbox")

            # Get actual chunk coordinates
            actual_page = chunk.get("page_num_int", [None])[0] if chunk.get("page_num_int") else None
            actual_bbox = chunk.get("bbox")

            # Validate page_index
            if cited_page is not None and actual_page is not None:
                if cited_page != actual_page:
                    errors.append(
                        f"page_index mismatch for chunk '{chunk_id}': "
                        f"cited={cited_page}, actual={actual_page}"
                    )

            # Validate bbox (if both exist and are lists)
            if cited_bbox and actual_bbox:
                if isinstance(cited_bbox, list) and isinstance(actual_bbox, list):
                    if len(cited_bbox) == len(actual_bbox) == 4:
                        # Allow small tolerance for coordinate differences
                        tolerance = 5  # pixels
                        for i in range(4):
                            if abs(cited_bbox[i] - actual_bbox[i]) > tolerance:
                                errors.append(
                                    f"bbox mismatch for chunk '{chunk_id}': "
                                    f"cited={cited_bbox}, actual={actual_bbox}"
                                )
                                break

        return errors
