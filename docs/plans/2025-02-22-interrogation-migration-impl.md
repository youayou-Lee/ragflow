# Phase 2: Interrogation Parser Migration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate interrogation.py to use Layer A (extract_universal_blocks) + Layer B (InterrogationPlugin) architecture while maintaining backward compatibility.

**Architecture:**
- Layer A: extract_universal_blocks() converts OCR sections → UniversalBlock list
- Layer B: InterrogationPlugin.process() converts UniversalBlock list → chunks
- chunk() function orchestrates: OCR → Layer A → Layer B

**Tech Stack:** Python 3.12, pytest, unittest.mock

---

## Task 1: Implement InterrogationPlugin

**Files:**
- Create: `rag/app/criminal/plugins/interrogation.py`
- Create: `test/unit/test_interrogation_plugin.py`

**Step 1: Write the failing test**

```python
# test/unit/test_interrogation_plugin.py

import pytest
from rag.app.criminal.plugins.interrogation import InterrogationPlugin
from rag.app.criminal.blocks import UniversalBlock, BlockType


class TestInterrogationPlugin:
    """Test InterrogationPlugin."""

    def test_doc_type(self):
        """Test doc_type property."""
        plugin = InterrogationPlugin()
        assert plugin.doc_type == "interrogation"

    def test_process_empty_blocks(self):
        """Test processing empty block list."""
        plugin = InterrogationPlugin()
        chunks = plugin.process([], {"docnm_kwt": "test.pdf"})
        assert chunks == []

    def test_process_header_blocks(self):
        """Test processing header blocks."""
        plugin = InterrogationPlugin()
        blocks = [
            UniversalBlock(BlockType.HEADER, "讯问笔录", 0, (0, 0, 100, 50)),
            UniversalBlock(BlockType.HEADER, "时间：2024年1月", 0, (0, 50, 100, 100)),
        ]
        chunks = plugin.process(blocks, {"docnm_kwt": "test.pdf"})
        assert len(chunks) == 1
        assert chunks[0]["chunk_type"] == "header"

    def test_process_qa_blocks(self):
        """Test processing QA pair blocks."""
        plugin = InterrogationPlugin()
        blocks = [
            UniversalBlock(BlockType.QA_PAIR, "问：你叫什么名字？", 0, (0, 0, 100, 50)),
            UniversalBlock(BlockType.QA_PAIR, "答：我叫张三", 0, (0, 50, 100, 100)),
            UniversalBlock(BlockType.QA_PAIR, "问：住在哪里？", 0, (0, 100, 100, 150)),
            UniversalBlock(BlockType.QA_PAIR, "答：北京", 0, (0, 150, 100, 200)),
        ]
        chunks = plugin.process(blocks, {"docnm_kwt": "test.pdf"})
        # Should merge into 2 QA pairs
        assert len(chunks) == 2
        assert all(c["chunk_type"] == "qa_pair" for c in chunks)
        assert chunks[0]["qa_index"] == 0
        assert chunks[1]["qa_index"] == 1

    def test_process_header_and_qa(self):
        """Test processing both header and QA blocks."""
        plugin = InterrogationPlugin()
        blocks = [
            UniversalBlock(BlockType.HEADER, "讯问笔录", 0, (0, 0, 100, 50)),
            UniversalBlock(BlockType.QA_PAIR, "问：姓名？", 0, (0, 50, 100, 100)),
            UniversalBlock(BlockType.QA_PAIR, "答：张三", 0, (0, 100, 100, 150)),
        ]
        chunks = plugin.process(blocks, {"docnm_kwt": "test.pdf"})
        assert len(chunks) == 2
        assert chunks[0]["chunk_type"] == "header"
        assert chunks[1]["chunk_type"] == "qa_pair"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest test/unit/test_interrogation_plugin.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write implementation**

```python
# rag/app/criminal/plugins/interrogation.py

from typing import List
from copy import deepcopy

from .base import ParserPlugin
from ..blocks import UniversalBlock, BlockType


class InterrogationPlugin(ParserPlugin):
    """
    Interrogation record parser plugin (讯问笔录解析插件).

    Processes UniversalBlock sequences from interrogation records
    and produces semantic chunks for indexing.
    """

    @property
    def doc_type(self) -> str:
        return "interrogation"

    def process(
        self,
        blocks: List[UniversalBlock],
        doc: dict,
        chat_mdl=None,
        **kwargs
    ) -> List[dict]:
        """
        Process blocks into chunks.

        1. Extract header blocks → single header chunk
        2. Merge consecutive Q/A blocks → QA pair chunks
        """
        chunks = []

        # 1. Process header blocks
        header_blocks = self.get_header_blocks(blocks)
        if header_blocks:
            header_chunk = self._make_header_chunk(header_blocks, doc)
            chunks.append(header_chunk)

        # 2. Process QA blocks
        qa_blocks = self.get_qa_blocks(blocks)
        if qa_blocks:
            qa_chunks = self._merge_qa_pairs(qa_blocks, doc)
            chunks.extend(qa_chunks)

        return chunks

    def _make_header_chunk(self, blocks: List[UniversalBlock], doc: dict) -> dict:
        """Create header chunk from header blocks."""
        d = deepcopy(doc)
        d["chunk_type"] = "header"

        # Combine text
        text = "\n".join(b.text for b in blocks)
        d["content_with_weight"] = text

        # Use first block's position
        d["page_no"] = blocks[0].page_no
        d["bbox"] = list(blocks[0].bbox)

        # Merge entities
        entities = self._merge_entities(blocks)
        if entities:
            d["entities"] = entities

        return d

    def _merge_qa_pairs(self, blocks: List[UniversalBlock], doc: dict) -> List[dict]:
        """Merge consecutive Q/A blocks into QA pair chunks."""
        chunks = []
        current_q = None
        current_a_blocks = []
        qa_index = 0

        for block in blocks:
            text = block.text
            if text.startswith(("问：", "问:", "问；", "问;")):
                # Save previous QA pair
                if current_q:
                    chunk = self._make_qa_chunk(current_q, current_a_blocks, doc, qa_index)
                    chunks.append(chunk)
                    qa_index += 1
                current_q = block
                current_a_blocks = []
            elif text.startswith(("答：", "答:", "答；", "答;")):
                current_a_blocks.append(block)

        # Save last QA pair
        if current_q:
            chunk = self._make_qa_chunk(current_q, current_a_blocks, doc, qa_index)
            chunks.append(chunk)

        return chunks

    def _make_qa_chunk(
        self,
        q_block: UniversalBlock,
        a_blocks: List[UniversalBlock],
        doc: dict,
        qa_index: int
    ) -> dict:
        """Create QA pair chunk."""
        d = deepcopy(doc)
        d["chunk_type"] = "qa_pair"
        d["qa_index"] = qa_index

        # Combine question and answer
        q_text = q_block.text
        a_text = "\n".join(b.text for b in a_blocks)
        d["content_with_weight"] = f"{q_text}\t{a_text}"

        # Use question block's position
        d["page_no"] = q_block.page_no
        d["bbox"] = list(q_block.bbox)

        # Merge entities
        all_blocks = [q_block] + a_blocks
        entities = self._merge_entities(all_blocks)
        if entities:
            d["entities"] = entities

        return d

    def _merge_entities(self, blocks: List[UniversalBlock]) -> dict:
        """Merge entities from multiple blocks."""
        merged = {"amounts": [], "dates": []}
        for block in blocks:
            if block.entities:
                merged["amounts"].extend(block.entities.get("amounts", []))
                merged["dates"].extend(block.entities.get("dates", []))
        merged["amounts"] = list(set(merged["amounts"]))
        merged["dates"] = list(set(merged["dates"]))
        return merged if (merged["amounts"] or merged["dates"]) else {}
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest test/unit/test_interrogation_plugin.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add rag/app/criminal/plugins/interrogation.py test/unit/test_interrogation_plugin.py
git commit -m "feat(criminal): add InterrogationPlugin for Layer B processing"
```

---

## Task 2: Update interrogation.py to use Layer A + Layer B

**Files:**
- Modify: `rag/app/interrogation.py`

**Step 1: Verify existing tests pass before changes**

Run: `uv run pytest test/unit/test_interrogation_chunker.py -v`
Expected: All tests PASS (baseline)

**Step 2: Modify chunk() function to use Layer A + Layer B**

Key changes to `rag/app/interrogation.py`:

1. Add import for Layer A and Layer B:
```python
from rag.app.criminal.blocks import extract_universal_blocks
from rag.app.criminal.plugins.interrogation import InterrogationPlugin
```

2. Modify chunk() function to use new architecture:
```python
def chunk(filename, binary=None, from_page=0, to_page=100000, lang="Chinese", callback=None, **kwargs):
    """Main chunking function using Layer A + Layer B architecture."""
    eng = lang.lower() == "english"

    doc = {"docnm_kwd": filename, "title_tks": rag_tokenizer.tokenize(re.sub(r"\.[a-zA-Z]+$", "", filename))}

    if not re.search(r"\.pdf$", filename, re.IGNORECASE):
        raise NotImplementedError("Interrogation parser currently only supports PDF format files.")

    callback(0.1, "Start to parse interrogation record.")

    parser_config = kwargs.get("parser_config", {})
    tenant_id = kwargs.get("tenant_id")
    kb_id = kwargs.get("kb_id")
    doc_id = parser_config.get("doc_id", "")

    # Step 1: OCR (same as before)
    from rag.app.naive import by_paddleocr
    sections, tables, pdf_parser = by_paddleocr(
        filename=filename,
        binary=binary,
        from_page=from_page,
        to_page=to_page,
        lang=lang,
        callback=callback,
        parser_config=parser_config,
        tenant_id=tenant_id,
        kb_id=kb_id,
        doc_id=doc_id,
    )
    callback(0.4, "OCR completed.")

    # Step 2: Layer A - Extract universal blocks
    blocks = extract_universal_blocks(sections, "interrogation")
    callback(0.6, f"Extracted {len(blocks)} blocks.")

    # Step 3: Layer B - Plugin processing
    plugin = InterrogationPlugin()
    chunks = plugin.process(blocks, doc, chat_mdl=kwargs.get("chat_mdl"))
    callback(0.8, f"Generated {len(chunks)} chunks.")

    # Step 4: Tokenize chunks (required for RAG)
    for c in chunks:
        content = c.get("content_with_weight", "")
        tokenize(c, content, eng)
        add_bbox_union(c)
        add_page_range(c)
        add_block_refs(c)

    callback(1.0, f"Completed. Total chunks: {len(chunks)}")
    return chunks
```

**Step 3: Run existing tests to verify compatibility**

Run: `uv run pytest test/unit/test_interrogation_chunker.py -v`
Expected: All tests PASS (backward compatible)

**Step 4: Commit**

```bash
git add rag/app/interrogation.py
git commit -m "refactor(interrogation): migrate to Layer A + Layer B architecture"
```

---

## Task 3: Integration Test

**Files:**
- Create: `test/unit/test_interrogation_integration.py`

**Step 1: Write integration test**

```python
# test/unit/test_interrogation_integration.py

import pytest
from unittest.mock import patch, MagicMock

from rag.app.criminal.blocks import extract_universal_blocks, BlockType
from rag.app.criminal.plugins.interrogation import InterrogationPlugin


class TestInterrogationIntegration:
    """Integration tests for Layer A + Layer B."""

    def test_full_pipeline(self):
        """Test full pipeline from sections to chunks."""
        # Simulate OCR output
        sections = [
            ("讯问笔录", "@@1\t10.0\t200.0\t20.0\t40.0##"),
            ("时间：2024年1月15日", "@@1\t10.0\t200.0\t50.0\t70.0##"),
            ("问：你叫什么名字？", "@@1\t10.0\t200.0\t80.0\t100.0##"),
            ("答：我叫张三", "@@1\t10.0\t200.0\t110.0\t130.0##"),
            ("问：收到42000元吗？", "@@1\t10.0\t200.0\t140.0\t160.0##"),
            ("答：是的，收到了42000元", "@@1\t10.0\t200.0\t170.0\t190.0##"),
        ]

        # Layer A
        blocks = extract_universal_blocks(sections, "interrogation")

        assert len(blocks) == 6
        assert blocks[0].block_type == BlockType.HEADER
        assert blocks[2].block_type == BlockType.QA_PAIR

        # Verify entities extracted
        assert blocks[1].entities is not None
        assert "2024年1月15日" in blocks[1].entities["dates"]

        # Layer B
        plugin = InterrogationPlugin()
        chunks = plugin.process(blocks, {"docnm_kwt": "test.pdf"})

        # Should have 1 header + 2 QA pairs
        assert len(chunks) == 3
        assert chunks[0]["chunk_type"] == "header"
        assert chunks[1]["chunk_type"] == "qa_pair"
        assert chunks[2]["chunk_type"] == "qa_pair"

        # Verify entities in QA chunks
        assert chunks[2]["entities"] is not None
        assert "42000" in chunks[2]["entities"]["amounts"]
```

**Step 2: Run integration test**

Run: `uv run pytest test/unit/test_interrogation_integration.py -v`
Expected: PASS

**Step 3: Commit**

```bash
git add test/unit/test_interrogation_integration.py
git commit -m "test(criminal): add integration test for Layer A + Layer B"
```

---

## Task 4: Run Full Test Suite

**Step 1: Run all criminal module tests**

Run: `uv run pytest test/unit/test_blocks.py test/unit/test_ner.py test/unit/test_plugins_base.py test/unit/test_interrogation_plugin.py test/unit/test_interrogation_integration.py -v`
Expected: All PASS

**Step 2: Run original interrogation tests**

Run: `uv run pytest test/unit/test_interrogation_chunker.py -v`
Expected: All PASS (backward compatible)

**Step 3: Final commit**

```bash
git add -A
git commit -m "feat(criminal): complete Phase 2 - interrogation migration to Layer A/B"
```

---

## Summary

**Phase 2 Complete:** Interrogation parser now uses Layer A + Layer B architecture.

**Files Created:**
- `rag/app/criminal/plugins/interrogation.py`
- `test/unit/test_interrogation_plugin.py`
- `test/unit/test_interrogation_integration.py`

**Files Modified:**
- `rag/app/interrogation.py`

**Next Steps:**
- Phase 3: Migrate indictment.py
- Phase 4: Further optimize plugin architecture
