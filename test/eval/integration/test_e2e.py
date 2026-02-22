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
"""End-to-end integration tests for legal document processing.

Tests the complete workflow:
1. Create dataset
2. Upload document
3. Parse document
4. Validate format
"""

from pathlib import Path

import pytest

from test.eval.evaluator.setup import EvaluationSetup


# Valid chunk types per document type
INDICTMENT_CHUNK_TYPES = {"section", "paragraph", "evidence_item"}
INTERROGATION_CHUNK_TYPES = {"header", "qa_pair", "qa_sub"}


class TestEndToEnd:
    """End-to-end test suite for complete document processing workflow."""

    def test_e2e_full_workflow(
        self,
        integration_setup: EvaluationSetup,
        temp_dataset_for_e2e: str,
        sample_files: dict[str, Path],
        test_config: dict,
    ):
        """Test the complete end-to-end workflow.

        Workflow:
        1. Upload indictment PDF
        2. Trigger parsing
        3. Wait for completion
        4. Validate chunks exist
        5. Validate chunk format

        Args:
            integration_setup: Logged-in EvaluationSetup instance
            temp_dataset_for_e2e: Temporary dataset ID (auto-cleaned)
            sample_files: Dictionary of sample file paths
            test_config: Test configuration dictionary
        """
        # Step 1: Upload document
        sample_path = sample_files["indictment"]
        assert sample_path.exists(), f"Sample file not found: {sample_path}"

        doc_id = integration_setup.upload_document(temp_dataset_for_e2e, str(sample_path))
        assert doc_id, "Document ID should not be empty"
        print(f"\n  Step 1: Uploaded document {doc_id}")

        # Step 2: Trigger parsing
        integration_setup.parse_document(temp_dataset_for_e2e, [doc_id])
        print(f"  Step 2: Triggered parsing")

        # Step 3: Wait for completion
        timeout = test_config.get("test", {}).get("parse_timeout", 300)
        interval = test_config.get("test", {}).get("parse_interval", 5)

        result = integration_setup.wait_for_parsing(
            temp_dataset_for_e2e,
            [doc_id],
            timeout=timeout,
            interval=interval,
        )
        assert result, "Parsing should complete successfully"
        print(f"  Step 3: Parsing completed")

        # Step 4: Validate document status
        session = integration_setup.session
        url = f"{integration_setup.base_url}/api/v1/datasets/{temp_dataset_for_e2e}/documents"
        resp = session.get(url)
        data = resp.json()

        docs = {d["id"]: d for d in data["data"].get("docs", [])}
        doc = docs.get(doc_id)

        assert doc is not None, "Document should be found"
        assert doc.get("run") == "DONE", f"Document status should be DONE, got: {doc.get('run')}"
        chunk_count = doc.get("chunk_num", 0)
        print(f"  Step 4: Document status DONE, {chunk_count} chunks")

        # Step 5: Validate chunk content
        chunks_url = f"{integration_setup.base_url}/api/v1/datasets/{temp_dataset_for_e2e}/documents/{doc_id}/chunks"
        resp = session.get(chunks_url, params={"page": 1, "page_size": 100})
        data = resp.json()

        assert data.get("code") == 0, "List chunks should succeed"

        chunks = data["data"].get("chunks", [])
        assert len(chunks) > 0, "Document should have chunks"

        # Validate each chunk has content
        for i, chunk in enumerate(chunks[:10]):  # Check first 10 chunks
            content = chunk.get("content", "")
            assert len(content) > 0, f"Chunk {i} should have content"

        print(f"  Step 5: Validated {len(chunks)} chunks have content")

        # Step 6: Validate chunk format (position_int, chunk_type)
        format_errors = []

        for i, chunk in enumerate(chunks):
            # Check position_int exists
            position_int = chunk.get("position_int")
            if position_int is None:
                format_errors.append(f"Chunk {i}: missing position_int")

            # Check chunk_type is valid
            chunk_type = chunk.get("chunk_type")
            if chunk_type and chunk_type not in INDICTMENT_CHUNK_TYPES:
                format_errors.append(f"Chunk {i}: unexpected chunk_type '{chunk_type}'")

        if format_errors:
            print(f"\n  Format errors found ({len(format_errors)}):")
            for err in format_errors[:10]:
                print(f"    - {err}")

        assert len(format_errors) == 0, f"Format validation failed with {len(format_errors)} errors"
        print(f"  Step 6: Format validation passed")

    def test_e2e_interrogation_workflow(
        self,
        integration_setup: EvaluationSetup,
        temp_dataset_for_e2e: str,
        sample_files: dict[str, Path],
        test_config: dict,
    ):
        """Test the complete workflow with interrogation document.

        Args:
            integration_setup: Logged-in EvaluationSetup instance
            temp_dataset_for_e2e: Temporary dataset ID (auto-cleaned)
            sample_files: Dictionary of sample file paths
            test_config: Test configuration dictionary
        """
        sample_path = sample_files["interrogation"]
        if not sample_path.exists():
            pytest.skip("Interrogation sample file not available")

        # Upload
        doc_id = integration_setup.upload_document(temp_dataset_for_e2e, str(sample_path))
        assert doc_id, "Document ID should not be empty"
        print(f"\n  Step 1: Uploaded interrogation document {doc_id}")

        # Parse
        integration_setup.parse_document(temp_dataset_for_e2e, [doc_id])
        print(f"  Step 2: Triggered parsing")

        # Wait (longer timeout for interrogation documents)
        interval = test_config.get("test", {}).get("parse_interval", 5)
        result = integration_setup.wait_for_parsing(
            temp_dataset_for_e2e,
            [doc_id],
            timeout=600,  # 10 minutes
            interval=interval,
        )
        assert result, "Parsing should complete successfully"
        print(f"  Step 3: Parsing completed")

        # Validate
        session = integration_setup.session
        url = f"{integration_setup.base_url}/api/v1/datasets/{temp_dataset_for_e2e}/documents"
        resp = session.get(url)
        data = resp.json()

        docs = {d["id"]: d for d in data["data"].get("docs", [])}
        doc = docs.get(doc_id)

        assert doc is not None, "Document should be found"
        assert doc.get("run") == "DONE", f"Document status should be DONE"
        print(f"  Step 4: Document status DONE, {doc.get('chunk_num', 0)} chunks")

        # Validate chunks
        chunks_url = f"{integration_setup.base_url}/api/v1/datasets/{temp_dataset_for_e2e}/documents/{doc_id}/chunks"
        resp = session.get(chunks_url, params={"page": 1, "page_size": 100})
        data = resp.json()

        chunks = data["data"].get("chunks", [])
        assert len(chunks) > 0, "Document should have chunks"

        # Validate chunk_type
        for i, chunk in enumerate(chunks[:10]):
            chunk_type = chunk.get("chunk_type")
            if chunk_type and chunk_type not in INTERROGATION_CHUNK_TYPES:
                pytest.fail(f"Chunk {i}: unexpected chunk_type '{chunk_type}'")

        print(f"  Step 5: Validated {len(chunks)} chunks")
