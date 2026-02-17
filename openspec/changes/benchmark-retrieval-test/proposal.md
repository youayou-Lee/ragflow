## Why

刑事 RAG 系统已完成 PR1-PR6 的开发，需要建立系统性测试来验证检索效果。当前缺乏：
- 标准化的测试题库
- 自动化的检索效果评估
- 可追溯的测试报告

**已有资源**:
- `benchmark/起诉意见书/曾庆成危险驾驶案/` - 20 道测试题（10 事实型 + 5 证据集合型 + 5 冲突缺口型）
- `benchmark/讯问笔录/陈明飞诈骗案/` - 25 道测试题（15 事实型 + 5 证据集合型 + 5 冲突缺口型）

## What Changes

### 新增功能
- **Benchmark 检索测试脚本**: 自动化测试脚本，读取题库并调用检索 API
- **测试报告生成**: 自动生成 markdown 格式的测试报告

### 测试指标
- **事实型题目召回率**: 答案是否在检索结果中
- **证据集合型题目完整性**: 是否检索到所有相关证据
- **冲突缺口型题目诚实性**: 系统是否正确识别缺失信息（"材料未显示"）

## Capabilities

### New Capabilities
- `benchmark-retrieval-test`: 自动化检索测试脚本
- `test-report-generation`: 测试结果报告自动生成

## Impact

### 改动的文件路径
```
test/testcases/test_benchmark/test_retrieval_benchmark.py  # 新增：测试脚本
test/testcases/test_benchmark/RESULTS.md                    # 新增：测试报告
test/testcases/test_benchmark/__init__.py                   # 新增：包初始化
```

### 新增接口/字段
- 测试命令: `uv run pytest test/testcases/test_benchmark/test_retrieval_benchmark.py -v`

### 不影响
- 现有 RAG 功能
- 生产环境
