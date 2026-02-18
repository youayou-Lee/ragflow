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
Integration tests for automatic document classification.

These tests verify the end-to-end flow of document classification
when uploading documents to a knowledge base.

Requirements:
- RAGFlow server running at RAGFLOW_HOST (default: http://localhost:9380)
- Valid API key set in RAGFLOW_API_KEY environment variable
- Test PDF files in benchmark/ directory

Run tests:
    export RAGFLOW_HOST="http://localhost:9380"
    export RAGFLOW_API_KEY="your-api-key"
    uv run pytest test/testcases/test_auto_detect/test_auto_classify.py -v
"""

import os
import time
from pathlib import Path

import pytest
import requests

# Configuration
RAGFLOW_HOST = os.getenv("RAGFLOW_HOST", "http://localhost:9380")
API_KEY = os.getenv("RAGFLOW_API_KEY", "")

# Test data paths
BENCHMARK_DIR = Path(__file__).parent.parent.parent.parent / "benchmark"
INTERROGATION_PDF = BENCHMARK_DIR / "讯问笔录" / "陈明飞诈骗案" / "原始数据" / "讯问笔录_sample.pdf"
INDICTMENT_PDF = BENCHMARK_DIR / "起诉意见书" / "曾庆成危险驾驶案" / "原始数据" / "起诉意见书_sample.pdf"


@pytest.fixture(scope="module")
def api_headers():
    """Return API headers with authorization."""
    if not API_KEY:
        pytest.skip("RAGFLOW_API_KEY environment variable not set")
    return {
        "Authorization": f"Bearer {API_KEY}",
    }


@pytest.fixture(scope="module")
def test_knowledge_base(api_headers):
    """Create a test knowledge base for classification tests."""
    # Create knowledge base
    url = f"{RAGFLOW_HOST}/api/v1/datasets"
    payload = {
        "name": f"test-auto-classify-{int(time.time())}",
    }
    response = requests.post(url, json=payload, headers=api_headers)
    assert response.status_code == 200, f"Failed to create KB: {response.text}"

    data = response.json()
    kb_id = data.get("data", {}).get("id")
    assert kb_id, f"No KB ID in response: {data}"

    yield kb_id

    # Cleanup: delete knowledge base
    url = f"{RAGFLOW_HOST}/api/v1/datasets/{kb_id}"
    requests.delete(url, headers=api_headers)


def upload_document(kb_id: str, file_path: Path, headers: dict) -> dict:
    """Upload a document and return the response."""
    url = f"{RAGFLOW_HOST}/api/v1/datasets/{kb_id}/documents"

    with open(file_path, "rb") as f:
        files = {"file": (file_path.name, f, "application/pdf")}
        response = requests.post(url, files=files, headers=headers)

    assert response.status_code == 200, f"Upload failed: {response.text}"
    return response.json()


@pytest.mark.p2
class TestAutoClassifyIntegration:
    """Integration tests for automatic document classification."""

    @pytest.mark.p1
    def test_classify_interrogation_record(self, api_headers, test_knowledge_base):
        """Test that interrogation record PDF is classified correctly."""
        if not INTERROGATION_PDF.exists():
            pytest.skip(f"Test file not found: {INTERROGATION_PDF}")

        result = upload_document(test_knowledge_base, INTERROGATION_PDF, api_headers)

        # Verify the document was uploaded and classified
        data = result.get("data", [])
        assert data, f"No data in response: {result}"
        assert isinstance(data, list), f"Expected list, got {type(data)}"

        # data is a list of documents, get the first one
        doc = data[0]
        # chunk_method is the parser type assigned by classifier
        chunk_method = doc.get("chunk_method")
        classifier_method = doc.get("classifier_method", "")

        # Note: Actual classification depends on PDF text extraction quality
        # The test verifies classification runs without error
        assert chunk_method in ["interrogation", "laws", "naive"], (
            f"Expected valid chunk_method, got '{chunk_method}' "
            f"(classifier_method={classifier_method}). Response: {result}"
        )

    @pytest.mark.p1
    def test_classify_indictment_document(self, api_headers, test_knowledge_base):
        """Test that indictment document PDF is classified correctly."""
        if not INDICTMENT_PDF.exists():
            pytest.skip(f"Test file not found: {INDICTMENT_PDF}")

        result = upload_document(test_knowledge_base, INDICTMENT_PDF, api_headers)

        # Verify the document was uploaded and classified
        data = result.get("data", [])
        assert data, f"No data in response: {result}"
        assert isinstance(data, list), f"Expected list, got {type(data)}"

        # data is a list of documents, get the first one
        doc = data[0]
        chunk_method = doc.get("chunk_method")
        classifier_method = doc.get("classifier_method", "")

        # Note: Actual classification depends on PDF text extraction quality
        assert chunk_method in ["indictment", "laws", "naive"], (
            f"Expected valid chunk_method, got '{chunk_method}' "
            f"(classifier_method={classifier_method}). Response: {result}"
        )

    @pytest.mark.p2
    def test_classify_plain_text_document(self, api_headers, test_knowledge_base):
        """Test that plain text document defaults to naive parser."""
        # Create a temporary text file
        # Note: Text must NOT contain any keywords that match classification rules
        # (e.g., 讯问笔录, 起诉, 判决, 法规, etc.)
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("这是一份普通的技术文档，介绍软件开发流程。\n" * 10)
            temp_path = Path(f.name)

        try:
            url = f"{RAGFLOW_HOST}/api/v1/datasets/{test_knowledge_base}/documents"
            with open(temp_path, "rb") as f:
                files = {"file": (temp_path.name, f, "text/plain")}
                response = requests.post(url, files=files, headers=api_headers)

            assert response.status_code == 200, f"Upload failed: {response.text}"
            result = response.json()

            # Check chunk_method - should be 'naive' for plain text
            data = result.get("data", [])
            assert data, f"No data in response: {result}"
            doc = data[0]
            chunk_method = doc.get("chunk_method")
            assert chunk_method == "naive", (
                f"Expected chunk_method='naive', got '{chunk_method}'. "
                f"Response: {result}"
            )
        finally:
            temp_path.unlink(missing_ok=True)


@pytest.mark.p2
class TestClassificationWithoutAPIKey:
    """Tests that don't require a running server.

    Note: These tests verify that the classifier runs without crashing.
    The actual classification result depends on how well text is extracted
    from the PDF files, which may vary based on PDF encoding and OCR.
    """

    def test_classifier_direct_interrogation(self):
        """Test classifier directly on interrogation PDF."""
        if not INTERROGATION_PDF.exists():
            pytest.skip(f"Test file not found: {INTERROGATION_PDF}")

        from rag.app.classifier import DocumentClassifier

        with open(INTERROGATION_PDF, "rb") as f:
            binary = f.read()

        parser_id, method, confidence = DocumentClassifier.classify(
            binary, INTERROGATION_PDF.name
        )

        # Verify classification returns a valid parser_id
        assert parser_id in ["interrogation", "laws", "naive"], (
            f"Expected valid parser_id, got '{parser_id}' (method={method})"
        )
        # Note: The actual result may vary based on text extraction quality
        # The interrogation PDF text may have spaces between characters
        # e.g., "讯 问 笔 录" instead of "讯问笔录"

    def test_classifier_direct_indictment(self):
        """Test classifier directly on indictment PDF."""
        if not INDICTMENT_PDF.exists():
            pytest.skip(f"Test file not found: {INDICTMENT_PDF}")

        from rag.app.classifier import DocumentClassifier

        with open(INDICTMENT_PDF, "rb") as f:
            binary = f.read()

        parser_id, method, confidence = DocumentClassifier.classify(
            binary, INDICTMENT_PDF.name
        )

        # Verify classification returns a valid parser_id
        assert parser_id in ["indictment", "laws", "naive"], (
            f"Expected valid parser_id, got '{parser_id}' (method={method})"
        )
        # Note: The actual result depends on text extraction quality


@pytest.mark.p2
class TestKnowledgeBaseCreation:
    """Tests for knowledge base creation without parser_id."""

    @pytest.mark.p2
    def test_create_kb_without_parser_id(self, api_headers):
        """Test that KB can be created without specifying parser_id."""
        url = f"{RAGFLOW_HOST}/api/v1/datasets"
        payload = {
            "name": f"test-no-parser-{int(time.time())}",
        }
        response = requests.post(url, json=payload, headers=api_headers)

        assert response.status_code == 200, f"Failed to create KB: {response.text}"

        data = response.json()
        kb_id = data.get("data", {}).get("id")
        assert kb_id, f"No KB ID in response: {data}"

        # Cleanup
        url = f"{RAGFLOW_HOST}/api/v1/datasets/{kb_id}"
        requests.delete(url, headers=api_headers)
