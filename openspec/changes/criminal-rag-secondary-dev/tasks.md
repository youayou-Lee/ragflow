# Implementation Tasks

## 1. Schema 扩展 (PR-1)

- [x] 1.1 在 ES schema 添加字段：`block_refs: JSON`, `bbox_union: ARRAY(Integer)`
- [x] 1.2 在 `rag/nlp/__init__.py` 的 `add_positions()` 函数中添加新字段处理
- [x] 1.3 在 `rag/svr/task_executor.py` 的 `insert_chunks()` 中存储新字段
- [x] 1.4 编写单元测试 `test/testcases/test_chunk_schema.py`
- [x] 1.5 验收：检查 ES 中新字段可写入/查询

## 2. 起诉意见书 Chunker (PR-2)

- [ ] 2.1 创建 `rag/app/indictment.py`（参考 `rag/app/interrogation.py`）
- [ ] 2.2 定义 section 触发词列表
- [ ] 2.3 实现 chunk() 方法：按触发词切分 section，段落切分（超过800字分割，参考 interrogation.py MAX_QA_LENGTH=2000）
- [ ] 2.4 可选实现 evidence_item 提取
- [ ] 2.5 计算 bbox_union 和 block_refs
- [ ] 2.6 在 `rag/svr/task_executor.py` 中注册新 chunker
- [ ] 2.7 编写单元测试 `test/testcases/test_indictment_chunker.py`
- [ ] 2.8 验收：给定样本起诉书，验证 section 切分覆盖关键段落

## 3. Answer Gate 校验器 (PR-3)

- [ ] 3.1 创建 `rag/answer_gate/validator.py`
- [ ] 3.2 实现 `AnswerGate.validate()` 方法：chunk_id 存在性校验
- [ ] 3.3 实现 excerpt 子串匹配校验
- [ ] 3.4 实现数值/日期严格落地校验（正则 + 子串匹配）
- [ ] 3.5 实现 page_index/bbox 来源校验
- [ ] 3.6 实现无证据返回逻辑（status="no_evidence"）
- [ ] 3.7 在 `api/db/services/dialog_service.py` 中集成 Answer Gate
- [ ] 3.8 编写单元测试 `test/testcases/test_answer_gate.py`
- [ ] 3.9 验收：无 evidence 返回 no_evidence；数值不在 excerpt 中返回 citation_insufficient

## 4. 检索扩展 (PR-4)

- [ ] 4.1 在 `rag/nlp/search.py:Dealer.retrieval()` 返回值中添加 block_refs
- [ ] 4.2 在 `api/apps/chunk_app.py` 的 `/list` 响应中包含 block_refs
- [ ] 4.3 添加 doc_type 过滤支持
- [ ] 4.4 确保 raw_chunks 在响应中返回
- [ ] 4.5 验收：curl 检索 API，验证响应含 block_refs 字段

## 5. 集成测试 (PR-5)

- [ ] 5.1 创建 `test/testcases/test_e2e_criminal_rag.py`
- [ ] 5.2 编写端到端测试：上传 → 解析 → 检索 → 问答 → 校验引用
- [ ] 5.3 更新 API 文档
- [ ] 5.4 验收：`uv run pytest test/testcases/test_e2e_criminal_rag.py -v`

---

## 复用现有组件（无需开发）

| 组件 | 文件路径 | 用途 |
|-----|---------|------|
| 讯问笔录 Parser | `rag/app/interrogation.py` | 直接使用 |
| PaddleOCR Parser | `deepdoc/parser/paddleocr_parser.py` | 直接使用 |
| LLMBundle | `api/db/services/llm_service.py` | 直接使用 |

---

## 验收命令

```bash
# PR1 Schema 扩展验收测试（包含边界值、集成、Schema验证、负面测试、业务场景）
uv run pytest test/unit/test_chunk_schema.py test/unit/test_chunk_schema_extended.py -v

# 带覆盖率的 PR1 验收
uv run pytest test/unit/test_chunk_schema.py test/unit/test_chunk_schema_extended.py -v \
  --cov=rag/nlp --cov-report=term-missing

# 仅运行 p1 优先级测试
uv run pytest test/unit/ -v -m p1

# 生成 CI 报告
uv run pytest test/unit/test_chunk_schema.py test/unit/test_chunk_schema_extended.py -v \
  --junitxml=test-results/pr1-acceptance.xml

# 其他 PR 验收命令
uv run pytest test/testcases/test_indictment_chunker.py -v
uv run pytest test/testcases/test_answer_gate.py -v
uv run pytest test/testcases/test_e2e_criminal_rag.py -v
```
