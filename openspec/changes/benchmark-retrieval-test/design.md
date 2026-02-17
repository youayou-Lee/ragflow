## Context

刑事 RAG 系统已完成 PR1-PR6 开发：
- PR-1: Schema 扩展 (block_refs, bbox_union)
- PR-2: 起诉意见书 Chunker
- PR-3: Answer Gate 校验器
- PR-4: 检索扩展
- PR-5: 集成测试
- PR-6: PaddleVL 作为默认 PDF Parser

现需建立 Benchmark 测试来验证检索效果。

## Goals / Non-Goals

**Goals:**
1. 创建可重复执行的检索测试脚本
2. 支持三种题型的自动评估：事实型、证据集合型、冲突缺口型
3. 生成结构化测试报告

**Non-Goals:**
1. 不测试 LLM 生成质量（仅测试检索）
2. 不建立 CI 自动化（手动执行）
3. 不做性能基准测试

## Decisions

### D1: 测试脚本实现方式

**决定**: 使用 pytest 框架 + 独立脚本模式

**理由**:
- pytest 提供标准化测试报告
- 独立脚本支持命令行灵活执行
- 复用 `test/benchmark/` 现有工具类

### D2: 题目解析方式

**决定**: 解析 markdown 格式的题库文件

**理由**:
- 题库已是 markdown 格式
- 正则解析简单可靠
- 便于人工审核和修改

### D3: 评估指标

**决定**: 使用三级指标

| 题型 | 指标 | 通过条件 |
|-----|------|---------|
| 事实型 | 召回率 | 答案字符串出现在检索结果中 |
| 证据集合型 | 完整性 | 所有证据项出现在检索结果中 |
| 冲突缺口型 | 诚实性 | 未找到相关内容（低相似度） |

## Risks / Trade-offs

| 风险 | 缓解措施 |
|-----|---------|
| 题库数量有限 | 后续持续扩充 |
| 事实型匹配过于简单 | 后续可增加语义匹配 |
| 冲突型判断依赖阈值 | 设置合理阈值，手动验证 |

## Test Plan

### 运行测试

```bash
# 配置环境变量
export RAGFLOW_HOST="http://127.0.0.1:9380"
export RAGFLOW_API_KEY="your-api-key"
export BENCHMARK_DATASET_IDS="dataset-id-1,dataset-id-2"

# 使用 pytest 运行
uv run pytest test/testcases/test_benchmark/test_retrieval_benchmark.py -v

# 或直接运行脚本生成报告
uv run python test/testcases/test_benchmark/test_retrieval_benchmark.py \
  --host http://127.0.0.1:9380 \
  --api-key your-api-key \
  --dataset-ids dataset-id-1,dataset-id-2 \
  --output RESULTS.md
```

### 预期结果

| 指标 | 目标 |
|-----|------|
| 事实型召回率 | ≥ 80% |
| 证据集合型完整性 | ≥ 70% |
| 冲突缺口型诚实性 | ≥ 70% |
