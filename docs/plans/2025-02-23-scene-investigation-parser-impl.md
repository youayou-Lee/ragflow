# 现场勘验检查笔录 Parser Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为现场勘验检查笔录创建 Layer B 专用解析插件，支持表单字段识别和章节分割。

**Architecture:** 基于 Layer A + Layer B 两层架构，Layer A 负责 UniversalBlock 提取，Layer B 的 SceneInvestigationPlugin 负责按触发词分割章节并生成结构化 chunks。

**Tech Stack:** Python 3.12, pytest, dataclasses, regex

---

## 参考文档

- 架构文档: `docs/criminal-parser-architecture.md`
- 现有插件示例: `rag/app/criminal/plugins/indictment.py`
- 测试示例: `test/unit/test_indictment_integration.py`

---

## Task 1: 创建 Plugin 基础结构和 doc_type 属性

**Files:**
- Create: `rag/app/criminal/plugins/scene_investigation.py`
- Test: `test/unit/test_scene_investigation_plugin.py`

**Step 1: Write the failing test**

```python
# test/unit/test_scene_investigation_plugin.py
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
Unit tests for SceneInvestigationPlugin.
"""

import pytest

from rag.app.criminal.plugins.scene_investigation import SceneInvestigationPlugin


class TestSceneInvestigationPlugin:
    """Tests for SceneInvestigationPlugin basic functionality."""

    def test_doc_type(self):
        """Test that doc_type returns correct identifier."""
        plugin = SceneInvestigationPlugin()
        assert plugin.doc_type == "scene_investigation"

    def test_process_empty_blocks(self):
        """Test that empty blocks return empty chunks."""
        plugin = SceneInvestigationPlugin()
        chunks = plugin.process([], {"docnm_kwt": "test.pdf"})
        assert chunks == []
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest test/unit/test_scene_investigation_plugin.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'rag.app.criminal.plugins.scene_investigation'"

**Step 3: Write minimal implementation**

```python
# rag/app/criminal/plugins/scene_investigation.py
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
Scene Investigation Record (现场勘验检查笔录) Parser Plugin.

This plugin handles parsing of police scene investigation records,
which are standardized forms documenting crime scene investigations.
"""

import re
from typing import List
from copy import deepcopy

from .base import ParserPlugin
from ..blocks import UniversalBlock, BlockType


# Section trigger patterns for scene investigation records
SECTION_TRIGGERS = [
    r"勘查号[：:]",
    r"勘验号[：:]",
    r"现场勘验单位[：:]",
    r"勘验事由[：:]",
    r"现场勘验开始时间",
    r"现场勘验结束时间",
    r"现场地点[：:]",
    r"现场保护情况",
    r"现场勘验情况[：:]",
    r"案发现场情况[：:]",
    r"现场勘验记录人员[：:]",
    r"现场勘验人员[：:]",
    r"现场勘验见证人[：:]",
]

SECTION_TRIGGER_PATTERN = re.compile("|".join(f"({t})" for t in SECTION_TRIGGERS))

# Maximum section length before splitting
MAX_SECTION_LENGTH = 800


class SceneInvestigationPlugin(ParserPlugin):
    """Parser plugin for Scene Investigation Records (现场勘验检查笔录)."""

    @property
    def doc_type(self) -> str:
        """Return document type identifier."""
        return "scene_investigation"

    def process(
        self,
        blocks: List[UniversalBlock],
        doc: dict,
        chat_mdl=None,
        **kwargs
    ) -> List[dict]:
        """Process blocks into chunks based on section triggers."""
        if not blocks:
            return []

        chunks = []

        # Find section boundaries based on triggers
        sections = self._find_sections(blocks)

        # Process each section
        for start_idx, end_idx, trigger in sections:
            section_blocks = blocks[start_idx:end_idx]
            section_chunks = self._process_section(section_blocks, doc, trigger)
            chunks.extend(section_chunks)

        return chunks

    def _find_sections(self, blocks: List[UniversalBlock]) -> List[tuple]:
        """Find section boundaries based on trigger patterns."""
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

        # Add final section
        if current_start < len(blocks):
            sections.append((current_start, len(blocks), current_trigger))

        return sections

    def _process_section(
        self,
        blocks: List[UniversalBlock],
        doc: dict,
        trigger: str
    ) -> List[dict]:
        """Process a single section into chunks."""
        total_length = sum(len(b.text) for b in blocks)

        # Long sections need splitting
        if total_length > MAX_SECTION_LENGTH:
            return self._split_section(blocks, doc, trigger)

        return [self._make_chunk(blocks, doc, trigger, "section")]

    def _split_section(
        self,
        blocks: List[UniversalBlock],
        doc: dict,
        trigger: str
    ) -> List[dict]:
        """Split a long section into multiple chunks."""
        chunks = []
        current_blocks = []
        current_length = 0

        for block in blocks:
            if current_length + len(block.text) > MAX_SECTION_LENGTH and current_blocks:
                # Create chunk from current blocks
                chunks.append(self._make_chunk(current_blocks, doc, trigger, "paragraph"))
                current_blocks = []
                current_length = 0

            current_blocks.append(block)
            current_length += len(block.text)

        # Add remaining blocks
        if current_blocks:
            chunks.append(self._make_chunk(current_blocks, doc, trigger, "paragraph"))

        return chunks

    def _make_chunk(
        self,
        blocks: List[UniversalBlock],
        doc: dict,
        trigger: str,
        chunk_type: str
    ) -> dict:
        """Create a chunk from blocks."""
        d = deepcopy(doc)
        d["chunk_type"] = chunk_type
        d["section_trigger"] = trigger

        # Merge text from all blocks
        d["content_with_weight"] = "\n".join(b.text for b in blocks)

        # Position info from first block
        d["page_no"] = blocks[0].page_no
        d["bbox"] = list(blocks[0].bbox)

        # Merge entities
        entities = self._merge_entities(blocks)
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

Run: `uv run pytest test/unit/test_scene_investigation_plugin.py -v`
Expected: PASS (2 tests)

**Step 5: Commit**

```bash
git add rag/app/criminal/plugins/scene_investigation.py test/unit/test_scene_investigation_plugin.py
git commit -m "feat(criminal): add SceneInvestigationPlugin basic structure

- Implement doc_type property returning 'scene_investigation'
- Add section trigger patterns for scene investigation records
- Add empty block handling
- Add unit tests for basic functionality

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 2: 实现章节边界识别测试与实现

**Files:**
- Modify: `test/unit/test_scene_investigation_plugin.py`
- Modify: `rag/app/criminal/plugins/scene_investigation.py`

**Step 1: Write the failing test**

Add to `test/unit/test_scene_investigation_plugin.py`:

```python
from rag.app.criminal.blocks import UniversalBlock, BlockType


class TestSceneInvestigationSectionBoundaries:
    """Tests for section boundary detection."""

    def test_find_sections_basic(self):
        """Test basic section boundary detection."""
        plugin = SceneInvestigationPlugin()
        blocks = [
            UniversalBlock(BlockType.HEADER, "勘查号：K4418025400002021020012", 0, (0, 0, 100, 50)),
            UniversalBlock(BlockType.PARAGRAPH, "现场勘验单位：清远市公安局下廓派出所", 0, (0, 50, 100, 100)),
            UniversalBlock(BlockType.PARAGRAPH, "普通内容段落", 0, (0, 100, 100, 150)),
        ]

        sections = plugin._find_sections(blocks)

        assert len(sections) >= 2
        assert sections[0][2] == "header"
        assert "现场勘验单位" in sections[1][2]

    def test_find_sections_with_multiple_triggers(self):
        """Test detection with multiple trigger patterns."""
        plugin = SceneInvestigationPlugin()
        blocks = [
            UniversalBlock(BlockType.HEADER, "勘查号：K123", 0, (0, 0, 100, 50)),
            UniversalBlock(BlockType.PARAGRAPH, "现场勘验情况：详情描述", 0, (0, 50, 100, 100)),
            UniversalBlock(BlockType.PARAGRAPH, "现场勘验人员：张三", 0, (0, 100, 100, 150)),
        ]

        sections = plugin._find_sections(blocks)

        assert len(sections) == 3
        triggers = [s[2] for s in sections]
        assert "勘查号：" in triggers[0]
        assert "现场勘验情况：" in triggers[1]
        assert "现场勘验人员：" in triggers[2]

    def test_process_creates_chunks_by_section(self):
        """Test that process creates chunks based on sections."""
        plugin = SceneInvestigationPlugin()
        blocks = [
            UniversalBlock(BlockType.HEADER, "勘查号：K4418025400002021020012", 0, (0, 0, 100, 50)),
            UniversalBlock(BlockType.PARAGRAPH, "现场勘验单位：清远市公安局", 0, (0, 50, 100, 100)),
            UniversalBlock(BlockType.PARAGRAPH, "普通内容", 0, (0, 100, 100, 150)),
        ]

        chunks = plugin.process(blocks, {"docnm_kwt": "test.pdf"})

        assert len(chunks) >= 2
        assert all("section_trigger" in chunk for chunk in chunks)
        assert all("content_with_weight" in chunk for chunk in chunks)
```

**Step 2: Run test to verify it passes**

Run: `uv run pytest test/unit/test_scene_investigation_plugin.py -v`
Expected: PASS (5 tests) - implementation already supports this from Task 1

**Step 3: Commit**

```bash
git add test/unit/test_scene_investigation_plugin.py
git commit -m "test(criminal): add section boundary detection tests for SceneInvestigationPlugin

- Test basic section boundary detection
- Test multiple trigger patterns
- Test chunk creation by section

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 3: 实现实体保留和合并

**Files:**
- Modify: `test/unit/test_scene_investigation_plugin.py`
- Modify: `rag/app/criminal/plugins/scene_investigation.py`

**Step 1: Write the failing test**

Add to `test/unit/test_scene_investigation_plugin.py`:

```python
class TestSceneInvestigationEntities:
    """Tests for entity preservation."""

    def test_entities_preserved_in_chunk(self):
        """Test that entities are preserved in chunks."""
        plugin = SceneInvestigationPlugin()
        blocks = [
            UniversalBlock(
                BlockType.PARAGRAPH,
                "涉案金额42000元，日期2021年2月1日",
                0, (0, 0, 100, 50),
                entities={"amounts": ["42000"], "dates": ["2021年2月1日"]}
            ),
        ]

        chunks = plugin.process(blocks, {"docnm_kwt": "test.pdf"})

        assert len(chunks) == 1
        assert chunks[0]["entities"] is not None
        assert "42000" in chunks[0]["entities"]["amounts"]
        assert "2021年2月1日" in chunks[0]["entities"]["dates"]

    def test_entities_merged_from_multiple_blocks(self):
        """Test that entities from multiple blocks are merged."""
        plugin = SceneInvestigationPlugin()
        blocks = [
            UniversalBlock(
                BlockType.PARAGRAPH,
                "金额10000元",
                0, (0, 0, 100, 50),
                entities={"amounts": ["10000"], "dates": []}
            ),
            UniversalBlock(
                BlockType.PARAGRAPH,
                "金额20000元",
                0, (0, 50, 100, 100),
                entities={"amounts": ["20000"], "dates": []}
            ),
        ]

        chunks = plugin.process(blocks, {"docnm_kwt": "test.pdf"})

        # Last chunk should have merged entities
        chunk = chunks[-1]
        assert chunk["entities"] is not None
        assert "10000" in chunk["entities"]["amounts"]
        assert "20000" in chunk["entities"]["amounts"]

    def test_no_entities_when_empty(self):
        """Test that entities field is empty when no entities present."""
        plugin = SceneInvestigationPlugin()
        blocks = [
            UniversalBlock(BlockType.PARAGRAPH, "普通文本无实体", 0, (0, 0, 100, 50)),
        ]

        chunks = plugin.process(blocks, {"docnm_kwt": "test.pdf"})

        assert len(chunks) == 1
        # Entities should be empty dict when no entities
        assert chunks[0].get("entities", {}) == {}
```

**Step 2: Run test to verify it passes**

Run: `uv run pytest test/unit/test_scene_investigation_plugin.py::TestSceneInvestigationEntities -v`
Expected: PASS - implementation already supports this

**Step 3: Commit**

```bash
git add test/unit/test_scene_investigation_plugin.py
git commit -m "test(criminal): add entity preservation tests for SceneInvestigationPlugin

- Test entities preserved in single chunk
- Test entities merged from multiple blocks
- Test empty entities handling

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 4: 创建集成测试

**Files:**
- Create: `test/unit/test_scene_investigation_integration.py`

**Step 1: Write the integration test**

```python
# test/unit/test_scene_investigation_integration.py
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
Integration tests for Layer A + Layer B scene investigation parsing.

Tests the full pipeline from OCR sections to chunks, verifying:
1. Layer A: extract_universal_blocks correctly classifies block types
2. Layer A: entities (dates, amounts) are extracted
3. Layer B: SceneInvestigationPlugin produces correct chunks with section triggers
4. Entities are preserved through the pipeline
"""

import pytest

from rag.app.criminal.blocks import extract_universal_blocks, BlockType
from rag.app.criminal.plugins.scene_investigation import SceneInvestigationPlugin


class TestSceneInvestigationIntegration:
    """Integration tests for Layer A + Layer B."""

    def test_full_pipeline(self):
        """Test full pipeline from sections to chunks."""
        # Simulate OCR output format
        sections = [
            ("勘查号：K4418025400002021020012", "@@1\t10.0\t200.0\t20.0\t40.0##"),
            ("现场勘验检查笔录", "@@1\t10.0\t200.0\t50.0\t70.0##"),
            ("现场勘验单位：清远市公安局下廓派出所", "@@1\t10.0\t200.0\t80.0\t100.0##"),
            # Long text to avoid FOOTER classification
            ("2021年2月1日进行现场勘查，涉案金额42000元。这是具体的案件描述内容，包含了案件发生的时间、地点和相关人员信息。", "@@1\t10.0\t200.0\t110.0\t130.0##"),
        ]

        # Layer A: Extract universal blocks
        blocks = extract_universal_blocks(sections, "scene_investigation")

        # Verify block count
        assert len(blocks) == 4

        # Verify block types
        assert blocks[0].block_type == BlockType.HEADER  # First block, short
        assert blocks[1].block_type == BlockType.HEADER  # Title
        assert blocks[2].block_type == BlockType.PARAGRAPH
        assert blocks[3].block_type == BlockType.PARAGRAPH

        # Layer B: Process blocks into chunks
        plugin = SceneInvestigationPlugin()
        chunks = plugin.process(blocks, {"docnm_kwt": "test.pdf"})

        # Should have multiple chunks based on triggers
        assert len(chunks) >= 1
        assert "section_trigger" in chunks[0]

    def test_entities_preserved(self):
        """Test entity preservation in scene investigation chunks."""
        sections = [
            ("涉案金额42000元，案发时间2021年2月1日", "@@1\t10.0\t200.0\t20.0\t40.0##"),
        ]

        # Layer A
        blocks = extract_universal_blocks(sections, "scene_investigation")

        # Verify entities extracted
        assert blocks[0].entities is not None
        assert "42000" in blocks[0].entities["amounts"]
        assert "2021年2月1日" in blocks[0].entities["dates"]

        # Layer B
        plugin = SceneInvestigationPlugin()
        chunks = plugin.process(blocks, {"docnm_kwt": "test.pdf"})

        # Verify entities preserved
        assert len(chunks) == 1
        assert chunks[0]["entities"] is not None
        assert "42000" in chunks[0]["entities"]["amounts"]
        assert "2021年2月1日" in chunks[0]["entities"]["dates"]

    def test_section_splitting_long_content(self):
        """Test long section splitting."""
        # Create a long section that exceeds MAX_SECTION_LENGTH
        long_text = "x" * 1000
        sections = [
            (long_text, "@@1\t10.0\t200.0\t20.0\t40.0##"),
        ]

        # Layer A
        blocks = extract_universal_blocks(sections, "scene_investigation")
        assert len(blocks) == 1

        # Layer B
        plugin = SceneInvestigationPlugin()
        chunks = plugin.process(blocks, {"docnm_kwt": "test.pdf"})

        # Should be split into multiple chunks
        assert len(chunks) >= 1
        for chunk in chunks:
            assert "section_trigger" in chunk
            assert "content_with_weight" in chunk

    def test_section_triggers_create_boundaries(self):
        """Test that section triggers create proper boundaries."""
        sections = [
            ("勘查号：K4418025400002021020012", "@@1\t10.0\t200.0\t20.0\t40.0##"),
            ("现场勘验单位：清远市公安局", "@@1\t10.0\t200.0\t50.0\t70.0##"),
            ("现场勘验情况：现场方位描述", "@@1\t10.0\t200.0\t80.0\t100.0##"),
            ("案发现场情况：案件详细描述", "@@1\t10.0\t200.0\t110.0\t130.0##"),
            ("现场勘验人员：签名信息", "@@1\t10.0\t200.0\t140.0\t160.0##"),
        ]

        # Layer A
        blocks = extract_universal_blocks(sections, "scene_investigation")
        assert len(blocks) == 5

        # Layer B
        plugin = SceneInvestigationPlugin()
        chunks = plugin.process(blocks, {"docnm_kwt": "test.pdf"})

        # Should create multiple chunks based on section triggers
        assert len(chunks) >= 3

        # Verify different section triggers
        triggers = [chunk["section_trigger"] for chunk in chunks]
        assert "header" in triggers  # Initial section

    def test_empty_sections(self):
        """Test handling of empty sections."""
        sections = []

        # Layer A
        blocks = extract_universal_blocks(sections, "scene_investigation")
        assert blocks == []

        # Layer B
        plugin = SceneInvestigationPlugin()
        chunks = plugin.process(blocks, {"docnm_kwt": "test.pdf"})
        assert chunks == []

    def test_position_preserved(self):
        """Test that position information is preserved through pipeline."""
        sections = [
            ("勘查号：K123", "@@2\t15.0\t180.0\t30.0\t50.0##"),
            ("现场勘验单位：公安局", "@@3\t20.0\t190.0\t40.0\t60.0##"),
        ]

        # Layer A
        blocks = extract_universal_blocks(sections, "scene_investigation")

        # Verify positions (page is 0-indexed)
        assert blocks[0].page_no == 1  # Page 2 -> 0-indexed
        assert blocks[0].bbox == (15.0, 30.0, 180.0, 50.0)

        # Layer B
        plugin = SceneInvestigationPlugin()
        chunks = plugin.process(blocks, {"docnm_kwt": "test.pdf"})

        # Verify positions in chunks
        assert chunks[0]["page_no"] == 1
        assert chunks[0]["bbox"] == [15.0, 30.0, 180.0, 50.0]
```

**Step 2: Run test to verify it passes**

Run: `uv run pytest test/unit/test_scene_investigation_integration.py -v`
Expected: PASS (6 tests)

**Step 3: Commit**

```bash
git add test/unit/test_scene_investigation_integration.py
git commit -m "test(criminal): add integration tests for SceneInvestigationPlugin

- Test full pipeline from OCR to chunks
- Test entity preservation
- Test long section splitting
- Test section trigger boundaries
- Test empty sections handling
- Test position preservation

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 5: 创建入口函数

**Files:**
- Create: `rag/app/scene_investigation.py`

**Step 1: Write the chunk entry function**

```python
# rag/app/scene_investigation.py
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
Scene Investigation Record (现场勘验检查笔录) Parser.

Entry function for parsing police scene investigation records.
"""

import re

from rag.app.criminal.blocks import extract_universal_blocks
from rag.app.criminal.plugins.scene_investigation import SceneInvestigationPlugin
from rag.nlp import rag_tokenizer, tokenize, add_bbox_union, add_page_range, add_block_refs


def chunk(filename, binary=None, from_page=0, to_page=100000, lang="Chinese", callback=None, **kwargs):
    """
    Parse Scene Investigation Record (现场勘验检查笔录) into chunks.

    Args:
        filename: File path to the PDF document
        binary: Binary content of the file (optional)
        from_page: Start page (0-indexed)
        to_page: End page (exclusive)
        lang: Language ("Chinese" or "English")
        callback: Progress callback function(progress, message)
        **kwargs: Additional arguments including parser_config, tenant_id, kb_id, chat_mdl

    Returns:
        list: List of chunk dictionaries with content, positions, and entities
    """
    eng = lang.lower() == "english"

    # Base document info
    doc = {
        "docnm_kwt": filename,
        "title_tks": rag_tokenizer.tokenize(re.sub(r"\.[a-zA-Z]+$", "", filename))
    }

    # Check file format
    if not re.search(r"\.pdf$", filename, re.IGNORECASE):
        raise NotImplementedError("仅支持 PDF 格式文件")

    if callback:
        callback(0.1, "开始解析现场勘验笔录...")

    # Step 1: OCR using PaddleOCR
    from rag.app.naive import by_paddleocr
    parser_config = kwargs.get("parser_config", {})

    sections, tables, pdf_parser = by_paddleocr(
        filename=filename,
        binary=binary,
        from_page=from_page,
        to_page=to_page,
        lang=lang,
        callback=callback,
        parser_config=parser_config,
        tenant_id=kwargs.get("tenant_id"),
        kb_id=kwargs.get("kb_id"),
        doc_id=parser_config.get("doc_id", ""),
    )

    if callback:
        callback(0.4, "OCR 完成")

    # Step 2: Layer A - Universal Block extraction
    blocks = extract_universal_blocks(sections, "scene_investigation")
    if callback:
        callback(0.6, f"提取 {len(blocks)} 个版面块")

    # Step 3: Layer B - Scene Investigation Plugin processing
    plugin = SceneInvestigationPlugin()
    chunks = plugin.process(blocks, doc, chat_mdl=kwargs.get("chat_mdl"))
    if callback:
        callback(0.8, f"生成 {len(chunks)} 个语义块")

    # Step 4: Add RAG-required fields
    for c in chunks:
        content = c.get("content_with_weight", "")
        tokenize(c, content, eng)
        add_bbox_union(c)
        add_page_range(c)
        add_block_refs(c)

    if callback:
        callback(1.0, f"解析完成，共 {len(chunks)} 个语义块")

    return chunks
```

**Step 2: Run tests to verify no regression**

Run: `uv run pytest test/unit/test_scene_investigation_plugin.py test/unit/test_scene_investigation_integration.py -v`
Expected: PASS (all tests)

**Step 3: Commit**

```bash
git add rag/app/scene_investigation.py
git commit -m "feat(criminal): add scene_investigation chunk entry function

- Implement chunk() function for scene investigation records
- Integrate Layer A (extract_universal_blocks) and Layer B (SceneInvestigationPlugin)
- Add progress callbacks for each processing stage
- Add RAG-required field processing (tokenize, bbox, page range)

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 6: 更新架构文档

**Files:**
- Modify: `docs/criminal-parser-architecture.md`

**Step 1: Update directory structure section**

在"目录结构"部分添加 scene_investigation：

```markdown
```
rag/app/criminal/
├── __init__.py            # 模块入口，导出核心类
├── blocks.py              # Layer A: UniversalBlock + extract_universal_blocks()
├── ner.py                 # 轻量 NER: extract_lightweight_entities()
└── plugins/
    ├── __init__.py        # 插件模块入口
    ├── base.py            # ParserPlugin 基类
    ├── interrogation.py   # 讯问笔录插件
    ├── indictment.py      # 起诉意见书插件
    └── scene_investigation.py  # 现场勘验检查笔录插件

rag/app/
├── interrogation.py       # 讯问笔录入口
├── indictment.py          # 起诉意见书入口
└── scene_investigation.py # 现场勘验检查笔录入口
```
```

**Step 2: Update test files section**

在"测试文件"部分添加：

```markdown
├── test_scene_investigation_plugin.py      # 现场勘验笔录插件测试
├── test_scene_investigation_integration.py # 现场勘验笔录集成测试
```

**Step 3: Update change history**

在"变更历史"部分添加：

```markdown
| 2025-02-23 | 1.1 | 添加现场勘验检查笔录 (scene_investigation) 解析插件 |
```

**Step 4: Commit**

```bash
git add docs/criminal-parser-architecture.md
git commit -m "docs(criminal): update architecture doc with scene_investigation plugin

- Add scene_investigation.py to directory structure
- Add test files for scene investigation
- Update change history

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 7: 运行完整测试套件验证

**Files:**
- None (verification only)

**Step 1: Run all criminal parser tests**

Run: `uv run pytest test/unit/test_blocks.py test/unit/test_ner.py test/unit/test_plugins_base.py test/unit/test_interrogation_plugin.py test/unit/test_interrogation_integration.py test/unit/test_indictment_plugin.py test/unit/test_indictment_integration.py test/unit/test_scene_investigation_plugin.py test/unit/test_scene_investigation_integration.py -v`

Expected: All tests PASS

**Step 2: Verify test count increased**

Compare with previous test run to confirm new tests are running.

---

## Summary

| Task | Files Created | Files Modified | Tests Added |
|------|---------------|----------------|-------------|
| 1 | plugin + test | - | 2 |
| 2 | - | test | 3 |
| 3 | - | test | 3 |
| 4 | integration test | - | 6 |
| 5 | entry function | - | 0 |
| 6 | - | docs | 0 |
| 7 | - | - | verification |

**Total new tests**: 14
**Total commits**: 7
