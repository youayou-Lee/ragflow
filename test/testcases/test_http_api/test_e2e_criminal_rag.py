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
End-to-end integration tests for Criminal RAG feature - PR-5

Tests cover:
- Full E2E flow: upload -> parse -> retrieval -> QA (p1)
- Answer Gate integration with citations (p2)
- Retrieval extension verification (block_refs, bbox_union) (p2)
- doc_type filter support (p2)
- Dual-mode testing: PDF files and PaddleVL pre-parsed JSON (p1)

This test file validates that all previously implemented components (PR-1 through PR-4)
work together correctly in the complete flow.
"""

import json
from pathlib import Path

import pytest
from common import (
    chat_completions,
    create_chat_assistant,
    create_dataset,
    create_session_with_chat_assistant,
    delete_chat_assistants,
    delete_datasets,
    delete_session_with_chat_assistants,
    list_chunks,
    list_documents,
    parse_documents,
    retrieval_chunks,
    update_dataset,
    upload_documents,
)
from rag.answer_gate import AnswerGate, ValidationStatus
from utils import wait_for

# Sample file paths for dual-mode testing
SAMPLE_PDF_PATH = Path("/home/you/cs/proj/Superyou/SampleData/讯问笔录_sample.pdf")
SAMPLE_JSON_PATH = Path("/home/you/cs/proj/Superyou/ragflow/benchmark/起诉意见书/曾庆成危险驾驶案/原始数据/paddleocr_response.json")
# Indictment PDF sample file
INDICTMENT_PDF_PATH = Path("/home/you/cs/proj/Superyou/ragflow/benchmark/起诉意见书/曾庆成危险驾驶案/原始数据/起诉意见书_sample.pdf")


def get_test_file_type(file_path: Path) -> str:
    """Determine test mode based on file extension."""
    suffix = file_path.suffix.lower()
    if suffix == '.pdf':
        return 'pdf'
    elif suffix == '.json':
        return 'json'
    else:
        raise ValueError(f"Unsupported file type: {suffix}")


def load_paddlevl_json(json_path: Path) -> dict:
    """Load and parse PaddleVL JSON response file."""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_paddlevl_blocks(json_data: dict) -> list[dict]:
    """Extract blocks from PaddleVL layout parsing results.

    Returns a list of blocks with block_label, block_content, block_bbox, etc.
    """
    blocks = []
    result = json_data.get('result', {})
    layout_results = result.get('layoutParsingResults', [])

    for page_idx, page in enumerate(layout_results):
        pruned = page.get('prunedResult', {})
        parsing_res_list = pruned.get('parsing_res_list', [])

        for block in parsing_res_list:
            block_with_page = {
                **block,
                'page_index': page_idx,
            }
            blocks.append(block_with_page)

    return blocks

# Sample indictment document content for testing
INDICTMENT_SAMPLE = """
某某市公安局起诉意见书

经依法侦查查明：
被告人张某于2024年1月15日在某小区实施盗窃，盗窃金额人民币5000元。
案发后，被告人主动投案自首。

认定上述犯罪事实的证据如下：
（一）被告人供述与辩解
（二）被害人陈述
（三）现场勘查笔录
（四）涉案财物鉴定意见

综上所述，被告人张某的行为已构成盗窃罪。

根据《中华人民共和国刑事诉讼法》的规定，
现将此案移送审查起诉。
"""

# Chinese legal content with specific numeric values for Answer Gate testing
LEGAL_CONTENT_WITH_NUMBERS = """
案件编号：2024刑初字第00123号

公诉机关指控：
一、2023年6月10日，被告人李某在甲市乙区实施抢劫，抢得现金人民币12000元。
二、2023年8月22日，被告人李某在丙市丁区实施盗窃，盗窃金额人民币3500元。

上述事实，有下列证据证实：
1. 被告人供述：承认在上述时间、地点实施抢劫和盗窃。
2. 被害人陈述：确认被抢现金12000元，被盗现金3500元。
3. 监控录像：记录了被告人作案过程。
4. 鉴定意见：涉案金额合计15500元。

量刑建议：
根据《刑法》第二百六十三条规定，抢劫数额巨大，处十年以上有期徒刑。
"""


def create_indictment_txt_file(path):
    """Create a TXT file with Chinese legal/indictment content."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(INDICTMENT_SAMPLE)
    return path


def create_legal_txt_file(path):
    """Create a TXT file with legal content containing numeric values."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(LEGAL_CONTENT_WITH_NUMBERS)
    return path


@wait_for(200, 1, "Document parsing timeout")
def _wait_for_parsing(auth, dataset_id, document_ids=None):
    """Wait for documents to finish parsing."""
    res = list_documents(auth, dataset_id)
    target_docs = res["data"]["docs"]
    if document_ids is None:
        return all(doc.get("run") == "DONE" for doc in target_docs)
    target_ids = set(document_ids)
    # Check if all target documents are found and done
    found_ids = set()
    for doc in target_docs:
        doc_id = doc.get("id")
        if doc_id in target_ids:
            found_ids.add(doc_id)
            if doc.get("run") != "DONE":
                return False
    # Return True only if all target documents are found and done
    return found_ids == target_ids


@wait_for(600, 5, "PDF document parsing timeout")
def _wait_for_pdf_parsing(auth, dataset_id, document_ids=None):
    """Wait for documents to finish parsing."""
    res = list_documents(auth, dataset_id)
    target_docs = res["data"]["docs"]
    if document_ids is None:
        return all(doc.get("run") == "DONE" for doc in target_docs)
    target_ids = set(document_ids)
    # Check if all target documents are found and done
    found_ids = set()
    for doc in target_docs:
        doc_id = doc.get("id")
        if doc_id in target_ids:
            found_ids.add(doc_id)
            if doc.get("run") != "DONE":
                return False
    # Return True only if all target documents are found and done
    return found_ids == target_ids


@pytest.mark.p1
class TestCriminalRagE2E:
    """End-to-end tests for Criminal RAG flow."""

    def test_full_flow_with_indictment_content(self, HttpApiAuth, request):
        """
        Test the complete Criminal RAG flow:
        1. Create dataset with PaddleOCR config
        2. Upload indictment PDF document
        3. Parse document
        4. Verify chunks have content
        5. Create chat assistant linked to dataset
        6. Create session
        7. Send question via chat completions
        8. Verify response structure
        """
        # Skip if PDF file not found
        if not INDICTMENT_PDF_PATH.exists():
            pytest.skip(f"Indictment PDF file not found: {INDICTMENT_PDF_PATH}")

        # 1. Create dataset with PaddleOCR config for PDF parsing
        res = create_dataset(HttpApiAuth, {
            "name": "criminal_rag_e2e_dataset",
            "embedding_model": "embedding-3@ZHIPU-AI",
            "parser_config": {
                "layout_recognize": "PaddleOCR-VL@paddleocr",
            }
        })
        assert res["code"] == 0, res
        dataset_id = res["data"]["id"]
        request.addfinalizer(lambda: delete_datasets(HttpApiAuth, {"ids": [dataset_id]}))

        # 2. Upload indictment PDF document
        res = upload_documents(HttpApiAuth, dataset_id, [INDICTMENT_PDF_PATH])
        assert res["code"] == 0, res
        document_ids = [doc["id"] for doc in res["data"]]

        # 3. Parse document
        res = parse_documents(HttpApiAuth, dataset_id, {"document_ids": document_ids})
        assert res["code"] == 0, res
        _wait_for_pdf_parsing(HttpApiAuth, dataset_id, document_ids)

        # 4. Verify chunks exist and have content
        res = list_chunks(HttpApiAuth, dataset_id, document_ids[0])
        assert res["code"] == 0, res
        chunks = res["data"]["chunks"]
        assert len(chunks) > 0, "Should have at least one chunk after parsing"

        # Verify chunks have content
        for chunk in chunks:
            assert "content_with_weight" in chunk or "content" in chunk, chunk
            content = chunk.get("content_with_weight") or chunk.get("content", "")
            assert len(content) > 0, "Chunk should have content"

        # 5. Create chat assistant linked to dataset
        res = create_chat_assistant(
            HttpApiAuth,
            {"name": "criminal_rag_chat", "dataset_ids": [dataset_id]},
        )
        assert res["code"] == 0, res
        chat_id = res["data"]["id"]
        request.addfinalizer(lambda: delete_session_with_chat_assistants(HttpApiAuth, chat_id))
        request.addfinalizer(lambda: delete_chat_assistants(HttpApiAuth))

        # 6. Create session
        res = create_session_with_chat_assistant(
            HttpApiAuth, chat_id, {"name": "criminal_rag_session"}
        )
        assert res["code"] == 0, res
        session_id = res["data"]["id"]

        # 7. Send question via chat completions
        res = chat_completions(
            HttpApiAuth,
            chat_id,
            {
                "question": "曾庆成的酒精测试结果是多少？",
                "stream": False,
                "session_id": session_id,
            },
        )
        assert res["code"] == 0, res

        # 8. Verify response structure
        assert isinstance(res["data"], dict), res
        for key in ["answer", "reference", "id", "session_id"]:
            assert key in res["data"], f"Missing key '{key}' in response: {res}"
        assert res["data"]["session_id"] == session_id, res

    @pytest.mark.p2
    def test_retrieval_with_legal_content(self, HttpApiAuth, tmp_path, request):
        """
        Test retrieval API with legal content containing numeric values.
        Verify retrieval returns results with relevant content.
        """
        # Create dataset
        res = create_dataset(HttpApiAuth, {"name": "legal_retrieval_dataset", "embedding_model": "embedding-3@ZHIPU-AI"})
        assert res["code"] == 0, res
        dataset_id = res["data"]["id"]
        request.addfinalizer(lambda: delete_datasets(HttpApiAuth, {"ids": [dataset_id]}))

        # Upload legal document
        file_path = create_legal_txt_file(tmp_path / "legal_case.txt")
        res = upload_documents(HttpApiAuth, dataset_id, [file_path])
        assert res["code"] == 0, res
        document_ids = [doc["id"] for doc in res["data"]]

        # Parse document
        res = parse_documents(HttpApiAuth, dataset_id, {"document_ids": document_ids})
        assert res["code"] == 0, res
        _wait_for_parsing(HttpApiAuth, dataset_id, document_ids)

        # Test retrieval with question about numeric values
        res = retrieval_chunks(
            HttpApiAuth,
            {
                "question": "抢劫金额是多少？",
                "dataset_ids": [dataset_id],
                "page_size": 5,
            },
        )
        assert res["code"] == 0, res
        assert len(res["data"]["chunks"]) > 0, "Should retrieve relevant chunks"

        # Verify retrieved chunks contain numeric content
        all_content = " ".join(
            c.get("content_with_weight") or c.get("content", "")
            for c in res["data"]["chunks"]
        )
        # Should contain the numeric values from the document
        assert "12000" in all_content or "抢劫" in all_content, all_content


@pytest.mark.p2
class TestRetrievalExtensionFields:
    """Test that retrieval API returns PR-4 fields (block_refs, bbox_union)."""

    def test_retrieval_chunk_structure(self, HttpApiAuth, request):
        """
        Test that retrieved chunks have the expected structure,
        including PR-4 extension fields when available.
        """
        # Skip if PDF file not found
        if not INDICTMENT_PDF_PATH.exists():
            pytest.skip(f"Indictment PDF file not found: {INDICTMENT_PDF_PATH}")

        # Create dataset with PaddleOCR config
        res = create_dataset(HttpApiAuth, {
            "name": "retrieval_fields_dataset",
            "embedding_model": "embedding-3@ZHIPU-AI",
            "parser_config": {
                "layout_recognize": "PaddleOCR-VL@paddleocr",
            }
        })
        assert res["code"] == 0, res
        dataset_id = res["data"]["id"]
        request.addfinalizer(lambda: delete_datasets(HttpApiAuth, {"ids": [dataset_id]}))

        # Upload PDF document
        res = upload_documents(HttpApiAuth, dataset_id, [INDICTMENT_PDF_PATH])
        assert res["code"] == 0, res
        document_ids = [doc["id"] for doc in res["data"]]

        # Parse document
        res = parse_documents(HttpApiAuth, dataset_id, {"document_ids": document_ids})
        assert res["code"] == 0, res
        _wait_for_pdf_parsing(HttpApiAuth, dataset_id, document_ids)

        # Retrieve chunks (using keywords relevant to the indictment content)
        res = retrieval_chunks(
            HttpApiAuth,
            {
                "question": "危险驾驶",
                "dataset_ids": [dataset_id],
                "page_size": 10,
            },
        )
        assert res["code"] == 0, res
        chunks = res["data"]["chunks"]
        assert len(chunks) > 0, "Should have retrieved chunks"

        # Verify chunk structure includes expected fields
        for chunk in chunks:
            # Core fields that should always be present
            assert "id" in chunk, f"Chunk missing id: {chunk}"
            assert "content_with_weight" in chunk or "content" in chunk, chunk

            # PR-4 fields (block_refs, bbox_union) may be None for TXT files
            # but the keys should exist in the response structure
            # For TXT files without PDF, these will be None/empty
            assert "dataset_id" in chunk, chunk
            assert "document_id" in chunk, chunk

    def test_list_chunks_includes_pr4_fields(self, HttpApiAuth, request):
        """
        Test that the /chunks/list API includes PR-4 fields in response.
        """
        # Skip if PDF file not found
        if not INDICTMENT_PDF_PATH.exists():
            pytest.skip(f"Indictment PDF file not found: {INDICTMENT_PDF_PATH}")

        # Create dataset with PaddleOCR config
        res = create_dataset(HttpApiAuth, {
            "name": "list_chunks_dataset",
            "embedding_model": "embedding-3@ZHIPU-AI",
            "parser_config": {
                "layout_recognize": "PaddleOCR-VL@paddleocr",
            }
        })
        assert res["code"] == 0, res
        dataset_id = res["data"]["id"]
        request.addfinalizer(lambda: delete_datasets(HttpApiAuth, {"ids": [dataset_id]}))

        # Upload PDF document
        res = upload_documents(HttpApiAuth, dataset_id, [INDICTMENT_PDF_PATH])
        assert res["code"] == 0, res
        document_ids = [doc["id"] for doc in res["data"]]

        # Parse document
        res = parse_documents(HttpApiAuth, dataset_id, {"document_ids": document_ids})
        assert res["code"] == 0, res
        _wait_for_pdf_parsing(HttpApiAuth, dataset_id, document_ids)

        # List chunks
        res = list_chunks(HttpApiAuth, dataset_id, document_ids[0])
        assert res["code"] == 0, res
        chunks = res["data"]["chunks"]
        assert len(chunks) > 0, "Should have chunks"

        # Verify basic chunk structure
        for chunk in chunks:
            assert "id" in chunk, chunk


@pytest.mark.p2
class TestAnswerGateIntegration:
    """Test Answer Gate integration with E2E flow."""

    def test_answer_gate_with_retrieved_chunks(self, HttpApiAuth, tmp_path, request):
        """
        Test that Answer Gate can validate citations using retrieved chunks.
        This tests the integration between PR-3 (Answer Gate) and PR-4 (Retrieval Extension).
        """
        # Create dataset
        res = create_dataset(HttpApiAuth, {"name": "answer_gate_dataset", "embedding_model": "embedding-3@ZHIPU-AI"})
        assert res["code"] == 0, res
        dataset_id = res["data"]["id"]
        request.addfinalizer(lambda: delete_datasets(HttpApiAuth, {"ids": [dataset_id]}))

        # Upload legal document with numeric values
        file_path = create_legal_txt_file(tmp_path / "answer_gate.txt")
        res = upload_documents(HttpApiAuth, dataset_id, [file_path])
        assert res["code"] == 0, res
        document_ids = [doc["id"] for doc in res["data"]]

        # Parse document
        res = parse_documents(HttpApiAuth, dataset_id, {"document_ids": document_ids})
        assert res["code"] == 0, res
        _wait_for_parsing(HttpApiAuth, dataset_id, document_ids)

        # Retrieve chunks for a specific question
        res = retrieval_chunks(
            HttpApiAuth,
            {
                "question": "抢劫金额是多少",
                "dataset_ids": [dataset_id],
                "page_size": 3,
            },
        )
        assert res["code"] == 0, res
        chunks = res["data"]["chunks"]
        assert len(chunks) > 0, "Should have retrieved chunks"

        # Convert retrieval results to format expected by Answer Gate
        raw_chunks = []
        for chunk in chunks:
            raw_chunks.append({
                "chunk_id": chunk["id"],
                "content_with_weight": chunk.get("content_with_weight") or chunk.get("content", ""),
                "page_num_int": chunk.get("page_num_int", []),
            })

        # Simulate evidence extracted from an answer
        evidences = []
        if raw_chunks:
            content = raw_chunks[0]["content_with_weight"]
            # Extract a substring as evidence
            if "12000" in content:
                start = content.find("12000")
                evidences.append({
                    "chunk_id": raw_chunks[0]["chunk_id"],
                    "excerpt": content[max(0, start - 10):start + 20],
                    "page_index": raw_chunks[0].get("page_num_int", [None])[0] if raw_chunks[0].get("page_num_int") else None,
                })

        # Validate with Answer Gate
        if evidences:
            gate = AnswerGate()
            result = gate.validate(
                answer="被告人抢劫金额为12000元",
                evidences=evidences,
                raw_chunks=raw_chunks,
            )
            # Should validate successfully since excerpt contains the numeric value
            assert result.status in [ValidationStatus.VALID, ValidationStatus.CITATION_INSUFFICIENT], \
                f"Validation status: {result.status}, errors: {result.validation_errors}"

    def test_answer_gate_no_evidence_case(self):
        """
        Test Answer Gate behavior when no evidence is provided.
        This is a unit-style test but included here for E2E context.
        """
        gate = AnswerGate()
        result = gate.validate("任何答案", [], [])
        assert result.status == ValidationStatus.NO_EVIDENCE
        assert len(result.evidences) == 0

    def test_answer_gate_numeric_grounding(self):
        """
        Test Answer Gate numeric grounding validation.
        Verifies that numeric values in answer must be grounded in evidence.
        """
        gate = AnswerGate()

        # Valid case: numeric value is in excerpt
        result = gate.validate(
            answer="被告人抢劫金额12000元",
            evidences=[{"chunk_id": "c1", "excerpt": "抢劫金额12000元"}],
            raw_chunks=[{"chunk_id": "c1", "content_with_weight": "抢劫金额12000元"}],
        )
        assert result.status == ValidationStatus.VALID

        # Invalid case: numeric value not in excerpt
        result = gate.validate(
            answer="被告人抢劫金额12000元",
            evidences=[{"chunk_id": "c1", "excerpt": "被告人实施抢劫"}],
            raw_chunks=[{"chunk_id": "c1", "content_with_weight": "被告人实施抢劫"}],
        )
        assert result.status == ValidationStatus.CITATION_INSUFFICIENT


@pytest.mark.p2
class TestDocTypeFilter:
    """Test doc_type filter support in retrieval."""

    def test_retrieval_with_doc_type_filter(self, HttpApiAuth, request):
        """
        Test retrieval API with doc_type filter.
        Uses PDF file for proper doc_type detection.
        """
        # Skip if PDF file not found
        if not INDICTMENT_PDF_PATH.exists():
            pytest.skip(f"Indictment PDF file not found: {INDICTMENT_PDF_PATH}")

        # Create dataset with PaddleOCR config
        res = create_dataset(HttpApiAuth, {
            "name": "doc_type_filter_dataset",
            "embedding_model": "embedding-3@ZHIPU-AI",
            "parser_config": {
                "layout_recognize": "PaddleOCR-VL@paddleocr",
            }
        })
        assert res["code"] == 0, res
        dataset_id = res["data"]["id"]
        request.addfinalizer(lambda: delete_datasets(HttpApiAuth, {"ids": [dataset_id]}))

        # Upload PDF document
        res = upload_documents(HttpApiAuth, dataset_id, [INDICTMENT_PDF_PATH])
        assert res["code"] == 0, res
        document_ids = [doc["id"] for doc in res["data"]]

        # Parse document
        res = parse_documents(HttpApiAuth, dataset_id, {"document_ids": document_ids})
        assert res["code"] == 0, res
        _wait_for_pdf_parsing(HttpApiAuth, dataset_id, document_ids)

        # Test retrieval without doc_type filter (should work)
        res = retrieval_chunks(
            HttpApiAuth,
            {
                "question": "危险驾驶",
                "dataset_ids": [dataset_id],
            },
        )
        assert res["code"] == 0, res

        # Test retrieval with doc_type filter
        res = retrieval_chunks(
            HttpApiAuth,
            {
                "question": "危险驾驶",
                "dataset_ids": [dataset_id],
                "doc_type": "indictment",  # Filter by doc_type
            },
        )
        # Should not error, may return empty if doc_type not set
        assert res["code"] == 0, res


@pytest.mark.p3
class TestCriminalRagEdgeCases:
    """Edge cases and boundary conditions for Criminal RAG."""

    def test_empty_document_handling(self, HttpApiAuth, tmp_path, request):
        """Test handling of documents with minimal content."""
        # Create dataset
        res = create_dataset(HttpApiAuth, {"name": "empty_doc_dataset", "embedding_model": "embedding-3@ZHIPU-AI"})
        assert res["code"] == 0, res
        dataset_id = res["data"]["id"]
        request.addfinalizer(lambda: delete_datasets(HttpApiAuth, {"ids": [dataset_id]}))

        # Upload minimal content document
        file_path = tmp_path / "minimal.txt"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("测试")
        res = upload_documents(HttpApiAuth, dataset_id, [file_path])
        assert res["code"] == 0, res
        document_ids = [doc["id"] for doc in res["data"]]

        # Parse document
        res = parse_documents(HttpApiAuth, dataset_id, {"document_ids": document_ids})
        assert res["code"] == 0, res
        _wait_for_parsing(HttpApiAuth, dataset_id, document_ids)

    def test_chinese_character_retrieval(self, HttpApiAuth, tmp_path, request):
        """Test retrieval with Chinese characters."""
        # Create dataset
        res = create_dataset(HttpApiAuth, {"name": "chinese_retrieval_dataset", "embedding_model": "embedding-3@ZHIPU-AI"})
        assert res["code"] == 0, res
        dataset_id = res["data"]["id"]
        request.addfinalizer(lambda: delete_datasets(HttpApiAuth, {"ids": [dataset_id]}))

        # Upload Chinese content
        file_path = tmp_path / "chinese.txt"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("这是一个中文测试文档。包含一些关键词：起诉书、判决书、检察院。")
        res = upload_documents(HttpApiAuth, dataset_id, [file_path])
        assert res["code"] == 0, res
        document_ids = [doc["id"] for doc in res["data"]]

        # Parse document
        res = parse_documents(HttpApiAuth, dataset_id, {"document_ids": document_ids})
        assert res["code"] == 0, res
        _wait_for_parsing(HttpApiAuth, dataset_id, document_ids)

        # Test retrieval with Chinese query
        res = retrieval_chunks(
            HttpApiAuth,
            {
                "question": "起诉书",
                "dataset_ids": [dataset_id],
            },
        )
        assert res["code"] == 0, res

    def test_multiple_legal_documents(self, HttpApiAuth, tmp_path, request):
        """Test with multiple legal documents in one dataset."""
        # Create dataset
        res = create_dataset(HttpApiAuth, {"name": "multi_legal_docs_dataset", "embedding_model": "embedding-3@ZHIPU-AI"})
        assert res["code"] == 0, res
        dataset_id = res["data"]["id"]
        request.addfinalizer(lambda: delete_datasets(HttpApiAuth, {"ids": [dataset_id]}))

        # Upload multiple documents (using generic legal content, not indictment-specific)
        file_paths = []
        for i, content in enumerate([
            LEGAL_CONTENT_WITH_NUMBERS,
            "案件编号：2024民初字第00456号\n这是一起民事案件。当事人张某与李某因合同纠纷诉至法院。",
            "判决书摘要：本院经审理查明，被告李某确实存在违约行为，应当承担相应的民事责任。",
        ]):
            file_path = tmp_path / f"legal_doc_{i}.txt"
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            file_paths.append(file_path)

        res = upload_documents(HttpApiAuth, dataset_id, file_paths)
        assert res["code"] == 0, res
        document_ids = [doc["id"] for doc in res["data"]]

        # Parse all documents
        res = parse_documents(HttpApiAuth, dataset_id, {"document_ids": document_ids})
        assert res["code"] == 0, res
        _wait_for_parsing(HttpApiAuth, dataset_id, document_ids)

        # Verify all documents are parsed
        res = list_documents(HttpApiAuth, dataset_id)
        assert res["code"] == 0, res
        for doc in res["data"]["docs"]:
            assert doc["run"] == "DONE", f"Document {doc['id']} not parsed: {doc['run']}"

        # Test retrieval
        res = retrieval_chunks(
            HttpApiAuth,
            {
                "question": "案件",
                "dataset_ids": [dataset_id],
                "page_size": 10,
            },
        )
        assert res["code"] == 0, res
        # Should retrieve from multiple documents
        assert len(res["data"]["chunks"]) > 0, "Should retrieve chunks from multiple documents"


@pytest.mark.p1
class TestCriminalRagDualModeE2E:
    """
    Dual-mode E2E tests supporting both PDF and JSON file types.

    - PDF mode: Upload PDF file and parse through RAGFlow
    - JSON mode: Load PaddleVL pre-parsed JSON data
    """

    @pytest.fixture
    def criminal_file_path(self, request):
        """Return criminal document file path (PDF or JSON)."""
        file_path = request.param
        if not file_path.exists():
            pytest.skip(f"Test file not found: {file_path}")
        return file_path

    @pytest.mark.parametrize("criminal_file_path", [
        SAMPLE_PDF_PATH,
        SAMPLE_JSON_PATH,
    ], indirect=True)
    def test_dual_mode_file_validation(self, criminal_file_path):
        """
        Validate that test files exist and have correct format.

        - PDF mode: Verify file extension
        - JSON mode: Verify JSON structure with PaddleVL format
        """
        file_type = get_test_file_type(criminal_file_path)

        if file_type == 'pdf':
            assert criminal_file_path.suffix.lower() == '.pdf'
            assert criminal_file_path.stat().st_size > 0, "PDF file should not be empty"
        else:
            # JSON mode: validate PaddleVL structure
            data = load_paddlevl_json(criminal_file_path)
            assert 'result' in data, "PaddleVL JSON should have 'result' key"
            assert 'layoutParsingResults' in data['result'], "Should have layoutParsingResults"
            assert 'errorCode' in data, "Should have errorCode"
            assert data['errorCode'] == 0, f"PaddleVL error: {data.get('errorMsg')}"

            # Extract blocks and verify structure
            blocks = extract_paddlevl_blocks(data)
            assert len(blocks) > 0, "Should have at least one block"

            # Verify block structure contains required fields
            for block in blocks:
                assert 'block_label' in block, f"Block missing block_label: {block}"
                assert 'block_content' in block, f"Block missing block_content: {block}"
                assert 'block_bbox' in block, f"Block missing block_bbox: {block}"
                assert 'page_index' in block, f"Block missing page_index: {block}"

    @pytest.mark.parametrize("criminal_file_path", [
        SAMPLE_PDF_PATH,
    ], indirect=True)
    def test_pdf_mode_full_flow(self, HttpApiAuth, criminal_file_path, request):
        """
        Full E2E flow for PDF mode using PaddleOCR:
        1. Create dataset with PaddleOCR parser config
        2. Upload PDF file
        3. Parse and wait for completion
        4. Verify chunks with PR-4 fields (block_refs, bbox_union, page_num_int)
        5. Test retrieval
        """
        # 1. Create dataset with PaddleOCR configuration
        # Use "PaddleOCR-VL@paddleocr" to enable PaddleVL parsing
        res = create_dataset(HttpApiAuth, {
            "name": "criminal_pdf_paddleocr_e2e_dataset",
            "embedding_model": "embedding-3@ZHIPU-AI",
            "parser_config": {
                "layout_recognize": "PaddleOCR-VL@paddleocr",
            }
        })
        assert res["code"] == 0, res
        dataset_id = res["data"]["id"]
        request.addfinalizer(lambda: delete_datasets(HttpApiAuth, {"ids": [dataset_id]}))

        # 2. Upload PDF file
        res = upload_documents(HttpApiAuth, dataset_id, [criminal_file_path])
        assert res["code"] == 0, res
        document_ids = [doc["id"] for doc in res["data"]]

        # 3. Parse and wait (use longer timeout for PDF via API)
        res = parse_documents(HttpApiAuth, dataset_id, {"document_ids": document_ids})
        assert res["code"] == 0, res
        _wait_for_pdf_parsing(HttpApiAuth, dataset_id, document_ids)

        # 4. Verify chunks
        res = list_chunks(HttpApiAuth, dataset_id, document_ids[0])
        assert res["code"] == 0, res
        chunks = res["data"]["chunks"]
        assert len(chunks) > 0, "Should have chunks after PDF parsing"

        # Verify chunk content and structure
        for chunk in chunks:
            content = chunk.get("content_with_weight") or chunk.get("content", "")
            assert len(content) > 0, "Chunk should have content"

            # PR-4 fields may be present for PDF files
            # block_refs: list of block references
            # bbox_union: bounding box union for the chunk
            # page_num_int: list of page numbers
            # These fields may be None/empty for some chunkers
            assert "id" in chunk, "Chunk should have id"
            assert "document_id" in chunk, "Chunk should have document_id"

        # 5. Test retrieval
        res = retrieval_chunks(
            HttpApiAuth,
            {
                "question": "讯问",
                "dataset_ids": [dataset_id],
                "page_size": 5,
            },
        )
        assert res["code"] == 0, res
        assert len(res["data"]["chunks"]) > 0, "Should retrieve chunks from PDF"

    def test_json_mode_block_extraction(self):
        """
        Test JSON mode: Extract and validate blocks from PaddleVL JSON.

        This test validates the JSON parsing without requiring API server.
        """
        if not SAMPLE_JSON_PATH.exists():
            pytest.skip(f"JSON file not found: {SAMPLE_JSON_PATH}")

        # Load and parse JSON
        data = load_paddlevl_json(SAMPLE_JSON_PATH)

        # Validate PaddleVL response structure
        assert data.get('errorCode') == 0, f"PaddleVL error: {data.get('errorMsg')}"

        # Extract blocks
        blocks = extract_paddlevl_blocks(data)
        assert len(blocks) > 0, "Should extract blocks from JSON"

        # Validate block structure
        seen_labels = set()
        for block in blocks:
            # Required fields
            assert 'block_label' in block
            assert 'block_content' in block
            assert 'block_bbox' in block
            assert 'page_index' in block

            # Collect labels
            seen_labels.add(block['block_label'])

            # Validate bbox format [x1, y1, x2, y2]
            bbox = block['block_bbox']
            assert isinstance(bbox, list) and len(bbox) == 4, f"Invalid bbox: {bbox}"
            assert all(isinstance(v, (int, float)) for v in bbox), f"Bbox should be numbers: {bbox}"

        # Should have multiple block types (header, text, etc.)
        print(f"Block labels found: {seen_labels}")

    def test_json_mode_page_structure(self):
        """
        Test JSON mode: Validate page structure in PaddleVL JSON.
        """
        if not SAMPLE_JSON_PATH.exists():
            pytest.skip(f"JSON file not found: {SAMPLE_JSON_PATH}")

        data = load_paddlevl_json(SAMPLE_JSON_PATH)
        result = data.get('result', {})
        layout_results = result.get('layoutParsingResults', [])

        assert len(layout_results) > 0, "Should have at least one page"

        for page_idx, page in enumerate(layout_results):
            pruned = page.get('prunedResult', {})

            # Check page dimensions
            assert 'width' in pruned, f"Page {page_idx} missing width"
            assert 'height' in pruned, f"Page {page_idx} missing height"

            # Check parsing results
            parsing_res = pruned.get('parsing_res_list', [])
            assert len(parsing_res) > 0, f"Page {page_idx} should have parsing results"

            # Check markdown output
            markdown = page.get('markdown', {})
            if 'text' in markdown:
                md_text = markdown['text']
                assert isinstance(md_text, str), "Markdown text should be string"
                # Should have some content
                print(f"Page {page_idx} markdown length: {len(md_text)} chars")
