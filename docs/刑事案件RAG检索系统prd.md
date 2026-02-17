
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
**PDF -> PaddleOCR API 解析 -> Block 入库 -> Chunk 生成 -> 索引构建（向量/关键词）-> 检索 -> LLM API 生成答案 -> Answer Gate 校验 -> 返回结果（可跳转高亮）**

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
  "doc_type": "indictment_opinion | interrogation_record",
  "page_index": 1,
  "page_width": 0,
  "page_height": 0,
  "block_id": 0,
  "block_order": 0,
  "label": "text | number | header | footer | other",
  "text": "string",
  "bbox": [0, 0, 0, 0],
  "polygon": [[0,0],[0,0],[0,0],[0,0]]
}
```

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

---

## 7. 非功能需求（MVP）

### 7.1 性能
- 单份 PDF（≤200 页）解析可接受为分钟级（以实际硬件为准）
- 单次问答（检索+生成+校验）目标在可交互范围（秒级到十秒级）

### 7.2 可追溯与审计
- 每次问答必须记录：检索结果、最终输出、Gate 结果、失败原因
- 便于评测与回放

### 7.3 可靠性
- OCR/解析失败必须可感知并提示（不可静默失败）
- 任何异常不得输出无引用结论

---

## 8. 评测与验收

### 8.1 金标题库（必须建设，否则指标无意义）

#### 8.1.0 现有题库资源

**项目已有题库**（位于 `benchmark/` 目录）：

| 文件 | 类型 | 题数 | 测试目标 |
|------|------|------|----------|
| 01-事实型题目.md | fact_retrieval | 10题 | 精确事实提取 |
| 02-证据集合型题目.md | evidence_aggregation | 10题 | 多证据聚合 |
| 03-冲突缺口型题目.md | gap_detection | 15题 | 信息缺失时的"不编造"能力 |
| **合计** | - | **35题** | - |

**现有题库格式**：
```markdown
## 1. 总收款金额

**问题**：成龙飞总共给了多少钱给陈明飞用于办理学位？

**答案**：42000元

**位置**：第2个问答，答部分
**证据原文**：`我只是收取了成龙飞的 42000 元用于办理成龙飞的孩子以及外甥入读清城区锦兴小学`
```

**已完成的Schema转换**：
- 转换脚本：`evaluation/convert_benchmark_to_json.py`
- JSON输出：`evaluation/gold_standard.json`
- 自动提取：数值归一化、缺口标记、多证据识别

#### 8.1.1 数据来源方案

**方案A：公开裁判文书（推荐用于MVP冷启动）**
- 数据源：中国裁判文书网、北大法宝（需授权）
- 处理方式：
  1. 下载已脱敏的刑事判决书/起诉书（公开渠道）
  2. 使用LLM生成模拟案卷材料（基于公开文书的案情重构）
  3. 人工校验生成内容的合理性
- 优点：数据获取成本低，法律合规
- 缺点：需人工脱敏处理

**方案B：合成数据集（MVP快速启动首选）**
- 使用LLM生成模拟刑事案卷（虚构案件，无隐私风险）
- 覆盖案件类型：盗窃、诈骗、故意伤害、毒品犯罪
- 每份案卷包含：起诉意见书 + 2-3份讯问/询问笔录
- 优点：零隐私风险，可控性强
- 缺点：可能与真实场景有gap

**方案C：合作律师提供（生产级数据）**
- 与执业律师合作，使用其代理过的已结案卷
- 必须经过严格脱敏处理
- 需签署数据使用协议
- 优点：真实场景，最高质量
- 缺点：获取周期长，合规成本高

**推荐路径**：MVP阶段采用方案B快速启动，后续逐步引入方案C的真实数据。

#### 8.1.2 标注工具选择

**推荐方案：Label Studio（开源 + 可定制）**

```
优势：
- 开源免费，支持私有化部署
- 支持PDF可视化标注
- 支持多标注员协作 + 质量控制
- 导出格式灵活（JSON/CSV）

部署方式：
docker run -it -p 8080:8080 -v $(pwd)/mydata:/label-studio/data heartexlabs/label-studio:latest
```

**轻量级替代方案：自研标注工具**

基于 Streamlit 快速构建：
- 文书展示区（PDF渲染 + 文本展示）
- 问题输入框
- 证据选择器（支持文本高亮选择）
- 导出为标准JSON

#### 8.1.3 金标题库 Schema 设计

```json
{
  "question_id": "q_001",
  "version": "1.0",
  "created_at": "2025-01-15T10:00:00Z",
  "annotator_id": "annotator_01",
  "reviewer_id": "reviewer_01",
  "review_status": "approved",

  "case_id": "case_2025_001",
  "doc_id": "doc_001",
  "doc_type": "indictment_opinion | interrogation_record",

  "question": "被告人张某的涉案金额是多少？",
  "question_type": "fact_retrieval | numerical | yes_no | summary",
  "difficulty": "easy | medium | hard",

  "expected_answer": {
    "status": "ok",
    "conclusion": "被告人张某的涉案金额为人民币15万元。",
    "reasoning": "根据起诉意见书第2页，被告人张某涉案金额为15万元。"
  },

  "evidence_chunks": [
    {
      "chunk_id": "chunk_001",
      "page_index": 2,
      "bbox": [100, 200, 400, 250],
      "excerpt": "被告人张某涉案金额人民币15万元"
    }
  ],

  "evidence_excerpts": [
    "被告人张某涉案金额人民币15万元"
  ],

  "numerical_values": [
    {
      "value": "150000",
      "normalized": 150000,
      "type": "currency",
      "unit": "人民币",
      "excerpt_match": "15万元"
    }
  ],

  "is_ood": false,
  "ood_reason": null,

  "metadata": {
    "requires_calculation": false,
    "requires_inference": false,
    "multi_hop": false,
    "temporal_reasoning": false
  }
}
```

**字段说明**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| question_id | string | 是 | 全局唯一问题ID |
| version | string | 是 | 题目版本号 |
| question | string | 是 | 标注问题文本 |
| question_type | enum | 是 | 问题类型分类 |
| difficulty | enum | 是 | 难度等级 |
| expected_answer | object | 是 | 期望的标准答案 |
| evidence_chunks | array | 是 | 金标证据块（含坐标） |
| evidence_excerpts | array | 是 | 金标摘录文本 |
| numerical_values | array | 条件必填 | 涉及的数值（数值类问题必填） |
| is_ood | boolean | 是 | 是否为分布外问题 |
| ood_reason | string | 条件必填 | OOD原因（OOD问题必填） |

#### 8.1.4 标注人员要求

**角色配置**：

| 角色 | 人数 | 专业要求 | 职责 |
|------|------|----------|------|
| 标注员 | 2-3人 | 法学专业背景/法律从业经验 | 问题设计 + 证据标注 |
| 审核员 | 1人 | 3年以上法律实务经验 | 标注质量审核 |
| 技术支持 | 1人 | 熟悉RAG评测体系 | Schema设计 + 工具维护 |

**标注员培训要点**：
1. 理解RAG系统的引用机制
2. 掌握证据标注的粒度标准
3. 数值类问题的精确性要求
4. OOD问题的定义与边界

#### 8.1.5 标注流程（三阶段质控）

```
┌─────────────────────────────────────────────────────────────┐
│                    标注工作流程                              │
├─────────────────────────────────────────────────────────────┤
│  阶段1：问题设计                                             │
│  ├─ 标注员阅读文书，设计问题（每份≥20题）                      │
│  ├─ 问题类型覆盖：事实型60%、数值型20%、推理型20%              │
│  └─ 自查：问题表述清晰、答案可从文书推导                       │
├─────────────────────────────────────────────────────────────┤
│  阶段2：证据标注                                             │
│  ├─ 标注金标证据（chunk_id + excerpt + bbox）                │
│  ├─ 标注期望答案和推理过程                                    │
│  ├─ OOD问题单独标注原因                                       │
│  └─ 自查：excerpt必须是原文精确子串                           │
├─────────────────────────────────────────────────────────────┤
│  阶段3：审核验收                                             │
│  ├─ 审核员100%审核所有题目                                    │
│  ├─ 不合格返回修改（标注问题、证据不完整等）                    │
│  ├─ 争议题目提交仲裁                                          │
│  └─ 通过审核的题目标记review_status=approved                  │
└─────────────────────────────────────────────────────────────┘
```

**质量指标**：
- 标注员自查通过率 ≥ 90%
- 审核员一次通过率 ≥ 80%
- 争议题目比例 < 5%

#### 8.1.6 分阶段建设方案（样本不足时的策略）

**Phase 0：POC验证（1-2周）**
- 文书数量：2-3份
- 题目数量：30-50题
- 目标：验证评测流水线可行性，不宣称指标

**Phase 1：MVP基础（2-4周）**
- 文书数量：5-8份
- 题目数量：100-150题
- 目标：初步评估系统表现，发现问题

**Phase 2：MVP完整（4-6周）**
- 文书数量：10份以上
- 题目数量：200题以上
- 目标：达到PRD定义的验收门槛

**Phase 3：生产级（持续）**
- 文书数量：持续扩充
- 题目数量：500题以上
- 目标：持续监控，迭代优化

---

### 8.2 三层评测体系

#### 8.2.1 第一层：硬规则评分（主裁，纯代码实现）

**评测维度**：

| 维度 | 检查内容 | 实现方式 | 通过标准 |
|------|----------|----------|----------|
| 引用存在性 | chunk_id是否存在于检索结果 | 集合成员检查 | 100% |
| Excerpt匹配 | excerpt是否为chunk.text的子串 | 子串匹配（允许空白差异） | 100% |
| 数值一致性 | 答案中数值是否在excerpt中出现 | 正则提取+精确匹配 | 100% |
| 坐标有效性 | bbox/page_index是否有效 | 范围检查 | 100% |

**代码框架**：

```python
# evaluation/hard_rules_evaluator.py

import re
from typing import List, Dict, Any
from dataclasses import dataclass

@dataclass
class HardRuleResult:
    """硬规则评测结果"""
    passed: bool
    rule_name: str
    details: Dict[str, Any]
    error_message: str = ""

class HardRulesEvaluator:
    """硬规则评分器"""

    def __init__(self, chunk_store: Dict[str, str]):
        """
        Args:
            chunk_store: chunk_id -> chunk.text 的映射
        """
        self.chunk_store = chunk_store

    def evaluate(self, gold_item: Dict, pred_answer: Dict) -> List[HardRuleResult]:
        """执行所有硬规则检查"""
        results = []

        # 规则1：引用存在性检查
        results.append(self._check_chunk_existence(pred_answer))

        # 规则2：Excerpt匹配检查
        results.append(self._check_excerpt_match(pred_answer))

        # 规则3：数值一致性检查
        results.append(self._check_numerical_consistency(
            gold_item, pred_answer
        ))

        # 规则4：坐标有效性检查
        results.append(self._check_coordinate_validity(pred_answer))

        return results

    def _check_chunk_existence(self, pred_answer: Dict) -> HardRuleResult:
        """检查引用的chunk是否真实存在"""
        evidence_chunk_ids = set()
        for ev in pred_answer.get("evidences", []):
            chunk_id = ev.get("chunk_id")
            if chunk_id:
                evidence_chunk_ids.add(chunk_id)

        missing_chunks = evidence_chunk_ids - set(self.chunk_store.keys())

        return HardRuleResult(
            passed=len(missing_chunks) == 0,
            rule_name="chunk_existence",
            details={
                "referenced_chunks": list(evidence_chunk_ids),
                "missing_chunks": list(missing_chunks)
            },
            error_message=f"不存在的chunk: {missing_chunks}" if missing_chunks else ""
        )

    def _check_excerpt_match(self, pred_answer: Dict) -> HardRuleResult:
        """检查excerpt是否为chunk.text的子串"""
        mismatches = []

        for ev in pred_answer.get("evidences", []):
            chunk_id = ev.get("chunk_id")
            excerpt = ev.get("excerpt", "")

            if chunk_id and chunk_id in self.chunk_store:
                chunk_text = self.chunk_store[chunk_id]
                # 标准化空白后检查子串
                normalized_excerpt = self._normalize_whitespace(excerpt)
                normalized_chunk = self._normalize_whitespace(chunk_text)

                if normalized_excerpt not in normalized_chunk:
                    mismatches.append({
                        "chunk_id": chunk_id,
                        "excerpt": excerpt[:50] + "...",
                        "reason": "excerpt不是chunk.text的子串"
                    })

        return HardRuleResult(
            passed=len(mismatches) == 0,
            rule_name="excerpt_match",
            details={"mismatches": mismatches},
            error_message=f"摘录不匹配数量: {len(mismatches)}" if mismatches else ""
        )

    def _check_numerical_consistency(self, gold_item: Dict, pred_answer: Dict) -> HardRuleResult:
        """检查答案中的数值是否都在证据摘录中出现"""
        # 从预测答案中提取数值
        conclusion = pred_answer.get("conclusion", "")
        reasoning = pred_answer.get("reasoning", "")
        combined_text = f"{conclusion} {reasoning}"

        # 提取数值（金额、日期、百分比等）
        numbers_in_answer = self._extract_numbers(combined_text)

        # 从证据摘录中提取数值
        excerpts = [ev.get("excerpt", "") for ev in pred_answer.get("evidences", [])]
        numbers_in_evidence = set()
        for excerpt in excerpts:
            numbers_in_evidence.update(self._extract_numbers(excerpt))

        # 检查答案中的数值是否都在证据中
        ungrounded_numbers = numbers_in_answer - numbers_in_evidence

        return HardRuleResult(
            passed=len(ungrounded_numbers) == 0,
            rule_name="numerical_consistency",
            details={
                "numbers_in_answer": list(numbers_in_answer),
                "numbers_in_evidence": list(numbers_in_evidence),
                "ungrounded_numbers": list(ungrounded_numbers)
            },
            error_message=f"未落地的数值: {ungrounded_numbers}" if ungrounded_numbers else ""
        )

    def _check_coordinate_validity(self, pred_answer: Dict) -> HardRuleResult:
        """检查坐标有效性"""
        invalid_coords = []

        for ev in pred_answer.get("evidences", []):
            page = ev.get("page_index")
            bbox = ev.get("bbox", [])

            if page is None or page < 0:
                invalid_coords.append({
                    "evidence": ev,
                    "reason": "无效的page_index"
                })
                continue

            if len(bbox) != 4 or any(not isinstance(x, (int, float)) for x in bbox):
                invalid_coords.append({
                    "evidence": ev,
                    "reason": "无效的bbox格式"
                })

        return HardRuleResult(
            passed=len(invalid_coords) == 0,
            rule_name="coordinate_validity",
            details={"invalid_count": len(invalid_coords)},
            error_message=f"无效坐标数量: {len(invalid_coords)}" if invalid_coords else ""
        )

    @staticmethod
    def _normalize_whitespace(text: str) -> str:
        """标准化空白字符"""
        return re.sub(r'\s+', ' ', text).strip()

    @staticmethod
    def _extract_numbers(text: str) -> set:
        """从文本中提取数值"""
        numbers = set()

        # 金额：15万元、150,000元、150000元
        money_pattern = r'(\d+(?:[,，]\d+)*(?:\.\d+)?)\s*(?:万|亿)?(?:元|美元|欧元)'
        for match in re.finditer(money_pattern, text):
            num_str = match.group(1).replace(',', '').replace('，', '')
            try:
                numbers.add(float(num_str))
            except ValueError:
                pass

        # 日期：2024年1月15日、2024-01-15
        date_pattern = r'(\d{4})[-年](\d{1,2})[-月](\d{1,2})日?'
        for match in re.finditer(date_pattern, text):
            numbers.add(f"{match.group(1)}-{match.group(2)}-{match.group(3)}")

        # 纯数字（用于浓度、次数等）
        pure_number_pattern = r'(?<![a-zA-Z\u4e00-\u9fff])(\d+(?:\.\d+)?)(?![a-zA-Z\u4e00-\u9fff])'
        for match in re.finditer(pure_number_pattern, text):
            try:
                numbers.add(float(match.group(1)))
            except ValueError:
                pass

        return numbers
```

#### 8.2.2 第二层：金标检索评分（主裁，代码统计）

**评测指标**：

| 指标 | 定义 | 计算方式 |
|------|------|----------|
| Recall@k | 金标证据出现在Top-k的比例 | len(金标∩预测) / len(金标) |
| MRR | 金标证据的排序倒数均值 | mean(1/rank) |
| Hit Rate | 至少一个金标被召回的比例 | 有召回/总数 |

**代码框架**：

```python
# evaluation/retrieval_evaluator.py

from typing import List, Dict, Set
from dataclasses import dataclass
import numpy as np

@dataclass
class RetrievalMetrics:
    """检索评测指标"""
    recall_at_5: float
    recall_at_10: float
    recall_at_20: float
    mrr: float
    hit_rate: float

class RetrievalEvaluator:
    """检索评分器"""

    def __init__(self, k_values: List[int] = [5, 10, 20]):
        self.k_values = k_values

    def evaluate(
        self,
        gold_items: List[Dict],
        retrieval_results: List[List[str]]  # 每个问题的检索结果chunk_id列表
    ) -> RetrievalMetrics:
        """
        评估检索性能

        Args:
            gold_items: 金标题库
            retrieval_results: 每个问题的Top-N检索结果
        """
        recalls = {k: [] for k in self.k_values}
        rr_list = []  # reciprocal rank
        hit_count = 0

        for gold, retrieved in zip(gold_items, retrieval_results):
            # 获取金标chunk_ids
            gold_chunks = set()
            for ev in gold.get("evidence_chunks", []):
                gold_chunks.add(ev["chunk_id"])

            if not gold_chunks:
                continue

            retrieved_set = set(retrieved)

            # Recall@k
            for k in self.k_values:
                top_k = set(retrieved[:k])
                recall = len(gold_chunks & top_k) / len(gold_chunks)
                recalls[k].append(recall)

            # MRR: 第一个金标出现的排名
            for rank, chunk_id in enumerate(retrieved, 1):
                if chunk_id in gold_chunks:
                    rr_list.append(1.0 / rank)
                    hit_count += 1
                    break
            else:
                rr_list.append(0.0)

        return RetrievalMetrics(
            recall_at_5=np.mean(recalls[5]) if recalls[5] else 0.0,
            recall_at_10=np.mean(recalls[10]) if recalls[10] else 0.0,
            recall_at_20=np.mean(recalls[20]) if recalls[20] else 0.0,
            mrr=np.mean(rr_list) if rr_list else 0.0,
            hit_rate=hit_count / len(gold_items) if gold_items else 0.0
        )

    def evaluate_single(
        self,
        gold_chunks: Set[str],
        retrieved_chunks: List[str]
    ) -> Dict[str, float]:
        """评估单个问题的检索性能"""
        results = {}

        for k in self.k_values:
            top_k = set(retrieved_chunks[:k])
            results[f"recall@{k}"] = len(gold_chunks & top_k) / len(gold_chunks) if gold_chunks else 0.0

        # MRR
        for rank, chunk_id in enumerate(retrieved_chunks, 1):
            if chunk_id in gold_chunks:
                results["rr"] = 1.0 / rank
                break
        else:
            results["rr"] = 0.0

        return results
```

#### 8.2.3 第三层：LLM评分（辅裁，LLM + 抽检）

**评分维度**：

| 维度 | 权重 | 说明 |
|------|------|------|
| 事实一致性 | 40% | 答案是否仅基于证据，无幻觉 |
| 推理正确性 | 30% | 推理过程是否逻辑正确 |
| 引用充分性 | 20% | 证据是否足够支撑结论 |
| 表述清晰度 | 10% | 答案是否清晰易懂 |

**Prompt模板**：

```python
# evaluation/llm_evaluator.py

LLM_EVAL_PROMPT = """
你是一个法律问答系统的评测专家。请对以下系统回答进行评分。

## 原始问题
{question}

## 金标答案
{gold_answer}

## 金标证据
{gold_evidence}

## 系统回答
{pred_answer}

## 系统引用的证据
{pred_evidence}

## 评分标准

请从以下维度评分（1-5分）：

1. **事实一致性**（1-5分）：
   - 5分：所有事实均有证据支撑，无幻觉
   - 3分：大部分事实有支撑，有轻微推断
   - 1分：存在明显的事实编造

2. **推理正确性**（1-5分）：
   - 5分：推理逻辑完全正确
   - 3分：推理基本正确，有小瑕疵
   - 1分：推理存在明显逻辑错误

3. **引用充分性**（1-5分）：
   - 5分：证据充分，足以支撑结论
   - 3分：证据基本充分，但不够全面
   - 1分：证据不足以支撑结论

4. **表述清晰度**（1-5分）：
   - 5分：表述清晰、专业、易于理解
   - 3分：基本清晰，有改进空间
   - 1分：表述混乱，难以理解

## 输出格式

请以JSON格式输出评分结果：
```json
{{
    "factual_consistency": <1-5>,
    "reasoning_correctness": <1-5>,
    "citation_sufficiency": <1-5>,
    "clarity": <1-5>,
    "overall_comments": "<简要评价>",
    "improvement_suggestions": "<改进建议>"
}}
```
"""

class LLMEvaluator:
    """LLM评分器"""

    def __init__(self, llm_client, model: str = "gpt-4"):
        self.llm_client = llm_client
        self.model = model

    async def evaluate(
        self,
        question: str,
        gold_answer: Dict,
        gold_evidence: List[Dict],
        pred_answer: Dict,
        pred_evidence: List[Dict]
    ) -> Dict:
        """执行LLM评分"""

        prompt = LLM_EVAL_PROMPT.format(
            question=question,
            gold_answer=gold_answer.get("conclusion", ""),
            gold_evidence=self._format_evidence(gold_evidence),
            pred_answer=pred_answer.get("conclusion", ""),
            pred_evidence=self._format_evidence(pred_evidence)
        )

        response = await self.llm_client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "你是专业的法律问答评测专家。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)

        # 计算加权总分
        weights = {
            "factual_consistency": 0.40,
            "reasoning_correctness": 0.30,
            "citation_sufficiency": 0.20,
            "clarity": 0.10
        }

        weighted_score = sum(
            result[dim] * weight for dim, weight in weights.items()
        )

        result["weighted_score"] = round(weighted_score, 2)

        return result

    @staticmethod
    def _format_evidence(evidence_list: List[Dict]) -> str:
        """格式化证据列表"""
        formatted = []
        for i, ev in enumerate(evidence_list, 1):
            formatted.append(f"[{i}] {ev.get('excerpt', ev.get('text', ''))}")
        return "\n".join(formatted)
```

---

### 8.3 评测流水线设计

#### 8.3.1 自动化评测脚本架构

```
evaluation/
├── __init__.py
├── config.py                 # 评测配置
├── pipeline.py               # 评测流水线主入口
├── evaluators/
│   ├── __init__.py
│   ├── hard_rules.py         # 硬规则评分器
│   ├── retrieval.py          # 检索评分器
│   └── llm_evaluator.py      # LLM评分器
├── loaders/
│   ├── __init__.py
│   └── gold_standard.py      # 金标题库加载器
├── runners/
│   ├── __init__.py
│   └── rag_runner.py         # RAG系统调用封装
├── reporters/
│   ├── __init__.py
│   ├── console_reporter.py   # 控制台报告
│   └── html_reporter.py      # HTML报告生成
└── utils/
    ├── __init__.py
    └── metrics.py            # 指标计算工具
```

**流水线主入口**：

```python
# evaluation/pipeline.py

import asyncio
from typing import List, Dict
from dataclasses import dataclass, field
from datetime import datetime
import json

from .evaluators.hard_rules import HardRulesEvaluator
from .evaluators.retrieval import RetrievalEvaluator
from .evaluators.llm_evaluator import LLMEvaluator
from .loaders.gold_standard import GoldStandardLoader
from .runners.rag_runner import RAGRunner

@dataclass
class EvaluationResult:
    """评测结果"""
    question_id: str
    hard_rules_passed: bool
    hard_rules_details: List[Dict]
    retrieval_metrics: Dict[str, float]
    llm_score: Dict = field(default_factory=dict)
    error: str = ""

@dataclass
class EvaluationReport:
    """评测报告"""
    timestamp: str
    total_questions: int
    hard_rules_pass_rate: float
    retrieval_metrics: Dict[str, float]
    llm_avg_score: float
    details: List[EvaluationResult]

class EvaluationPipeline:
    """评测流水线"""

    def __init__(self, config: Dict):
        self.config = config

        # 初始化各组件
        self.gold_loader = GoldStandardLoader(config["gold_standard_path"])
        self.rag_runner = RAGRunner(config["rag_endpoint"])
        self.hard_evaluator = HardRulesEvaluator()
        self.retrieval_evaluator = RetrievalEvaluator()
        self.llm_evaluator = LLMEvaluator(config["llm_config"])

    async def run(self, sample_size: int = None) -> EvaluationReport:
        """执行完整评测"""
        # 加载金标题库
        gold_items = self.gold_loader.load_all()
        if sample_size:
            gold_items = gold_items[:sample_size]

        results = []

        for gold in gold_items:
            try:
                # 调用RAG系统
                rag_response = await self.rag_runner.query(
                    case_id=gold["case_id"],
                    question=gold["question"]
                )

                # 硬规则评分
                hard_results = self.hard_evaluator.evaluate(
                    gold, rag_response["answer"]
                )
                hard_passed = all(r.passed for r in hard_results)

                # 检索评分
                retrieval_metrics = self.retrieval_evaluator.evaluate_single(
                    set(ev["chunk_id"] for ev in gold.get("evidence_chunks", [])),
                    rag_response["retrieved_chunks"]
                )

                # LLM评分（可选，对失败案例或抽样）
                llm_score = {}
                if self._should_llm_evaluate(hard_passed, gold):
                    llm_score = await self.llm_evaluator.evaluate(
                        question=gold["question"],
                        gold_answer=gold["expected_answer"],
                        gold_evidence=gold["evidence_chunks"],
                        pred_answer=rag_response["answer"],
                        pred_evidence=rag_response["answer"].get("evidences", [])
                    )

                results.append(EvaluationResult(
                    question_id=gold["question_id"],
                    hard_rules_passed=hard_passed,
                    hard_rules_details=[r.__dict__ for r in hard_results],
                    retrieval_metrics=retrieval_metrics,
                    llm_score=llm_score
                ))

            except Exception as e:
                results.append(EvaluationResult(
                    question_id=gold["question_id"],
                    hard_rules_passed=False,
                    hard_rules_details=[],
                    retrieval_metrics={},
                    error=str(e)
                ))

        # 汇总报告
        return self._generate_report(results)

    def _should_llm_evaluate(self, hard_passed: bool, gold: Dict) -> bool:
        """判断是否需要LLM评分"""
        # 失败案例必评
        if not hard_passed:
            return True
        # 抽样评估（20%）
        import random
        return random.random() < 0.2

    def _generate_report(self, results: List[EvaluationResult]) -> EvaluationReport:
        """生成评测报告"""
        total = len(results)
        hard_passed = sum(1 for r in results if r.hard_rules_passed)

        # 汇总检索指标
        retrieval_agg = {
            "recall@5": sum(r.retrieval_metrics.get("recall@5", 0) for r in results) / total,
            "recall@10": sum(r.retrieval_metrics.get("recall@10", 0) for r in results) / total,
            "recall@20": sum(r.retrieval_metrics.get("recall@20", 0) for r in results) / total,
            "mrr": sum(r.retrieval_metrics.get("rr", 0) for r in results) / total,
        }

        # 汇总LLM评分
        llm_scores = [r.llm_score.get("weighted_score", 0) for r in results if r.llm_score]
        llm_avg = sum(llm_scores) / len(llm_scores) if llm_scores else 0.0

        return EvaluationReport(
            timestamp=datetime.now().isoformat(),
            total_questions=total,
            hard_rules_pass_rate=hard_passed / total,
            retrieval_metrics=retrieval_agg,
            llm_avg_score=llm_avg,
            details=results
        )
```

#### 8.3.2 评测报告格式

**JSON报告格式**：

```json
{
  "report_id": "eval_20250115_001",
  "timestamp": "2025-01-15T14:30:00Z",
  "config": {
    "rag_endpoint": "http://localhost:8000",
    "gold_standard_version": "1.0",
    "sample_size": 200
  },
  "summary": {
    "total_questions": 200,
    "hard_rules_pass_rate": 0.985,
    "retrieval": {
      "recall@5": 0.72,
      "recall@10": 0.85,
      "recall@20": 0.96,
      "mrr": 0.68
    },
    "llm_avg_score": 4.2,
    "ood_trigger_rate": 0.94
  },
  "breakdown": {
    "by_question_type": {
      "fact_retrieval": {"count": 120, "pass_rate": 0.99},
      "numerical": {"count": 40, "pass_rate": 0.95},
      "yes_no": {"count": 20, "pass_rate": 1.0},
      "summary": {"count": 20, "pass_rate": 0.90}
    },
    "by_doc_type": {
      "indictment_opinion": {"count": 100, "pass_rate": 0.98},
      "interrogation_record": {"count": 100, "pass_rate": 0.97}
    },
    "by_difficulty": {
      "easy": {"count": 80, "pass_rate": 1.0},
      "medium": {"count": 80, "pass_rate": 0.97},
      "hard": {"count": 40, "pass_rate": 0.90}
    }
  },
  "failures": [
    {
      "question_id": "q_042",
      "question": "...",
      "failure_reason": "numerical_consistency",
      "details": "..."
    }
  ],
  "recommendations": [
    "数值提取模块需要优化，特别是金额格式的识别",
    "建议增加对复杂日期表述的训练样本"
  ]
}
```

#### 8.3.3 CI/CD集成方案

**GitHub Actions配置**：

```yaml
# .github/workflows/evaluation.yml

name: RAG Evaluation

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 2 * * *'  # 每天凌晨2点运行

jobs:
  evaluate:
    runs-on: ubuntu-latest

    services:
      rag-server:
        image: your-registry/rag-server:latest
        ports:
          - 8000:8000
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r evaluation/requirements.txt

      - name: Run evaluation
        env:
          RAG_ENDPOINT: http://localhost:8000
          LLM_API_KEY: ${{ secrets.LLM_API_KEY }}
        run: |
          python -m evaluation.pipeline --output reports/eval_report.json

      - name: Check thresholds
        run: |
          python scripts/check_thresholds.py reports/eval_report.json

      - name: Upload report
        uses: actions/upload-artifact@v4
        with:
          name: evaluation-report
          path: reports/

      - name: Comment on PR
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const report = JSON.parse(fs.readFileSync('reports/eval_report.json'));
            const summary = report.summary;

            const body = `
            ## 评测结果

            | 指标 | 值 | 阈值 | 状态 |
            |------|-----|------|------|
            | 硬规则通过率 | ${summary.hard_rules_pass_rate * 100}% | 100% | ${summary.hard_rules_pass_rate >= 1.0 ? '✅' : '❌'} |
            | Recall@20 | ${summary.retrieval['recall@20'] * 100}% | 95% | ${summary.retrieval['recall@20'] >= 0.95 ? '✅' : '❌'} |
            | LLM评分 | ${summary.llm_avg_score} | 4.0 | ${summary.llm_avg_score >= 4.0 ? '✅' : '❌'} |
            `;

            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: body
            });
```

**阈值检查脚本**：

```python
# scripts/check_thresholds.py

import json
import sys

THRESHOLDS = {
    "hard_rules_pass_rate": 1.0,  # 必须100%
    "retrieval.recall@20": 0.95,
    "ood_trigger_rate": 0.95,
    "llm_avg_score": 4.0
}

def check_thresholds(report_path: str) -> bool:
    with open(report_path) as f:
        report = json.load(f)

    all_passed = True

    for metric, threshold in THRESHOLDS.items():
        # 支持嵌套路径
        value = report["summary"]
        for key in metric.split("."):
            value = value[key]

        passed = value >= threshold
        status = "✅ PASS" if passed else "❌ FAIL"

        print(f"{metric}: {value} >= {threshold} [{status}]")

        if not passed:
            all_passed = False

    return all_passed

if __name__ == "__main__":
    report_path = sys.argv[1]
    if check_thresholds(report_path):
        print("\n所有阈值检查通过!")
        sys.exit(0)
    else:
        print("\n存在未通过的阈值检查!")
        sys.exit(1)
```

---

### 8.4 MVP门槛评估

#### 8.4.1 样本规模合理性分析

| 样本量 | 统计意义 | 置信区间(95%) | 适用场景 |
|--------|----------|---------------|----------|
| 50题 | 勉强可用 | ±14% | POC验证 |
| 100题 | 基本可行 | ±10% | 早期迭代 |
| 200题 | 较为可靠 | ±7% | MVP验收 |
| 500题 | 统计稳健 | ±4% | 生产发布 |

**结论**：200题/10份文书的MVP门槛是合理的，能在7%误差范围内评估系统性能。

#### 8.4.2 分阶段建设建议

**第一阶段（POC，2周）**
- 目标：验证评测流水线
- 规模：3份文书/50题
- 交付：可运行的评测脚本

**第二阶段（Alpha，4周）**
- 目标：初步评估系统性能
- 规模：6份文书/120题
- 交付：首份评测报告 + 问题清单

**第三阶段（MVP，6周）**
- 目标：达到验收门槛
- 规模：10份文书/200题
- 交付：完整评测报告 + 发布决策

---

### 8.5 MVP完成标准（更新）

| 指标 | 阈值 | 验证方式 |
|------|------|----------|
| 硬规则评分 | = 100% | 自动化脚本 |
| Retrieval Recall@20 | ≥ 95% | 自动化脚本 |
| OOD "材料未显示"触发正确率 | ≥ 95% | 自动化脚本 |
| LLM评分（加权） | ≥ 4.0/5.0 | LLM评估 |
| 人工抽检一致性 | ≥ 90% | 抽检≥20%样本 |
| 金标题库规模 | ≥ 200题/10份文书 | 人工验收 |

---

## 9. MVP 不做事项（明确 Non-goals）
- 高级分析：时间线、证据链、矛盾点检测、辩护策略建议
- 外部检索增强：类案检索、法条引用增强、裁判文书网对接
- 交互增强：多轮对话
- 用户系统：账号/权限/付费
- 导出报告、多语言

---

## 10. 风险与对策（必须写清）

1. **扫描 OCR 噪声**导致召回与引用不稳定
   - 对策：hybrid 检索、chunking 规则稳健化、评测驱动迭代
2. **坐标映射错误**导致高亮错位
   - 对策：记录 page_width/page_height；前端渲染使用同源尺寸；加入可视化回放工具
3. **样本不足导致指标虚高/虚低**
   - 对策：先建题库与回放链路，再谈阈值
```