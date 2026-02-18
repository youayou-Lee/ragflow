## Context

RAGFlow 已内置多个可复用组件：
- **讯问笔录 Parser**: `rag/app/interrogation.py` - 已实现 QA 对识别和 chunk_type
- **PaddleOCR Parser**: `deepdoc/parser/paddleocr_parser.py` - 已支持扫描 PDF OCR
- **LLMBundle**: `api/db/services/llm_service.py` - 已封装 LLM/Embedding 调用

二开仅需补充：
1. 起诉意见书 Chunker（参考 interrogation.py 模式）
2. Answer Gate 校验器
3. block_refs 字段扩展

## Goals / Non-Goals

**Goals:**
1. 实现起诉意见书结构化 chunking（参考现有 interrogation.py）
2. 扩展 chunk schema 支持新字段（block_refs, bbox_union）
3. 实现 Answer Gate 强制校验机制
4. 保持向后兼容，不影响现有功能

**Non-Goals:**
1. 不修改讯问笔录 Parser（复用现有）
2. 不新建 PaddleVL Parser（使用现有 PaddleOCR）
3. 不修改前端高亮系统
4. 不做 polygon 精确轮廓（MVP 用 bbox）
5. 不做多轮对话

## Decisions

### D1: 起诉意见书 Chunker 实现方式

**决定**: 参考 `rag/app/interrogation.py` 模式，新建 `rag/app/indictment.py`

**备选方案**:
1. 在 naive.py 内部根据内容特征判断 - 不够准确
2. 使用通用 chunker + 后处理 - 无法保证结构化

**理由**:
- 保持代码风格一致
- 复用 position_int 格式
- 便于后续维护

### D2: Schema 扩展方式

**决定**: 在 ES schema 中添加可选字段 + 使用 metadata JSON 双写

**备选方案**:
1. 修改 ES mapping 添加新字段并重建索引 - 成本高
2. 仅使用 metadata JSON - 查询效率低

**理由**:
- ES 新字段不需重建索引
- metadata 提供灵活性
- 兼容现有数据

### D3: Answer Gate 实现位置

**决定**: 新建 `rag/answer_gate/validator.py`，在 `dialog_service.async_chat()` 中调用

**备选方案**:
1. 在 LLM prompt 中约束 - 不可靠，LLM 可能绕过
2. 作为独立微服务 - 过度设计

**理由**:
- 同步调用，失败快速返回
- 便于测试
- 可通过配置禁用

## Risks / Trade-offs

| 风险 | 缓解措施 |
|-----|---------|
| Answer Gate 过严导致拒绝率过高 | 可配置校验强度；记录拒绝原因供调优 |
| 起诉意见书格式多样 | 先支持标准格式，非标准格式降级为 paragraph chunk |
| block_refs 数据量增加 | 只存储必要引用 {page_index, block_id}，不存储完整 block |

## Migration Plan

### 阶段 1: Schema 扩展 (PR-1)
1. 添加 ES 字段：block_refs, bbox_union
2. 验证新字段可写入/查询

### 阶段 2: 起诉意见书 Chunker (PR-2)
1. 参考 interrogation.py 实现
2. 单元测试覆盖边界情况

### 阶段 3: Answer Gate (PR-3)
1. 实现校验逻辑
2. 集成到对话流程

### 阶段 4: 检索扩展 (PR-4)
1. 返回 block_refs
2. 添加 doc_type 过滤

### 阶段 5: 集成测试 (PR-5)
1. 端到端测试
2. 金标题库验证

### 回滚策略
- 每个 PR 独立可回滚
- Answer Gate 可通过配置禁用
- 新 chunker 可通过 parser 配置切换回 naive
