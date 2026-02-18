# 自动检测文书类型解析方案

## Why

当前 RAGFlow 在创建知识库时需要用户预先选择解析方法，这对于法律案件场景不够友好：
1. 同一案件需要上传多种文书（讯问笔录、鉴定报告、起诉意见书等）
2. 不同类型文书需要不同的结构化解析方案才能获得最佳效果
3. 用户在上传前很难判断应该选择哪种解析方法

解决方案：移除知识库创建时的解析方法选择，改为上传文件时自动识别文书类型并触发对应解析逻辑。

## What Changes

### Frontend
- **BREAKING**: 移除知识库创建对话框中的 `parseType` 选择（内置/Pipeline）
- **BREAKING**: 移除知识库创建对话框中的解析方法下拉框
- 简化知识库创建流程为：名称 + 嵌入模型

### Backend
- **BREAKING**: `/api/ckb/create` 接口移除 `parser_id` 和 `parseType` 参数要求
- 新增文书类型自动识别服务：基于内容分析（LLM/规则）识别文书类型
- 上传文件时自动调用识别服务，分配对应的解析器
- 支持的法律文书类型：
  - `interrogation`: 讯问/询问笔录
  - `indictment`: 起诉意见书
  - `laws`: 其他法律文书（兜底）
  - 其他通用类型：`naive`（通用文档）

### Detection Logic
- 内容分析识别：通过 LLM 或规则匹配识别文书标题/特征
- 识别流程：
  1. 提取文档前 N 字符作为样本
  2. 调用分类模型/规则进行类型判断
  3. 返回最匹配的解析器类型

## Capabilities

### New Capabilities
- `document-type-classifier`: 文书类型自动识别服务，基于内容分析判断文档应使用的解析器

### Modified Capabilities
- `knowledgebase-creation`: 知识库创建流程简化，移除解析方法选择
- `document-upload`: 文档上传时自动识别类型并分配解析器

## Impact

### 代码改动
- `web/src/pages/datasets/dataset-creating-dialog.tsx` - 移除解析选择 UI
- `web/src/pages/dataset/dataset-setting/configuration/common-item.tsx` - 移除 ParseTypeItem/ChunkMethodItem 组件
- `api/apps/kb_app.py` - 修改 KB 创建接口参数
- `api/db/services/knowledgebase_service.py` - 修改 KB 创建逻辑
- `api/apps/document_app.py` - 上传时调用类型识别
- `api/utils/file_utils.py` - 新增内容分析函数
- `rag/app/classifier.py` (新建) - 文书类型分类器

### API 变更
- `POST /api/ckb/create`: `parser_id` 和 `parseType` 变为可选，默认不设置
- 新增内部服务：`DocumentClassifier.classify(binary, filename) -> parser_id`

### 依赖
- 需要一个轻量级 LLM 用于文档分类（可复用已有的 embedding/chat 模型配置）
