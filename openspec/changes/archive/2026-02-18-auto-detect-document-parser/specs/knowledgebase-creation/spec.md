# 知识库创建流程

## MODIFIED Requirements

### Requirement: 知识库创建应简化解析方法选择
系统 SHALL 在创建知识库时不再要求用户选择解析方法，简化创建流程。

#### Scenario: 创建知识库无需选择解析方法
- **WHEN** 用户创建新知识库
- **THEN** 系统 SHALL 仅要求提供：知识库名称、嵌入模型
- **AND** 系统 SHALL NOT 显示解析方法选择（parseType 和 parser_id）

#### Scenario: 知识库创建 API 参数变更
- **WHEN** 调用 POST /api/ckb/create 接口
- **THEN** parser_id 和 parseType 参数 SHALL 为可选
- **AND** 如果未提供，parser_id SHALL 默认为空或 "naive"

#### Scenario: 兼容已有 API 调用
- **WHEN** 调用方仍然传递 parser_id 参数
- **THEN** 系统 SHALL 接受该参数但不强制使用
- **AND** 文档上传时的自动分类 SHALL 可覆盖此默认值

## ADDED Requirements

### Requirement: 前端创建对话框应移除解析选择组件
前端 SHALL 完全移除知识库创建对话框中的 parseType 选择和 parser 方法下拉框。

#### Scenario: 创建对话框仅显示必要字段
- **WHEN** 用户打开创建知识库对话框
- **THEN** 对话框 SHALL 仅显示：知识库名称、描述（可选）、嵌入模型选择
- **AND** 对话框 SHALL NOT 显示：解析类型选择、解析方法下拉框
