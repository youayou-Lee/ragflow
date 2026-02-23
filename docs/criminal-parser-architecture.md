# 刑事文书解析架构文档

## 概述

本文档描述了刑事文书解析的两层架构设计（Layer A + Layer B），用于将不同类型的法律文书转换为可检索的语义块。

## 架构设计

### 两层架构

```
PDF → OCR → sections → Layer A (extract_universal_blocks) → UniversalBlocks
                                                        ↓
                          Layer B Plugin (ParserPlugin) → chunks
```

| 层 | 职责 | 输入 | 输出 |
|---|------|------|------|
| Layer A | 通用 Block 抽取 | OCR sections | UniversalBlock 列表 |
| Layer B | 文书类型深解析 | UniversalBlock 列表 | Chunk 列表 |

### 设计决策

| 决策项 | 选择 | 理由 |
|--------|------|------|
| 架构方案 | 重构 chunk 函数架构 | 最符合 Layer A/B 分层设计 |
| Block vs Chunk | Block=版面单位，Chunk=语义单位 | 职责分离，Layer A 保持简单 |
| NER 时机 | Layer A 只做轻量 NER（数值+日期） | 数值是 PRD 硬约束核心 |
| 定位信息 | 完整 bbox | 现有代码已使用，支持精确定位 |
| Block Type 识别 | 纯规则匹配 | 版面特征规则足够，避免 LLM 不确定性 |
| 迁移策略 | 渐进式 4 阶段迁移 | 每阶段可验证，风险可控 |

## 目录结构

```
rag/app/criminal/
├── __init__.py            # 模块入口，导出核心类
├── blocks.py              # Layer A: UniversalBlock + extract_universal_blocks()
├── ner.py                 # 轻量 NER: extract_lightweight_entities()
└── plugins/
    ├── __init__.py        # 插件模块入口
    ├── base.py            # ParserPlugin 基类
    ├── interrogation.py   # 讯问笔录插件
    └── indictment.py      # 起诉意见书插件

rag/app/
├── interrogation.py       # 讯问笔录入口，使用 Layer A + Layer B
└── indictment.py          # 起诉意见书入口，使用 Layer A + Layer B
```

## Layer A: 通用 Block 抽取

### UniversalBlock Schema

```python
from dataclasses import dataclass
from typing import Optional
from enum import Enum

class BlockType(str, Enum):
    """版面元素类型"""
    HEADER = "header"        # 文书头部（标题、基本信息）
    PARAGRAPH = "paragraph"  # 普通段落
    QA_PAIR = "qa_pair"      # 问答对（问：/答：）
    TABLE = "table"          # 表格
    LIST = "list"            # 列表项
    SEAL = "seal"            # 印章
    FOOTER = "footer"        # 页脚

@dataclass
class UniversalBlock:
    """通用 Block 结构"""
    block_type: BlockType     # 版面类型
    text: str                 # 文本内容
    page_no: int              # 页码（0-indexed）
    bbox: tuple[float, float, float, float]  # (x0, y0, x1, y1)
    doc_type_hint: Optional[str] = None      # 文书类型弱提示
    entities: Optional[dict] = None          # 轻量 NER 结果
```

### extract_universal_blocks()

```python
def extract_universal_blocks(
    sections: list,           # OCR 输出的 sections 列表
    doc_type_hint: str = None # 可选的文书类型提示
) -> list[UniversalBlock]:
    """从 OCR 输出提取通用 Block 列表"""
```

### infer_block_type() 规则

| 优先级 | 类型 | 规则 |
|--------|------|------|
| 1 | SEAL | "印章" in text 或 (len < 10 and "章" in text) |
| 2 | QA_PAIR | 以 "问："/"问:"/"答："/"答:" 开头 |
| 3 | LIST | 匹配编号模式 `^\s*[\d一二三四五六七八九十]+[\.、）]` |
| 4 | HEADER | position == "first" and len < 500 |
| 5 | FOOTER | position == "last" and len < 50 |
| 6 | PARAGRAPH | 默认 |

### 轻量 NER

只提取数值和日期，满足 PRD 硬约束：

```python
def extract_lightweight_entities(text: str) -> Optional[dict]:
    """
    返回: {"amounts": [...], "dates": [...]} 或 None
    """
```

提取模式：
- **金额**: `42000元`, `42,000.00`, `三万元`
- **日期**: `2024-01-15`, `2024年3月15日`, `1月15日`

## Layer B: 文书类型插件

### ParserPlugin 基类

```python
from abc import ABC, abstractmethod

class ParserPlugin(ABC):
    """Layer B 插件基类"""

    @property
    @abstractmethod
    def doc_type(self) -> str:
        """文书类型标识"""
        pass

    @abstractmethod
    def process(
        self,
        blocks: list[UniversalBlock],
        doc: dict,
        chat_mdl=None,
        **kwargs
    ) -> list[dict]:
        """处理 Block 序列，生成 chunks"""
        pass

    # 辅助方法
    def get_header_blocks(self, blocks) -> list[UniversalBlock]: ...
    def get_qa_blocks(self, blocks) -> list[UniversalBlock]: ...
    def get_paragraph_blocks(self, blocks) -> list[UniversalBlock]: ...
```

### InterrogationPlugin (讯问笔录)

**特点**：
- 合并连续的 问:/答: blocks 为 QA_PAIR chunks
- Header blocks 合并为单个 header chunk
- 支持 qa_index 顺序编号

**输出 chunk 类型**：
- `header` - 文书头部
- `qa_pair` - 问答对

### IndictmentPlugin (起诉意见书)

**特点**：
- 基于 section trigger phrases 识别文档结构
- 长段落自动分割（>800 字符）
- 支持 section_trigger 元数据

**Section Triggers**：
```python
SECTION_TRIGGERS = [
    "经依法侦查查明",
    "经依法审查查明",
    "现查明",
    "认定上述犯罪事实的证据如下",
    "综上所述",
    "本院认为",
    "此致",
]
```

**输出 chunk 类型**：
- `section` - 完整章节
- `paragraph` - 长章节分割后的段落

## 如何扩展专用解析方案

本节描述如何为新文书类型设计专用解析方案。

### 第一步：分析文书结构

#### 1.1 收集示例文书

收集 3-5 份同类型的真实文书（脱敏后），分析其共同特征：

```markdown
# 文书分析模板

## 基本信息
- 文书类型：起诉书 / 判决书 / 证据清单 / ...
- 典型长度：X-Y 页
- 结构复杂度：低 / 中 / 高

## 版面特征
- 是否有固定表头？
- 是否有问答结构（问：/答：）？
- 是否有编号列表？
- 是否有表格？
- 是否有印章/签名区？

## 语义结构
- 主要章节有哪些？（如：当事人信息、案件事实、证据清单、法律依据、结论）
- 章节之间是否有固定边界词？（如"经审理查明"、"本院认为"）
- 是否有需要特殊提取的字段？（如案号、金额、日期）

## PRD 约束检查
- 哪些数值需要精确定位？（金额、数量）
- 哪些日期需要提取？
- 哪些内容需要支持"精确定位引用"？
```

#### 1.2 分析示例

**以起诉意见书为例**：

```
文书结构：
├── 头部（标题 + 基本信息）
│   └── "起诉意见书" / 犯罪嫌疑人信息 / 案由
├── 案件事实
│   └── 触发词："经依法侦查查明"
├── 证据清单
│   └── 触发词："认定上述犯罪事实的证据如下"
│   └── 编号项：（一）（二）（三）或 1. 2. 3.
├── 法律依据
│   └── 触发词："综上所述" / "本院认为"
└── 结尾
    └── 触发词："此致"

版面特征：
- 无问答结构
- 有编号列表（证据项）
- 章节边界清晰（有固定触发词）
```

### 第二步：设计解析方案

#### 2.1 评估是否需要专用方案

| 条件 | 需要 Layer B 专用插件 | 可直接用 Layer A |
|------|----------------------|------------------|
| 有固定章节结构 | ✅ | ❌ |
| 需要合并/拆分 blocks | ✅ | ❌ |
| 有特殊 chunk 类型 | ✅ | ❌ |
| 只需要简单分块 | ❌ | ✅ |
| 文书结构简单且无特殊需求 | ❌ | ✅ |

#### 2.2 设计 Chunk 类型

根据文书语义结构定义 chunk 类型：

```python
class MyDocChunkType(StrEnum):
    """文书特定的 chunk 类型"""
    HEADER = "header"           # 文书头部
    PARTY_INFO = "party_info"   # 当事人信息
    FACTS = "facts"             # 案件事实
    EVIDENCE = "evidence"       # 证据清单
    LEGAL_BASIS = "legal_basis" # 法律依据
    CONCLUSION = "conclusion"   # 结论
```

#### 2.3 设计解析规则

**规则类型**：

| 规则类型 | 适用场景 | 示例 |
|----------|----------|------|
| Trigger Phrases | 章节边界识别 | `"经审理查明"` 开始新章节 |
| Pattern Matching | 编号项识别 | `^（\d+）|^(\d+)\.` 匹配证据编号 |
| Block 合并 | 连续相关内容 | 连续 问/答 合并为 QA_PAIR |
| Block 拆分 | 长内容分段 | >800 字符按自然段拆分 |
| 字段提取 | 结构化信息 | 提取案号、金额、日期 |

### 第三步：实现插件

#### 3.1 插件模板

```python
# rag/app/criminal/plugins/my_doc_type.py

import re
from typing import List
from copy import deepcopy

from .base import ParserPlugin
from ..blocks import UniversalBlock, BlockType


# 1. 定义章节触发词
SECTION_TRIGGERS = [
    r"触发词1",
    r"触发词2",
    # ...
]
SECTION_TRIGGER_PATTERN = re.compile("|".join(f"({t})" for t in SECTION_TRIGGERS))

# 2. 定义其他解析规则
MAX_SECTION_LENGTH = 800  # 长章节拆分阈值


class MyDocTypePlugin(ParserPlugin):
    """文书类型解析插件"""

    @property
    def doc_type(self) -> str:
        return "my_doc_type"

    def process(
        self,
        blocks: List[UniversalBlock],
        doc: dict,
        chat_mdl=None,
        **kwargs
    ) -> List[dict]:
        """处理 blocks 生成 chunks"""
        if not blocks:
            return []

        chunks = []

        # 策略1: 按章节边界分组
        sections = self._find_sections(blocks)

        # 策略2: 对每个章节生成 chunk
        for start_idx, end_idx, trigger in sections:
            section_blocks = blocks[start_idx:end_idx]
            section_chunks = self._process_section(section_blocks, doc, trigger)
            chunks.extend(section_chunks)

        return chunks

    def _find_sections(self, blocks: List[UniversalBlock]) -> List[tuple]:
        """根据触发词识别章节边界"""
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

    def _process_section(
        self,
        blocks: List[UniversalBlock],
        doc: dict,
        trigger: str
    ) -> List[dict]:
        """处理单个章节"""
        total_length = sum(len(b.text) for b in blocks)

        # 长章节需要拆分
        if total_length > MAX_SECTION_LENGTH:
            return self._split_section(blocks, doc, trigger)

        return [self._make_chunk(blocks, doc, trigger, "section")]

    def _make_chunk(
        self,
        blocks: List[UniversalBlock],
        doc: dict,
        trigger: str,
        chunk_type: str
    ) -> dict:
        """创建 chunk"""
        d = deepcopy(doc)
        d["chunk_type"] = chunk_type
        d["section_trigger"] = trigger

        # 合并文本
        d["content_with_weight"] = "\n".join(b.text for b in blocks)

        # 位置信息（取第一个 block）
        d["page_no"] = blocks[0].page_no
        d["bbox"] = list(blocks[0].bbox)

        # 合并实体
        entities = self._merge_entities(blocks)
        if entities:
            d["entities"] = entities

        return d

    def _merge_entities(self, blocks: List[UniversalBlock]) -> dict:
        """合并多个 block 的实体"""
        merged = {"amounts": [], "dates": []}
        for block in blocks:
            if block.entities:
                merged["amounts"].extend(block.entities.get("amounts", []))
                merged["dates"].extend(block.entities.get("dates", []))
        merged["amounts"] = list(set(merged["amounts"]))
        merged["dates"] = list(set(merged["dates"]))
        return merged if (merged["amounts"] or merged["dates"]) else {}
```

#### 3.2 入口函数模板

```python
# rag/app/my_doc_type.py

from rag.app.criminal.blocks import extract_universal_blocks
from rag.app.criminal.plugins.my_doc_type import MyDocTypePlugin
from rag.nlp import rag_tokenizer, tokenize, add_bbox_union, add_page_range, add_block_refs
import re

def chunk(filename, binary=None, from_page=0, to_page=100000, lang="Chinese", callback=None, **kwargs):
    """
    文书类型解析入口

    Args:
        filename: 文件路径
        binary: 二进制内容
        from_page: 起始页
        to_page: 结束页
        lang: 语言
        callback: 进度回调

    Returns:
        list: chunk 列表
    """
    eng = lang.lower() == "english"

    # 基础文档信息
    doc = {
        "docnm_kwd": filename,
        "title_tks": rag_tokenizer.tokenize(re.sub(r"\.[a-zA-Z]+$", "", filename))
    }

    # 检查文件格式
    if not re.search(r"\.pdf$", filename, re.IGNORECASE):
        raise NotImplementedError("仅支持 PDF 格式")

    callback(0.1, "开始解析...")

    # Step 1: OCR
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

    callback(0.4, "OCR 完成")

    # Step 2: Layer A - 通用 Block 抽取
    blocks = extract_universal_blocks(sections, "my_doc_type")
    callback(0.6, f"提取 {len(blocks)} 个 blocks")

    # Step 3: Layer B - 专用解析
    plugin = MyDocTypePlugin()
    chunks = plugin.process(blocks, doc, chat_mdl=kwargs.get("chat_mdl"))
    callback(0.8, f"生成 {len(chunks)} 个 chunks")

    # Step 4: 添加 RAG 所需字段
    for c in chunks:
        content = c.get("content_with_weight", "")
        tokenize(c, content, eng)
        add_bbox_union(c)
        add_page_range(c)
        add_block_refs(c)

    callback(1.0, f"完成，共 {len(chunks)} 个 chunks")
    return chunks
```

### 第四步：测试验证

#### 4.1 单元测试

```python
# test/unit/test_my_doc_type_plugin.py

import pytest
from rag.app.criminal.plugins.my_doc_type import MyDocTypePlugin
from rag.app.criminal.blocks import UniversalBlock, BlockType


class TestMyDocTypePlugin:
    def test_doc_type(self):
        plugin = MyDocTypePlugin()
        assert plugin.doc_type == "my_doc_type"

    def test_process_empty(self):
        plugin = MyDocTypePlugin()
        chunks = plugin.process([], {})
        assert chunks == []

    def test_section_boundaries(self):
        """测试章节边界识别"""
        plugin = MyDocTypePlugin()
        blocks = [
            UniversalBlock(BlockType.HEADER, "文书标题", 0, (0, 0, 100, 50)),
            UniversalBlock(BlockType.PARAGRAPH, "触发词1 后的内容", 0, (0, 50, 100, 100)),
        ]
        chunks = plugin.process(blocks, {})
        assert len(chunks) >= 1

    def test_entities_preserved(self):
        """测试实体保留"""
        plugin = MyDocTypePlugin()
        blocks = [
            UniversalBlock(
                BlockType.PARAGRAPH,
                "涉案金额42000元，日期2024年1月15日",
                0, (0, 0, 100, 50),
                entities={"amounts": ["42000"], "dates": ["2024年1月15日"]}
            ),
        ]
        chunks = plugin.process(blocks, {})
        assert chunks[0]["entities"] is not None
```

#### 4.2 集成测试

```python
# test/unit/test_my_doc_type_integration.py

from rag.app.criminal.blocks import extract_universal_blocks
from rag.app.criminal.plugins.my_doc_type import MyDocTypePlugin


def test_full_pipeline():
    """测试完整流水线"""
    sections = [
        ("文书标题", "@@1\t10.0\t200.0\t20.0\t40.0##"),
        ("正常内容段落", "@@1\t10.0\t200.0\t50.0\t70.0##"),
        ("触发词1后的内容", "@@1\t10.0\t200.0\t80.0\t100.0##"),
    ]

    # Layer A
    blocks = extract_universal_blocks(sections, "my_doc_type")

    # Layer B
    plugin = MyDocTypePlugin()
    chunks = plugin.process(blocks, {})

    assert len(chunks) >= 1
    assert "section_trigger" in chunks[0]
```

#### 4.3 真实文档测试

```bash
# 使用真实 PDF 测试
uv run python -c "
from rag.app.my_doc_type import chunk

def callback(prog=None, msg=''):
    print(f'[{prog:.0%}] {msg}' if prog else msg)

result = chunk('path/to/real_document.pdf', callback=callback)
print(f'Total chunks: {len(result)}')
for i, c in enumerate(result[:5]):
    print(f'[{i}] {c.get(\"chunk_type\")}: {c.get(\"content_with_weight\", \"\")[:50]}...')
"
```

### 第五步：文档和提交

1. 更新本文档的"目录结构"部分
2. 更新本文档的"测试文件"部分
3. 提交代码：
   ```bash
   git add rag/app/criminal/plugins/my_doc_type.py \
           rag/app/my_doc_type.py \
           test/unit/test_my_doc_type_plugin.py \
           test/unit/test_my_doc_type_integration.py

   git commit -m "feat(criminal): add MyDocType parser plugin

   - Implement MyDocTypePlugin for Layer B parsing
   - Add chunk() entry function
   - Add unit and integration tests
   - Support section-based parsing with trigger phrases"
   ```

---

## 快速新增文书类型（简化版）

如果文书结构简单，不需要复杂的章节识别：

```python
# rag/app/criminal/plugins/simple_doc.py

from .base import ParserPlugin
from ..blocks import UniversalBlock

class SimpleDocPlugin(ParserPlugin):
    @property
    def doc_type(self) -> str:
        return "simple_doc"

    def process(self, blocks, doc, **kwargs):
        """简单处理：每个 block 生成一个 chunk"""
        return [
            {
                "chunk_type": "paragraph",
                "content_with_weight": b.text,
                "page_no": b.page_no,
                "bbox": list(b.bbox),
                "entities": b.entities or {},
                **doc
            }
            for b in blocks
        ]
```

---

## 如何新增文书类型

### 1. 实现 ParserPlugin

```python
# rag/app/criminal/plugins/my_doc_type.py

from .base import ParserPlugin
from ..blocks import UniversalBlock, BlockType

class MyDocTypePlugin(ParserPlugin):
    @property
    def doc_type(self) -> str:
        return "my_doc_type"

    def process(self, blocks, doc, chat_mdl=None, **kwargs):
        chunks = []

        # 你的处理逻辑
        for block in blocks:
            if block.block_type == BlockType.HEADER:
                chunk = self._make_header_chunk(block, doc)
                chunks.append(chunk)
            # ...

        return chunks
```

### 2. 创建入口函数

```python
# rag/app/my_doc_type.py

from rag.app.criminal.blocks import extract_universal_blocks
from rag.app.criminal.plugins.my_doc_type import MyDocTypePlugin
from rag.nlp import rag_tokenizer, tokenize, add_bbox_union, add_page_range, add_block_refs

def chunk(filename, binary=None, from_page=0, to_page=100000, lang="Chinese", callback=None, **kwargs):
    eng = lang.lower() == "english"
    doc = {"docnm_kwd": filename, "title_tks": rag_tokenizer.tokenize(...)}

    # Step 1: OCR
    from rag.app.naive import by_paddleocr
    sections, tables, pdf_parser = by_paddleocr(...)

    # Step 2: Layer A
    blocks = extract_universal_blocks(sections, "my_doc_type")

    # Step 3: Layer B
    plugin = MyDocTypePlugin()
    chunks = plugin.process(blocks, doc)

    # Step 4: 添加 RAG 所需字段
    for c in chunks:
        tokenize(c, c.get("content_with_weight", ""), eng)
        add_bbox_union(c)
        add_page_range(c)
        add_block_refs(c)

    return chunks
```

## 测试

### 测试文件

```
test/unit/
├── test_blocks.py                    # Layer A 测试
├── test_ner.py                       # NER 测试
├── test_plugins_base.py              # 插件基类测试
├── test_interrogation_plugin.py      # 讯问笔录插件测试
├── test_interrogation_integration.py # 讯问笔录集成测试
├── test_interrogation_chunker.py     # 讯问笔录向后兼容测试
├── test_indictment_plugin.py         # 起诉意见书插件测试
├── test_indictment_integration.py    # 起诉意见书集成测试
└── test_indictment_chunker.py        # 起诉意见书向后兼容测试
```

### 运行测试

```bash
# 运行所有 criminal 模块测试
uv run pytest test/unit/test_blocks.py test/unit/test_ner.py test/unit/test_plugins_base.py \
    test/unit/test_interrogation_plugin.py test/unit/test_interrogation_integration.py \
    test/unit/test_indictment_plugin.py test/unit/test_indictment_integration.py \
    test/unit/test_interrogation_chunker.py test/unit/test_indictment_chunker.py -v
```

## 相关文档

- [设计文档](plans/2025-02-22-universal-block-parser-design.md)
- [Phase 1 实现计划](plans/2025-02-22-universal-block-parser-impl.md)
- [Phase 2 实现计划](plans/2025-02-22-interrogation-migration-impl.md)
- [Phase 3 实现计划](plans/2025-02-22-indictment-migration-impl.md)

## 变更历史

| 日期 | 版本 | 变更内容 |
|------|------|----------|
| 2025-02-22 | 1.0 | 初始版本，完成 Phase 1-3 迁移 |
