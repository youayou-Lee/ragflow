## Why

律师/检察官在案卷分析中高频进行"找证据—核对原文—复述结论"工作，人工查找成本高且容易遗漏。

**重要发现**：RAGFlow 已内置部分所需功能：
- 讯问笔录 Parser (`rag/app/interrogation.py`) - 已支持 QA 对识别和 chunk_type
- PaddleOCR Parser (`deepdoc/parser/paddleocr_parser.py`) - 已支持扫描 PDF OCR
- LLMBundle (`api/db/services/llm_service.py`) - 已封装 LLM/Embedding 调用

本项目基于 RAGFlow 进行二次开发，**仅需补充缺失功能**，构建面向刑事案件扫描版案卷 PDF 的"可检索、可追溯引用、可强制校验"的 RAG 问答系统。

## What Changes

### 新增功能
- **起诉意见书 Chunker**: 按触发词（如"经依法侦查查明"）切分 section/paragraph
- **Answer Gate 校验器**: 强制校验 LLM 输出，无证据返回"材料未显示"，数值必须落地
- **Block 引用机制**: chunk 存储对原始 block 的引用 (block_refs)，支持精确高亮

### 修改功能
- **Chunk Schema 扩展**: 新增 `block_refs`、`bbox_union` 字段（chunk_type 已存在）
- **检索返回结构**: 返回 `block_refs` 支持前端精确定位

### 配置/集成
- **PaddleOCR 配置**: 启用现有 PaddleOCR Parser 的版面检测功能

## Capabilities

### New Capabilities
- `indictment-chunker`: 起诉意见书 section/paragraph 切分，参考现有 interrogation.py 模式实现
- `answer-gate`: LLM 输出强制校验器（引用存在性、数值落地、无证据拦截）

### Modified Capabilities
- `chunk-schema`: 扩展 chunk 元数据字段（新增 block_refs、bbox_union）
- `retrieval-api`: 检索结果返回 block_refs 字段

### 复用现有功能（无需开发）
- `interrogation-parser`: 已存在 `rag/app/interrogation.py`
- `paddleocr-parser`: 已存在 `deepdoc/parser/paddleocr_parser.py`
- `llm-bundle`: 已存在 `api/db/services/llm_service.py`

## Impact

### 改动的文件路径
```
rag/app/indictment.py                  # 新增：起诉意见书 Chunker
rag/answer_gate/validator.py           # 新增：引用校验器
api/db/services/dialog_service.py      # 修改：集成 Answer Gate
rag/nlp/__init__.py                    # 修改：扩展 add_positions
rag/nlp/search.py                      # 修改：返回 block_refs
api/apps/chunk_app.py                  # 修改：API 响应扩展
tools/es-to-oceanbase-migration/...    # 修改：新增 ES 字段
```

### 新增接口/字段
- `IndictmentChunker.chunk()` → List[SectionChunk]
- `AnswerGate.validate(answer, raw_chunks)` → ValidationResult
- Schema 字段: `block_refs: JSON`, `bbox_union: ARRAY(Integer)`

### 不影响
- 讯问笔录解析（复用现有）
- PaddleOCR（复用现有，仅配置）
- 前端高亮系统（已支持 positions）
- 混合检索逻辑
