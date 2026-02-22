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
"""Integration tests for parsing output format validation.

Tests verify the format of parsed chunks, especially:
- position_int: coordinate information
- page_num_int: page numbers
- chunk_type: valid chunk types per document type
"""

from typing import Any

import pytest

from test.eval.evaluator.setup import EvaluationSetup


# Valid chunk types per document type
INDICTMENT_CHUNK_TYPES = {"section", "paragraph", "evidence_item"}
INTERROGATION_CHUNK_TYPES = {"header", "qa_pair", "qa_sub"}


def validate_position_format(position_int: Any) -> list[str]:
    """Validate position_int format and return any errors.

    Expected format: [[page, left, right, top, bottom], ...]

    Args:
        position_int: The position_int field from a chunk

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    if position_int is None:
        errors.append("position_int is None")
        return errors

    if not isinstance(position_int, list):
        errors.append(f"position_int is not a list: {type(position_int)}")
        return errors

    if len(position_int) == 0:
        errors.append("position_int is empty")
        return errors

    for i, pos in enumerate(position_int):
        if not isinstance(pos, list):
            errors.append(f"position_int[{i}] is not a list: {type(pos)}")
            continue

        if len(pos) != 5:
            errors.append(f"position_int[{i}] has {len(pos)} elements, expected 5")
            continue

        # Validate each element is a number
        for j, val in enumerate(pos):
            if not isinstance(val, (int, float)):
                errors.append(f"position_int[{i}][{j}] is not a number: {type(val)}")

    return errors


def validate_page_numbers(page_num_int: Any, expected_pages: set[int]) -> list[str]:
    """Validate page_num_int format and consistency.

    Args:
        page_num_int: The page_num_int field from a chunk
        expected_pages: Set of valid page numbers

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    if page_num_int is None:
        errors.append("page_num_int is None")
        return errors

    if not isinstance(page_num_int, list):
        errors.append(f"page_num_int is not a list: {type(page_num_int)}")
        return errors

    if len(page_num_int) == 0:
        errors.append("page_num_int is empty")
        return errors

    for i, page in enumerate(page_num_int):
        if not isinstance(page, int):
            errors.append(f"page_num_int[{i}] is not an int: {type(page)}")

    return errors


class TestFormatValidation:
    """Test suite for parsing output format validation."""

    def test_indictment_format(
        self,
        integration_setup: EvaluationSetup,
        indictment_single_dataset: str,
    ):
        """Validate indictment chunk format.

        Checks:
        - chunk_type is valid for indictments
        - position_int exists and has correct format
        - page_num_int exists and has correct format
        - Coordinates are valid (non-negative, within bounds)

        Args:
            integration_setup: Logged-in EvaluationSetup instance
            indictment_single_dataset: Prebuilt dataset ID with single indictment
        """
        session = integration_setup.session

        # Get documents
        docs_url = f"{integration_setup.base_url}/api/v1/datasets/{indictment_single_dataset}/documents"
        resp = session.get(docs_url)
        data = resp.json()

        docs = data["data"].get("docs", [])
        assert len(docs) >= 1, "Dataset should have at least one document"

        doc_id = docs[0]["id"]
        total_pages = docs[0].get("total_pages", 0)

        # Get all chunks (with larger page size)
        chunks_url = f"{integration_setup.base_url}/api/v1/datasets/{indictment_single_dataset}/documents/{doc_id}/chunks"
        resp = session.get(chunks_url, params={"page": 1, "page_size": 100})
        data = resp.json()

        assert data.get("code") == 0, "List chunks should succeed"

        chunks = data["data"].get("chunks", [])
        assert len(chunks) > 0, "Document should have chunks"

        # Collect valid page numbers
        valid_pages = set(range(1, total_pages + 1)) if total_pages > 0 else set()

        # Validate each chunk
        errors = []
        chunk_types_found = set()

        for i, chunk in enumerate(chunks):
            chunk_id = chunk.get("id", f"index_{i}")

            # Check chunk_type
            chunk_type = chunk.get("chunk_type")
            if chunk_type:
                chunk_types_found.add(chunk_type)
                if chunk_type not in INDICTMENT_CHUNK_TYPES:
                    errors.append(f"Chunk {chunk_id}: unexpected chunk_type '{chunk_type}'")

            # Check position_int
            position_int = chunk.get("position_int")
            pos_errors = validate_position_format(position_int)
            for err in pos_errors:
                errors.append(f"Chunk {chunk_id}: {err}")

            # Check page_num_int
            page_num_int = chunk.get("page_num_int")
            page_errors = validate_page_numbers(page_num_int, valid_pages)
            for err in page_errors:
                errors.append(f"Chunk {chunk_id}: {err}")

        # Report results
        print(f"\n  Validated {len(chunks)} chunks")
        print(f"  Chunk types found: {chunk_types_found}")

        if errors:
            print(f"\n  Errors found ({len(errors)}):")
            for err in errors[:10]:  # Show first 10 errors
                print(f"    - {err}")
            if len(errors) > 10:
                print(f"    ... and {len(errors) - 10} more")

        # Assert no critical errors
        assert len(errors) == 0, f"Format validation failed with {len(errors)} errors"

    def test_interrogation_format(
        self,
        integration_setup: EvaluationSetup,
        interrogation_single_dataset: str,
    ):
        """Validate interrogation chunk format.

        Checks:
        - chunk_type is valid for interrogations
        - position_int exists and has correct format
        - page_num_int exists and has correct format
        - Coordinates are valid (non-negative, within bounds)

        Args:
            integration_setup: Logged-in EvaluationSetup instance
            interrogation_single_dataset: Prebuilt dataset ID with single interrogation
        """
        session = integration_setup.session

        # Get documents
        docs_url = f"{integration_setup.base_url}/api/v1/datasets/{interrogation_single_dataset}/documents"
        resp = session.get(docs_url)
        data = resp.json()

        docs = data["data"].get("docs", [])
        assert len(docs) >= 1, "Dataset should have at least one document"

        doc_id = docs[0]["id"]
        total_pages = docs[0].get("total_pages", 0)

        # Get all chunks
        chunks_url = f"{integration_setup.base_url}/api/v1/datasets/{interrogation_single_dataset}/documents/{doc_id}/chunks"
        resp = session.get(chunks_url, params={"page": 1, "page_size": 100})
        data = resp.json()

        assert data.get("code") == 0, "List chunks should succeed"

        chunks = data["data"].get("chunks", [])
        assert len(chunks) > 0, "Document should have chunks"

        # Collect valid page numbers
        valid_pages = set(range(1, total_pages + 1)) if total_pages > 0 else set()

        # Validate each chunk
        errors = []
        chunk_types_found = set()

        for i, chunk in enumerate(chunks):
            chunk_id = chunk.get("id", f"index_{i}")

            # Check chunk_type
            chunk_type = chunk.get("chunk_type")
            if chunk_type:
                chunk_types_found.add(chunk_type)
                if chunk_type not in INTERROGATION_CHUNK_TYPES:
                    errors.append(f"Chunk {chunk_id}: unexpected chunk_type '{chunk_type}'")

            # Check position_int
            position_int = chunk.get("position_int")
            pos_errors = validate_position_format(position_int)
            for err in pos_errors:
                errors.append(f"Chunk {chunk_id}: {err}")

            # Check page_num_int
            page_num_int = chunk.get("page_num_int")
            page_errors = validate_page_numbers(page_num_int, valid_pages)
            for err in page_errors:
                errors.append(f"Chunk {chunk_id}: {err}")

        # Report results
        print(f"\n  Validated {len(chunks)} chunks")
        print(f"  Chunk types found: {chunk_types_found}")

        if errors:
            print(f"\n  Errors found ({len(errors)}):")
            for err in errors[:10]:  # Show first 10 errors
                print(f"    - {err}")
            if len(errors) > 10:
                print(f"    ... and {len(errors) - 10} more")

        # Assert no critical errors
        assert len(errors) == 0, f"Format validation failed with {len(errors)} errors"

    def test_position_coordinates_valid(
        self,
        integration_setup: EvaluationSetup,
        indictment_single_dataset: str,
    ):
        """Test that position coordinates are valid numbers within expected bounds.

        Args:
            integration_setup: Logged-in EvaluationSetup instance
            indictment_single_dataset: Prebuilt dataset ID with single indictment
        """
        session = integration_setup.session

        # Get documents
        docs_url = f"{integration_setup.base_url}/api/v1/datasets/{indictment_single_dataset}/documents"
        resp = session.get(docs_url)
        data = resp.json()

        docs = data["data"].get("docs", [])
        doc_id = docs[0]["id"]

        # Get chunks
        chunks_url = f"{integration_setup.base_url}/api/v1/datasets/{indictment_single_dataset}/documents/{doc_id}/chunks"
        resp = session.get(chunks_url, params={"page": 1, "page_size": 100})
        data = resp.json()

        chunks = data["data"].get("chunks", [])

        invalid_coords = []

        for i, chunk in enumerate(chunks):
            position_int = chunk.get("position_int")
            if not position_int:
                continue

            for j, pos in enumerate(position_int):
                if len(pos) != 5:
                    continue

                page, left, right, top, bottom = pos

                # Basic validity checks
                if page < 0:
                    invalid_coords.append(f"Chunk {i}, pos {j}: negative page {page}")
                if left < 0 or right < 0 or top < 0 or bottom < 0:
                    invalid_coords.append(
                        f"Chunk {i}, pos {j}: negative coords ({left}, {right}, {top}, {bottom})"
                    )
                if right < left:
                    invalid_coords.append(
                        f"Chunk {i}, pos {j}: right < left ({right} < {left})"
                    )
                if bottom < top:
                    invalid_coords.append(
                        f"Chunk {i}, pos {j}: bottom < top ({bottom} < {top})"
                    )

        if invalid_coords:
            print(f"\n  Invalid coordinates found ({len(invalid_coords)}):")
            for coord in invalid_coords[:10]:
                print(f"    - {coord}")

        assert len(invalid_coords) == 0, f"Found {len(invalid_coords)} invalid coordinates"
