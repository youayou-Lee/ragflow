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
Unit tests for criminal case RAG chunk schema extension.

Tests for new fields: block_refs, bbox_union, page_range.
"""
import pytest

from rag.nlp import add_bbox_union, add_page_range, add_block_refs


pytestmark = pytest.mark.p1


class TestAddBboxUnion:
    """Test cases for add_bbox_union function."""

    def test_single_position(self):
        """Single position should return that bbox"""
        d = {
            "position_int": [(1, 100, 200, 50, 150)]  # (page, left, right, top, bottom)
        }
        add_bbox_union(d)
        assert d["bbox_union"] == [100, 50, 200, 150]

    def test_multiple_positions(self):
        """Multiple positions should return union bbox"""
        d = {
            "position_int": [
                (1, 100, 200, 50, 150),
                (1, 150, 250, 100, 200),
                (2, 80, 180, 30, 130),
            ]
        }
        add_bbox_union(d)
        # x1=min(100,150,80)=80, y1=min(50,100,30)=30
        # x2=max(200,250,180)=250, y2=max(150,200,130)=200
        assert d["bbox_union"] == [80, 30, 250, 200]

    def test_empty_position(self):
        """Empty position_int should not add bbox_union"""
        d = {"position_int": []}
        add_bbox_union(d)
        assert "bbox_union" not in d

    def test_missing_position(self):
        """Missing position_int should not add bbox_union"""
        d = {}
        add_bbox_union(d)
        assert "bbox_union" not in d

    def test_preserves_existing_fields(self):
        """Should preserve existing fields in dict"""
        d = {
            "position_int": [(1, 100, 200, 50, 150)],
            "content": "test content",
            "chunk_type": "qa_pair"
        }
        add_bbox_union(d)
        assert d["content"] == "test content"
        assert d["chunk_type"] == "qa_pair"
        assert d["bbox_union"] == [100, 50, 200, 150]


class TestAddPageRange:
    """Test cases for add_page_range function."""

    def test_single_page(self):
        """Single page should return [n, n]"""
        d = {"page_num_int": [1]}
        add_page_range(d)
        assert d["page_range"] == [1, 1]

    def test_multiple_pages(self):
        """Multiple pages should return [min, max]"""
        d = {"page_num_int": [2, 3, 5, 3]}
        add_page_range(d)
        assert d["page_range"] == [2, 5]

    def test_unordered_pages(self):
        """Unordered pages should still return [min, max]"""
        d = {"page_num_int": [5, 2, 8, 1]}
        add_page_range(d)
        assert d["page_range"] == [1, 8]

    def test_empty_pages(self):
        """Empty page_num_int should not add page_range"""
        d = {"page_num_int": []}
        add_page_range(d)
        assert "page_range" not in d

    def test_missing_pages(self):
        """Missing page_num_int should not add page_range"""
        d = {}
        add_page_range(d)
        assert "page_range" not in d


class TestAddBlockRefs:
    """Test cases for add_block_refs function."""

    def test_auto_generated_block_ids(self):
        """Should auto-generate block IDs if not provided"""
        d = {
            "position_int": [
                (1, 100, 200, 50, 150),
                (2, 150, 250, 100, 200),
            ]
        }
        add_block_refs(d)
        assert len(d["block_refs"]) == 2
        assert d["block_refs"][0] == {"page_index": 1, "block_id": "p1_0"}
        assert d["block_refs"][1] == {"page_index": 2, "block_id": "p2_1"}

    def test_custom_block_ids(self):
        """Should use provided block IDs"""
        d = {
            "position_int": [
                (1, 100, 200, 50, 150),
                (2, 150, 250, 100, 200),
            ]
        }
        add_block_refs(d, block_ids=["block_a", "block_b"])
        assert d["block_refs"][0]["block_id"] == "block_a"
        assert d["block_refs"][1]["block_id"] == "block_b"

    def test_partial_custom_block_ids(self):
        """Should auto-generate for missing block IDs"""
        d = {
            "position_int": [
                (1, 100, 200, 50, 150),
                (2, 150, 250, 100, 200),
            ]
        }
        add_block_refs(d, block_ids=["block_a"])  # Only one ID provided
        assert d["block_refs"][0]["block_id"] == "block_a"
        assert d["block_refs"][1]["block_id"] == "p2_1"  # Auto-generated

    def test_empty_positions(self):
        """Empty position_int should not add block_refs"""
        d = {"position_int": []}
        add_block_refs(d)
        assert "block_refs" not in d

    def test_missing_positions(self):
        """Missing position_int should not add block_refs"""
        d = {}
        add_block_refs(d)
        assert "block_refs" not in d


class TestIntegration:
    """Integration tests for all new fields together."""

    def test_all_fields_together(self):
        """All new fields should work together"""
        d = {
            "position_int": [
                (1, 100, 200, 50, 150),
                (2, 150, 250, 100, 200),
            ],
            "page_num_int": [1, 2],
            "content_with_weight": "test content",
        }
        add_bbox_union(d)
        add_page_range(d)
        add_block_refs(d, block_ids=["block_1", "block_2"])

        assert d["bbox_union"] == [100, 50, 250, 200]
        assert d["page_range"] == [1, 2]
        assert len(d["block_refs"]) == 2
        assert d["block_refs"][0]["block_id"] == "block_1"
        assert d["block_refs"][1]["block_id"] == "block_2"
        # Original fields preserved
        assert d["content_with_weight"] == "test content"

    def test_qa_pair_chunk(self):
        """Test typical QA pair chunk from interrogation record"""
        d = {
            "position_int": [(1, 50, 500, 100, 200)],
            "page_num_int": [1],
            "chunk_type": "qa_pair",
            "content_with_weight": "问：你的姓名？\t答：张三",
        }
        add_bbox_union(d)
        add_page_range(d)
        add_block_refs(d)

        assert d["bbox_union"] == [50, 100, 500, 200]
        assert d["page_range"] == [1, 1]
        assert d["block_refs"][0]["page_index"] == 1
        assert d["chunk_type"] == "qa_pair"
