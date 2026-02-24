
# 法律智能问答系统（刑事案卷 RAG）- 产品需求文档（MVP）

## 0. 一句话定义
面向刑事案件扫描版案卷 PDF，构建“可检索、可追溯引用、可强制校验”的 RAG 问答系统：**任何结论必须被原文证据支持，并能点击跳转到 PDF 页内高亮位置**。

---

## 1. 背景与目标

### 1.1 为什么要做
律师/检察官在案卷分析中高频进行“找证据—核对原文—复述结论”，人工查找成本高且容易遗漏。

### 1.2 解决的问题（MVP）
- 在大量案卷中快速定位与问题相关的原文证据
- 输出结构化答案，并提供可核验引用（页码 + 坐标 + 摘录）
- 避免模型编造：无证据则明确“材料未显示”

### 1.3 范围与前提（强约束）
- 输入文件类型：**扫描型 PDF**
- OCR/版面解析：使用 **PaddleOCR API**（RAGFlow 已集成，前端配置 API Key）
- 支持文书类型（MVP）：
  1) 讯问/询问笔录
  2) 起诉意见书

---

## 2. 成功标准（可量化指标）

> 注意：以下指标仅在“金标题库规模满足要求”时才具有意义（见第 8 章）。

| 指标 | 阈值 | 定义 |
|---|---|---|
| Citation Precision | ≥ 98% | 引用摘录 **必须包含** 支撑该结论的事实/数值（抽检+自动校验结合） |
| Numeric/Date Grounding | = 100% | 任何答案中出现的金额/日期/浓度等数值，必须在证据摘录中 **逐字出现**（严格匹配） |
| Retrieval Recall@20 | ≥ 95% | 金标问题的关键证据 chunk 在 Top-20 检索结果中出现 |
| OOD “材料未显示” 触发正确率 | ≥ 95% | 对题库外问题不乱答：应答为“材料未显示/引用不足” |

---

## 3. 目标用户与使用场景

| 用户 | 场景 | 核心诉求 |
|---|---|---|
| 律师 | 案件研究、会见/庭前准备 | 快速找到可引用原文证据 |
| 检察官 | 证据核查、审查起诉 | 证据定位 + 结论可核验 |
| 律师团队 | 协作办案 | 统一引用口径、减少遗漏 |

---

## 4. 用户故事（MVP）
1) 用户上传一份扫描 PDF 案卷，系统完成解析与入库。
2) 用户提出问题（单轮），系统返回：结论 + 证据引用 + 推理说明 + 材料缺口 + 检索原始片段。
3) 用户点击引用，可跳转到对应 PDF 页并高亮证据位置。
4) 若无证据或引用不充分，系统强制返回“材料未显示/引用不足”，不输出结论。

---

## 5. 系统模块与核心流程

### 5.1 总流程
**PDF -> PaddleOCR API 解析 -> Layer A (通用Block抽取) -> Layer B (文书插件Chunking) -> 索引构建（向量/关键词）-> 检索 -> LLM API 生成答案 -> Answer Gate 校验 -> 返回结果（可跳转高亮）**

### 5.2 解析架构原则

#### 两层架构
- **Layer A（通用Block层）**：所有文书统一处理，输出标准化 Block（含位置、类型、轻量 NER），保证"精确定位引用"和"禁止无证据断言"的硬约束落地
- **Layer B（文书插件层）**：按文书类型扩展，只对 P0 文书深度解析，无专用插件时走通用 Chunker 兜底

#### 扩展方式
新增文书类型只需：
1. 实现 `DocumentPlugin` 接口
2. 注册到 `plugin_registry`
3. 主链路无需修改

#### 兜底策略
无专用插件时自动走通用 Chunker，保证所有文书可检索

---

## 6. 功能需求（MVP）

### 6.1 文书解析与 Block 入库（Ingestion）

#### 6.1.1 输入
- 扫描型 PDF（单文件）
- 元信息：`case_id`、`doc_type`（手动选择或规则识别）

#### 6.1.2 输出（Block 层：不可丢失的原始事实层）
将 PaddleOCR API 输出的每个版面块作为 Block 保存（不做"智能合并"导致信息丢失）。

**Block Schema（统一数据契约）**
```json
{
  "case_id": "string",
  "doc_id": "string",
  "doc_type": "indictment_opinion | interrogation_record | judgment | evidence_volume | ...",
  "page_index": 1,
  "page_width": 595,
  "page_height": 842,
  "block_id": "string",
  "block_order": 0,
  "block_type": "text | doc_title | paragraph_title | table | image | list | header | footer | seal | number",
  "text": "string",
  "bbox": [x0, y0, x1, y1],
  "polygon": [[x0,y0],[x1,y0],[x1,y1],[x0,y1]],
  "entities": {
    "amounts": ["50000元", "人民币叁万元整"],
    "dates": ["2023年5月12日", "2023.05.12"]
  }
}
```

> **字段说明**：
> - `block_type`：复用 PaddleOCR 输出的版面类型，不做额外语义分类
> - `entities`：轻量 NER 结果，仅包含金额和时间（规则实现）

#### 6.1.3 验收标准
- Given：上传扫描 PDF
- When：解析完成
- Then：
  - 每页至少输出一组 Block（按 `block_order` 可稳定排序）
  - 每个 Block 必须包含 `page_index + bbox/polygon + text`
  - 页面尺寸 `page_width/page_height` 必须可用于前端坐标映射

---

### 6.2 Chunk 生成（检索单位层）

> Chunk 是**检索与引用的最小单位**。Chunk 必须能回溯到 Block（用于高亮与校验）。

#### 6.2.0 插件化架构

Chunk 生成采用**插件化架构**，根据 `doc_type` 路由到对应插件：

```
Layer A (Blocks) -> 插件路由 -> Layer B 插件 (Chunks)
                              ├─ InterrogationPlugin (讯问笔录)
                              ├─ IndictmentPlugin (起诉意见书)
                              └─ GenericChunker (兜底)
```

**插件接口**：
```python
class DocumentPlugin(ABC):
    @property
    @abstractmethod
    def doc_type(self) -> str: ...

    @abstractmethod
    def transform(self, blocks: List[Block]) -> List[Chunk]: ...
```

#### 6.2.1 Chunk Schema
```json
{
  "case_id": "string",
  "doc_id": "string",
  "doc_type": "indictment_opinion | interrogation_record",
  "chunk_id": "string",
  "chunk_type": "qa_pair | paragraph | evidence_item | section",
  "text": "string",
  "page_range": [1, 2],
  "bbox_union": [0,0,0,0],
  "block_refs": [{"page_index":1,"block_id":2},{"page_index":1,"block_id":3}],
  "anchors": {
    "text_hash": "string",
    "excerpt_head": "string"
  }
}
```

#### 6.2.2 讯问/询问笔录 Chunking（规则法，MVP）
- 识别 `问：` 与 `答：` 前缀
- 以“1 个问 + 其后的 1..n 个答”为一个 `qa_pair` chunk
- `bbox_union` 为该 QA 相关 blocks 的 bbox 合并

**验收**
- Given：一份讯问/询问笔录 PDF
- Then：能输出 QA 对 chunk；每个 chunk 可定位到页码+坐标

#### 6.2.3 起诉意见书 Chunking（段落/小节优先，MVP）
- 基于明显小节触发词（如“经依法侦查查明”“认定上述犯罪事实的证据如下”“综上所述”等）切分为 section
- section 内按长度（建议 300~800 字）进一步切 paragraph chunk
- 证据列表（1、2、3…）可额外生成 `evidence_item` chunk（可选）

**验收**
- Given：一份起诉意见书 PDF
- Then：输出 section/paragraph chunk；每个 chunk 可定位到页码+坐标

> 备注：起诉意见书的“字段级结构抽取”（姓名/籍贯/职业等）不作为 MVP 强制要求，可作为后续增强。

---

### 6.3 知识库构建与检索（Indexing & Retrieval）

#### 6.3.1 索引
- 向量索引：以 **Chunk.text** 为输入生成 embedding
- 关键词索引（BM25/倒排）：以 **Chunk.text** 为输入
- 过滤字段：`case_id`、`doc_type`、`doc_id`

#### 6.3.2 检索策略（MVP：混合检索）
- hybrid：BM25 TopN + Vector TopN 合并去重
- 结果必须返回：
  - `chunk_id`
  - `chunk.text`
  - `page_range + bbox_union`
  - `block_refs`

**验收**
- Given：已导入案件文书
- When：搜索关键词（如“收款”）
- Then：优先返回包含关键词的相关 chunk（笔录场景：返回 QA chunk），且带来源页码与可高亮坐标

---

### 6.4 智能问答（Generation）

#### 6.4.1 输入
- `case_id`
- 用户自然语言问题（单轮）
- 可选过滤：`doc_type`

#### 6.4.2 输出（结构化 + 可校验）
建议采用 JSON 输出（便于 Answer Gate 校验与前端渲染）：
```json
{
  "status": "ok | no_evidence | citation_insufficient",
  "conclusion": "string | null",
  "evidences": [
    {
      "chunk_id": "string",
      "page_index": 1,
      "bbox": [0,0,0,0],
      "excerpt": "string"
    }
  ],
  "reasoning": "string",
  "gaps": ["string"],
  "raw_chunks": [
    {"chunk_id":"string","page_range":[1,1],"bbox_union":[0,0,0,0],"text":"string"}
  ]
}
```

#### 6.4.3 硬约束（必须系统保证）
1. 无证据断言禁止：没有可用证据则 `status=no_evidence`，`conclusion=null`
2. 数值/日期严格落地：答案里出现的数值必须在 `evidences[].excerpt` 中逐字出现
3. 引用可定位：每条 evidence 必须带 `page_index + bbox`，用于点击跳转高亮

---

### 6.5 引用校验器 Answer Gate（强制层）

#### 6.5.1 校验规则（纯代码）
对模型输出执行校验：
1. `chunk_id` 必须存在于本次 `raw_chunks` 或库中可查
2. `excerpt` 必须为 `chunk.text` 的子串（substring）
3. 结论/推理中抽取出的金额/日期/浓度等数值必须在 `excerpt` 中逐字出现（严格匹配）
4. `page_index/bbox` 必须来自 chunk 元数据（不允许模型自造）

#### 6.5.2 失败处理（严格模式）
- 返回：
```json
{
  "status": "citation_insufficient",
  "conclusion": null,
  "evidences": [],
  "reasoning": "",
  "gaps": ["引用不足，无法得出可靠结论"],
  "raw_chunks": [ ... ]
}
```

