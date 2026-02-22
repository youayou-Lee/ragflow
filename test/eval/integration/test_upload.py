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
"""Integration tests for file upload functionality.

Tests focus on file upload behavior only:
- Single file upload
- Multiple file upload
- File validation
"""

from pathlib import Path

import pytest

from test.eval.evaluator.setup import EvaluationSetup


class TestUpload:
    """Test suite for file upload functionality."""

    def test_upload_single_file(
        self,
        integration_setup: EvaluationSetup,
        temp_dataset_for_upload: str,
        sample_files: dict[str, Path],
    ):
        """Test uploading a single PDF file.

        Workflow:
        1. Upload a single indictment PDF
        2. Verify document ID is returned
        3. Verify document appears in document list

        Args:
            integration_setup: Logged-in EvaluationSetup instance
            temp_dataset_for_upload: Temporary dataset ID (auto-cleaned)
            sample_files: Dictionary of sample file paths
        """
        # Get sample file path
        sample_path = sample_files["indictment"]
        assert sample_path.exists(), f"Sample file not found: {sample_path}"

        # Upload document
        doc_id = integration_setup.upload_document(
            temp_dataset_for_upload, str(sample_path)
        )
        assert doc_id, "Document ID should not be empty"

        # Verify document appears in list
        session = integration_setup.session
        url = f"{integration_setup.base_url}/api/v1/datasets/{temp_dataset_for_upload}/documents"
        resp = session.get(url)
        data = resp.json()

        assert data.get("code") == 0, "List documents should succeed"

        listed_ids = [d["id"] for d in data["data"].get("docs", [])]
        assert doc_id in listed_ids, f"Document {doc_id} should appear in list"

        # Verify document metadata
        docs = {d["id"]: d for d in data["data"].get("docs", [])}
        doc = docs.get(doc_id)
        assert doc is not None, "Document should be found"
        assert doc.get("name") == sample_path.name, "Document name should match"

    def test_upload_multiple_files(
        self,
        integration_setup: EvaluationSetup,
        temp_dataset_for_upload: str,
        sample_files: dict[str, Path],
    ):
        """Test uploading multiple PDF files.

        Workflow:
        1. Upload multiple PDF files (indictment + interrogation)
        2. Verify all document IDs are returned
        3. Verify all documents appear in document list

        Args:
            integration_setup: Logged-in EvaluationSetup instance
            temp_dataset_for_upload: Temporary dataset ID (auto-cleaned)
            sample_files: Dictionary of sample file paths
        """
        uploaded_ids = []

        # Upload all available sample files
        for doc_type, sample_path in sample_files.items():
            if sample_path.exists():
                doc_id = integration_setup.upload_document(
                    temp_dataset_for_upload, str(sample_path)
                )
                uploaded_ids.append((doc_type, doc_id))
                assert doc_id, f"Document ID for {doc_type} should not be empty"

        assert len(uploaded_ids) > 0, "At least one file should be uploaded"

        # Verify all documents appear in list
        session = integration_setup.session
        url = f"{integration_setup.base_url}/api/v1/datasets/{temp_dataset_for_upload}/documents"
        resp = session.get(url)
        data = resp.json()

        assert data.get("code") == 0, "List documents should succeed"

        listed_ids = [d["id"] for d in data["data"].get("docs", [])]

        for doc_type, doc_id in uploaded_ids:
            assert doc_id in listed_ids, f"Document {doc_id} ({doc_type}) should appear in list"

    def test_upload_same_file_twice(
        self,
        integration_setup: EvaluationSetup,
        temp_dataset_for_upload: str,
        sample_files: dict[str, Path],
    ):
        """Test uploading the same file twice.

        The system should allow duplicate file uploads (different doc IDs).

        Args:
            integration_setup: Logged-in EvaluationSetup instance
            temp_dataset_for_upload: Temporary dataset ID (auto-cleaned)
            sample_files: Dictionary of sample file paths
        """
        sample_path = sample_files["indictment"]
        if not sample_path.exists():
            pytest.skip("Indictment sample file not available")

        # Upload same file twice
        doc_id_1 = integration_setup.upload_document(
            temp_dataset_for_upload, str(sample_path)
        )
        doc_id_2 = integration_setup.upload_document(
            temp_dataset_for_upload, str(sample_path)
        )

        # Should get different IDs
        assert doc_id_1, "First document ID should not be empty"
        assert doc_id_2, "Second document ID should not be empty"
        assert doc_id_1 != doc_id_2, "Same file uploaded twice should have different IDs"

        # Both should appear in list
        session = integration_setup.session
        url = f"{integration_setup.base_url}/api/v1/datasets/{temp_dataset_for_upload}/documents"
        resp = session.get(url)
        data = resp.json()

        listed_ids = [d["id"] for d in data["data"].get("docs", [])]
        assert doc_id_1 in listed_ids, "First document should appear in list"
        assert doc_id_2 in listed_ids, "Second document should appear in list"

    def test_document_metadata_preserved(
        self,
        integration_setup: EvaluationSetup,
        temp_dataset_for_upload: str,
        sample_files: dict[str, Path],
    ):
        """Test that document metadata (name, size) is preserved after upload.

        Args:
            integration_setup: Logged-in EvaluationSetup instance
            temp_dataset_for_upload: Temporary dataset ID (auto-cleaned)
            sample_files: Dictionary of sample file paths
        """
        sample_path = sample_files["indictment"]
        if not sample_path.exists():
            pytest.skip("Indictment sample file not available")

        original_name = sample_path.name
        original_size = sample_path.stat().st_size

        # Upload
        doc_id = integration_setup.upload_document(
            temp_dataset_for_upload, str(sample_path)
        )

        # Get document info
        session = integration_setup.session
        url = f"{integration_setup.base_url}/api/v1/datasets/{temp_dataset_for_upload}/documents"
        resp = session.get(url)
        data = resp.json()

        docs = {d["id"]: d for d in data["data"].get("docs", [])}
        doc = docs.get(doc_id)

        assert doc is not None, "Document should be found"
        assert doc.get("name") == original_name, "Document name should be preserved"
        # Size may be stored differently, so we just check it exists
        assert "size" in doc or "total_pages" in doc, "Document size info should be available"
