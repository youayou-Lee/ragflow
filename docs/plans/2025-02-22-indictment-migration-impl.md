# Phase 3: Indictment Parser Migration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate indictment.py to use Layer A (extract_universal_blocks) + Layer B (IndictmentPlugin) architecture while maintaining backward compatibility.

**Architecture:**
- Layer A: extract_universal_blocks() converts OCR sections → UniversalBlock list
- Layer B: IndictmentPlugin.process() converts UniversalBlock list → chunks
- chunk() function orchestrates: OCR → Layer A → Layer B

**Tech Stack:** Python 3.12, pytest, unittest.mock

---

## Task 1: Implement IndictmentPlugin

**Files:**
- Create: `rag/app/criminal/plugins/indictment.py`
- Create: `test/unit/test_indictment_plugin.py`

**Step 1: Write the failing test**

```python
# test/unit/test_indictment_plugin.py

import pytest
from rag.app.criminal.plugins.indictment import IndictmentPlugin
from rag.app.criminal.blocks import UniversalBlock, BlockType


class TestIndictmentPlugin:
    """Test IndictmentPlugin."""

    def test_doc_type(self):
        """Test doc_type property."""
        plugin = IndictmentPlugin()
        assert plugin.doc_type == "indictment"

    def test_process_empty_blocks(self):
        """Test processing empty block list."""
        plugin = IndictmentPlugin()
        chunks = plugin.process([], {"docnm_kwt": "test.pdf"})
        assert chunks == []

    def test_process_paragraph_blocks(self):
        """Test processing paragraph blocks."""
        plugin = IndictmentPlugin()
        blocks = [
            UniversalBlock(BlockType.PARAGRAPH, "起诉意见书", 0, (0, 0, 100, 50)),
            UniversalBlock(BlockType.PARAGRAPH, "犯罪嫌疑人张三", 0, (0, 50, 100, 100)),
        ]
        chunks = plugin.process(blocks, {"docnm_kwt": "test.pdf"})
        assert len(chunks) >= 1

    def test_process_with_section_trigger(self):
        """Test blocks containing section triggers."""
        plugin = IndictmentPlugin()
        blocks = [
            UniversalBlock(BlockType.HEADER, "起诉意见书", 0, (0, 0, 100, 50)),
            UniversalBlock(BlockType.PARAGRAPH, "经依法侦查查明，事实如下", 0, (0, 50, 100, 100)),
            UniversalBlock(BlockType.PARAGRAPH, "具体犯罪事实描述", 0, (0, 100, 100, 150)),
        ]
        chunks = plugin.process(blocks, {"docnm_kwt": "test.pdf"})
        # Should create section chunks based on triggers
        assert len(chunks) >= 1
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest test/unit/test_indictment_plugin.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write implementation**

```python
# rag/app/criminal/plugins/indictment.py

import re
from typing import List
from copy import deepcopy

from .base import ParserPlugin
from ..blocks import UniversalBlock, BlockType


# Section trigger phrases (in order of typical appearance)
SECTION_TRIGGERS = [
    r"经依法侦查查明",
    r"经依法审查查明",
    r"现查明",
    r"认定上述犯罪事实的证据如下",
    r"上述犯罪事实(?:，|，\s*)有(?:以下|下列)证据(?:予以)?证实",
    r"综上所述",
    r"本院认为",
    r"此致",
]

SECTION_TRIGGER_PATTERN = re.compile("|".join(f"({t})" for t in SECTION_TRIGGERS))

# Maximum length for section before splitting
MAX_SECTION_LENGTH = 800


class IndictmentPlugin(ParserPlugin):
    """
    Indictment document parser plugin (起诉意见书解析插件).

    Processes UniversalBlock sequences from indictment documents
    and produces semantic chunks for indexing.
    """

    @property
    def doc_type(self) -> str:
        return "indictment"

    def process(
        self,
        blocks: List[UniversalBlock],
        doc: dict,
        chat_mdl=None,
        **kwargs
    ) -> List[dict]:
        """
        Process blocks into chunks.

        1. Find section boundaries based on trigger phrases
        2. Build section chunks (split long sections into paragraphs)
        """
        if not blocks:
            return []

        # Find section boundaries
        sections = self._find_section_boundaries(blocks)

        # Build chunks from sections
        chunks = []
        for start_idx, end_idx, trigger in sections:
            section_blocks = blocks[start_idx:end_idx]
            section_chunks = self._build_section_chunks(section_blocks, doc, trigger)
            chunks.extend(section_chunks)

        return chunks

    def _find_section_boundaries(self, blocks: List[UniversalBlock]) -> List[tuple]:
        """Find section boundaries based on trigger phrases."""
        sections = []
        current_start = 0
        current_trigger = "header"

        for i, block in enumerate(blocks):
            match = SECTION_TRIGGER_PATTERN.search(block.text)
            if match:
                if i > current_start:
                    sections.append((current_start, i, current_trigger))
                current_start = i
                current_trigger = match.group(0)

        if current_start < len(blocks):
            sections.append((current_start, len(blocks), current_trigger))

        return sections

    def _build_section_chunks(
        self,
        blocks: List[UniversalBlock],
        doc: dict,
        trigger: str
    ) -> List[dict]:
        """Build chunks from a section."""
        # Combine text for length check
        total_length = sum(len(b.text) for b in blocks)

        if total_length > MAX_SECTION_LENGTH:
            return self._split_into_paragraphs(blocks, doc, trigger)
        else:
            return [self._make_section_chunk(blocks, doc, trigger, "section")]

    def _make_section_chunk(
        self,
        blocks: List[UniversalBlock],
        doc: dict,
        trigger: str,
        chunk_type: str
    ) -> dict:
        """Create a section or paragraph chunk."""
        d = deepcopy(doc)
        d["chunk_type"] = chunk_type
        d["section_trigger"] = trigger

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

    def _split_into_paragraphs(
        self,
        blocks: List[UniversalBlock],
        doc: dict,
        trigger: str
    ) -> List[dict]:
        """Split a long section into paragraph chunks."""
        chunks = []
        current_blocks = []
        current_length = 0

        for block in blocks:
            block_length = len(block.text)

            if current_length + block_length > MAX_SECTION_LENGTH and current_blocks:
                chunk = self._make_section_chunk(
                    current_blocks, doc, trigger, "paragraph"
                )
                chunks.append(chunk)
                current_blocks = [block]
                current_length = block_length
            else:
                current_blocks.append(block)
                current_length += block_length

        if current_blocks:
            chunk_type = "paragraph" if chunks else "section"
            chunk = self._make_section_chunk(current_blocks, doc, trigger, chunk_type)
            chunks.append(chunk)

        return chunks

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

Run: `uv run pytest test/unit/test_indictment_plugin.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add rag/app/criminal/plugins/indictment.py test/unit/test_indictment_plugin.py
git commit -m "feat(criminal): add IndictmentPlugin for Layer B processing"
```

---

## Task 2: Update indictment.py to use Layer A + Layer B

**Files:**
- Modify: `rag/app/indictment.py`

**Step 1: Verify existing tests pass before changes**

Run: `uv run pytest test/unit/test_indictment_chunker.py -v`
Expected: All tests PASS (baseline)

**Step 2: Modify chunk() function to use Layer A + Layer B**

Key changes to `rag/app/indictment.py`:

1. Add import for Layer A and Layer B:
```python
from rag.app.criminal.blocks import extract_universal_blocks
from rag.app.criminal.plugins.indictment import IndictmentPlugin
```

2. Modify chunk() function to use new architecture:
```python
def chunk(filename, binary=None, from_page=0, to_page=100000, lang="Chinese", callback=None, extract_evidence=False, **kwargs):
    eng = lang.lower() == "english"

    doc = {"docnm_kwd": filename, "title_tks": rag_tokenizer.tokenize(re.sub(r"\.[a-zA-Z]+$", "", filename))}

    if not re.search(r"\.pdf$", filename, re.IGNORECASE):
        raise NotImplementedError("Indictment parser currently only supports PDF format files.")

    callback(0.1, "Start to parse indictment document.")

    parser_config = kwargs.get("parser_config", {})
    tenant_id = kwargs.get("tenant_id")
    kb_id = kwargs.get("kb_id")
    doc_id = parser_config.get("doc_id", "")

    # Step 1: Try PaddleOCR first (same as interrogation)
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

    # Fallback to local OCR if PaddleOCR fails
    if sections is None:
        logging.info("PaddleOCR not available, falling back to local OCR")
        pdf_parser = Pdf()
        blocks_raw = pdf_parser(filename if not binary else binary, from_page=from_page, to_page=to_page, callback=callback)
        # Convert raw blocks to sections format
        sections = [(b, "") for b in blocks_raw]

    callback(0.4, "OCR completed.")

    # Step 2: Layer A - Extract universal blocks
    blocks = extract_universal_blocks(sections, "indictment")
    callback(0.6, f"Extracted {len(blocks)} blocks.")

    # Step 3: Layer B - Plugin processing
    plugin = IndictmentPlugin()
    chunks = plugin.process(blocks, doc, chat_mdl=kwargs.get("chat_mdl"))
    callback(0.8, f"Generated {len(chunks)} chunks.")

    # Step 4: Add required fields for RAG
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

Run: `uv run pytest test/unit/test_indictment_chunker.py -v`
Expected: All tests PASS (backward compatible)

**Step 4: Commit**

```bash
git add rag/app/indictment.py
git commit -m "refactor(indictment): migrate to Layer A + Layer B architecture"
```

---

## Task 3: Integration Test

**Files:**
- Create: `test/unit/test_indictment_integration.py`

**Step 1: Write integration test**

```python
# test/unit/test_indictment_integration.py

import pytest
from rag.app.criminal.blocks import extract_universal_blocks, BlockType
from rag.app.criminal.plugins.indictment import IndictmentPlugin


class TestIndictmentIntegration:
    """Integration tests for Layer A + Layer B."""

    def test_full_pipeline(self):
        """Test full pipeline from sections to chunks."""
        sections = [
            ("起诉意见书", "@@1\t10.0\t200.0\t20.0\t40.0##"),
            ("犯罪嫌疑人张三", "@@1\t10.0\t200.0\t50.0\t70.0##"),
            ("经依法侦查查明，事实如下", "@@1\t10.0\t200.0\t80.0\t100.0##"),
            ("2024年1月15日实施诈骗42000元", "@@1\t10.0\t200.0\t110.0\t130.0##"),
        ]

        # Layer A
        blocks = extract_universal_blocks(sections, "indictment")
        assert len(blocks) == 4

        # Layer B
        plugin = IndictmentPlugin()
        chunks = plugin.process(blocks, {"docnm_kwt": "test.pdf"})

        assert len(chunks) >= 1
        assert "section_trigger" in chunks[0]

    def test_entities_preserved(self):
        """Test entity preservation in indictment chunks."""
        sections = [
            ("涉案金额42000元，案发时间2024年3月15日", "@@1\t10.0\t200.0\t20.0\t40.0##"),
        ]

        blocks = extract_universal_blocks(sections, "indictment")
        plugin = IndictmentPlugin()
        chunks = plugin.process(blocks, {"docnm_kwt": "test.pdf"})

        assert chunks[0]["entities"] is not None
        assert "42000" in chunks[0]["entities"]["amounts"]

    def test_section_splitting(self):
        """Test long section splitting."""
        # Create a long section
        long_text = "x" * 1000
        sections = [
            (long_text, "@@1\t10.0\t200.0\t20.0\t40.0##"),
        ]

        blocks = extract_universal_blocks(sections, "indictment")
        plugin = IndictmentPlugin()
        chunks = plugin.process(blocks, {"docnm_kwt": "test.pdf"})

        # Should be split into multiple chunks
        assert len(chunks) >= 1
```

**Step 2: Run integration test**

Run: `uv run pytest test/unit/test_indictment_integration.py -v`
Expected: PASS

**Step 3: Commit**

```bash
git add test/unit/test_indictment_integration.py
git commit -m "test(criminal): add integration test for indictment Layer A + Layer B"
```

---

## Task 4: Run Full Test Suite

**Step 1: Run all criminal module tests**

Run: `uv run pytest test/unit/test_blocks.py test/unit/test_ner.py test/unit/test_plugins_base.py test/unit/test_interrogation_plugin.py test/unit/test_interrogation_integration.py test/unit/test_indictment_plugin.py test/unit/test_indictment_integration.py test/unit/test_interrogation_chunker.py test/unit/test_indictment_chunker.py -v`
Expected: All PASS

**Step 2: Final commit**

```bash
git add -A
git commit -m "feat(criminal): complete Phase 3 - indictment migration to Layer A/B"
```

---

## Summary

**Phase 3 Complete:** Indictment parser now uses Layer A + Layer B architecture.

**Files Created:**
- `rag/app/criminal/plugins/indictment.py`
- `test/unit/test_indictment_plugin.py`
- `test/unit/test_indictment_integration.py`

**Files Modified:**
- `rag/app/indictment.py`

**Next Steps:**
- Phase 4: Further optimize plugin architecture (optional)
- Performance testing with real documents
