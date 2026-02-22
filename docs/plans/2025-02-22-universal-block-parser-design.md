# 通用 Block 解析架构设计

## 概述

将现有的"每种文书一套解析方案"架构重构为"Layer A 通用 Block 抽取 + Layer B 文书类型插件"的两层架构。

## 设计目标

1. **统一 Block 层**：所有文书共享通用 Block 结构，保证 PRD 中的硬约束落地
2. **精确定位引用**：每个 chunk 必须有 `page_index + bbox`
3. **禁止无证据断言**：数值必须在证据摘录中逐字出现
4. **可扩展**：新增文书类型只需加插件，不动主链路

## 架构设计

### 两层架构

```
PDF → OCR → sections → Layer A → UniversalBlocks → Layer B Plugin → Chunks
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
| 目录结构 | `criminal/` 目录分离 | 插件独立，方便扩展 |
| Block Type 识别 | 纯规则匹配 | 版面特征规则足够，避免 LLM 不确定性 |
| 迁移策略 | 渐进式 4 阶段迁移 | 每阶段可验证，风险可控 |

## UniversalBlock Schema

```python
# rag/app/criminal/blocks.py

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
    """通用 Block 结构 - Layer A 输出"""

    # 必须字段
    block_type: BlockType
    text: str
    page_no: int
    bbox: tuple[float, float, float, float]  # (x0, y0, x1, y1)

    # 可选字段
    doc_type_hint: Optional[str] = None      # 文书类型弱提示
    entities: Optional[dict] = None          # 轻量 NER 结果

    # entities 结构示例:
    # {
    #     "amounts": [42000, 1500.50, "三万元"],
    #     "dates": ["2024-01-15", "2024年3月"]
    # }
```

## Layer A 核心函数

### extract_universal_blocks()

```python
def extract_universal_blocks(
    sections: list,           # OCR 输出的 sections 列表
    doc_type_hint: str = None # 可选的文书类型提示
) -> list[UniversalBlock]:
    """
    从 OCR 输出提取通用 Block 列表
    """
    blocks = []

    for section in sections:
        # 解析位置标签: @@page\tx0\tx1\ttop\tbottom##text
        page_no, bbox, text = parse_position_tag(section)

        # 识别 block_type
        block_type = infer_block_type(
            text=text,
            position=get_relative_position(section, sections),
            doc_type_hint=doc_type_hint
        )

        # 轻量 NER（只提取数值和日期）
        entities = extract_lightweight_entities(text)

        blocks.append(UniversalBlock(
            block_type=block_type,
            text=text,
            page_no=page_no,
            bbox=bbox,
            doc_type_hint=doc_type_hint,
            entities=entities
        ))

    return blocks
```

### infer_block_type()

```python
def infer_block_type(
    text: str,
    position: str,  # "first", "middle", "last"
    doc_type_hint: str = None
) -> BlockType:
    """基于规则识别 block 类型"""

    # 印章检测
    if "印章" in text or len(text) < 10 and "章" in text:
        return BlockType.SEAL

    # QA 对检测（讯问笔录特征）
    if text.startswith(("问：", "问:", "答：", "答:")):
        return BlockType.QA_PAIR

    # 列表检测
    if re.match(r'^\s*[\d一二三四五六七八九十]+[\.、）]\s', text):
        return BlockType.LIST

    # 头部检测（位置在前且较短）
    if position == "first" and len(text) < 500:
        return BlockType.HEADER

    # 页脚检测
    if position == "last" and len(text) < 100:
        return BlockType.FOOTER

    # 默认为段落
    return BlockType.PARAGRAPH
```

## 轻量 NER

```python
# rag/app/criminal/ner.py

def extract_lightweight_entities(text: str) -> dict:
    """
    轻量 NER：只提取数值和日期
    满足 PRD "禁止无证据断言" 约束
    """
    entities = {"amounts": [], "dates": []}

    # 金额提取
    amount_patterns = [
        r'(\d+(?:,\d{3})*(?:\.\d{1,2})?)\s*[元万]',
        r'([一二三四五六七八九十百千万亿]+)\s*元',
    ]
    for pattern in amount_patterns:
        entities["amounts"].extend(re.findall(pattern, text))

    # 日期提取
    date_patterns = [
        r'(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?)',
        r'(\d{1,2}月\d{1,2}日)',
    ]
    for pattern in date_patterns:
        entities["dates"].extend(re.findall(pattern, text))

    # 去重
    entities["amounts"] = list(set(entities["amounts"]))
    entities["dates"] = list(set(entities["dates"]))

    return entities if (entities["amounts"] or entities["dates"]) else None
```

## Layer B 插件基类

```python
# rag/app/criminal/plugins/base.py

from abc import ABC, abstractmethod

class ParserPlugin(ABC):
    """
    Layer B 插件基类
    输入: Block 序列
    输出: Chunk 序列
    """

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
        """
        处理 Block 序列，生成 chunks

        Returns:
            chunk 列表，每个 chunk 包含:
            - content_with_weight: 文本内容
            - chunk_type: 语义类型
            - page_no: 页码
            - bbox: 定位信息
            - entities: 实体信息
            - metadata: 元数据（可选）
        """
        pass

    def get_header_blocks(self, blocks: list[UniversalBlock]) -> list[UniversalBlock]:
        return [b for b in blocks if b.block_type == BlockType.HEADER]

    def get_qa_blocks(self, blocks: list[UniversalBlock]) -> list[UniversalBlock]:
        return [b for b in blocks if b.block_type == BlockType.QA_PAIR]
```

## Interrogation 插件示例

```python
# rag/app/criminal/plugins/interrogation.py

class InterrogationPlugin(ParserPlugin):
    """讯问笔录解析插件"""

    @property
    def doc_type(self) -> str:
        return "interrogation"

    def process(
        self,
        blocks: list[UniversalBlock],
        doc: dict,
        chat_mdl=None,
        **kwargs
    ) -> list[dict]:
        chunks = []

        # 1. 处理 Header Block
        header_blocks = self.get_header_blocks(blocks)
        if header_blocks:
            chunks.append(self._make_header_chunk(header_blocks))

        # 2. 合并连续的 Q/A blocks 为 QA_PAIR chunks
        qa_chunks = self._merge_qa_pairs(blocks, chat_mdl)
        chunks.extend(qa_chunks)

        return chunks

    def _merge_qa_pairs(self, blocks, chat_mdl=None) -> list[dict]:
        """将连续的 问:/答: blocks 合并为 QA_PAIR chunks"""
        qa_blocks = self.get_qa_blocks(blocks)
        chunks = []
        current_q = None
        current_a_blocks = []

        for block in qa_blocks:
            if block.text.startswith(("问：", "问:")):
                if current_q:
                    chunks.append(self._make_qa_chunk(current_q, current_a_blocks, len(chunks)))
                current_q = block
                current_a_blocks = []
            elif block.text.startswith(("答：", "答:")):
                current_a_blocks.append(block)

        if current_q:
            chunks.append(self._make_qa_chunk(current_q, current_a_blocks, len(chunks)))

        return chunks
```

## 目录结构

```
rag/app/
├── criminal/
│   ├── __init__.py
│   ├── blocks.py              # Layer A: UniversalBlock + extract_universal_blocks()
│   ├── ner.py                 # 轻量 NER: extract_lightweight_entities()
│   └── plugins/
│       ├── __init__.py
│       ├── base.py            # ParserPlugin 基类
│       ├── interrogation.py   # 讯问笔录插件
│       └── indictment.py      # 起诉意见书插件
├── interrogation.py           # 入口，调用 InterrogationPlugin
├── indictment.py              # 入口，调用 IndictmentPlugin
└── naive.py                   # OCR（不变）
```

## 迁移计划

| 阶段 | 任务 | 验收标准 |
|------|------|----------|
| **Phase 1** | 实现 Layer A | `blocks.py` + `ner.py` 单测通过 |
| **Phase 2** | interrogation 迁移 | 现有测试通过，输出兼容 |
| **Phase 3** | indictment 迁移 | 现有测试通过，输出兼容 |
| **Phase 4** | 插件化重构 | 新增文书类型只需加插件 |

### Phase 1 详细任务

- [ ] 创建 rag/app/criminal/ 目录
- [ ] 实现 blocks.py
  - [ ] UniversalBlock dataclass
  - [ ] BlockType 枚举
  - [ ] extract_universal_blocks()
  - [ ] infer_block_type() 规则
  - [ ] parse_position_tag() 解析
- [ ] 实现 ner.py
  - [ ] extract_lightweight_entities()
- [ ] 单元测试
  - [ ] test_blocks.py
  - [ ] test_ner.py

## 参考

- PRD: `docs/刑事案件RAG检索系统prd.md`
- 现有实现: `rag/app/interrogation.py`, `rag/app/indictment.py`
- LLM 元数据提取: `rag/nlp/interrogation_extractor.py`
