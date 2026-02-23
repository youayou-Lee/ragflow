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
