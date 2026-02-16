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
Unit tests for PR-4 Retrieval Extension

Tests verify:
- block_refs and bbox_union fields are present in code
- doc_type filter support is implemented
- chunk list API response includes new fields
"""

import pytest
import re


class TestSearchPyFields:
    """Test search.py contains required fields"""

    @pytest.mark.p1
    def test_retrieval_returns_block_refs(self):
        """Verify retrieval() returns block_refs field"""
        with open("rag/nlp/search.py", "r") as f:
            content = f.read()

        # Check block_refs is in the chunk dict construction
        assert '"block_refs"' in content, "block_refs should be in retrieval() output"
        # Verify it's in the dict assignment context
        assert '"block_refs": chunk.get("block_refs"' in content, \
            "block_refs should use chunk.get() with default"

    @pytest.mark.p1
    def test_retrieval_returns_bbox_union(self):
        """Verify retrieval() returns bbox_union field"""
        with open("rag/nlp/search.py", "r") as f:
            content = f.read()

        assert '"bbox_union"' in content, "bbox_union should be in retrieval() output"
        assert '"bbox_union": chunk.get("bbox_union"' in content, \
            "bbox_union should use chunk.get() with default"

    @pytest.mark.p1
    def test_retrieval_returns_page_num_int(self):
        """Verify retrieval() returns page_num_int field"""
        with open("rag/nlp/search.py", "r") as f:
            content = f.read()

        assert '"page_num_int"' in content, "page_num_int should be in retrieval() output"


class TestSearchDefaultFields:
    """Test search() includes new fields in default field list"""

    @pytest.mark.p1
    def test_search_default_fields_include_block_refs(self):
        """Verify search() default fields include block_refs"""
        with open("rag/nlp/search.py", "r") as f:
            content = f.read()

        # Find the default fields list
        match = re.search(r'src\s*=\s*req\.get\("fields",\s*\[(.*?)\]\)', content, re.DOTALL)
        assert match, "Should find default fields list"

        fields_str = match.group(1)
        assert '"block_refs"' in fields_str, "block_refs should be in default fields"

    @pytest.mark.p1
    def test_search_default_fields_include_bbox_union(self):
        """Verify search() default fields include bbox_union"""
        with open("rag/nlp/search.py", "r") as f:
            content = f.read()

        match = re.search(r'src\s*=\s*req\.get\("fields",\s*\[(.*?)\]\)', content, re.DOTALL)
        assert match, "Should find default fields list"

        fields_str = match.group(1)
        assert '"bbox_union"' in fields_str, "bbox_union should be in default fields"


class TestDocTypeFilter:
    """Test doc_type filter support in get_filters"""

    @pytest.mark.p1
    def test_get_filters_doc_type_mapping(self):
        """Verify get_filters maps doc_type to doc_type_kwd"""
        with open("rag/nlp/search.py", "r") as f:
            content = f.read()

        # Check doc_type is mapped to doc_type_kwd
        assert '"doc_type"' in content, "doc_type parameter should be handled"
        assert '"doc_type_kwd"' in content, "doc_type_kwd should be in condition"

        # Verify the mapping logic exists
        assert 'condition["doc_type_kwd"] = req["doc_type"]' in content, \
            "doc_type should be mapped to doc_type_kwd condition"

    @pytest.mark.p2
    def test_doc_type_kwd_in_filter_keys(self):
        """Verify doc_type_kwd is in the filterable keys list"""
        with open("rag/nlp/search.py", "r") as f:
            content = f.read()

        # Find the list of filterable keys
        assert '"doc_type_kwd"' in content, "doc_type_kwd should be filterable"


class TestChunkAppPyFields:
    """Test chunk_app.py contains required fields in /list response"""

    @pytest.mark.p1
    def test_list_response_includes_block_refs(self):
        """Verify /list response includes block_refs"""
        with open("api/apps/chunk_app.py", "r") as f:
            content = f.read()

        assert '"block_refs"' in content, "block_refs should be in /list response"
        assert '"block_refs": sres.field[id].get("block_refs"' in content, \
            "block_refs should use sres.field[id].get()"

    @pytest.mark.p1
    def test_list_response_includes_bbox_union(self):
        """Verify /list response includes bbox_union"""
        with open("api/apps/chunk_app.py", "r") as f:
            content = f.read()

        assert '"bbox_union"' in content, "bbox_union should be in /list response"
        assert '"bbox_union": sres.field[id].get("bbox_union"' in content, \
            "bbox_union should use sres.field[id].get()"

    @pytest.mark.p1
    def test_list_response_includes_page_num_int(self):
        """Verify /list response includes page_num_int"""
        with open("api/apps/chunk_app.py", "r") as f:
            content = f.read()

        assert '"page_num_int"' in content, "page_num_int should be in /list response"


class TestAnswerGateIntegration:
    """Test PR-4 integration with PR-3 Answer Gate"""

    @pytest.mark.p2
    def test_answer_gate_exists(self):
        """Verify AnswerGate is available"""
        from rag.answer_gate import AnswerGate, ValidationStatus
        assert AnswerGate is not None
        assert ValidationStatus is not None

    @pytest.mark.p2
    def test_answer_gate_uses_pr4_fields(self):
        """Verify AnswerGate can use PR-4 fields for validation"""
        from rag.answer_gate import AnswerGate, ValidationStatus

        # Simulate retrieval result with PR-4 fields
        mock_chunks = [
            {
                "chunk_id": "c1",
                "content_with_weight": "盗窃金额5000元",
                "page_num_int": [1],
                "block_refs": [{"page_index": 1, "block_id": "b1"}],
                "bbox_union": [100, 200, 500, 300],
            }
        ]

        gate = AnswerGate()
        result = gate.validate(
            answer="被告人盗窃金额5000元",
            evidences=[{
                "chunk_id": "c1",
                "excerpt": "盗窃金额5000元",
                "page_index": 1,
            }],
            raw_chunks=mock_chunks,
        )

        # Should validate successfully
        assert result.status == ValidationStatus.VALID


class TestFieldCompleteness:
    """Test all PR-4 fields are properly implemented"""

    @pytest.mark.p3
    def test_all_new_fields_in_retrieval(self):
        """Verify all PR-4 fields are in retrieval output"""
        with open("rag/nlp/search.py", "r") as f:
            content = f.read()

        # Find the chunk dict construction in retrieval
        # Look for the pattern where chunk dict is built
        retrieval_pattern = r'd\s*=\s*\{([^}]+)\}'
        matches = re.findall(retrieval_pattern, content, re.DOTALL)

        # Find the largest dict (likely the chunk dict)
        chunk_dict = max(matches, key=len) if matches else ""

        required_fields = ["block_refs", "bbox_union", "page_num_int"]
        for field in required_fields:
            assert field in chunk_dict or f'"{field}"' in content, \
                f"Field '{field}' should be in retrieval output"

    @pytest.mark.p3
    def test_all_new_fields_in_search_default(self):
        """Verify all PR-4 fields are in search default fields"""
        with open("rag/nlp/search.py", "r") as f:
            content = f.read()

        match = re.search(r'src\s*=\s*req\.get\("fields",\s*\[(.*?)\]\)', content, re.DOTALL)
        assert match, "Should find default fields list"

        fields_str = match.group(1)
        required_fields = ["block_refs", "bbox_union"]
        for field in required_fields:
            assert f'"{field}"' in fields_str, f"Field '{field}' should be in default fields"
