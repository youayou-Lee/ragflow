# 两层解析架构实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现两层文档解析架构，Layer A 通用 Block 抽取 + Layer B 文书类型插件

**Architecture:**
- Layer A：所有文书统一处理，输出标准化 Block（含位置、类型、轻量 NER）
- Layer B：插件化架构，按文书类型扩展，无插件时走通用 Chunker 兜底

**Tech Stack:** Python 3.12, dataclasses, abc, re (规则 NER), pytest

**设计文档:** `docs/plans/2025-02-24-two-layer-parsing-architecture-design.md`

---

## 现有代码分析

**已实现（在 `rag/app/naive.py`）：**
- `BlockType` 枚举（行 72-81）
- `UniversalBlock` 数据类（行 84-106）
- `extract_lightweight_entities()` 轻量 NER（行 113-164）
- `parse_position_tag()` 位置标签解析（行 175-213）
- `infer_block_type()` 块类型推断（行 216-257）
- `extract_universal_blocks()` 主 Layer A 函数（行 280-341）

**需要新建：**
- `rag/app/criminal/` 目录及插件模块
- Layer B 插件接口和注册表
- 讯问笔录插件
- 起诉意见书插件
- 通用 Chunker

---

## Task 1: 创建 Layer B 插件基础设施

**Files:**
- Create: `rag/app/criminal/__init__.py`
- Create: `rag/app/criminal/plugins/__init__.py`
- Create: `rag/app/criminal/plugins/base.py`
- Create: `tests/unit/rag/app/criminal/test_plugin_base.py`

**Step 1: 写失败测试**

```python
# tests/unit/rag/app/criminal/test_plugin_base.py
import pytest
from rag.app.criminal.plugins.base import DocumentPlugin, Chunk, plugin_registry


class TestDocumentPlugin:
    def test_plugin_base_is_abstract(self):
        """DocumentPlugin 应该是抽象类，不能直接实例化"""
        with pytest.raises(TypeError):
            DocumentPlugin()

    def test_plugin_must_implement_transform(self):
        """插件必须实现 transform 方法"""

        class IncompletePlugin(DocumentPlugin):
            @property
            def doc_type(self) -> str:
                return "test"

        with pytest.raises(TypeError):
            IncompletePlugin()


class TestPluginRegistry:
    def test_register_plugin(self):
        """插件可以注册到注册表"""

        @plugin_registry.register("test_doc")
        class TestPlugin(DocumentPlugin):
            @property
            def doc_type(self) -> str:
                return "test_doc"

            def transform(self, blocks):
                return []

        assert plugin_registry.get("test_doc") is not None

    def test_get_nonexistent_plugin_returns_none(self):
        """获取不存在的插件返回 None"""
        assert plugin_registry.get("nonexistent") is None


class TestChunk:
    def test_chunk_creation(self):
        """Chunk 可以正常创建"""
        chunk = Chunk(
            case_id="case1",
            doc_id="doc1",
            doc_type="test",
            chunk_id="chunk1",
            chunk_type="paragraph",
            text="test content",
            page_range=[1, 1],
            bbox_union=[0, 0, 100, 100],
            block_refs=[{"page_index": 1, "block_id": "b1"}],
        )
        assert chunk.case_id == "case1"
        assert chunk.text == "test content"
```

**Step 2: 运行测试验证失败**

Run: `uv run pytest tests/unit/rag/app/criminal/test_plugin_base.py -v`
Expected: FAIL (模块不存在)

**Step 3: 创建目录结构**

```bash
mkdir -p rag/app/criminal/plugins
mkdir -p tests/unit/rag/app/criminal
```

**Step 4: 实现 Chunk 数据类和插件基类**

```python
# rag/app/criminal/__init__.py
"""Criminal document parsing module."""

from .plugins import plugin_registry, DocumentPlugin, Chunk

__all__ = ["plugin_registry", "DocumentPlugin", "Chunk"]
```

```python
# rag/app/criminal/plugins/__init__.py
"""Layer B plugins for document type-specific chunking."""

from .base import DocumentPlugin, Chunk, plugin_registry

__all__ = ["DocumentPlugin", "Chunk", "plugin_registry"]
```

```python
# rag/app/criminal/plugins/base.py
"""
Layer B plugin infrastructure.

Provides the base class for document type plugins and the plugin registry.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Callable, Type


@dataclass
class Chunk:
    """
    Chunk structure - Layer B output.

    Attributes:
        case_id: Case identifier
        doc_id: Document identifier
        doc_type: Document type (e.g., "interrogation_record")
        chunk_id: Unique chunk identifier
        chunk_type: Type of chunk (paragraph, qa_pair, section, table, image)
        text: Text content
        page_range: [start_page, end_page] (1-indexed)
        bbox_union: Bounding box union [x0, y0, x1, y1]
        block_refs: List of block references [{"page_index": 1, "block_id": "xxx"}]
        metadata: Additional metadata
    """

    case_id: str
    doc_id: str
    doc_type: str
    chunk_id: str
    chunk_type: str
    text: str
    page_range: List[int]
    bbox_union: List[float]
    block_refs: List[Dict[str, Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)


class DocumentPlugin(ABC):
    """
    Base class for document type plugins.

    Each plugin handles a specific document type and transforms
    Block sequences into Chunk sequences.
    """

    @property
    @abstractmethod
    def doc_type(self) -> str:
        """Return the document type this plugin handles."""
        pass

    @property
    def priority(self) -> int:
        """Priority for plugin selection (lower = higher priority)."""
        return 100

    @abstractmethod
    def transform(self, blocks: List[Any]) -> List[Chunk]:
        """
        Transform Block sequence into Chunk sequence.

        Args:
            blocks: List of UniversalBlock objects from Layer A

        Returns:
            List of Chunk objects
        """
        pass


class PluginRegistry:
    """Registry for document type plugins."""

    def __init__(self):
        self._plugins: Dict[str, Type[DocumentPlugin]] = {}

    def register(self, doc_type: str) -> Callable:
        """
        Decorator to register a plugin for a document type.

        Usage:
            @plugin_registry.register("interrogation_record")
            class InterrogationPlugin(DocumentPlugin):
                ...
        """
        def decorator(plugin_class: Type[DocumentPlugin]) -> Type[DocumentPlugin]:
            self._plugins[doc_type] = plugin_class
            return plugin_class
        return decorator

    def get(self, doc_type: str) -> Optional[DocumentPlugin]:
        """Get plugin instance for document type."""
        plugin_class = self._plugins.get(doc_type)
        if plugin_class:
            return plugin_class()
        return None

    def list_plugins(self) -> List[str]:
        """List all registered document types."""
        return list(self._plugins.keys())


# Global plugin registry
plugin_registry = PluginRegistry()
```

**Step 5: 创建测试目录的 `__init__.py`**

```bash
touch tests/unit/rag/app/__init__.py
touch tests/unit/rag/app/criminal/__init__.py
touch tests/unit/rag/__init__.py
touch tests/unit/rag/app/criminal/plugins/__init__.py
```

**Step 6: 运行测试验证通过**

Run: `uv run pytest tests/unit/rag/app/criminal/test_plugin_base.py -v`
Expected: PASS

**Step 7: 提交**

```bash
git add rag/app/criminal/ tests/unit/rag/app/criminal/
git commit -m "feat(criminal): add Layer B plugin infrastructure

- Add DocumentPlugin abstract base class
- Add Chunk dataclass for plugin output
- Add PluginRegistry for plugin management
- Add unit tests for plugin base"
```

---

## Task 2: 实现通用 Chunker（兜底插件）

**Files:**
- Create: `rag/app/criminal/plugins/generic_chunker.py`
- Create: `tests/unit/rag/app/criminal/plugins/test_generic_chunker.py`

**Step 1: 写失败测试**

```python
# tests/unit/rag/app/criminal/plugins/test_generic_chunker.py
import pytest
from rag.app.criminal.plugins.generic_chunker import GenericChunker
from rag.app.naive import UniversalBlock, BlockType


def make_block(text: str, block_type: BlockType = BlockType.PARAGRAPH,
               page_no: int = 0, bbox: tuple = (0, 0, 100, 50)) -> UniversalBlock:
    """Helper to create a UniversalBlock for testing."""
    return UniversalBlock(
        block_type=block_type,
        text=text,
        page_no=page_no,
        bbox=bbox,
    )


class TestGenericChunker:
    def test_chunker_doc_type_is_wildcard(self):
        """通用 Chunker 的 doc_type 应该是 '*'"""
        chunker = GenericChunker()
        assert chunker.doc_type == "*"

    def test_filter_ignored_blocks(self):
        """应该过滤掉 number, header, footer, seal 类型的 block"""
        chunker = GenericChunker()
        blocks = [
            make_block("Page 1", BlockType.FOOTER),
            make_block("Main content here", BlockType.PARAGRAPH),
            make_block("印章", BlockType.SEAL),
            make_block("Another paragraph", BlockType.PARAGRAPH),
        ]
        chunks = chunker.transform(blocks)
        # Should only have chunks from PARAGRAPH blocks
        assert len(chunks) >= 1
        assert "Main content" in chunks[0].text or "Another paragraph" in chunks[0].text

    def test_merge_consecutive_text_blocks(self):
        """连续的 text/paragraph block 应该被合并"""
        chunker = GenericChunker()
        blocks = [
            make_block("First paragraph. ", BlockType.PARAGRAPH),
            make_block("Second paragraph. ", BlockType.PARAGRAPH),
            make_block("Third paragraph.", BlockType.PARAGRAPH),
        ]
        chunks = chunker.transform(blocks)
        assert len(chunks) == 1
        assert "First paragraph" in chunks[0].text
        assert "Second paragraph" in chunks[0].text
        assert "Third paragraph" in chunks[0].text

    def test_paragraph_title_creates_boundary(self):
        """paragraph_title 应该作为切分边界"""
        chunker = GenericChunker()
        blocks = [
            make_block("Content before title", BlockType.PARAGRAPH),
            make_block("Section Title", BlockType.HEADER),  # Using HEADER as section marker
            make_block("Content after title", BlockType.PARAGRAPH),
        ]
        chunks = chunker.transform(blocks)
        # Should create at least 2 chunks due to title boundary
        assert len(chunks) >= 2

    def test_table_block_preserved_intact(self):
        """table block 应该保持完整，独立成 chunk"""
        chunker = GenericChunker()
        blocks = [
            make_block("Before table", BlockType.PARAGRAPH),
            make_block("Table content here", BlockType.TABLE),
            make_block("After table", BlockType.PARAGRAPH),
        ]
        chunks = chunker.transform(blocks)
        # Table should be its own chunk
        table_chunks = [c for c in chunks if c.chunk_type == "table"]
        assert len(table_chunks) == 1
        assert "Table content" in table_chunks[0].text

    def test_chunk_size_control(self):
        """Chunk 大小应该受控制（目标 200-800 字符，最大 1500）"""
        chunker = GenericChunker()
        # Create a very long block
        long_text = "这是一段很长的文本。" * 500  # ~4000 chars
        blocks = [make_block(long_text, BlockType.PARAGRAPH)]
        chunks = chunker.transform(blocks)
        # Should be split due to max size limit
        for chunk in chunks:
            assert len(chunk.text) <= 1500, f"Chunk too long: {len(chunk.text)}"

    def test_empty_blocks_returns_empty_list(self):
        """空 block 列表应该返回空 chunk 列表"""
        chunker = GenericChunker()
        chunks = chunker.transform([])
        assert chunks == []
```

**Step 2: 运行测试验证失败**

Run: `uv run pytest tests/unit/rag/app/criminal/plugins/test_generic_chunker.py -v`
Expected: FAIL (模块不存在)

**Step 3: 实现通用 Chunker**

```python
# rag/app/criminal/plugins/generic_chunker.py
"""
Generic Chunker - Fallback plugin for unsupported document types.

Implements a layered chunking strategy:
1. Filter: Remove ignored block types (number, header, footer, seal)
2. Boundary: Identify chunk boundaries (paragraph_title, semantic patterns)
3. Merge: Combine consecutive text blocks
4. Size Control: Split chunks that exceed max size
"""

import logging
import re
from typing import List, Any

from .base import Chunk, DocumentPlugin
from rag.app.naive import UniversalBlock, BlockType


logger = logging.getLogger(__name__)


# Block types to filter out (not included in chunks)
IGNORED_BLOCK_TYPES = {
    BlockType.FOOTER,
    BlockType.SEAL,
}

# Block types that should be preserved as standalone chunks
PRESERVED_BLOCK_TYPES = {
    BlockType.TABLE,
}

# Maximum chunk size in characters
MAX_CHUNK_SIZE = 1500
# Target minimum chunk size
MIN_CHUNK_SIZE = 50


class GenericChunker(DocumentPlugin):
    """Generic chunker for unsupported document types."""

    @property
    def doc_type(self) -> str:
        return "*"  # Wildcard - handles all types

    @property
    def priority(self) -> int:
        return 1000  # Lowest priority - used as fallback

    def transform(self, blocks: List[UniversalBlock]) -> List[Chunk]:
        """
        Transform blocks into chunks using layered strategy.

        Args:
            blocks: List of UniversalBlock from Layer A

        Returns:
            List of Chunk objects
        """
        if not blocks:
            return []

        chunks = []
        current_chunk_blocks: List[UniversalBlock] = []
        current_text = ""

        for block in blocks:
            # Step 1: Filter ignored blocks
            if block.block_type in IGNORED_BLOCK_TYPES:
                continue

            # Step 2: Handle preserved blocks (table, image)
            if block.block_type in PRESERVED_BLOCK_TYPES:
                # Flush current accumulated blocks first
                if current_chunk_blocks:
                    chunk = self._create_chunk(current_chunk_blocks, current_text.strip())
                    if chunk:
                        chunks.append(chunk)
                    current_chunk_blocks = []
                    current_text = ""

                # Create standalone chunk for preserved block
                chunk = self._create_chunk([block], block.text, chunk_type="table")
                if chunk:
                    chunks.append(chunk)
                continue

            # Step 3: Check for boundary (HEADER acts as section marker)
            if block.block_type == BlockType.HEADER and current_chunk_blocks:
                # Flush current chunk and start new one
                chunk = self._create_chunk(current_chunk_blocks, current_text.strip())
                if chunk:
                    chunks.append(chunk)
                current_chunk_blocks = []
                current_text = ""

            # Step 4: Accumulate text
            block_text = block.text.strip()
            if not block_text:
                continue

            # Check size limit
            if len(current_text) + len(block_text) + 1 > MAX_CHUNK_SIZE:
                # Flush current chunk
                if current_chunk_blocks:
                    chunk = self._create_chunk(current_chunk_blocks, current_text.strip())
                    if chunk:
                        chunks.append(chunk)
                current_chunk_blocks = []
                current_text = ""

            current_chunk_blocks.append(block)
            current_text = current_text + "\n" + block_text if current_text else block_text

        # Flush remaining blocks
        if current_chunk_blocks:
            chunk = self._create_chunk(current_chunk_blocks, current_text.strip())
            if chunk:
                chunks.append(chunk)

        return chunks

    def _create_chunk(
        self,
        blocks: List[UniversalBlock],
        text: str,
        chunk_type: str = "paragraph"
    ) -> Chunk | None:
        """Create a chunk from a list of blocks."""
        if not blocks or not text:
            return None

        # Skip if text too short
        if len(text) < MIN_CHUNK_SIZE:
            return None

        # Calculate page range and bbox union
        pages = sorted(set(b.page_no for b in blocks))
        page_range = [pages[0] + 1, pages[-1] + 1]  # Convert to 1-indexed

        # Calculate bbox union
        x0 = min(b.bbox[0] for b in blocks)
        y0 = min(b.bbox[1] for b in blocks)
        x1 = max(b.bbox[2] for b in blocks)
        y1 = max(b.bbox[3] for b in blocks)

        # Create block refs
        block_refs = [
            {"page_index": b.page_no, "block_id": str(id(b))}
            for b in blocks
        ]

        return Chunk(
            case_id="",  # Will be filled by caller
            doc_id="",   # Will be filled by caller
            doc_type="", # Will be filled by caller
            chunk_id="", # Will be filled by caller
            chunk_type=chunk_type,
            text=text,
            page_range=page_range,
            bbox_union=[x0, y0, x1, y1],
            block_refs=block_refs,
            metadata={"is_generic_chunked": True},
        )
```

**Step 4: 更新 plugins/__init__.py 导出**

```python
# rag/app/criminal/plugins/__init__.py
"""Layer B plugins for document type-specific chunking."""

from .base import DocumentPlugin, Chunk, plugin_registry
from .generic_chunker import GenericChunker

__all__ = ["DocumentPlugin", "Chunk", "plugin_registry", "GenericChunker"]
```

**Step 5: 运行测试验证通过**

Run: `uv run pytest tests/unit/rag/app/criminal/plugins/test_generic_chunker.py -v`
Expected: PASS

**Step 6: 提交**

```bash
git add rag/app/criminal/plugins/generic_chunker.py
git add rag/app/criminal/plugins/__init__.py
git add tests/unit/rag/app/criminal/plugins/test_generic_chunker.py
git commit -m "feat(criminal): add GenericChunker fallback plugin

- Filter ignored block types (footer, seal)
- Preserve table blocks as standalone chunks
- Merge consecutive text blocks
- Enforce chunk size limits (50-1500 chars)
- Add comprehensive unit tests"
```

---

## Task 3: 实现讯问笔录插件

**Files:**
- Create: `rag/app/criminal/plugins/interrogation_plugin.py`
- Create: `tests/unit/rag/app/criminal/plugins/test_interrogation_plugin.py`

**Step 1: 写失败测试**

```python
# tests/unit/rag/app/criminal/plugins/test_interrogation_plugin.py
import pytest
from rag.app.criminal.plugins.interrogation_plugin import InterrogationPlugin
from rag.app.naive import UniversalBlock, BlockType


def make_block(text: str, block_type: BlockType = BlockType.QA_PAIR,
               page_no: int = 0, bbox: tuple = (0, 0, 100, 50)) -> UniversalBlock:
    return UniversalBlock(block_type=block_type, text=text, page_no=page_no, bbox=bbox)


class TestInterrogationPlugin:
    def test_doc_type(self):
        """插件应该处理 interrogation_record 类型"""
        plugin = InterrogationPlugin()
        assert plugin.doc_type == "interrogation_record"

    def test_single_qa_pair(self):
        """单个问答对应该生成一个 qa_pair chunk"""
        plugin = InterrogationPlugin()
        blocks = [
            make_block("问：你叫什么名字？"),
            make_block("答：我叫张三。"),
        ]
        chunks = plugin.transform(blocks)
        assert len(chunks) == 1
        assert chunks[0].chunk_type == "qa_pair"
        assert "问：你叫什么名字？" in chunks[0].text
        assert "答：我叫张三。" in chunks[0].text

    def test_multiple_qa_pairs(self):
        """多个问答对应该生成多个 qa_pair chunks"""
        plugin = InterrogationPlugin()
        blocks = [
            make_block("问：你叫什么名字？"),
            make_block("答：我叫张三。"),
            make_block("问：你住在哪里？"),
            make_block("答：我住在北京。"),
        ]
        chunks = plugin.transform(blocks)
        assert len(chunks) == 2
        assert all(c.chunk_type == "qa_pair" for c in chunks)

    def test_question_with_multiple_answers(self):
        """一个问题多个回答应该合并为一个 qa_pair"""
        plugin = InterrogationPlugin()
        blocks = [
            make_block("问：描述一下经过？"),
            make_block("答：那天我在路上走着，"),
            make_block("答：然后看到了一个钱包。"),
        ]
        chunks = plugin.transform(blocks)
        assert len(chunks) == 1
        assert chunks[0].chunk_type == "qa_pair"
        assert "走着" in chunks[0].text
        assert "钱包" in chunks[0].text

    def test_header_block_as_metadata(self):
        """HEADER block 应该作为元数据，不单独成 chunk"""
        plugin = InterrogationPlugin()
        blocks = [
            make_block("讯问笔录", BlockType.HEADER),
            make_block("问：你是谁？"),
            make_block("答：我是证人。"),
        ]
        chunks = plugin.transform(blocks)
        qa_chunks = [c for c in chunks if c.chunk_type == "qa_pair"]
        assert len(qa_chunks) == 1

    def test_empty_blocks(self):
        """空 block 列表应该返回空 chunk 列表"""
        plugin = InterrogationPlugin()
        chunks = plugin.transform([])
        assert chunks == []
```

**Step 2: 运行测试验证失败**

Run: `uv run pytest tests/unit/rag/app/criminal/plugins/test_interrogation_plugin.py -v`
Expected: FAIL

**Step 3: 实现讯问笔录插件**

```python
# rag/app/criminal/plugins/interrogation_plugin.py
"""
Interrogation Record Plugin - Handles police interrogation transcripts.

Recognizes Q/A patterns and groups them into qa_pair chunks.
"""

import logging
import re
from typing import List

from .base import Chunk, DocumentPlugin
from rag.app.naive import UniversalBlock, BlockType


logger = logging.getLogger(__name__)


class InterrogationPlugin(DocumentPlugin):
    """Plugin for handling interrogation record documents."""

    @property
    def doc_type(self) -> str:
        return "interrogation_record"

    @property
    def priority(self) -> int:
        return 10  # High priority

    def transform(self, blocks: List[UniversalBlock]) -> List[Chunk]:
        """
        Transform blocks into qa_pair chunks.

        Grouping logic:
        - Each "问：" starts a new QA pair
        - Following "答：" blocks are merged with the question
        - Multiple "答：" blocks are concatenated

        Args:
            blocks: List of UniversalBlock from Layer A

        Returns:
            List of Chunk objects with chunk_type="qa_pair"
        """
        if not blocks:
            return []

        chunks = []
        current_qa_blocks: List[UniversalBlock] = []
        current_qa_text = ""
        header_text = ""

        for block in blocks:
            text = block.text.strip()

            # Handle header blocks
            if block.block_type == BlockType.HEADER:
                header_text = text
                continue

            # Skip empty blocks
            if not text:
                continue

            # Check if this is a new question
            if text.startswith(("问：", "问:")):
                # Flush previous QA pair
                if current_qa_blocks:
                    chunk = self._create_qa_chunk(
                        current_qa_blocks,
                        current_qa_text,
                        header_text
                    )
                    if chunk:
                        chunks.append(chunk)

                # Start new QA pair
                current_qa_blocks = [block]
                current_qa_text = text

            elif text.startswith(("答：", "答:")):
                # Add answer to current QA pair
                current_qa_blocks.append(block)
                current_qa_text += "\n" + text

            elif current_qa_blocks:
                # Continuation of previous answer
                current_qa_blocks.append(block)
                current_qa_text += "\n" + text

        # Flush final QA pair
        if current_qa_blocks:
            chunk = self._create_qa_chunk(
                current_qa_blocks,
                current_qa_text,
                header_text
            )
            if chunk:
                chunks.append(chunk)

        return chunks

    def _create_qa_chunk(
        self,
        blocks: List[UniversalBlock],
        text: str,
        header: str = ""
    ) -> Chunk | None:
        """Create a qa_pair chunk from blocks."""
        if not blocks or not text:
            return None

        # Calculate page range
        pages = sorted(set(b.page_no for b in blocks))
        page_range = [pages[0] + 1, pages[-1] + 1]

        # Calculate bbox union
        x0 = min(b.bbox[0] for b in blocks)
        y0 = min(b.bbox[1] for b in blocks)
        x1 = max(b.bbox[2] for b in blocks)
        y1 = max(b.bbox[3] for b in blocks)

        # Create block refs
        block_refs = [
            {"page_index": b.page_no, "block_id": str(id(b))}
            for b in blocks
        ]

        metadata = {}
        if header:
            metadata["doc_title"] = header

        return Chunk(
            case_id="",
            doc_id="",
            doc_type=self.doc_type,
            chunk_id="",
            chunk_type="qa_pair",
            text=text.strip(),
            page_range=page_range,
            bbox_union=[x0, y0, x1, y1],
            block_refs=block_refs,
            metadata=metadata,
        )
```

**Step 4: 更新 plugins/__init__.py**

```python
# rag/app/criminal/plugins/__init__.py
from .base import DocumentPlugin, Chunk, plugin_registry
from .generic_chunker import GenericChunker
from .interrogation_plugin import InterrogationPlugin

__all__ = [
    "DocumentPlugin",
    "Chunk",
    "plugin_registry",
    "GenericChunker",
    "InterrogationPlugin",
]
```

**Step 5: 运行测试验证通过**

Run: `uv run pytest tests/unit/rag/app/criminal/plugins/test_interrogation_plugin.py -v`
Expected: PASS

**Step 6: 提交**

```bash
git add rag/app/criminal/plugins/interrogation_plugin.py
git add rag/app/criminal/plugins/__init__.py
git add tests/unit/rag/app/criminal/plugins/test_interrogation_plugin.py
git commit -m "feat(criminal): add InterrogationPlugin for interrogation records

- Recognize 问/答 pattern for Q/A pairing
- Group question with following answers
- Support multi-line answers
- Add header as chunk metadata
- Add comprehensive unit tests"
```

---

## Task 4: 实现起诉意见书插件

**Files:**
- Create: `rag/app/criminal/plugins/indictment_plugin.py`
- Create: `tests/unit/rag/app/criminal/plugins/test_indictment_plugin.py`

**Step 1: 写失败测试**

```python
# tests/unit/rag/app/criminal/plugins/test_indictment_plugin.py
import pytest
from rag.app.criminal.plugins.indictment_plugin import IndictmentPlugin
from rag.app.naive import UniversalBlock, BlockType


def make_block(text: str, block_type: BlockType = BlockType.PARAGRAPH,
               page_no: int = 0, bbox: tuple = (0, 0, 100, 50)) -> UniversalBlock:
    return UniversalBlock(block_type=block_type, text=text, page_no=page_no, bbox=bbox)


class TestIndictmentPlugin:
    def test_doc_type(self):
        """插件应该处理 indictment_opinion 类型"""
        plugin = IndictmentPlugin()
        assert plugin.doc_type == "indictment_opinion"

    def test_section_detection(self):
        """应该识别关键章节触发词"""
        plugin = IndictmentPlugin()
        blocks = [
            make_block("起诉意见书", BlockType.HEADER),
            make_block("犯罪嫌疑人张三，男，1990年出生。"),
            make_block("经依法侦查查明："),
            make_block("2023年5月，犯罪嫌疑人张三实施了诈骗行为。"),
            make_block("认定上述犯罪事实的证据如下："),
            make_block("1. 受害人陈述"),
            make_block("2. 转账记录"),
        ]
        chunks = plugin.transform(blocks)
        # Should have multiple sections
        assert len(chunks) >= 2

    def test_paragraph_chunking(self):
        """章节内应该按段落切分"""
        plugin = IndictmentPlugin()
        long_text = "这是一段很长的文字。" * 200  # ~1600 chars
        blocks = [
            make_block("经依法侦查查明："),
            make_block(long_text),
        ]
        chunks = plugin.transform(blocks)
        # Should split long text into multiple chunks
        for chunk in chunks:
            if chunk.chunk_type == "paragraph":
                assert len(chunk.text) <= 1500

    def test_empty_blocks(self):
        """空 block 列表应该返回空 chunk 列表"""
        plugin = IndictmentPlugin()
        chunks = plugin.transform([])
        assert chunks == []
```

**Step 2: 运行测试验证失败**

Run: `uv run pytest tests/unit/rag/app/criminal/plugins/test_indictment_plugin.py -v`
Expected: FAIL

**Step 3: 实现起诉意见书插件**

```python
# rag/app/criminal/plugins/indictment_plugin.py
"""
Indictment Opinion Plugin - Handles prosecution opinion documents.

Implements section-based chunking with key trigger phrases.
"""

import logging
import re
from typing import List

from .base import Chunk, DocumentPlugin
from rag.app.naive import UniversalBlock, BlockType


logger = logging.getLogger(__name__)


# Section trigger phrases (start of major sections)
SECTION_TRIGGERS = [
    "经依法侦查查明",
    "认定上述犯罪事实的证据如下",
    "综上所述",
    "此致",
    "检察员",
]

# Maximum chunk size
MAX_CHUNK_SIZE = 1500
MIN_CHUNK_SIZE = 50


class IndictmentPlugin(DocumentPlugin):
    """Plugin for handling indictment opinion documents."""

    @property
    def doc_type(self) -> str:
        return "indictment_opinion"

    @property
    def priority(self) -> int:
        return 10

    def transform(self, blocks: List[UniversalBlock]) -> List[Chunk]:
        """
        Transform blocks into section and paragraph chunks.

        Strategy:
        1. Detect section boundaries using trigger phrases
        2. Within sections, merge consecutive paragraphs
        3. Split if chunk exceeds max size

        Args:
            blocks: List of UniversalBlock from Layer A

        Returns:
            List of Chunk objects
        """
        if not blocks:
            return []

        chunks = []
        current_section_blocks: List[UniversalBlock] = []
        current_text = ""
        current_section_title = ""

        for block in blocks:
            text = block.text.strip()

            # Skip empty blocks
            if not text:
                continue

            # Check for section trigger
            is_section_start = any(text.startswith(trigger) for trigger in SECTION_TRIGGERS)

            if is_section_start:
                # Flush current chunk
                if current_section_blocks and current_text:
                    chunk = self._create_chunk(
                        current_section_blocks,
                        current_text,
                        "section" if current_section_title else "paragraph",
                        current_section_title
                    )
                    if chunk:
                        chunks.append(chunk)

                # Start new section
                current_section_blocks = [block]
                current_text = text
                current_section_title = text[:50]  # Use first 50 chars as title
                continue

            # Check size limit
            if len(current_text) + len(text) + 1 > MAX_CHUNK_SIZE:
                # Flush current chunk
                if current_section_blocks and current_text:
                    chunk = self._create_chunk(
                        current_section_blocks,
                        current_text,
                        "paragraph",
                        current_section_title
                    )
                    if chunk:
                        chunks.append(chunk)
                current_section_blocks = []
                current_text = ""

            # Accumulate
            current_section_blocks.append(block)
            current_text = current_text + "\n" + text if current_text else text

        # Flush remaining
        if current_section_blocks and current_text:
            chunk = self._create_chunk(
                current_section_blocks,
                current_text,
                "section" if current_section_title else "paragraph",
                current_section_title
            )
            if chunk:
                chunks.append(chunk)

        return chunks

    def _create_chunk(
        self,
        blocks: List[UniversalBlock],
        text: str,
        chunk_type: str,
        section_title: str = ""
    ) -> Chunk | None:
        """Create a chunk from blocks."""
        if not blocks or not text:
            return None

        if len(text) < MIN_CHUNK_SIZE:
            return None

        pages = sorted(set(b.page_no for b in blocks))
        page_range = [pages[0] + 1, pages[-1] + 1]

        x0 = min(b.bbox[0] for b in blocks)
        y0 = min(b.bbox[1] for b in blocks)
        x1 = max(b.bbox[2] for b in blocks)
        y1 = max(b.bbox[3] for b in blocks)

        block_refs = [
            {"page_index": b.page_no, "block_id": str(id(b))}
            for b in blocks
        ]

        metadata = {}
        if section_title:
            metadata["section_title"] = section_title

        return Chunk(
            case_id="",
            doc_id="",
            doc_type=self.doc_type,
            chunk_id="",
            chunk_type=chunk_type,
            text=text.strip(),
            page_range=page_range,
            bbox_union=[x0, y0, x1, y1],
            block_refs=block_refs,
            metadata=metadata,
        )
```

**Step 4: 更新 plugins/__init__.py**

```python
# rag/app/criminal/plugins/__init__.py
from .base import DocumentPlugin, Chunk, plugin_registry
from .generic_chunker import GenericChunker
from .interrogation_plugin import InterrogationPlugin
from .indictment_plugin import IndictmentPlugin

__all__ = [
    "DocumentPlugin",
    "Chunk",
    "plugin_registry",
    "GenericChunker",
    "InterrogationPlugin",
    "IndictmentPlugin",
]
```

**Step 5: 运行测试验证通过**

Run: `uv run pytest tests/unit/rag/app/criminal/plugins/test_indictment_plugin.py -v`
Expected: PASS

**Step 6: 提交**

```bash
git add rag/app/criminal/plugins/indictment_plugin.py
git add rag/app/criminal/plugins/__init__.py
git add tests/unit/rag/app/criminal/plugins/test_indictment_plugin.py
git commit -m "feat(criminal): add IndictmentPlugin for prosecution opinions

- Detect section boundaries with trigger phrases
- Section-based chunking strategy
- Size-controlled paragraph splitting
- Add section_title metadata
- Add unit tests"
```

---

## Task 5: 实现插件路由和集成

**Files:**
- Create: `rag/app/criminal/router.py`
- Create: `tests/unit/rag/app/criminal/test_router.py`

**Step 1: 写失败测试**

```python
# tests/unit/rag/app/criminal/test_router.py
import pytest
from rag.app.criminal.router import route_to_plugin, get_chunker_for_doc_type
from rag.app.naive import UniversalBlock, BlockType


def make_block(text: str) -> UniversalBlock:
    return UniversalBlock(
        block_type=BlockType.PARAGRAPH,
        text=text,
        page_no=0,
        bbox=(0, 0, 100, 50),
    )


class TestRouter:
    def test_route_to_interrogation_plugin(self):
        """interrogation_record 类型应该路由到讯问笔录插件"""
        blocks = [make_block("问：你是谁？"), make_block("答：我是张三。")]
        chunks = route_to_plugin(blocks, "interrogation_record")
        assert len(chunks) == 1
        assert chunks[0].chunk_type == "qa_pair"

    def test_route_to_indictment_plugin(self):
        """indictment_opinion 类型应该路由到起诉意见书插件"""
        blocks = [make_block("经依法侦查查明：犯罪嫌疑人张三。")]
        chunks = route_to_plugin(blocks, "indictment_opinion")
        assert len(chunks) >= 1

    def test_route_to_generic_chunker(self):
        """未知类型应该路由到通用 Chunker"""
        blocks = [make_block("Some random content.")]
        chunks = route_to_plugin(blocks, "unknown_type")
        assert len(chunks) >= 1
        assert chunks[0].metadata.get("is_generic_chunked") is True

    def test_get_chunker_for_doc_type(self):
        """get_chunker_for_doc_type 应该返回正确的插件实例"""
        from rag.app.criminal.plugins import InterrogationPlugin, IndictmentPlugin, GenericChunker

        assert isinstance(get_chunker_for_doc_type("interrogation_record"), InterrogationPlugin)
        assert isinstance(get_chunker_for_doc_type("indictment_opinion"), IndictmentPlugin)
        assert isinstance(get_chunker_for_doc_type("unknown"), GenericChunker)
```

**Step 2: 运行测试验证失败**

Run: `uv run pytest tests/unit/rag/app/criminal/test_router.py -v`
Expected: FAIL

**Step 3: 实现路由模块**

```python
# rag/app/criminal/router.py
"""
Plugin router - Routes blocks to appropriate chunker based on doc_type.
"""

from typing import List, Any

from .plugins import (
    DocumentPlugin,
    Chunk,
    plugin_registry,
    GenericChunker,
    InterrogationPlugin,
    IndictmentPlugin,
)
from rag.app.naive import UniversalBlock


# Global generic chunker instance
_generic_chunker = GenericChunker()


def get_chunker_for_doc_type(doc_type: str) -> DocumentPlugin:
    """
    Get the appropriate chunker for a document type.

    Args:
        doc_type: Document type identifier

    Returns:
        DocumentPlugin instance (specific or generic fallback)
    """
    plugin = plugin_registry.get(doc_type)
    if plugin:
        return plugin
    return _generic_chunker


def route_to_plugin(blocks: List[UniversalBlock], doc_type: str) -> List[Chunk]:
    """
    Route blocks to appropriate plugin and return chunks.

    This is the main entry point for Layer B processing.

    Args:
        blocks: List of UniversalBlock from Layer A
        doc_type: Document type (e.g., "interrogation_record")

    Returns:
        List of Chunk objects
    """
    chunker = get_chunker_for_doc_type(doc_type)
    return chunker.transform(blocks)
```

**Step 4: 更新 __init__.py 导出**

```python
# rag/app/criminal/__init__.py
"""Criminal document parsing module."""

from .plugins import plugin_registry, DocumentPlugin, Chunk
from .plugins import GenericChunker, InterrogationPlugin, IndictmentPlugin
from .router import route_to_plugin, get_chunker_for_doc_type

__all__ = [
    "plugin_registry",
    "DocumentPlugin",
    "Chunk",
    "GenericChunker",
    "InterrogationPlugin",
    "IndictmentPlugin",
    "route_to_plugin",
    "get_chunker_for_doc_type",
]
```

**Step 5: 运行测试验证通过**

Run: `uv run pytest tests/unit/rag/app/criminal/test_router.py -v`
Expected: PASS

**Step 6: 运行所有 criminal 模块测试**

Run: `uv run pytest tests/unit/rag/app/criminal/ -v`
Expected: PASS

**Step 7: 提交**

```bash
git add rag/app/criminal/router.py rag/app/criminal/__init__.py
git add tests/unit/rag/app/criminal/test_router.py
git commit -m "feat(criminal): add plugin router for Layer B

- route_to_plugin: main entry point for chunking
- get_chunker_for_doc_type: returns appropriate chunker
- Falls back to GenericChunker for unknown types
- Add comprehensive tests"
```

---

## Task 6: 更新 PRD 文档

**Files:**
- Modify: `docs/刑事案件RAG检索系统prd.md`

**Step 1: 更新 PRD 第 5 章**

在 5.1 总流程后添加 5.2 章节，更新 6.1 和 6.2 章节。

参考设计文档 `docs/plans/2025-02-24-two-layer-parsing-architecture-design.md` 第 7 节的内容。

**Step 2: 提交**

```bash
git add docs/刑事案件RAG检索系统prd.md
git commit -m "docs: update PRD with two-layer parsing architecture

- Add 5.2 section for architecture principles
- Update 6.1 Block Schema with block_type and entities
- Update 6.2 with plugin-based chunking
- Reference design document"
```

---

## Task 7: 集成测试

**Files:**
- Create: `tests/integration/rag/app/criminal/test_integration.py`

**Step 1: 写集成测试**

```python
# tests/integration/rag/app/criminal/test_integration.py
"""
Integration tests for two-layer parsing architecture.
"""

import pytest
from rag.app.criminal import route_to_plugin, InterrogationPlugin, IndictmentPlugin
from rag.app.naive import UniversalBlock, BlockType, extract_universal_blocks


class TestTwoLayerIntegration:
    """Integration tests for the complete two-layer pipeline."""

    def test_interrogation_record_pipeline(self):
        """Test complete pipeline for interrogation record."""
        # Simulated OCR output (sections with position tags)
        sections = [
            ("讯问笔录", "@@1\t0\t100\t0\t50##"),
            ("问：你叫什么名字？", "@@1\t0\t100\t50\t100##"),
            ("答：我叫张三。", "@@1\t0\t100\t100\t150##"),
            ("问：你住在哪里？", "@@1\t0\t100\t150\t200##"),
            ("答：我住在北京。", "@@1\t0\t100\t200\t250##"),
        ]

        # Layer A: Extract universal blocks
        blocks = extract_universal_blocks(sections, doc_type_hint="interrogation_record")
        assert len(blocks) == 5

        # Layer B: Route to plugin
        chunks = route_to_plugin(blocks, "interrogation_record")

        # Verify output
        assert len(chunks) == 2  # Two QA pairs
        assert all(c.chunk_type == "qa_pair" for c in chunks)

    def test_indictment_opinion_pipeline(self):
        """Test complete pipeline for indictment opinion."""
        sections = [
            ("起诉意见书", "@@1\t0\t100\t0\t50##"),
            ("犯罪嫌疑人张三，男，1990年出生。", "@@1\t0\t100\t50\t100##"),
            ("经依法侦查查明：2023年5月，犯罪嫌疑人实施了诈骗。", "@@1\t0\t100\t100\t200##"),
            ("认定上述犯罪事实的证据如下：1. 受害人陈述 2. 转账记录", "@@1\t0\t100\t200\t300##"),
        ]

        # Layer A
        blocks = extract_universal_blocks(sections, doc_type_hint="indictment_opinion")

        # Layer B
        chunks = route_to_plugin(blocks, "indictment_opinion")

        # Verify output
        assert len(chunks) >= 1

    def test_unknown_type_uses_generic_chunker(self):
        """Test that unknown types use generic chunker."""
        sections = [
            ("Some document title", "@@1\t0\t100\t0\t50##"),
            ("Paragraph 1 content here.", "@@1\t0\t100\t50\t100##"),
            ("Paragraph 2 content here.", "@@1\t0\t100\t100\t150##"),
        ]

        blocks = extract_universal_blocks(sections)
        chunks = route_to_plugin(blocks, "unknown_document_type")

        # Should use generic chunker
        assert len(chunks) >= 1
        assert chunks[0].metadata.get("is_generic_chunked") is True
```

**Step 2: 创建目录并运行测试**

```bash
mkdir -p tests/integration/rag/app/criminal
touch tests/integration/rag/__init__.py
touch tests/integration/rag/app/__init__.py
touch tests/integration/rag/app/criminal/__init__.py
```

Run: `uv run pytest tests/integration/rag/app/criminal/test_integration.py -v`
Expected: PASS

**Step 3: 提交**

```bash
git add tests/integration/
git commit -m "test: add integration tests for two-layer parsing

- Test complete pipeline for interrogation records
- Test complete pipeline for indictment opinions
- Test generic chunker fallback"
```

---

## 执行顺序总结

1. **Task 1**: 插件基础设施（基类、注册表、Chunk 数据类）
2. **Task 2**: 通用 Chunker（兜底插件）
3. **Task 3**: 讯问笔录插件
4. **Task 4**: 起诉意见书插件
5. **Task 5**: 路由模块
6. **Task 6**: 更新 PRD 文档
7. **Task 7**: 集成测试

每个 Task 遵循 TDD：先写测试 → 运行确认失败 → 实现 → 运行确认通过 → 提交
