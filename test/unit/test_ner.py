# test/unit/test_ner.py

import pytest
from rag.app.criminal.ner import extract_lightweight_entities


class TestExtractLightweightEntities:
    """Test lightweight NER extraction (amounts and dates only)."""

    def test_extract_amounts_numeric(self):
        """Test numeric amount extraction."""
        text = "涉案金额42000元，已退还1500.50元"
        entities = extract_lightweight_entities(text)

        assert entities is not None
        assert "42000" in entities["amounts"]
        assert "1500.50" in entities["amounts"]

    def test_extract_amounts_chinese(self):
        """Test Chinese numeral amount extraction."""
        text = "诈骗金额三万元，退赔一万元"
        entities = extract_lightweight_entities(text)

        assert entities is not None
        assert "三万" in entities["amounts"]
        assert "一万" in entities["amounts"]

    def test_extract_dates_iso_format(self):
        """Test ISO format date extraction."""
        text = "案发时间为2024-01-15，2024/03/20又作案"
        entities = extract_lightweight_entities(text)

        assert entities is not None
        assert "2024-01-15" in entities["dates"]
        assert "2024/03/20" in entities["dates"]

    def test_extract_dates_chinese_format(self):
        """Test Chinese format date extraction."""
        text = "2024年1月15日实施诈骗"
        entities = extract_lightweight_entities(text)

        assert entities is not None
        assert "2024年1月15日" in entities["dates"]

    def test_no_entities(self):
        """Test text without amounts or dates."""
        text = "这是一段普通文本，没有金额和日期"
        entities = extract_lightweight_entities(text)

        assert entities is None

    def test_deduplication(self):
        """Test that duplicate entities are removed."""
        text = "42000元和42000元是同一笔"
        entities = extract_lightweight_entities(text)

        assert entities is not None
        assert entities["amounts"].count("42000") == 1
