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
"""Integration tests for interrogation record (讯问笔录) parsing.

Tests use prebuilt datasets to avoid repeated setup:
- Single document parsing test
- Multiple document parsing test
"""

import pytest

from test.eval.evaluator.setup import EvaluationSetup


class TestParseInterrogation:
    """Test suite for interrogation record parsing."""

    def test_parse_single_interrogation(
        self,
        integration_setup: EvaluationSetup,
        interrogation_single_dataset: str,
    ):
        """Test parsing a single interrogation document.

        Uses prebuilt dataset with one pre-parsed interrogation document.
        Verifies that parsing is complete and documents are in DONE state.

        Args:
            integration_setup: Logged-in EvaluationSetup instance
            interrogation_single_dataset: Prebuilt dataset ID with single interrogation
        """
        # Get document list from prebuilt dataset
        session = integration_setup.session
        url = f"{integration_setup.base_url}/api/v1/datasets/{interrogation_single_dataset}/documents"
        resp = session.get(url)
        data = resp.json()

        assert data.get("code") == 0, "List documents should succeed"

        docs = data["data"].get("docs", [])
        assert len(docs) >= 1, "Dataset should have at least one document"

        # Verify document status
        for doc in docs:
            status = doc.get("run")
            assert status == "DONE", f"Document {doc.get('id')} should be DONE, got: {status}"
            chunk_count = doc.get("chunk_num", 0)
            print(f"  Document {doc.get('name')}: {chunk_count} chunks")

    def test_parse_multiple_interrogations(
        self,
        integration_setup: EvaluationSetup,
        interrogation_multiple_dataset: str,
    ):
        """Test parsing multiple interrogation documents.

        Uses prebuilt dataset with multiple pre-parsed interrogation documents.
        Verifies all documents are in DONE state.

        Args:
            integration_setup: Logged-in EvaluationSetup instance
            interrogation_multiple_dataset: Prebuilt dataset ID with multiple interrogations
        """
        # Get document list from prebuilt dataset
        session = integration_setup.session
        url = f"{integration_setup.base_url}/api/v1/datasets/{interrogation_multiple_dataset}/documents"
        resp = session.get(url)
        data = resp.json()

        assert data.get("code") == 0, "List documents should succeed"

        docs = data["data"].get("docs", [])
        assert len(docs) >= 2, "Dataset should have at least two documents"

        # Verify all documents are parsed
        for doc in docs:
            status = doc.get("run")
            assert status == "DONE", f"Document {doc.get('id')} should be DONE, got: {status}"
            chunk_count = doc.get("chunk_num", 0)
            print(f"  Document {doc.get('name')}: {chunk_count} chunks")

    def test_interrogation_chunk_count(
        self,
        integration_setup: EvaluationSetup,
        interrogation_single_dataset: str,
    ):
        """Test that parsed interrogation has generated chunks.

        Args:
            integration_setup: Logged-in EvaluationSetup instance
            interrogation_single_dataset: Prebuilt dataset ID with single interrogation
        """
        # Get document list
        session = integration_setup.session
        url = f"{integration_setup.base_url}/api/v1/datasets/{interrogation_single_dataset}/documents"
        resp = session.get(url)
        data = resp.json()

        docs = data["data"].get("docs", [])
        assert len(docs) >= 1, "Dataset should have at least one document"

        doc = docs[0]
        assert doc.get("run") == "DONE", "Document should be fully parsed"

        # Check chunk count
        chunk_count = doc.get("chunk_num", 0)
        assert chunk_count > 0, "Parsed document should have at least one chunk"
        print(f"  Total chunks: {chunk_count}")

    def test_interrogation_chunk_content(
        self,
        integration_setup: EvaluationSetup,
        interrogation_single_dataset: str,
    ):
        """Test that interrogation chunks have actual content.

        Args:
            integration_setup: Logged-in EvaluationSetup instance
            interrogation_single_dataset: Prebuilt dataset ID with single interrogation
        """
        # Get document list
        session = integration_setup.session
        url = f"{integration_setup.base_url}/api/v1/datasets/{interrogation_single_dataset}/documents"
        resp = session.get(url)
        data = resp.json()

        docs = data["data"].get("docs", [])
        assert len(docs) >= 1, "Dataset should have at least one document"

        doc_id = docs[0]["id"]

        # Get chunks
        chunks_url = f"{integration_setup.base_url}/api/v1/datasets/{interrogation_single_dataset}/documents/{doc_id}/chunks"
        resp = session.get(chunks_url, params={"page": 1, "page_size": 10})
        data = resp.json()

        assert data.get("code") == 0, "List chunks should succeed"

        chunks = data["data"].get("chunks", [])
        assert len(chunks) > 0, "Document should have chunks"

        # Verify chunks have content
        for i, chunk in enumerate(chunks[:5]):  # Check first 5 chunks
            content = chunk.get("content", "")
            assert len(content) > 0, f"Chunk {i} should have content"
            assert content.strip(), f"Chunk {i} content should not be empty"
            print(f"  Chunk {i}: {len(content)} chars")
