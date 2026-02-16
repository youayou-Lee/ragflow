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
Unit tests for Answer Gate Validator - PR-3

Tests cover:
- Core validation functionality (p1)
- Numeric grounding validation (p2)
- Boundary cases and integration (p3)
"""

import pytest
from rag.answer_gate import AnswerGate, ValidationStatus


class TestValidateNoEvidence:
    """p1: Core functionality - no evidence case"""

    @pytest.mark.p1
    def test_validate_no_evidence_empty_lists(self):
        """No chunks should return no_evidence status"""
        gate = AnswerGate()
        result = gate.validate("任何答案", [], [])
        assert result.status == ValidationStatus.NO_EVIDENCE
        assert len(result.evidences) == 0
        assert "No evidences or chunks provided" in result.validation_errors

    @pytest.mark.p1
    def test_validate_no_evidence_none_evidences(self):
        """None evidences should return no_evidence status"""
        gate = AnswerGate()
        result = gate.validate("任何答案", None, [{"chunk_id": "c1"}])
        assert result.status == ValidationStatus.NO_EVIDENCE

    @pytest.mark.p1
    def test_validate_no_evidence_none_chunks(self):
        """None chunks should return no_evidence status"""
        gate = AnswerGate()
        result = gate.validate("任何答案", [{"chunk_id": "c1"}], None)
        assert result.status == ValidationStatus.NO_EVIDENCE


class TestValidateChunkExistence:
    """p1: Core functionality - chunk_id validation"""

    @pytest.mark.p1
    def test_validate_chunk_id_missing(self):
        """chunk_id not in raw chunks should report error"""
        gate = AnswerGate()
        result = gate.validate(
            "被告人张某犯盗窃罪",
            [{"chunk_id": "c_nonexistent", "excerpt": "盗窃"}],
            [{"chunk_id": "c1", "content_with_weight": "盗窃案件"}],
        )
        assert result.status == ValidationStatus.CITATION_INSUFFICIENT
        assert any("not found" in e for e in result.validation_errors)

    @pytest.mark.p1
    def test_validate_missing_chunk_id_in_evidence(self):
        """Evidence without chunk_id should report error"""
        gate = AnswerGate()
        result = gate.validate(
            "被告人张某犯盗窃罪",
            [{"excerpt": "盗窃"}],  # No chunk_id
            [{"chunk_id": "c1", "content_with_weight": "盗窃案件"}],
        )
        assert result.status == ValidationStatus.CITATION_INSUFFICIENT
        assert any("missing chunk_id" in e for e in result.validation_errors)


class TestValidateExcerptSubstring:
    """p1: Core functionality - excerpt matching"""

    @pytest.mark.p1
    def test_validate_excerpt_exact_match(self):
        """Exact excerpt match should be valid"""
        gate = AnswerGate()
        result = gate.validate(
            "被告人盗窃金额5000元",
            [{"chunk_id": "c1", "excerpt": "盗窃金额5000元"}],
            [{"chunk_id": "c1", "content_with_weight": "经查，被告人盗窃金额5000元整"}],
        )
        assert result.status == ValidationStatus.VALID
        assert len(result.evidences) == 1

    @pytest.mark.p1
    def test_validate_excerpt_not_substring(self):
        """Excerpt not in chunk should report error"""
        gate = AnswerGate()
        result = gate.validate(
            "被告人盗窃金额5000元",
            [{"chunk_id": "c1", "excerpt": "抢劫金额10000元"}],
            [{"chunk_id": "c1", "content_with_weight": "经查，被告人盗窃金额5000元整"}],
        )
        assert result.status == ValidationStatus.CITATION_INSUFFICIENT
        assert any("not found" in e for e in result.validation_errors)

    @pytest.mark.p1
    def test_validate_empty_excerpt(self):
        """Empty excerpt should be acceptable"""
        gate = AnswerGate()
        result = gate.validate(
            "被告人犯盗窃罪",
            [{"chunk_id": "c1", "excerpt": ""}],
            [{"chunk_id": "c1", "content_with_weight": "盗窃案件"}],
        )
        # Empty excerpt is valid, just no match to check
        assert result.status == ValidationStatus.VALID


class TestNumericGrounding:
    """p2: Numeric value grounding validation"""

    @pytest.mark.p2
    def test_numeric_grounding_valid(self):
        """Numeric value in excerpt should be valid"""
        gate = AnswerGate()
        result = gate.validate(
            "被告人盗窃金额5000元",
            [{"chunk_id": "c1", "excerpt": "盗窃金额5000元"}],
            [{"chunk_id": "c1", "content_with_weight": "盗窃金额5000元"}],
        )
        assert result.status == ValidationStatus.VALID

    @pytest.mark.p2
    def test_numeric_grounding_missing(self):
        """Numeric value not in excerpt should return citation_insufficient"""
        gate = AnswerGate()
        result = gate.validate(
            "被告人盗窃金额5000元",
            [{"chunk_id": "c1", "excerpt": "盗窃案件"}],
            [{"chunk_id": "c1", "content_with_weight": "盗窃案件"}],
        )
        assert result.status == ValidationStatus.CITATION_INSUFFICIENT
        assert any("5000元" in e and "not found" in e for e in result.validation_errors)

    @pytest.mark.p2
    def test_numeric_grounding_disabled(self):
        """With strict_numeric_validation=False, missing numeric should be ok"""
        gate = AnswerGate(strict_numeric_validation=False)
        result = gate.validate(
            "被告人盗窃金额5000元",
            [{"chunk_id": "c1", "excerpt": "盗窃案件"}],
            [{"chunk_id": "c1", "content_with_weight": "盗窃案件"}],
        )
        assert result.status == ValidationStatus.VALID

    @pytest.mark.p2
    def test_date_extraction(self):
        """Date extraction and validation"""
        gate = AnswerGate()
        result = gate.validate(
            "案发时间为2024年3月15日",
            [{"chunk_id": "c1", "excerpt": "2024年3月15日案发"}],
            [{"chunk_id": "c1", "content_with_weight": "2024年3月15日案发"}],
        )
        assert result.status == ValidationStatus.VALID

    @pytest.mark.p2
    def test_date_missing_in_evidence(self):
        """Date not in evidence should fail"""
        gate = AnswerGate()
        result = gate.validate(
            "案发时间为2024年3月15日",
            [{"chunk_id": "c1", "excerpt": "案件详情"}],
            [{"chunk_id": "c1", "content_with_weight": "案件详情"}],
        )
        assert result.status == ValidationStatus.CITATION_INSUFFICIENT

    @pytest.mark.p2
    def test_percentage_grounding(self):
        """Percentage value grounding"""
        gate = AnswerGate()
        result = gate.validate(
            "被告人血液酒精浓度达到85%",
            [{"chunk_id": "c1", "excerpt": "酒精浓度85%"}],
            [{"chunk_id": "c1", "content_with_weight": "血液酒精浓度85%"}],
        )
        assert result.status == ValidationStatus.VALID

    @pytest.mark.p2
    def test_amount_with_chinese_units(self):
        """Amount with Chinese units (万/亿)"""
        gate = AnswerGate()
        result = gate.validate(
            "涉案金额达5万元",
            [{"chunk_id": "c1", "excerpt": "金额5万元"}],
            [{"chunk_id": "c1", "content_with_weight": "涉案金额5万元"}],
        )
        assert result.status == ValidationStatus.VALID


class TestCoordinateProvenance:
    """p3: Page index and bbox validation"""

    @pytest.mark.p3
    def test_coordinate_provenance_valid(self):
        """Matching page_index should be valid"""
        gate = AnswerGate()
        result = gate.validate(
            "被告人张某犯盗窃罪",
            [{"chunk_id": "c1", "excerpt": "盗窃", "page_index": 1}],
            [{"chunk_id": "c1", "content_with_weight": "盗窃", "page_num_int": [1]}],
        )
        assert result.status == ValidationStatus.VALID

    @pytest.mark.p3
    def test_coordinate_provenance_mismatch(self):
        """Mismatched page_index should report error"""
        gate = AnswerGate()
        result = gate.validate(
            "被告人张某犯盗窃罪",
            [{"chunk_id": "c1", "excerpt": "盗窃", "page_index": 2}],
            [{"chunk_id": "c1", "content_with_weight": "盗窃", "page_num_int": [1]}],
        )
        assert result.status == ValidationStatus.CITATION_INSUFFICIENT
        assert any("page_index mismatch" in e for e in result.validation_errors)

    @pytest.mark.p3
    def test_coordinate_validation_disabled(self):
        """With enable_coordinate_validation=False, mismatched coords should be ok"""
        gate = AnswerGate(enable_coordinate_validation=False)
        result = gate.validate(
            "被告人张某犯盗窃罪",
            [{"chunk_id": "c1", "excerpt": "盗窃", "page_index": 2}],
            [{"chunk_id": "c1", "content_with_weight": "盗窃", "page_num_int": [1]}],
        )
        assert result.status == ValidationStatus.VALID


class TestFuzzyExcerptMatch:
    """p3: Fuzzy matching for OCR errors"""

    @pytest.mark.p3
    def test_fuzzy_excerpt_match(self):
        """OCR error with slight difference should match with fuzzy threshold"""
        gate = AnswerGate(fuzzy_match_threshold=0.85)
        # Simulate OCR error: "盗窃" vs "盗穷" (similar characters)
        result = gate.validate(
            "被告人犯盗窃罪",
            [{"chunk_id": "c1", "excerpt": "盗窃金额5000元"}],
            [{"chunk_id": "c1", "content_with_weight": "盗穷金额5000元"}],  # Note: 窃 vs 穷
        )
        # Should match with fuzzy threshold
        assert result.status == ValidationStatus.VALID

    @pytest.mark.p3
    def test_fuzzy_excerpt_below_threshold(self):
        """Below threshold fuzzy match should fail"""
        gate = AnswerGate(fuzzy_match_threshold=0.99)  # Very high threshold
        result = gate.validate(
            "被告人犯盗窃罪",
            [{"chunk_id": "c1", "excerpt": "盗窃金额5000元"}],
            [{"chunk_id": "c1", "content_with_weight": "完全不同的内容"}],
        )
        assert result.status == ValidationStatus.CITATION_INSUFFICIENT


class TestIntegrationWithMockDialog:
    """p3: Integration test with mock dialog context"""

    @pytest.mark.p3
    def test_integration_with_mock_dialog(self):
        """Simulate dialog integration with typical chunks"""
        gate = AnswerGate()

        # Simulate typical dialog chunks
        chunks = [
            {
                "chunk_id": "doc1_p1_c1",
                "content_with_weight": "经审理查明，被告人张某于2024年1月在某小区实施盗窃，"
                "盗窃金额人民币5000元。案发后，被告人主动投案自首。",
                "page_num_int": [1],
                "bbox": [100, 200, 500, 300],
            },
            {
                "chunk_id": "doc1_p2_c1",
                "content_with_weight": "被告人血液酒精浓度检测结果为120mg/100ml，"
                "属于醉酒驾驶。",
                "page_num_int": [2],
                "bbox": [100, 100, 500, 200],
            },
        ]

        evidences = [
            {
                "chunk_id": "doc1_p1_c1",
                "excerpt": "盗窃金额人民币5000元",
                "page_index": 1,
            },
        ]

        result = gate.validate(
            answer="被告人张某盗窃金额5000元，后主动投案自首。",
            evidences=evidences,
            raw_chunks=chunks,
        )

        assert result.status == ValidationStatus.VALID
        assert len(result.evidences) == 1

    @pytest.mark.p3
    def test_multiple_evidences_mixed_validity(self):
        """Multiple evidences with mixed validity"""
        gate = AnswerGate()

        chunks = [
            {"chunk_id": "c1", "content_with_weight": "盗窃金额5000元"},
            {"chunk_id": "c2", "content_with_weight": "抢劫案件"},
        ]

        evidences = [
            {"chunk_id": "c1", "excerpt": "盗窃金额5000元"},  # Valid
            {"chunk_id": "c2", "excerpt": "不存在的摘要"},  # Invalid excerpt
        ]

        result = gate.validate(
            answer="被告人盗窃金额5000元",
            evidences=evidences,
            raw_chunks=chunks,
        )

        # Should fail because one evidence has invalid excerpt
        assert result.status == ValidationStatus.CITATION_INSUFFICIENT


class TestEdgeCases:
    """p3: Edge cases and boundary conditions"""

    @pytest.mark.p3
    def test_empty_answer(self):
        """Empty answer should still validate"""
        gate = AnswerGate()
        result = gate.validate(
            "",
            [{"chunk_id": "c1", "excerpt": "内容"}],
            [{"chunk_id": "c1", "content_with_weight": "内容"}],
        )
        assert result.status == ValidationStatus.VALID

    @pytest.mark.p3
    def test_chunk_without_content(self):
        """Chunk without content should handle gracefully"""
        gate = AnswerGate()
        result = gate.validate(
            "被告人犯罪",
            [{"chunk_id": "c1", "excerpt": "内容"}],
            [{"chunk_id": "c1"}],  # No content
        )
        assert result.status == ValidationStatus.CITATION_INSUFFICIENT
        assert any("no content" in e for e in result.validation_errors)

    @pytest.mark.p3
    def test_content_with_weight_fallback(self):
        """Should fallback to 'content' if 'content_with_weight' is missing"""
        gate = AnswerGate()
        result = gate.validate(
            "被告人犯罪",
            [{"chunk_id": "c1", "excerpt": "盗窃"}],
            [{"chunk_id": "c1", "content": "盗窃案件"}],  # Only 'content', no 'content_with_weight'
        )
        assert result.status == ValidationStatus.VALID

    @pytest.mark.p3
    def test_conclusion_parameter(self):
        """Conclusion parameter should be preserved in result"""
        gate = AnswerGate()
        result = gate.validate(
            "被告人犯罪",
            [{"chunk_id": "c1", "excerpt": "盗窃"}],
            [{"chunk_id": "c1", "content_with_weight": "盗窃案件"}],
            conclusion="被告人构成盗窃罪",
        )
        assert result.conclusion == "被告人构成盗窃罪"
