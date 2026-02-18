# 文书类型自动识别服务

## ADDED Requirements

### Requirement: 系统应基于文档内容自动识别文书类型
系统 SHALL 在文档上传时分析文档内容，自动判断文书类型并返回对应的解析器标识。

#### Scenario: 识别讯问笔录
- **WHEN** 上传标题包含"讯问笔录"或"询问笔录"的文档
- **THEN** 系统 SHALL 返回 parser_id 为 "interrogation"

#### Scenario: 识别起诉意见书
- **WHEN** 上传标题包含"起诉意见书"的文档
- **THEN** 系统 SHALL 返回 parser_id 为 "indictment"

#### Scenario: 识别法律条文
- **WHEN** 上传格式符合法律条文特征的文档
- **THEN** 系统 SHALL 返回 parser_id 为 "laws"

#### Scenario: 无法识别时使用默认解析器
- **WHEN** 上传无法通过规则或 LLM 识别类型的文档
- **THEN** 系统 SHALL 返回 parser_id 为 "naive"（通用解析器）

### Requirement: 规则匹配应优先于 LLM 分类
系统 SHALL 优先使用规则匹配进行类型识别，仅在规则无法判断时调用 LLM。

#### Scenario: 规则匹配成功
- **WHEN** 文档内容匹配预定义规则（如标题关键词）
- **THEN** 系统 SHALL 直接返回匹配结果，不调用 LLM

#### Scenario: 规则匹配失败触发 LLM
- **WHEN** 文档内容不匹配任何预定义规则
- **THEN** 系统 SHALL 调用 LLM 进行内容分析

### Requirement: LLM 分类应使用轻量级模型
系统 SHALL 使用配置的轻量级 LLM 模型进行文档分类，以控制成本和延迟。

#### Scenario: LLM 分类成功
- **WHEN** 调用 LLM 进行分类且返回有效结果
- **THEN** 系统 SHALL 返回 LLM 判断的 parser_id

#### Scenario: LLM 分类超时
- **WHEN** LLM 调用超过设定的超时时间（默认 5 秒）
- **THEN** 系统 SHALL 返回默认 parser_id "naive"

#### Scenario: LLM 分类失败
- **WHEN** LLM 调用返回错误或无效响应
- **THEN** 系统 SHALL 返回默认 parser_id "naive"

### Requirement: 分类服务应提供日志记录
系统 SHALL 记录每次分类的结果、方法和置信度，便于后续优化。

#### Scenario: 记录分类日志
- **WHEN** 完成一次文档分类
- **THEN** 系统 SHALL 记录：文档 ID、分类方法（rule/llm）、parser_id、置信度、耗时
