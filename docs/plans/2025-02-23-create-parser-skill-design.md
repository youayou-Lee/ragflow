# Create Parser Skill 设计文档

## 概述

创建一个 skill 用于标准化扩展专有文书解析方案的流程。用户调用此 skill 后，系统会自动分析文书、设计方案、编写代码、测试验证。

## Skill 元信息

| 属性 | 值 |
|------|-----|
| 名称 | `create-parser` |
| 触发方式 | 主动调用：用户说"我要为 XXX 文书创建专用解析方案" |
| 输入 | PDF 文件路径（必须）+ 可选参数 |
| 输出 | 完整的 ParserPlugin + 测试 + 文档 |

## 输入参数

```bash
/create-parser <pdf_path> [--type <doc_type>] [--llm]
```

| 参数 | 必须 | 说明 |
|------|------|------|
| `pdf_path` | 是 | 示例 PDF 文件路径 |
| `--type` | 否 | 文书类型名称，默认从 PDF 内容推断 |
| `--llm` | 否 | 强制启用 LLM 增强，默认由 skill 分析后推荐 |

## SOP 流程

### Phase 1: 分析准备

```
1.1 阅读架构文档
    → docs/criminal-parser-architecture.md
    → 了解 Layer A/B 架构、如何扩展

1.2 调用 PaddleOCR 脚本
    → python scripts/paddle_VL_1_5_full.py
    → 修改 file_path 为用户提供的 PDF
    → 输出: layout.json + output/doc_X.md

1.3 分析文书结构
    → Markdown: 分析文本内容、章节结构、触发词
    → JSON: 分析版面元素类型、位置信息
    → 输出: 文书结构分析报告
```

**分析报告模板**：
```markdown
# 文书结构分析报告

## 基本信息
- 文书类型：{推断的类型}
- 页数：X 页
- 结构复杂度：低/中/高

## 版面特征
- 是否有固定表头？
- 是否有问答结构（问：/答：）？
- 是否有编号列表？
- 是否有表格？
- 是否有印章/签名区？

## 语义结构
- 主要章节：{章节列表}
- 章节触发词：{触发词列表}
- 特殊字段：{需要提取的字段}

## 推荐方案
- 是否需要专用解析：是/否
- 是否推荐 LLM 增强：是/否
- 推荐 chunk 类型：{类型列表}
```

### Phase 2: 方案设计

```
2.1 判断是否需要专用解析方案
    → 条件：有固定章节结构 / 需要合并拆分 / 有特殊 chunk 类型
    → 不需要：直接使用 Layer A，无需插件

2.2 判断是否推荐 LLM 增强
    → 条件：复杂字段提取 / 语义理解需求 / 非结构化信息
    → 向用户展示分析结果，让用户确认

2.3 设计解析方案
    → Chunk 类型定义
    → Section triggers / 解析规则
    → 生成方案文档

2.4 用户确认方案
    → 展示完整方案
    → 用户确认或修改

2.5 使用 writing-plans skill 生成实现计划
    → 调用 /writing-plans
    → 生成详细的 task-by-task 实现计划
```

### Phase 3: 实现开发

```
3.1 创建 worktree
    → 自动生成分支名: feature/parser-{doc_type}
    → 向用户确认分支名
    → 调用 using-git-worktrees skill

3.2 使用 test-driven-development skill
    → 调用 /test-driven-development
    → 每个 chunk 类型/功能：先写失败测试 → 实现 → 测试通过
    → 包含单元测试 + 集成测试
```

**TDD 任务列表**：
1. 写 Plugin 基础结构测试 → 实现
2. 写 Section 边界识别测试 → 实现
3. 写 Chunk 生成测试 → 实现
4. 写实体合并测试 → 实现
5. 写入口函数测试 → 实现
6. 写集成测试 → 验证完整流程

### Phase 4: 验证提交

```
4.1 使用 verification-before-completion skill
    → 调用 /verification-before-completion
    → 运行所有测试
    → 确认无回归
    → 运行原有 parser 测试确保兼容

4.2 提交代码
    → 更新 docs/criminal-parser-architecture.md
    → 添加新文书类型到目录结构
    → git commit + push
```

## 文件输出

完成后会创建以下文件：

```
rag/app/criminal/plugins/
└── {doc_type}.py              # ParserPlugin 实现

rag/app/
└── {doc_type}.py              # 入口函数

test/unit/
├── test_{doc_type}_plugin.py  # 单元测试
└── test_{doc_type}_integration.py  # 集成测试
```

## 依赖的 Skills

| Skill | 调用时机 | 用途 |
|-------|----------|------|
| `writing-plans` | Phase 2.5 | 生成详细实现计划 |
| `using-git-worktrees` | Phase 3.1 | 创建隔离工作区 |
| `test-driven-development` | Phase 3.2 | TDD 流程实现 |
| `verification-before-completion` | Phase 4.1 | 完成前验证 |

## 错误处理

| 场景 | 处理方式 |
|------|----------|
| PDF 文件不存在 | 报错退出，提示正确路径 |
| OCR API 调用失败 | 报错退出，提示检查网络/Token |
| 不需要专用解析 | 告知用户，建议直接使用现有 parser |
| 测试失败 | 停止流程，进入调试模式 |
| 用户拒绝方案 | 返回修改方案，重新确认 |

## 示例调用

```
用户: 我要为起诉书创建专用解析方案，示例文件在 /path/to/qisu-shu.pdf

Skill:
1. 读取架构文档...
2. 调用 OCR 脚本...
3. 分析文书结构...

   📋 文书结构分析报告

   文书类型: 起诉书
   页数: 5 页
   结构复杂度: 中

   版面特征:
   - 固定表头: 是
   - 问答结构: 否
   - 编号列表: 是（证据项）

   语义结构:
   - 章节: 当事人信息、案件事实、证据清单、法律依据、诉讼请求
   - 触发词: "经审理查明"、"上述事实有下列证据证实"、"本院认为"

   推荐方案:
   - 需要专用解析: ✅ 是
   - LLM 增强: ❌ 不推荐（结构清晰，规则足够）
   - Chunk 类型: header, section, evidence_item

4. 是否确认此方案？[确认/修改]

用户: 确认

Skill:
5. 生成实现计划...
6. 创建 worktree: feature/parser-qisu-shu，确认？[确认/修改]

用户: 确认

Skill:
7. 使用 TDD 流程实现...
   [进度条] 测试 → 实现 → 测试通过

8. 验证完成，提交代码
```

## 设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 触发方式 | 主动调用 | 用户明确知道要做什么 |
| LLM 增强 | 分析后推荐 | 避免过度使用，节省成本 |
| 分析输入 | Markdown + JSON | 文本内容 + 版面结构结合 |
| 测试策略 | 单元测试 + 集成测试 | 全面覆盖 |
| 开发流程 | TDD | 避免返工 |
| 分支命名 | 自动生成 + 确认 | 规范且有灵活性 |
