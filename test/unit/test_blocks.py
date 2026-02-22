# test/unit/test_blocks.py

import pytest
from rag.app.criminal.blocks import BlockType, UniversalBlock


class TestBlockType:
    """Test BlockType enum."""

    def test_block_type_values(self):
        """Test that all expected block types exist."""
        assert BlockType.HEADER.value == "header"
        assert BlockType.PARAGRAPH.value == "paragraph"
        assert BlockType.QA_PAIR.value == "qa_pair"
        assert BlockType.TABLE.value == "table"
        assert BlockType.LIST.value == "list"
        assert BlockType.SEAL.value == "seal"
        assert BlockType.FOOTER.value == "footer"


class TestUniversalBlock:
    """Test UniversalBlock dataclass."""

    def test_required_fields(self):
        """Test creating block with required fields only."""
        block = UniversalBlock(
            block_type=BlockType.PARAGRAPH,
            text="Test content",
            page_no=0,
            bbox=(0.0, 0.0, 100.0, 50.0),
        )
        assert block.block_type == BlockType.PARAGRAPH
        assert block.text == "Test content"
        assert block.page_no == 0
        assert block.bbox == (0.0, 0.0, 100.0, 50.0)
        assert block.doc_type_hint is None
        assert block.entities is None

    def test_optional_fields(self):
        """Test creating block with all fields."""
        block = UniversalBlock(
            block_type=BlockType.QA_PAIR,
            text="问：你叫什么名字？",
            page_no=1,
            bbox=(10.0, 20.0, 200.0, 40.0),
            doc_type_hint="interrogation",
            entities={"amounts": ["42000"], "dates": ["2024-01-15"]},
        )
        assert block.doc_type_hint == "interrogation"
        assert block.entities["amounts"] == ["42000"]
