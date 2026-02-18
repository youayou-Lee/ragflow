# 文档上传流程

## MODIFIED Requirements

### Requirement: 文档上传时应自动识别文书类型
系统 SHALL 在文档上传时自动调用分类服务识别文书类型，并分配对应的解析器。

#### Scenario: 上传文档自动分类
- **WHEN** 用户上传文档到知识库
- **THEN** 系统 SHALL 调用 DocumentClassifier 服务识别文档类型
- **AND** 系统 SHALL 将返回的 parser_id 设置到文档记录

#### Scenario: 分类结果覆盖 KB 默认值
- **WHEN** 文档被分类为特定类型
- **THEN** 文档的 parser_id SHALL 使用分类结果
- **AND** 不使用知识库的默认 parser_id

### Requirement: 保持现有文件类型检测
系统 SHALL 保持现有的基于文件扩展名的检测逻辑，作为内容分析的前置步骤。

#### Scenario: 图片文件使用 picture 解析器
- **WHEN** 上传图片文件（jpg, png, gif 等）
- **THEN** 系统 SHALL 直接使用 "picture" 解析器，跳过内容分析

#### Scenario: 音频文件使用 audio 解析器
- **WHEN** 上传音频文件（mp3, wav, flac 等）
- **THEN** 系统 SHALL 直接使用 "audio" 解析器，跳过内容分析

#### Scenario: 文档文件进行内容分析
- **WHEN** 上传 PDF、DOCX、TXT 等文档文件
- **THEN** 系统 SHALL 调用 DocumentClassifier 进行内容分析

## ADDED Requirements

### Requirement: 上传流程应记录分类信息
系统 SHALL 在文档记录中保存分类方法和结果信息。

#### Scenario: 保存分类元数据
- **WHEN** 文档完成分类
- **THEN** 系统 SHALL 在文档记录中保存：
  - `parser_id`: 分类结果
  - `classifier_method`: 分类方法（rule/llm/fallback）
  - `classifier_confidence`: 置信度（如适用）
