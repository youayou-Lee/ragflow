# 实现任务清单

## 1. 后端 - 文书分类服务

- [x] 1.1 创建 `rag/app/classifier.py` 文档分类器模块
- [x] 1.2 实现规则匹配分类逻辑（讯问笔录、起诉意见书关键词检测）
- [x] 1.3 实现 LLM 兜底分类逻辑（调用轻量级模型判断文书类型）
- [x] 1.4 添加分类日志记录功能
- [x] 1.5 编写分类器单元测试

## 2. 后端 - 知识库创建 API 改造

- [x] 2.1 修改 `api/apps/kb_app.py` 的 create 接口，parser_id 和 parseType 改为可选
- [x] 2.2 修改 `api/db/services/knowledgebase_service.py` 的 create_with_name 方法
- [x] 2.3 更新 API 文档和参数验证

## 3. 后端 - 文档上传集成分类

- [x] 3.1 修改 `api/apps/document_app.py` upload 接口，集成分类器调用（分类逻辑在 task_executor.py）
- [x] 3.2 在文档记录中保存分类元数据（parser_id, classifier_method, classifier_confidence）
- [x] 3.3 保持现有文件类型检测逻辑（图片、音频等）
- [x] 3.4 编写上传流程集成测试

## 4. 前端 - 移除解析方法选择

- [x] 4.1 修改 `web/src/pages/datasets/dataset-dataflow-creating-dialog.tsx`，移除 parseType 和 parser 选择
- [x] 4.2 移除或注释 `web/src/pages/dataset/dataset-setting/configuration/common-item.tsx` 中的 ParseTypeItem 组件（保留但不强制）
- [x] 4.3 移除或注释 ChunkMethodItem 组件（保留但不强制）
- [x] 4.4 更新表单验证逻辑（移除 parser_id 必填验证）
- [x] 4.5 更新前端类型定义

## 5. 端到端验证

- [x] 5.1 启动后端服务，验证 KB 创建 API 不再要求 parser_id
- [x] 5.2 使用 Playwright 打开前端，验证创建对话框无解析选择
- [x] 5.3 上传测试文档，验证自动分类功能
- [x] 5.4 验证讯问笔录文档被分类为 interrogation
- [x] 5.5 验证起诉意见书被分类为 indictment
- [x] 5.6 验证普通文档使用 naive 解析器

## 6. 文档和清理

- [x] 6.1 更新 CLAUDE.md 中的相关说明
- [x] 6.2 清理未使用的代码和导入
- [x] 6.3 运行 ruff format 和 ruff check 确保代码风格
