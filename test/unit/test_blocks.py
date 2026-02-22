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


class TestInferBlockType:
    """Test block type inference from text content."""

    def test_infer_seal(self):
        """Test seal/stamp detection."""
        from rag.app.criminal.blocks import infer_block_type

        assert infer_block_type("（印章）", "middle") == BlockType.SEAL
        assert infer_block_type("章", "middle") == BlockType.SEAL

    def test_infer_qa_pair(self):
        """Test Q/A pair detection."""
        from rag.app.criminal.blocks import infer_block_type

        assert infer_block_type("问：你叫什么名字？", "middle") == BlockType.QA_PAIR
        assert infer_block_type("答：我叫张三", "middle") == BlockType.QA_PAIR
        assert infer_block_type("问:今天几号?", "middle") == BlockType.QA_PAIR

    def test_infer_list(self):
        """Test list item detection."""
        from rag.app.criminal.blocks import infer_block_type

        assert infer_block_type("1. 第一项内容", "middle") == BlockType.LIST
        assert infer_block_type("2、第二项内容", "middle") == BlockType.LIST
        assert infer_block_type("一、基本情况", "middle") == BlockType.LIST

    def test_infer_header(self):
        """Test header detection based on position."""
        from rag.app.criminal.blocks import infer_block_type

        short_text = "讯问笔录"
        assert infer_block_type(short_text, "first") == BlockType.HEADER

        # Long text at first position is not header
        long_text = "这是一段很长的内容" * 100
        assert infer_block_type(long_text, "first") == BlockType.PARAGRAPH

    def test_infer_footer(self):
        """Test footer detection based on position."""
        from rag.app.criminal.blocks import infer_block_type

        short_text = "第 1 页 共 3 页"
        assert infer_block_type(short_text, "last") == BlockType.FOOTER

        # Long text at last position is not footer
        long_text = "这是一段很长的内容" * 10
        assert infer_block_type(long_text, "last") == BlockType.PARAGRAPH

    def test_infer_paragraph_default(self):
        """Test default paragraph type."""
        from rag.app.criminal.blocks import infer_block_type

        assert infer_block_type("这是一段普通文本。", "middle") == BlockType.PARAGRAPH
        assert infer_block_type("普通内容", "middle") == BlockType.PARAGRAPH


class TestExtractUniversalBlocks:
    """Test main block extraction function."""

    def test_extract_from_simple_sections(self):
        """Test extraction from simple OCR sections."""
        from rag.app.criminal.blocks import extract_universal_blocks

        # Simulate OCR output format from by_paddleocr
        sections = [
            ("讯问笔录", "@@1\t10.0\t200.0\t20.0\t40.0##"),
            ("问：你叫什么名字？", "@@1\t10.0\t200.0\t50.0\t70.0##"),
            ("答：我叫张三", "@@1\t10.0\t200.0\t80.0\t100.0##"),
        ]

        blocks = extract_universal_blocks(sections, "interrogation")

        assert len(blocks) == 3
        assert blocks[0].block_type == BlockType.HEADER
        assert blocks[1].block_type == BlockType.QA_PAIR
        assert blocks[2].block_type == BlockType.QA_PAIR

    def test_extract_with_entities(self):
        """Test that entities are extracted."""
        from rag.app.criminal.blocks import extract_universal_blocks

        sections = [
            ("2024年1月15日收到42000元", "@@1\t10.0\t200.0\t20.0\t40.0##"),
        ]

        blocks = extract_universal_blocks(sections)

        assert len(blocks) == 1
        assert blocks[0].entities is not None
        assert "42000" in blocks[0].entities["amounts"]
        assert "2024年1月15日" in blocks[0].entities["dates"]

    def test_extract_positions(self):
        """Test that positions are correctly extracted."""
        from rag.app.criminal.blocks import extract_universal_blocks

        sections = [
            ("Test content", "@@2\t15.0\t180.0\t30.0\t50.0##"),
        ]

        blocks = extract_universal_blocks(sections)

        assert blocks[0].page_no == 1  # Page 2 -> 0-indexed
        assert blocks[0].bbox == (15.0, 30.0, 180.0, 50.0)

    def test_extract_empty_sections(self):
        """Test handling of empty sections."""
        from rag.app.criminal.blocks import extract_universal_blocks

        blocks = extract_universal_blocks([])
        assert blocks == []

    def test_doc_type_hint_propagated(self):
        """Test that doc_type_hint is propagated to blocks."""
        from rag.app.criminal.blocks import extract_universal_blocks

        sections = [
            ("内容", "@@1\t10.0\t200.0\t20.0\t40.0##"),
        ]

        blocks = extract_universal_blocks(sections, "indictment")

        assert blocks[0].doc_type_hint == "indictment"
