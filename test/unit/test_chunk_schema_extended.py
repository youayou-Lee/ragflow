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
Extended unit tests for criminal case RAG chunk schema extension.

This file supplements test_chunk_schema.py with:
- Boundary value tests
- Integration tests with add_positions()
- Schema type validation
- Negative test cases
- Criminal RAG business scenario tests
"""
import json
import sys
from pathlib import Path
import pytest

from rag.nlp import (
    add_positions,
    add_bbox_union,
    add_page_range,
    add_block_refs,
)

# Add the es_ob_migration module path
_es_ob_path = Path(__file__).parent.parent.parent / "tools" / "es-to-oceanbase-migration" / "src"
if str(_es_ob_path) not in sys.path:
    sys.path.insert(0, str(_es_ob_path))

# Import schema definitions for validation
from es_ob_migration.schema import RAGFLOW_COLUMNS, ARRAY_COLUMNS, JSON_COLUMNS

pytestmark = pytest.mark.p1


class TestBboxUnionBoundaryValues:
    """Boundary value tests for add_bbox_union function."""

    def test_large_coordinate_values(self):
        """Large coordinate values should be handled correctly."""
        d = {
            "position_int": [(1, 0, 10000, 0, 20000)]
        }
        add_bbox_union(d)
        assert d["bbox_union"] == [0, 0, 10000, 20000]

    def test_same_position_multiple_times(self):
        """Duplicate positions should not affect the union result."""
        d = {
            "position_int": [
                (1, 100, 200, 50, 150),
                (1, 100, 200, 50, 150),
                (1, 100, 200, 50, 150),
            ]
        }
        add_bbox_union(d)
        assert d["bbox_union"] == [100, 50, 200, 150]

    def test_overlapping_positions(self):
        """Overlapping positions should produce correct union."""
        d = {
            "position_int": [
                (1, 100, 200, 50, 150),
                (1, 150, 250, 100, 200),  # overlaps with first
            ]
        }
        add_bbox_union(d)
        # x1=min(100,150)=100, y1=min(50,100)=50
        # x2=max(200,250)=250, y2=max(150,200)=200
        assert d["bbox_union"] == [100, 50, 250, 200]

    def test_zero_coordinates(self):
        """Zero coordinates should be handled correctly."""
        d = {
            "position_int": [(1, 0, 0, 0, 0)]
        }
        add_bbox_union(d)
        assert d["bbox_union"] == [0, 0, 0, 0]

    def test_negative_like_large_pages(self):
        """Large page numbers (edge case for page index) should work."""
        d = {
            "position_int": [(999, 100, 200, 50, 150)]
        }
        add_bbox_union(d)
        assert d["bbox_union"] == [100, 50, 200, 150]


class TestPageRangeBoundaryValues:
    """Boundary value tests for add_page_range function."""

    def test_large_page_numbers(self):
        """Large page numbers should be handled correctly."""
        d = {"page_num_int": [1000, 2000, 3000]}
        add_page_range(d)
        assert d["page_range"] == [1000, 3000]

    def test_duplicate_page_numbers(self):
        """Duplicate page numbers should produce correct range."""
        d = {"page_num_int": [5, 5, 5, 5]}
        add_page_range(d)
        assert d["page_range"] == [5, 5]

    def test_single_large_page_number(self):
        """Single large page number should produce [n, n]."""
        d = {"page_num_int": [9999]}
        add_page_range(d)
        assert d["page_range"] == [9999, 9999]


class TestBlockRefsBoundaryValues:
    """Boundary value tests for add_block_refs function."""

    def test_many_positions(self):
        """Many positions should generate correct block_refs."""
        positions = [(i, 100 * i, 200 * i, 50 * i, 150 * i) for i in range(1, 101)]
        d = {"position_int": positions}
        add_block_refs(d)
        assert len(d["block_refs"]) == 100
        # Verify first and last
        assert d["block_refs"][0] == {"page_index": 1, "block_id": "p1_0"}
        assert d["block_refs"][99] == {"page_index": 100, "block_id": "p100_99"}

    def test_block_ids_with_special_characters(self):
        """Block IDs with special characters should be preserved."""
        d = {
            "position_int": [
                (1, 100, 200, 50, 150),
                (2, 150, 250, 100, 200),
            ]
        }
        add_block_refs(d, block_ids=["block-001", "block_002"])
        assert d["block_refs"][0]["block_id"] == "block-001"
        assert d["block_refs"][1]["block_id"] == "block_002"

    def test_block_ids_unicode(self):
        """Block IDs with unicode characters should be preserved."""
        d = {
            "position_int": [(1, 100, 200, 50, 150)]
        }
        add_block_refs(d, block_ids=["区块_001"])
        assert d["block_refs"][0]["block_id"] == "区块_001"


class TestIntegrationWithAddPositions:
    """Integration tests: add_positions -> extension functions data flow."""

    def test_full_pipeline_single_position(self):
        """Full pipeline with single position."""
        d = {}
        poss = [(0, 100, 200, 50, 150)]  # 0-indexed page

        add_positions(d, poss)
        add_bbox_union(d)
        add_page_range(d)
        add_block_refs(d)

        # add_positions converts to 1-indexed pages
        assert d["bbox_union"] == [100, 50, 200, 150]
        assert d["page_range"] == [1, 1]
        assert d["block_refs"][0]["page_index"] == 1

    def test_full_pipeline_multiple_pages(self):
        """Full pipeline across multiple pages."""
        d = {}
        poss = [
            (0, 100, 200, 50, 150),
            (1, 150, 250, 100, 200),
            (2, 80, 180, 30, 130),
        ]

        add_positions(d, poss)
        add_bbox_union(d)
        add_page_range(d)
        add_block_refs(d)

        assert d["bbox_union"] == [80, 30, 250, 200]
        assert d["page_range"] == [1, 3]
        assert len(d["block_refs"]) == 3
        assert d["block_refs"][0]["page_index"] == 1
        assert d["block_refs"][1]["page_index"] == 2
        assert d["block_refs"][2]["page_index"] == 3

    def test_full_pipeline_with_custom_block_ids(self):
        """Full pipeline with custom block IDs."""
        d = {}
        poss = [(0, 100, 200, 50, 150), (1, 150, 250, 100, 200)]

        add_positions(d, poss)
        add_bbox_union(d)
        add_page_range(d)
        add_block_refs(d, block_ids=["custom_a", "custom_b"])

        assert d["block_refs"][0]["block_id"] == "custom_a"
        assert d["block_refs"][1]["block_id"] == "custom_b"

    def test_add_positions_creates_required_fields(self):
        """add_positions should create all required fields for extensions."""
        d = {}
        poss = [(0, 100, 200, 50, 150)]

        add_positions(d, poss)

        assert "position_int" in d
        assert "page_num_int" in d
        assert "top_int" in d
        assert d["position_int"] == [(1, 100, 200, 50, 150)]
        assert d["page_num_int"] == [1]
        assert d["top_int"] == [50]

    def test_extension_functions_after_manual_position_setting(self):
        """Extension functions should work with manually set positions."""
        d = {
            "position_int": [(1, 100, 200, 50, 150)],
            "page_num_int": [1],
        }

        add_bbox_union(d)
        add_page_range(d)
        add_block_refs(d)

        assert d["bbox_union"] == [100, 50, 200, 150]
        assert d["page_range"] == [1, 1]
        assert len(d["block_refs"]) == 1

    def test_empty_positions_no_side_effects(self):
        """Empty positions should not cause side effects."""
        d = {"content_with_weight": "test content"}

        add_positions(d, [])
        add_bbox_union(d)
        add_page_range(d)
        add_block_refs(d)

        # Only original content should remain
        assert d == {"content_with_weight": "test content"}


class TestSchemaValidation:
    """Validate output types match RAGFLOW_COLUMNS definitions."""

    def test_bbox_union_type_validation(self):
        """bbox_union should match schema type ARRAY(Integer)."""
        d = {"position_int": [(1, 100, 200, 50, 150)]}
        add_bbox_union(d)

        assert isinstance(d["bbox_union"], list)
        assert len(d["bbox_union"]) == 4
        assert all(isinstance(x, int) for x in d["bbox_union"])

        # Verify schema definition
        schema = RAGFLOW_COLUMNS["bbox_union"]
        assert schema["ob_type"] == "ARRAY(Integer)"
        assert schema["is_array"] is True
        assert schema["nullable"] is True

    def test_page_range_type_validation(self):
        """page_range should match schema type ARRAY(Integer)."""
        d = {"page_num_int": [1, 3, 5]}
        add_page_range(d)

        assert isinstance(d["page_range"], list)
        assert len(d["page_range"]) == 2
        assert all(isinstance(x, int) for x in d["page_range"])

        # Verify schema definition
        schema = RAGFLOW_COLUMNS["page_range"]
        assert schema["ob_type"] == "ARRAY(Integer)"
        assert schema["is_array"] is True

    def test_block_refs_type_validation(self):
        """block_refs should match schema type JSON."""
        d = {"position_int": [(1, 100, 200, 50, 150)]}
        add_block_refs(d)

        assert isinstance(d["block_refs"], list)
        assert all(isinstance(ref, dict) for ref in d["block_refs"])
        assert "page_index" in d["block_refs"][0]
        assert "block_id" in d["block_refs"][0]

        # Verify schema definition
        schema = RAGFLOW_COLUMNS["block_refs"]
        assert schema["ob_type"] == "JSON"
        assert schema["is_json"] is True

    def test_array_columns_registry(self):
        """ARRAY_COLUMNS should include new extension fields."""
        assert "bbox_union" in ARRAY_COLUMNS
        assert "page_range" in ARRAY_COLUMNS

    def test_json_columns_registry(self):
        """JSON_COLUMNS should include block_refs."""
        assert "block_refs" in JSON_COLUMNS


class TestNegativeCases:
    """Negative test cases for exception handling."""

    def test_bbox_union_with_malformed_position(self):
        """Malformed position should not crash bbox_union."""
        d = {"position_int": [(1, 100)]}  # Missing coordinates
        # This should not raise an exception
        try:
            add_bbox_union(d)
            # If it succeeds, verify it handled the case
            if "bbox_union" in d:
                assert len(d["bbox_union"]) == 4
        except (IndexError, TypeError):
            # Expected behavior - malformed data should either be ignored or raise
            pass

    def test_page_range_with_non_integer_values(self):
        """Non-integer page numbers should be handled."""
        d = {"page_num_int": [1, "invalid", 3]}  # type: ignore
        try:
            add_page_range(d)
            if "page_range" in d:
                # Should either skip invalid values or handle them
                assert len(d["page_range"]) == 2
        except (TypeError, ValueError):
            # Expected behavior
            pass

    def test_block_refs_with_none_block_ids(self):
        """None in block_ids list should be passed through (current behavior)."""
        d = {
            "position_int": [
                (1, 100, 200, 50, 150),
                (2, 150, 250, 100, 200),
            ]
        }
        # The function passes through None when in block_ids list
        add_block_refs(d, block_ids=[None, "valid_id"])  # type: ignore
        assert "block_refs" in d
        # Current behavior: None is passed through, not auto-generated
        assert d["block_refs"][0]["block_id"] is None
        assert d["block_refs"][1]["block_id"] == "valid_id"


class TestCriminalRAGUseCases:
    """Business scenario tests for Criminal RAG application."""

    def test_interrogation_record_qa_pair(self):
        """Test typical interrogation record QA pair chunk."""
        d = {}
        poss = [(0, 50, 500, 100, 200)]  # First page, wide bbox

        add_positions(d, poss)
        add_bbox_union(d)
        add_page_range(d)
        add_block_refs(d)

        # Simulate additional fields from interrogation parser
        d["chunk_type"] = "qa_pair"
        d["content_with_weight"] = "问：你的姓名？\t答：张三"

        assert d["bbox_union"] == [50, 100, 500, 200]
        assert d["page_range"] == [1, 1]
        assert d["chunk_type"] == "qa_pair"
        assert d["block_refs"][0]["page_index"] == 1

    def test_cross_page_section(self):
        """Test section that spans multiple pages."""
        d = {}
        poss = [
            (0, 50, 500, 800, 900),   # Bottom of page 1
            (1, 50, 500, 50, 150),    # Top of page 2
            (1, 50, 500, 200, 300),   # Middle of page 2
        ]

        add_positions(d, poss)
        add_bbox_union(d)
        add_page_range(d)
        add_block_refs(d)

        d["chunk_type"] = "section"
        d["content_with_weight"] = "经依法审查查明：\n...(跨页内容)..."

        assert d["page_range"] == [1, 2]
        assert len(d["block_refs"]) == 3
        assert d["chunk_type"] == "section"

    def test_evidence_item_with_metadata(self):
        """Test evidence item chunk with metadata."""
        d = {}
        poss = [(2, 100, 400, 300, 400)]  # Page 3

        add_positions(d, poss)
        add_bbox_union(d)
        add_page_range(d)
        add_block_refs(d, block_ids=["evidence_001"])

        d["chunk_type"] = "evidence_item"
        d["content_with_weight"] = "证据1：讯问笔录（2024年1月15日）"

        assert d["page_range"] == [3, 3]
        assert d["block_refs"][0]["block_id"] == "evidence_001"
        assert d["chunk_type"] == "evidence_item"


class TestJsonSerialization:
    """Test JSON serialization for storage compatibility."""

    def test_block_refs_json_serializable(self):
        """block_refs should be JSON serializable for storage."""
        d = {"position_int": [(1, 100, 200, 50, 150)]}
        add_block_refs(d)

        # Should not raise
        json_str = json.dumps(d["block_refs"])
        parsed = json.loads(json_str)

        assert parsed == d["block_refs"]

    def test_full_chunk_json_serializable(self):
        """Full chunk with all extensions should be JSON serializable."""
        d = {
            "position_int": [(1, 100, 200, 50, 150)],
            "page_num_int": [1],
            "content_with_weight": "test content",
            "chunk_type": "qa_pair",
        }

        add_bbox_union(d)
        add_page_range(d)
        add_block_refs(d)

        # Should not raise
        json_str = json.dumps(d, ensure_ascii=False)
        parsed = json.loads(json_str)

        assert parsed["bbox_union"] == [100, 50, 200, 150]
        assert parsed["page_range"] == [1, 1]
        assert parsed["chunk_type"] == "qa_pair"
