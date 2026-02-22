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


class TestParsePositionTag:
    """Test position tag parsing."""

    def test_parse_single_page_tag(self):
        """Test parsing a single page position tag."""
        from rag.app.criminal.blocks import parse_position_tag

        text = "@@1\t10.0\t200.0\t50.0\t80.0##Hello World"
        page_no, bbox, content = parse_position_tag(text)

        assert page_no == 0  # 0-indexed
        assert bbox == (10.0, 50.0, 200.0, 80.0)  # (x0, y0, x1, y1)
        assert content == "Hello World"

    def test_parse_page_range_tag(self):
        """Test parsing a page range position tag."""
        from rag.app.criminal.blocks import parse_position_tag

        text = "@@1-2\t10.0\t200.0\t50.0\t80.0##Multi-page content"
        page_no, bbox, content = parse_position_tag(text)

        assert page_no == 0  # Uses first page, 0-indexed
        assert content == "Multi-page content"

    def test_parse_no_tag(self):
        """Test parsing text without position tag."""
        from rag.app.criminal.blocks import parse_position_tag

        text = "Plain text without tag"
        page_no, bbox, content = parse_position_tag(text)

        assert page_no == 0
        assert bbox is None
        assert content == "Plain text without tag"

    def test_parse_tag_format_variations(self):
        """Test various tag formats from OCR output."""
        from rag.app.criminal.blocks import parse_position_tag

        # Format from by_paddleocr: (content, tag) -> tag + content
        text = "@@2\t15.5\t180.3\t30.2\t60.8##答：我是张三"
        page_no, bbox, content = parse_position_tag(text)

        assert page_no == 1  # Page 2 -> index 1
        assert bbox == (15.5, 30.2, 180.3, 60.8)
        assert content == "答：我是张三"
