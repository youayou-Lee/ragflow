# RAGFlow RAG 评测框架

统一的 RAG 系统评测框架，用于评估检索准确率和答案正确性。

---

## 目录

1. [设计原则](#设计原则)
2. [快速开始](#快速开始)
3. [目录结构](#目录结构)
4. [评测流程](#评测流程)
5. [题型与评分逻辑](#题型与评分逻辑)
6. [配置说明](#配置说明)
7. [如何添加新测试用例](#如何添加新测试用例)
8. [如何解读评测结果](#如何解读评测结果)
9. [常见问题](#常见问题)

---

## 设计原则

### 职责分离

```
┌─────────────────────────────────────────────────────────────┐
│ 评测框架 (test/eval/)                                       │
│ - 测量 RAG 系统表现                                         │
│ - 不改变检索行为                                            │
│ - 默认使用服务端配置                                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ RAGFlow 服务端 (独立配置)                                   │
│ - Embedding 模型选择                                        │
│ - 分块算法配置                                              │
│ - 重排序模型设置                                            │
│ - 相似度阈值默认值                                          │
└─────────────────────────────────────────────────────────────┘
```

### 配置优先级

```
命令行参数 > config.yaml > 服务端默认值
```

---

## 快速开始

### 前置条件

1. RAGFlow 服务已启动 (`http://127.0.0.1:9380`)
2. 已配置 LLM API Key（如 ZHIPU-AI）
3. 测试数据已准备在 `benchmark/` 目录

### 运行评测

```bash
# 完整评测（使用服务端默认参数）
uv run python test/eval/run.py

# 按案件过滤
uv run python test/eval/run.py --case "曾庆成危险驾驶案"

# 按题型过滤
uv run python test/eval/run.py --category factual

# 保留资源（不清理数据集和对话助手）
uv run python test/eval/run.py --no-cleanup

# 自定义配置文件
uv run python test/eval/run.py --config my_config.yaml
```

### 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--config` | 配置文件路径 | `test/eval/config.yaml` |
| `--case` | 按案件名称过滤 | 全部 |
| `--category` | 按题型过滤 (factual/evidence/gap) | 全部 |
| `--no-cleanup` | 评测后保留资源 | 清理 |
| `--base-path` | 测试数据目录 | `benchmark` |
| `--output-dir` | 报告输出目录 | `test/eval/reports` |

---

## 目录结构

```
test/eval/
├── config.yaml              # 评测配置
├── run.py                   # 主入口
├── models.py                # 数据模型
│
├── evaluator/               # 评测器（核心逻辑）
│   ├── setup.py             # 登录、数据集创建、文档上传
│   ├── retrieval.py         # 检索评测器
│   ├── chat.py              # 对话评测器
│   └── matcher.py           # 答案匹配器
│
├── report/                  # 报告生成
│   ├── json_report.py       # JSON 格式报告
│   └── md_report.py         # Markdown 格式报告
│
└── questions/               # 题目解析
    ├── parser.py            # Markdown 题目解析器
    └── types.py             # 题型判断工具
```

---

## 评测流程

```
1. 加载配置
   │
   ▼
2. 解析测试题目
   │  从 benchmark/ 目录加载 Markdown 格式的题目
   │
   ▼
3. 登录 RAGFlow
   │  使用 config.yaml 中的账号密码
   │
   ▼
4. 创建测试环境
   │  - 创建数据集
   │  - 上传文档
   │  - 等待解析完成
   │  - 创建对话助手
   │
   ▼
5. 执行评测
   │  对每道题目：
   │  - 调用检索 API
   │  - 调用对话 API
   │  - 匹配答案
   │  - 记录结果
   │
   ▼
6. 生成报告
   │  - JSON 报告（机器可读）
   │  - Markdown 报告（人类可读）
   │
   ▼
7. 清理资源（可选）
```

---

## 题型与评分逻辑

### 1. 事实型 (factual)

**目标**：验证系统能否正确提取事实信息。

**匹配策略**：

| 策略 | 说明 | 得分 |
|------|------|------|
| 精确匹配 | 标准化后直接包含 | 1.0 |
| 语义等价 | 通过语义映射表匹配 | 0.95 |
| 部分匹配 | 关键词覆盖率 ≥60% | 0.6-0.9 |
| 组织机构 | 机构名称部分匹配 | 0.9 |

**特殊处理**：
- **布尔值**：检测肯定/否定词，处理否定语境
- **数字**：支持格式差异（如 `1,000` vs `1000`）
- **组织名**：支持地名前缀省略

**示例**：
```
问题：犯罪嫌疑人是谁？
预期答案：曾庆成
实际答案：犯罪嫌疑人是曾庆成
结果：✅ 匹配（精确匹配）
```

### 2. 证据集合型 (evidence)

**目标**：验证系统能否收集完整的证据清单。

**匹配策略**：覆盖率计算

```
覆盖率 = 匹配的证据项数 / 预期证据项总数
通过阈值：默认 50%（可在 config.yaml 配置）
```

**语义等价映射表**：

```python
"供述" ~ ["供述材料", "口供", "供述笔录", "供述内容"]
"讯问笔录" ~ ["讯问记录", "询问笔录", "询问记录", "审讯笔录"]
"鉴定意见" ~ ["鉴定报告", "鉴定结论", "司法鉴定", "检验鉴定"]
"血液酒精检测" ~ ["血醇检测", "酒精检测报告", "血液检测"]
"视听资料" ~ ["录音录像", "监控录像", "视频资料"]
```

**匹配类型优先级**：
1. 精确匹配 (exact)
2. 子串匹配 (substring)
3. 语义等价 (semantic)
4. 模糊匹配 (fuzzy)
5. 部分匹配 (partial)

**示例**：
```
预期：供述材料、讯问笔录、鉴定意见、血液酒精检测报告
实际：供述、询问笔录、鉴定报告、血醇检测报告

匹配：
- 供述材料 → 供述 (semantic) ✅
- 讯问笔录 → 询问笔录 (semantic) ✅
- 鉴定意见 → 鉴定报告 (semantic) ✅
- 血液酒精检测报告 → 血醇检测报告 (semantic) ✅

覆盖率：4/4 = 100% → 通过
```

### 3. 冲突缺口型 (gap)

**目标**：验证系统能否正确识别"信息缺失"。

**匹配策略**：否定关键词检测

**否定关键词列表**（部分）：

```
中文：
- 材料未显示、文档未提及、无法确定
- 未记载、没有信息、未找到
- 无法从材料中得知、材料中没有
- 未提供、没有明确提及、未知

英文（LLM可能返回英文）：
- not found, no relevant content
- not provided, not available
- does not contain, unable to
```

**否定句式检测**：
```
- "没有" + 名词（如：没有记录、没有信息）
- "无" + 名词（如：无记录、无信息）
- "材料中(没有|未|无)..."
- "无法(从|在)材料..."
```

**示例**：
```
问题：被害人的教育背景是什么？
预期答案：材料未显示
实际答案：根据提供的材料，未记载被害人的教育背景信息

检测到否定词："未记载" → ✅ 通过
```

---

## 配置说明

### config.yaml 完整示例

```yaml
# 服务器配置
server:
  base_url: "http://127.0.0.1:9380"
  api_version: "v1"

# 认证信息
auth:
  email: "qa@infiniflow.org"
  password: "..."  # 加密后的密码

# 数据集配置
dataset:
  name_prefix: "eval_benchmark"       # 数据集名称前缀
  embedding_model: "embedding-3@ZHIPU-AI"
  chunk_method: "naive"

# 对话助手配置
chat:
  llm_model: "glm-4-flash@ZHIPU-AI"

# 检索参数（可选，null = 使用服务端默认值）
retrieval:
  top_k: null                    # 返回多少个 chunk
  similarity_threshold: null     # 相似度阈值

# 测试配置
test:
  parse_timeout: 300             # 文档解析超时（秒）
  parse_interval: 5              # 解析轮询间隔（秒）

# 测试用例
test_cases:
  - name: "曾庆成危险驾驶案"
    doc_type: "indictment"
    path: "benchmark/起诉意见书/曾庆成危险驾驶案/原始数据/起诉意见书_sample.pdf"
  - name: "陈明飞诈骗案"
    doc_type: "interrogation"
    path: "benchmark/讯问笔录/陈明飞诈骗案/原始数据/讯问笔录_sample.pdf"

# 匹配配置
matching:
  factual:
    case_sensitive: false
  evidence:
    coverage_threshold: 0.5      # 覆盖率阈值
  gap:
    negative_keywords:
      - "材料未显示"
      - "文档未提及"
      - "not found"
      # ... 更多关键词
```

---

## 如何添加新测试用例

### 1. 准备测试文档

将 PDF 文档放入 `benchmark/` 目录：

```
benchmark/
├── 起诉意见书/
│   └── 新案件名/
│       └── 原始数据/
│           └── 起诉意见书.pdf
└── 讯问笔录/
    └── 新案件名/
        └── 原始数据/
            └── 讯问笔录.pdf
```

### 2. 创建题目文件

在案件目录下创建三个 Markdown 文件：

**01-事实型题目.md**：
```markdown
## 1. 问题标题

**问题**：犯罪嫌疑人的姓名是什么？

**答案**：张三

**证据原文**：`犯罪嫌疑人张三...`

**位置**：`第1页`

---

## 2. 另一个问题
...
```

**02-证据集合型题目.md**：
```markdown
## 1. 案件证据

**问题**：本案收集了哪些证据？

**答案**：
1. 供述材料
2. 讯问笔录
3. 鉴定意见
4. 物证

**证据原文**：`...`

**位置**：`第3-5页`
```

**03-冲突缺口型题目.md**：
```markdown
## 1. 缺失信息

**问题**：被害人的职业是什么？

**答案**：材料未显示

**证据原文**：`无`

**位置**：`无`
```

### 3. 更新配置文件

在 `config.yaml` 的 `test_cases` 中添加：

```yaml
test_cases:
  - name: "新案件名"
    doc_type: "indictment"  # 或 interrogation
    path: "benchmark/起诉意见书/新案件名/原始数据/起诉意见书.pdf"
```

### 4. 运行评测

```bash
uv run python test/eval/run.py --case "新案件名"
```

---

## 如何解读评测结果

### 控制台输出

```
2024-01-15 10:30:00 - INFO - Loading questions...
2024-01-15 10:30:00 - INFO - Loaded 45 questions
2024-01-15 10:30:01 - INFO - Creating dataset: eval_benchmark_20240115_103000
2024-01-15 10:30:02 - INFO - Dataset created: abc123
...
2024-01-15 10:35:00 - INFO - Testing question 1/45: 犯罪嫌疑人是谁？...
2024-01-15 10:35:01 - INFO -   ✓ Score: 1.00 | Time: 523ms
2024-01-15 10:35:02 - INFO - Testing question 2/45: ...
2024-01-15 10:35:03 - INFO -   ✗ Score: 0.00 | Time: 498ms
...
============================================================
EVALUATION SUMMARY
============================================================
Total:   45
Passed:  37
Failed:  8
Score:   82.2%
============================================================
```

### Markdown 报告

```markdown
# RAG Evaluation Benchmark Report

**Timestamp**: 2024-01-15T10:40:00

## Summary

| Metric | Value |
|--------|-------|
| Total Questions | 45 |
| Passed | 37 |
| Failed | 8 |
| **Score** | **82.2%** |

## By Category

| Category | Total | Passed | Score |
|----------|-------|--------|-------|
| Factual | 25 | 22 | 88.0% |
| Evidence | 10 | 8 | 80.0% |
| Gap | 10 | 7 | 70.0% |

## By Case

| Case | Total | Passed | Score |
|------|-------|--------|-------|
| 曾庆成危险驾驶案 | 20 | 18 | 90.0% |
| 陈明飞诈骗案 | 25 | 19 | 76.0% |
```

### JSON 报告

```json
{
  "meta": {
    "timestamp": "2024-01-15T10:40:00",
    "config": { ... }
  },
  "summary": {
    "total": 45,
    "passed": 37,
    "score": 0.822,
    "by_category": { ... },
    "by_case": { ... }
  },
  "results": [
    {
      "question_id": "曾庆成危险驾驶案_factual_1",
      "question": "犯罪嫌疑人是谁？",
      "expected_answer": "曾庆成",
      "actual_answer": "犯罪嫌疑人是曾庆成...",
      "matched": true,
      "score": 1.0,
      "category": "factual",
      "timing": { "total_ms": 523 }
    },
    ...
  ]
}
```

### 性能指标

| 指标 | 含义 | 参考值 |
|------|------|--------|
| Score | 总体正确率 | ≥80% 为良好 |
| Factual Score | 事实提取准确率 | ≥85% |
| Evidence Score | 证据收集完整率 | ≥70% |
| Gap Score | 缺失识别正确率 | ≥70% |
| Avg Time | 平均响应时间 | <2s |

---

## 常见问题

### Q: 为什么使用服务端默认参数？

**A**: 评测的目的是测量系统表现，而不是调参。检索参数（top_k、阈值）应该在服务端配置，评测框架只负责测量结果。

### Q: 如何临时调整检索参数？

**A**: 在 `config.yaml` 中设置：

```yaml
retrieval:
  top_k: 20              # 覆盖服务端默认值
  similarity_threshold: 0.1
```

或通过命令行：

```bash
# 目前不支持命令行传参，请修改 config.yaml
```

### Q: 如何添加新的语义等价词？

**A**: 编辑 `test/eval/evaluator/matcher.py`，在 `EVIDENCE_EQUIVALENCES` 字典中添加：

```python
EVIDENCE_EQUIVALENCES = {
    # 添加新的等价词组
    "新词": ["同义词1", "同义词2", "同义词3"],
    ...
}
```

### Q: 评测后数据集被删除了怎么办？

**A**: 使用 `--no-cleanup` 保留资源：

```bash
uv run python test/eval/run.py --no-cleanup
```

### Q: 如何只测试某一类题型？

**A**: 使用 `--category` 参数：

```bash
uv run python test/eval/run.py --category factual
uv run python test/eval/run.py --category evidence
uv run python test/eval/run.py --category gap
```

---

## 与 test/benchmark/ 的区别

| 特性 | `test/benchmark/` | `test/eval/` |
|------|-------------------|--------------|
| 目的 | 性能压测 | 准确性评测 |
| 指标 | 延迟、吞吐量 | 正确率、召回率 |
| 关注点 | HTTP API 性能 | RAG 质量 |
| 报告 | 性能统计 | 正确性分析 |

两个框架用途不同，可以配合使用进行全面测试。

---

## License

Apache License 2.0
