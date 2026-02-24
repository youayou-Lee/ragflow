# 两层解析架构设计文档

> 创建日期：2025-02-24
> 状态：已确认
> 关联PRD：docs/刑事案件RAG检索系统prd.md

## 1. 背景

当前PRD的设计是每种文书类型（讯问笔录、起诉意见书）有独立的解析策略，这会导致：
- 每增加一种文书就要写一套完整的解析逻辑
- 主链路与文书类型强耦合
- 维护成本随文书类型数量线性增长

## 2. 设计目标

- **解耦**：将通用处理与文书特定处理分离
- **可扩展**：新增文书类型只需加插件，不动主链路
- **兜底**：无专用插件时也能保证基本检索能力

## 3. 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         处理流水线                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   PDF ──► PaddleOCR API ──► Layer A (通用Block抽取)             │
│                                 │                               │
│                                 ▼                               │
│                         ┌──────────────┐                        │
│                         │ doc_type     │  ◄── 用户手动指定       │
│                         │ (文书类型)    │                        │
│                         └──────┬───────┘                        │
│                                │                                │
│              ┌─────────────────┼─────────────────┐              │
│              ▼                 ▼                 ▼              │
│      ┌─────────────┐   ┌─────────────┐   ┌─────────────┐        │
│      │ 讯问笔录插件 │   │起诉意见书插件│   │ 通用Chunker │        │
│      │  (Layer B)  │   │  (Layer B)  │   │   (兜底)    │        │
│      └──────┬──────┘   └──────┬──────┘   └──────┬──────┘        │
│              │                 │                 │              │
│              └─────────────────┼─────────────────┘              │
│                                ▼                                │
│                           Chunks                                │
│                                │                                │
│                                ▼                                │
│                     索引构建（向量/关键词）                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 4. Layer A - 通用Block抽取

### 4.1 职责

保证"精确定位引用"和"禁止无证据断言"的硬约束落地。

### 4.2 Block Schema

```json
{
  "case_id": "string",
  "doc_id": "string",
  "doc_type": "interrogation_record | indictment_opinion | judgment | evidence_volume | ...",
  "page_index": 1,
  "page_width": 595,
  "page_height": 842,
  "block_id": "string",
  "block_order": 0,
  "block_type": "text | doc_title | paragraph_title | table | image | list | header | footer | seal | number",
  "text": "string",
  "bbox": [x0, y0, x1, y1],
  "polygon": [[x0,y0], [x1,y0], [x1,y1], [x0,y1]],
  "entities": {
    "amounts": ["50000元", "人民币叁万元整"],
    "dates": ["2023年5月12日", "2023.05.12"]
  }
}
```

### 4.3 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `block_type` | string | 复用PaddleOCR输出的版面类型 |
| `entities.amounts` | array | 轻量NER抽取的金额（规则实现） |
| `entities.dates` | array | 轻量NER抽取的时间（规则实现） |

### 4.4 处理逻辑

1. 接收 PaddleOCR API 输出
2. 标准化为统一 Block Schema
3. 执行轻量 NER（规则抽取金额、时间）
4. 输出 Block 序列

### 4.5 设计决策

- **block_type 来源**：直接复用 PaddleOCR 版面类型，不做额外语义分类
- **NER 范围**：只做金额和时间抽取，规则实现，不依赖复杂模型
- **文书类型识别**：MVP阶段由用户手动指定，自动识别作为后续增强

## 5. Layer B - 文书类型插件层

### 5.1 职责

Block 序列 → Chunk 序列（可扩展、可插拔）

### 5.2 插件接口规范

```python
from abc import ABC, abstractmethod
from typing import List

class Block:
    """Block 数据结构"""
    case_id: str
    doc_id: str
    doc_type: str
    page_index: int
    page_width: int
    page_height: int
    block_id: str
    block_order: int
    block_type: str
    text: str
    bbox: List[int]
    polygon: List[List[int]]
    entities: dict

class Chunk:
    """Chunk 数据结构"""
    case_id: str
    doc_id: str
    doc_type: str
    chunk_id: str
    chunk_type: str
    text: str
    page_range: List[int]
    bbox_union: List[int]
    block_refs: List[dict]
    metadata: dict

class DocumentPlugin(ABC):
    """文书类型插件基类"""

    @property
    @abstractmethod
    def doc_type(self) -> str:
        """支持的文书类型"""
        pass

    @property
    def priority(self) -> int:
        """优先级（数字越小越优先），默认100"""
        return 100

    @abstractmethod
    def transform(self, blocks: List[Block]) -> List[Chunk]:
        """将Block序列转换为Chunk序列"""
        pass
```

### 5.3 插件路由逻辑

```python
def route_to_plugin(blocks: List[Block], doc_type: str) -> List[Chunk]:
    # 1. 查找匹配插件
    plugin = plugin_registry.get(doc_type)

    # 2. 无匹配则走通用Chunker
    if plugin is None:
        plugin = generic_chunker

    # 3. 执行转换
    return plugin.transform(blocks)
```

### 5.4 MVP 插件清单

| 插件 | doc_type | 核心逻辑 |
|------|----------|----------|
| 讯问笔录插件 | `interrogation_record` | 识别"问/答"模式，归并为 `qa_pair` Chunk |
| 起诉意见书插件 | `indictment_opinion` | 按章节触发词切分 `section`，段落切 `paragraph` |
| 通用Chunker | `*` (兜底) | 分层切分：过滤→边界识别→合并→大小控制 |

### 5.5 扩展方式

新增文书类型只需：

```python
@plugin_registry.register("judgment")
class JudgmentPlugin(DocumentPlugin):
    doc_type = "judgment"

    def transform(self, blocks: List[Block]) -> List[Chunk]:
        # 判决书专用逻辑...
        pass
```

## 6. 通用 Chunker（兜底插件）

### 6.1 职责

为无专用插件的文书提供基础 Chunk 生成能力。

### 6.2 处理流程

```
Block序列 ──► [1.过滤] ──► [2.边界识别] ──► [3.合并] ──► [4.大小控制] ──► Chunk序列
```

### 6.3 Block 过滤策略

| block_type | 处理 | 原因 |
|------------|------|------|
| `text` | ✅ 保留 | 主要内容 |
| `paragraph_title` | ✅ 保留 | 作为边界标志 |
| `table` | ✅ 保留 | 独立成 Chunk |
| `image` | ✅ 保留 | 独立成 Chunk |
| `list` | ✅ 保留 | 合并到相邻段落 |
| `doc_title` | ⚠️ 元数据 | 不单独成 Chunk，作为 Chunk 元信息 |
| `number` | ❌ 过滤 | 页码、编号 |
| `header` | ❌ 过滤 | 页眉 |
| `footer` | ❌ 过滤 | 页脚 |
| `seal` | ❌ 过滤 | 印章标记 |

### 6.4 边界识别规则

```python
BOUNDARY_PATTERNS = {
    # 段落标题作为强边界
    "paragraph_title": StrongBoundary,

    # 语义模式作为弱边界
    "semantic": [
        r"^第[一二三四五六七八九十\d]+[条章节]",  # 法律条款
        r"^[一二三四五六七八九十]+、",            # 列表项
        r"^(\d+)[\.、]",                         # 数字编号
        r"^(经|现|综上|据此|据此认定)",           # 常见起始词
    ]
}
```

### 6.5 合并策略

- 连续 `text` block 合并（保留换行分隔）
- 遇到 `paragraph_title` 分段，新 Chunk 开始

### 6.6 Chunk 大小控制

| 参数 | 值 | 说明 |
|------|-----|------|
| 目标大小 | 200-800 字符 | 平衡检索精度与上下文完整性 |
| 最大限制 | 1500 字符 | 超过则强制切分 |
| 最小限制 | 50 字符 | 过小则合并到相邻 Chunk |

### 6.7 通用 Chunk Schema

```json
{
  "case_id": "string",
  "doc_id": "string",
  "doc_type": "string",
  "chunk_id": "string",
  "chunk_type": "paragraph | section | table | image",
  "text": "string",
  "page_range": [1, 2],
  "bbox_union": [x0, y0, x1, y1],
  "block_refs": [{"page_index": 1, "block_id": "xxx"}],
  "metadata": {
    "title": "段落标题（如有）",
    "is_generic_chunked": true
  }
}
```

## 7. 与现有 PRD 的对接

### 7.1 需要更新的章节

| PRD 章节 | 变更内容 |
|----------|----------|
| 5.1 总流程 | 更新为两层架构流程图 |
| 6.1 文书解析与 Block 入库 | 更新 Block Schema，增加 `block_type` 和 `entities` |
| 6.2 Chunk 生成 | 重构为插件化架构，增加通用 Chunker 说明 |
| 1.3 范围与前提 | 增加"架构原则：两层解析，插件扩展" |

### 7.2 新增章节建议

在 PRD 中增加 5.2 章节：

```markdown
### 5.2 解析架构原则

#### 两层架构
- **Layer A（通用Block层）**：所有文书统一处理，保证定位引用落地
- **Layer B（文书插件层）**：按文书类型扩展，只对P0文书深度解析

#### 扩展方式
新增文书类型只需：
1. 实现 `DocumentPlugin` 接口
2. 注册到 `plugin_registry`
3. 主链路无需修改

#### 兜底策略
无专用插件时自动走通用 Chunker，保证所有文书可检索
```

### 7.3 Block Schema 变更对比

```diff
  {
    "case_id": "string",
    "doc_id": "string",
    "doc_type": "...",
    "page_index": 1,
    "page_width": 0,
    "page_height": 0,
    "block_id": 0,
    "block_order": 0,
-   "label": "text | number | header | footer | other",
+   "block_type": "text | doc_title | paragraph_title | table | image | list | header | footer | seal | number",
    "text": "string",
    "bbox": [0, 0, 0, 0],
    "polygon": [[0,0],[0,0],[0,0],[0,0]],
+   "entities": {
+     "amounts": [],
+     "dates": []
+   }
  }
```

## 8. 设计决策记录

| 决策点 | 选项 | 选择 | 理由 |
|--------|------|------|------|
| Layer A block_type 来源 | A) OCR版面级 B) 语义级 | A | 复用PaddleOCR输出，不增加复杂度 |
| NER 执行时机 | A) Layer A内置 B) 推迟到检索 C) 可选增强 | A | 金额时间是核心约束，规则实现简单 |
| 文书类型识别 | A) 自动识别 B) Layer A推断 C) 用户指定 | C | MVP最简单，后续迭代 |
| Layer B 职责 | A) Block→Chunk B) 增强+Chunk C) 只抽取字段 | A | 职责单一，插件纯粹 |
| 无插件处理 | A) 通用Chunker B) 拒绝 C) 只存Block | A | 保证所有文书可检索 |
| 通用Chunker策略 | A) 固定长度 B) 段落优先 C) Block直接映射 | B | 利用block_type信息，符合语义 |
