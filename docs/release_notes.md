---
sidebar_position: 2
slug: /release_notes
sidebar_custom_props: {
  sidebarIcon: LucideClipboardPenLine
}
---
# 版本发布

最新版本中的主要功能、改进和错误修复。


## v0.23.1

发布于 2025 年 12 月 31 日。

### 改进

- 记忆：增强了选择所有记忆类型时记忆提取的稳定性。
- RAG：优化了图像和表格的上下文窗口提取策略。


### 修复的问题

- 记忆：
  - 如果存在空记忆对象，RAGFlow 服务器无法启动。
  - 无法删除新创建的空记忆。
- RAG：不支持 MDX 文件解析。

### 数据源

- GitHub
- Gitlab
- Asana
- IMAP

## v0.23.0

发布于 2025 年 12 月 27 日。

### 新功能

- 记忆
   - 实现了用于管理记忆的**记忆**接口。
   - 支持通过**检索**或**消息**组件配置上下文。
- 智能体
   - 通过重构底层架构提高了**智能体**组件的性能。
   - **智能体**组件现在可以输出结构化数据供下游组件使用。
   - 支持使用 webhook 触发智能体执行。
   - 支持语音输入/输出。
   - 支持为每个**智能体**组件配置多个**检索**组件。
- 摄入流水线
  - 支持在**转换器**组件中提取目录以提高长上下文 RAG 性能。
- 数据集
   - 支持为图像和表格配置上下文窗口。
   - 引入父子分块策略。
   - 支持在文件解析期间自动生成元数据。
- 聊天：支持语音输入。

### 改进

- RAG：显著加速 GraphRAG 生成。
- 将 RAGFlow 的文档引擎 [Infinity](https://github.com/infiniflow/infinity) 升级到 v0.6.15（向后兼容）。

### 数据源

- Google Cloud Storage
- Gmail
- Dropbox
- WebDAV
- Airtable

### 模型支持

- GPT-5.2
- GPT-5.2 Pro
- GPT-5.1
- GPT-5.1 Instant
- Claude Opus 4.5
- MiniMax M2
- GLM-4.7
- MinerU 配置界面。
- AI Badgr（模型提供商）。

### API 变更

#### HTTP API

- [与智能体对话](./references/http_api_reference.md#converse-with-agent) 返回完整的执行跟踪日志。
- [创建聊天补全](./references/http_api_reference.md#create-chat-completion) 支持基于元数据的过滤。
- [与聊天助手对话](./references/http_api_reference.md#converse-with-chat-assistant) 支持基于元数据的过滤。

## v0.22.1

发布于 2025 年 11 月 19 日。

### 改进

- 智能体：
  - 支持以 Word 或 Markdown 格式导出智能体输出。
  - 添加**列表操作**组件。
  - 添加**变量聚合器**组件。
- 数据源：
  - 支持 S3 兼容数据源，例如 MinIO。
  - 添加与 JIRA 的数据同步。
- 继续重新设计**个人资料**页面布局。
- 将 Flask Web 框架从同步升级到异步，增加并发性并防止在请求上游 LLM 服务时导致的阻塞问题。

### 修复的问题

- v0.22.0 问题：用户无法解析上传的文件或在包含已解析文件的数据集中切换嵌入模型，使用的是来自 `-full` RAGFlow 版本的内置模型。
- Word 文档中的图像连接。[#11310](https://github.com/infiniflow/ragflow/pull/11310)
- 聊天历史记录中的混合图像和文本未正确显示。

### 新支持的模型

- Gemini 3 Pro Preview

## v0.22.0

发布于 2025 年 11 月 12 日。

### 重大变更

:::danger 重要
从本版本开始，我们仅发布精简版（不包含嵌入模型）Docker 镜像，并且不再在镜像标签后附加 `-slim` 后缀。
:::

### 新功能

- 数据集：
  - 支持从五个在线来源（AWS S3、Google Drive、Notion、Confluence 和 Discord）同步数据。
  - 可以在整个数据集或单个文档上构建 RAPTOR。
- 摄入流水线：在**解析器**组件中支持 [Docling 文档解析](https://github.com/docling-project/docling)。
- 推出了新的管理 Web UI 仪表板，用于图形化用户管理和服务状态监控。
- 智能体：
  - 支持结构化输出。
  - 支持**检索**组件中的元数据过滤。
  - 引入**变量聚合器**组件，具有数据操作和会话变量定义功能。

### 改进

- 智能体：支持在**等待响应**组件中可视化先前组件的输出。
- 改造模型提供商页面。
- 将 RAGFlow 的文档引擎 Infinity 升级到 v0.6.5。

### 新增模型

- Kimi-K2-Thinking

### 新的智能体模板

- 交互式智能体，结合实时用户反馈以动态优化智能体输出。

## v0.21.1

发布于 2025 年 10 月 23 日。

### 新功能

- 实验性：添加使用 MinerU 解析 PDF 文档的支持。请参阅[此处](./faq.mdx#how-to-use-mineru-to-parse-pdf-documents)。

### 改进

- 增强数据集和个人中心页面的 UI/UX。
- 将 RAGFlow 的文档引擎 [Infinity](https://github.com/infiniflow/infinity) 升级到 v0.6.1。

### 修复的问题

- 视频解析问题。

## v0.21.0

发布于 2025 年 10 月 15 日。

### 新功能

- 可编排的摄入流水线：支持定制的数据摄入和清理工作流，使用户能够灵活设计其数据流或直接在画布上应用官方数据流模板。
- GraphRAG 和 RAPTOR 写入过程优化：用手动批量构建替换自动增量构建过程，显著减少构建开销。
- 长上下文 RAG：自动生成文档级目录（TOC）结构，以缓解由于不准确或过度分块导致的上下文丢失，大幅提高检索质量。此功能现在可通过目录提取模板使用。请参阅[此处](./guides/dataset/extract_table_of_contents.md)。
- 视频文件解析：通过支持视频文件解析扩展系统的多模态数据处理能力。
- 管理 CLI：引入用于系统管理的新命令行工具，允许用户通过命令行管理和监控 RAGFlow 的服务状态。

### 改进

- 重新设计 RAGFlow 的登录和注册页面。
- 将 RAGFlow 的文档引擎 Infinity 升级到 v0.6.0。

### 新支持的模型

- 通义千问 3 系列
- Claude Sonnet 4.5
- 美团 LongCat-Flash-Thinking

### 新的智能体模板

- 公司研究报告深度分析智能体：专为金融机构设计，帮助分析师快速整理信息、生成研究报告并做出投资决策。
- 可编排的摄入流水线模板：允许用户在画布上应用此模板以快速建立标准化的数据摄入和清理流程。

## v0.20.5

发布于 2025 年 9 月 10 日。

### 改进

- 智能体：
  - 智能体性能优化：提高简单任务的规划和反思速度；优化可并行化场景的并发工具调用，显著减少整体响应时间。
  - **系统提示**部分提供了四个框架级提示块，支持在框架级别自定义和覆盖提示，从而增强灵活性和控制。请参阅[此处](./guides/agent/agent_component_reference/agent.mdx#system-prompt)。
  - **执行 SQL** 组件增强：用文本输入字段替换原始变量引用组件，允许用户编写自由格式的 SQL 查询并引用变量。请参阅[此处](./guides/agent/agent_component_reference/execute_sql.md)。
- 聊天：重新启用**推理**和**跨语言搜索**。

### 新支持的模型

- 美团 LongCat
- Kimi：kimi-k2-turbo-preview 和 kimi-k2-0905-preview
- Qwen：qwen3-max-preview
- SiliconFlow：DeepSeek V3.1

### 修复的问题

- 数据集：已删除的文件仍然可搜索。
- 聊天：无法与 Ollama 模型聊天。
- 智能体：
  - **引用**开关失败。
  - 任务模式下的智能体仍需要对话来触发。
  - 多轮对话中的重复答案。
  - 并行执行结果的重复摘要。

### API 变更

#### HTTP API

- 向[检索数据块](./references/http_api_reference.md#retrieve-chunks)方法添加主体参数 `"metadata_condition"`，支持检索期间基于元数据的数据块过滤。[#9877](https://github.com/infiniflow/ragflow/pull/9877)

#### Python API

- 向[检索数据块](./references/python_api_reference.md#retrieve-chunks)方法添加参数 `metadata_condition`，支持检索期间基于元数据的数据块过滤。[#9877](https://github.com/infiniflow/ragflow/pull/9877)

## v0.20.4

发布于 2025 年 8 月 27 日。

### 改进

- 智能体组件：完成智能体组件的中文本地化。
- 引入 `ENABLE_TIMEOUT_ASSERTION` 环境变量以启用或禁用文件解析任务的超时断言。
- 数据集：
  - 改进 Markdown 文件解析，支持 AST 以避免意外分块。
  - 增强 HTML 解析，支持基于 bs4 的 HTML 标签遍历。

### 新支持的模型

ZHIPU GLM-4.5

### 新的智能体模板

电商客户服务工作流：专为处理产品功能和多产品比较的查询以及管理安装预约预订而设计的模板。

### 修复的问题

- 数据集：
  - 无法与团队共享资源。
  - 对上传文件的数量和大小限制不当。
- 聊天：
  - 无法预览响应中的引用文件。
  - 文件上传后无法发送消息。
- OAuth2 认证失败。
- 数据集中多条件元数据搜索的逻辑错误。
- 多轮对话中的引用无限增加。

## v0.20.3

发布于 2025 年 8 月 20 日。

### 改进

- 改造**数据集**、**聊天**和**搜索**页面的用户界面。
- 搜索和聊天：引入文档级元数据过滤，支持在聊天或搜索期间自动或手动过滤。
- 搜索：支持创建适合各种业务场景的搜索应用。
- 聊天：支持在单个**聊天**页面上比较最多三个聊天模型设置的答案性能。
- 智能体：
  - 在**智能体**组件中实现开关以启用或禁用引用。
  - 引入拖放方法来创建组件。
- 文档：更正 API 参考中的不准确之处。

### 新的智能体模板

- 报告智能体：用于在内部问答场景中生成摘要报告的模板，支持显示表格和公式。[#9427](https://github.com/infiniflow/ragflow/pull/9427)

### 修复的问题

- v0.20.0 中引入的超时机制导致 GraphRAG 等任务停止。
- 对话期间**智能体**组件中缺少预定义的开场问候。
- 提示编辑器中的自动换行问题。
- PyPDF 导致的内存泄漏问题。[#9469](https://github.com/infiniflow/ragflow/pull/9469)

### API 变更

#### 已弃用

[与智能体创建会话](./references/http_api_reference.md#create-session-with-agent)

## v0.20.1

发布于 2025 年 8 月 8 日。

### 新功能

- **检索**组件现在支持使用变量动态指定数据集名称。
- 用户界面现在包括法语语言选项。

### 新支持的模型

- GPT-5
- Claude 4.1

### 新的智能体模板（工作流和智能体）

- SQL 助手工作流：使非技术团队（例如运营、产品）能够独立查询业务数据。
- 选择您的知识库工作流：让用户在对话期间选择要查询的数据集。[#9325](https://github.com/infiniflow/ragflow/pull/9325)
- 选择您的知识库智能体：通过扩展的推理时间提供更高质量的响应，适合复杂查询。[#9325](https://github.com/infiniflow/ragflow/pull/9325)

### 修复的问题

- **智能体**组件无法调用通过 vLLM 安装的模型。
- 智能体无法与团队共享。
- 将智能体嵌入网页无法正常工作。

## v0.20.0

发布于 2025 年 8 月 4 日。

### 兼容性变更

从 v0.20.0 开始，智能体不再与早期版本兼容，升级后必须重新构建以前版本的所有现有智能体。

### 新功能

- 智能体和工作流的统一编排。
- 全面重构智能体，大大增强其功能和可用性，支持多智能体配置、规划和反思以及可视化功能。
- 完全实现 MCP 功能，允许导入 MCP 服务器、智能体作为 MCP 客户端运行，以及 RAGFlow 本身作为 MCP 服务器运行。
- 访问智能体的运行时日志。
- 通过管理面板提供与智能体的聊天历史记录。
- 集成新的、更强大的 Infinity 版本，以 Infinity 作为底层文档引擎启用自动标记功能。
- 支持文件引用信息的 OpenAI 兼容 API。
- 支持新模型，包括 Kimi K2、Grok 4 和 Voyage 嵌入。
- RAGFlow 的代码库现在镜像在 Gitee 上。
- 引入新的模型提供商 Gitee AI。

### 引入的新智能体模板

- 基于多智能体的深度研究：由主导智能体与多个子智能体协作的团队合作，不同于传统工作流编排。
- 利用内部数据集的智能问答聊天机器人，专为客户服务和培训场景设计。
- RAGFlow 团队用于筛选、分析和记录候选人信息的简历分析模板。
- 将原始想法转化为 SEO 友好的博客内容的博客生成工作流。
- 智能客户服务工作流。
- 通过语义分析将用户反馈引导至适当团队的用户反馈分析模板。
- 旅行计划器：使用网络搜索和地图 MCP 服务器协助旅行规划。
- 图片翻译：翻译上传照片中的内容。
- 从内部数据集和网络检索答案的信息搜索助手。

## v0.19.1

发布于 2025 年 6 月 23 日。

### 修复的问题

- 高并发请求期间的内存泄漏问题。
- 启用 GraphRAG 实体解析时大文件解析冻结。[#8223](https://github.com/infiniflow/ragflow/pull/8223)
- 在独立模式下使用沙箱时出现的上下文错误。[#8340](https://github.com/infiniflow/ragflow/pull/8340)
- Ollama 导致的 CPU 使用率过高问题。[#8216](https://github.com/infiniflow/ragflow/pull/8216)
- 代码组件中的错误。[#7949](https://github.com/infiniflow/ragflow/pull/7949)
- 通过 API 创建数据集时添加对通过 Ollama 或 VLLM 安装的模型的支持。[#8069](https://github.com/infiniflow/ragflow/pull/8069)
- 为 S3 存储桶访问启用基于角色的身份验证。[#8149](https://github.com/infiniflow/ragflow/pull/8149)

### 新支持的模型

- Qwen 3 Embedding。[#8184](https://github.com/infiniflow/ragflow/pull/8184)
- Voyage Multimodal 3。[#7987](https://github.com/infiniflow/ragflow/pull/7987)

## v0.19.0

发布于 2025 年 5 月 26 日。

### 新功能

- 在知识和聊天模块中支持[跨语言搜索](./references/glossary.mdx#cross-language-search)，增强多语言环境（例如中英数据集）中的搜索准确性和用户体验。
- 智能体组件：新的代码组件支持 Python 和 JavaScript 脚本，使开发人员能够处理更复杂的任务，例如动态数据处理。
- 增强的图像显示：聊天和搜索中的图像现在直接在响应中渲染，而不是作为外部引用。知识检索测试可以直接检索图像，而不是从图像中提取的文本。
- Claude 4 和 ChatGPT o3：开发人员现在可以使用最新发布的、最先进的 Claude 模型和 OpenAI 最新的 ChatGPT o3 推理模型。

> 以下功能由我们的社区贡献：

- 智能体组件：在生成组件中启用工具调用。感谢 [notsyncing](https://github.com/notsyncing)。
- Markdown 渲染：markdown 文件中的图像引用可以在分块后显示。感谢 [Woody-Hu](https://github.com/Woody-Hu)。
- 文档引擎支持：OpenSearch 现在可以用作 RAGFlow 的文档引擎。感谢 [pyyuhao](https://github.com/pyyuhao)。

### 文档

#### 新增文档

- [选择 PDF 解析器](./guides/dataset/select_pdf_parser.md)
- [启用 Excel2HTML](./guides/dataset/enable_excel2html.md)
- [代码组件](./guides/agent/agent_component_reference/code.mdx)

## v0.18.0

发布于 2025 年 4 月 23 日。

### 兼容性变更

从本版本开始，内置的重新排序模型已被删除，因为它们对检索率的影响很小，但会显著增加检索时间。

### 新功能

- MCP 服务器：通过 MCP 启用对 RAGFlow 数据集的访问。
- DeepDoc 支持在文档布局识别期间采用 VLM 模型作为处理流水线，能够深入分析 PDF 和 DOCX 文件中的图像。
- OpenAI 兼容 API：可以通过 OpenAI 兼容 API 调用智能体。
- 用户注册控制：管理员可以通过环境变量启用或禁用用户注册。
- 团队协作：可以与团队成员共享智能体。
- 智能体版本控制：所有更新都被连续记录，并且可以通过导出回滚到以前的版本。

![export_agent](https://raw.githubusercontent.com/infiniflow/ragflow-docs/main/images/export_agent_as_json.jpg)

### 改进

- 增强答案引用：提高了生成响应中的引用准确性。
- 增强问答体验：用户现在可以在对话期间手动停止流式输出。

### 文档

#### 新增文档

- [设置页面排名](./guides/dataset/set_page_rank.md)
- [启用 RAPTOR](./guides/dataset/enable_raptor.md)
- [为聊天助手设置变量](./guides/chat/set_chat_variables.md)
- [启动 RAGFlow MCP 服务器](./develop/mcp/launch_mcp_server.md)

## v0.17.2

发布于 2025 年 3 月 13 日。

### 兼容性变更

- 从**聊天配置**中删除 **Max_tokens** 设置。
- 从**生成**、**重写**、**分类**、**关键词**智能体组件中删除 **Max_tokens** 设置。

从本版本开始，如果您仍然看到 RAGFlow 的响应被切断或截断，请检查您的模型提供商的 **Max_tokens** 设置。

### 改进

- 添加 OpenAI 兼容 API。
- 引入德语用户界面。
- 加速知识图谱提取。
- 在**检索**智能体组件中启用基于 Tavily 的网络搜索。
- 添加通义千问 QwQ 模型（OpenAI 兼容）。
- 在**常规**分块方法中支持 CSV 文件。

### 修复的问题

- 无法通过 Ollama/Xinference 添加模型，这是 v0.17.1 中引入的问题。

### API 变更

#### HTTP API

- [创建聊天补全](./references/http_api_reference.md#openai-compatible-api)

#### Python API

- [创建聊天补全](./references/python_api_reference.md#openai-compatible-api)

## v0.17.1

发布于 2025 年 3 月 11 日。

### 改进

- 提高英文分词质量。
- 改进 Markdown 文档解析中的表格提取逻辑。
- 更新 SiliconFlow 的模型列表。
- 支持解析 XLS 文件（Excel 97-2003）并改进相应的错误处理。
- 支持 Huggingface 重新排序模型。
- 在聊天助手和**重写**智能体组件中启用相对时间表达式（"现在"、"昨天"、"上周"、"明年"等）。

### 修复的问题

- 重复的知识图谱提取问题。
- API 调用问题。
- **PDF 解析器**（也称为**文档解析器**）下拉选项中的选项缺失。
- Tavily 网络搜索问题。
- 无法在 AI 聊天中预览图表或图像。

### 文档

#### 新增文档

- [使用标签集](./guides/dataset/use_tag_sets.md)

## v0.17.0

发布于 2025 年 3 月 3 日。

### 新功能

- AI 聊天：为智能体推理实现深度研究。要启用此功能，请在聊天助手对话框的**提示引擎**选项卡下启用**推理**开关。
- AI 聊天：利用基于 Tavily 的网络搜索增强智能体推理中的上下文。要启用此功能，请在聊天助手对话框的**助手设置**选项卡下输入正确的 Tavily API 密钥。
- AI 聊天：支持在不指定数据集的情况下开始聊天。
- AI 聊天：除了 PDF 文件外，还可以预览和引用 HTML 文件。
- 数据集：向数据集配置添加**PDF 解析器**（也称为**文档解析器**）下拉菜单。这包括 DeepDoc 模型选项，该选项耗时较长；一个更快的**朴素**选项（纯文本），跳过 DLA（文档布局分析）、OCR（光学字符识别）和 TSR（表格结构识别）任务；以及几个目前*实验性的*大型模型选项。请参阅[此处](./guides/dataset/select_pdf_parser.md)。
- 智能体组件：**(x)** 或正斜杠 `/` 可用于在**生成**或**模板**组件的系统提示字段中插入可用键（变量）。
- 对象存储：支持使用阿里云 OSS（对象存储服务）作为文件存储选项。
- 模型：更新通义千问（Qwen）支持的模型列表，添加 DeepSeek 专用模型；添加 ModelScope 作为模型提供商。
- API：可以通过 API 更新文档元数据。

以下图表说明了 RAGFlow 深度研究的工作流程：

![Image](https://github.com/user-attachments/assets/f65d4759-4f09-4d9d-9549-c0e1fe907525)

以下是集成深度研究的对话屏幕截图：

![Image](https://github.com/user-attachments/assets/165b88ff-1f5d-4fb8-90e2-c836b25e32e9)

### API 变更

#### HTTP API

向[更新文档](./references/http_api_reference.md#update-document)方法添加主体参数 `"meta_fields"`。

#### Python API

向[更新文档](./references/python_api_reference.md#update-document)方法添加键选项 `"meta_fields"`。

### 文档

#### 新增文档

- [运行检索测试](./guides/dataset/run_retrieval_test.md)

## v0.16.0

发布于 2025 年 2 月 6 日。

### 新功能

- 支持 DeepSeek R1 和 DeepSeek V3。
- GraphRAG 重构：知识图谱是在整个数据集上动态构建的，而不是在单个文件上，并且在开始解析新上传的文件时自动更新。请参阅[此处](https://ragflow.io/docs/dev/construct_knowledge_graph)。
- 添加**迭代**智能体组件和**研究报告生成器**智能体模板。请参阅[此处](./guides/agent/agent_component_reference/iteration.mdx)。
- 新的 UI 语言：葡萄牙语。
- 允许为数据集中的特定文件设置元数据，以增强 AI 驱动的聊天。请参阅[此处](./guides/dataset/set_metadata.md)。
- 将 RAGFlow 的文档引擎 [Infinity](https://github.com/infiniflow/infinity) 升级到 v0.6.0.dev3。
- 支持为 DeepDoc 启用 GPU 加速（请参阅 [docker-compose-gpu.yml](https://github.com/infiniflow/ragflow/blob/main/docker/docker-compose-gpu.yml)）。
- 支持创建和引用**标签**数据集，作为弥合查询和响应之间语义鸿沟的重要里程碑。

:::danger 重要
**标签数据集**功能在 [Infinity](https://github.com/infiniflow/infinity) 文档引擎上*不可用*。
:::

### 文档

#### 新增文档

- [构建知识图谱](./guides/dataset/construct_knowledge_graph.md)
- [设置元数据](./guides/dataset/set_metadata.md)
- [开始组件](./guides/agent/agent_component_reference/begin.mdx)
- [生成组件](./guides/agent/agent_component_reference/generate.mdx)
- [交互组件](./guides/agent/agent_component_reference/interact.mdx)
- [检索组件](./guides/agent/agent_component_reference/retrieval.mdx)
- [分类组件](./guides/agent/agent_component_reference/categorize.mdx)
- [关键词组件](./guides/agent/agent_component_reference/keyword.mdx)
- [消息组件](./guides/agent/agent_component_reference/message.mdx)
- [重写组件](./guides/agent/agent_component_reference/rewrite.mdx)
- [开关组件](./guides/agent/agent_component_reference/switch.mdx)
- [集中器组件](./guides/agent/agent_component_reference/concentrator.mdx)
- [模板组件](./guides/agent/agent_component_reference/template.mdx)
- [迭代组件](./guides/agent/agent_component_reference/iteration.mdx)
- [注释组件](./guides/agent/agent_component_reference/note.mdx)

## v0.15.1

发布于 2024 年 12 月 25 日。

### 升级

- 将 RAGFlow 的文档引擎 [Infinity](https://github.com/infiniflow/infinity) 升级到 v0.5.2。
- 增强文档解析状态的日志显示。

### 修复的问题

本版本修复了以下问题：

- [Infinity](https://github.com/infiniflow/infinity) 返回的 `SCORE not found` 和 `position_int` 错误。
- 更改特定数据集中的嵌入模型后，其他数据集中的嵌入模型无法再更改。
- 由于重复加载嵌入模型导致问答和 AI 搜索响应缓慢。
- 无法使用 RAPTOR 解析文档。
- 使用**表格**解析方法会导致信息丢失。
- 各种 API 问题。

### API 变更

#### HTTP API

向以下 API 添加可选参数 `"user_id"`：

- [与聊天助手创建会话](https://ragflow.io/docs/dev/http_api_reference#create-session-with-chat-assistant)
- [更新聊天助手的会话](https://ragflow.io/docs/dev/http_api_reference#update-chat-assistants-session)
- [列出聊天助手的会话](https://ragflow.io/docs/dev/http_api_reference#list-chat-assistants-sessions)
- [与智能体创建会话](https://ragflow.io/docs/dev/http_api_reference#create-session-with-agent)
- [与聊天助手对话](https://ragflow.io/docs/dev/http_api_reference#converse-with-chat-assistant)
- [与智能体对话](https://ragflow.io/docs/dev/http_api_reference#converse-with-agent)
- [列出智能体会话](https://ragflow.io/docs/dev/http_api_reference#list-agent-sessions)

## v0.15.0

发布于 2024 年 12 月 18 日。

### 新功能

- 引入特定于智能体的其他 API。
- 支持使用页面排名分数提高跨多个数据集搜索时的检索性能。
- 在聊天和智能体中提供 iframe，以促进将 RAGFlow 集成到您的网页中。
- 添加 Helm 图表，用于在 Kubernetes 上部署 RAGFlow。
- 支持以 JSON 格式导入或导出智能体。
- 支持对智能体组件/工具进行步骤运行。
- 添加新的 UI 语言：日语。
- 支持从故障中恢复 GraphRAG 和 RAPTOR，增强任务管理弹性。
- 添加更多 Mistral 模型。
- 向 UI 添加暗黑模式，允许用户在浅色和深色主题之间切换。

### 改进

- 升级 DeepDoc 中的文档布局分析模型。
- 显著提高使用 [Infinity](https://github.com/infiniflow/infinity) 作为文档引擎时的检索性能。

### API 变更

#### HTTP API

- [列出智能体会话](https://ragflow.io/docs/dev/http_api_reference#list-agent-sessions)
- [列出智能体](https://ragflow.io/docs/dev/http_api_reference#list-agents)

#### Python API

- [列出智能体会话](https://ragflow.io/docs/dev/python_api_reference#list-agent-sessions)
- [列出智能体](https://ragflow.io/docs/dev/python_api_reference#list-agents)

## v0.14.1

发布于 2024 年 11 月 29 日。

### 改进

添加 [Infinity 的配置文件](https://github.com/infiniflow/ragflow/blob/main/docker/infinity_conf.toml) 以方便集成和定制 [Infinity](https://github.com/infiniflow/infinity) 作为文档引擎。从本版本开始，可以直接在 RAGFlow 中更新 Infinity 的配置，并在使用 `docker compose` 重启 RAGFlow 后立即生效。[#3715](https://github.com/infiniflow/ragflow/pull/3715)

### 修复的问题

本版本修复了以下问题：

- 点击后无法显示或编辑数据块的内容。
- Elasticsearch 中的 `'Not found'` 错误。
- 解析期间中文文本变得乱码。
- 与 Polars 的兼容性问题。
- Infinity 与 GraphRAG 之间的兼容性问题。

## v0.14.0

发布于 2024 年 11 月 26 日。

### 新功能

- 支持 [Infinity](https://github.com/infiniflow/infinity) 或 Elasticsearch（默认）作为文档引擎，用于向量存储和全文索引。[#2894](https://github.com/infiniflow/ragflow/pull/2894)
- 通过向智能体添加更多变量并实现自动保存来增强用户体验。
- 添加受 [Andrew Ng 的翻译智能体](https://github.com/andrewyng/translation-agent) 启发的三步翻译智能体模板。
- 添加经过 SEO 优化的博客写作智能体模板。
- 提供与智能体对话的 HTTP 和 Python API。
- 支持在检索过程中使用英语同义词。
- 优化词权重计算，减少 50% 的检索时间。
- 通过更多性能指标改进任务执行器监控。
- 用 Valkey 替换 Redis。
- 添加三种新的 UI 语言（*由社区贡献*）：印度尼西亚语、西班牙语和越南语。

### 兼容性变更

从本版本开始，**service_config.yaml.template** 替换 **service_config.yaml** 用于配置后端服务。在 Docker 容器启动时，会自动填充此模板文件中定义的环境变量，并从中自动生成 **service_config.yaml**。[#3341](https://github.com/infiniflow/ragflow/pull/3341)

这种方法消除了在更改 **.env** 后手动更新 **service_config.yaml** 的需要，便于动态环境配置。

:::danger 重要
在尝试这种新方法之前，请确保[将您的代码**和** Docker 镜像升级到此版本](https://ragflow.io/docs/dev/upgrade_ragflow#upgrade-ragflow-to-the-most-recent-officially-published-release)。
:::

### API 变更

#### HTTP API

- [与智能体创建会话](https://ragflow.io/docs/dev/http_api_reference#create-session-with-agent)
- [与智能体对话](https://ragflow.io/docs/dev/http_api_reference#converse-with-agent)

#### Python API

- [与智能体创建会话](https://ragflow.io/docs/dev/python_api_reference#create-session-with-agent)
- [与智能体对话](https://ragflow.io/docs/dev/python_api_reference#create-session-with-agent)

### 文档

#### 新增文档

- [配置](https://ragflow.io/docs/dev/configurations)
- [管理团队成员](./guides/team/manage_team_members.md)
- [对 RAGFlow 的依赖项运行运行状况检查](https://ragflow.io/docs/dev/run_health_check)

## v0.13.0

发布于 2024 年 10 月 31 日。

### 新功能

- 为所有用户添加团队管理功能。
- 更新智能体 UI 以提高可用性。
- 在**常规**分块方法中添加对 Markdown 分块的支持。
- 在智能体 UI 中引入**调用**工具。
- 集成对 Dify 的知识库 API 的支持。
- 添加对 GLM4-9B 和 Yi-Lightning 模型的支持。
- 引入用于数据集管理、数据集内文件管理和聊天助手管理的 HTTP 和 Python API。

:::tip 注意
要下载 RAGFlow 的 Python SDK：

```bash
pip install ragflow-sdk==0.13.0
```
:::

### 文档

#### 新增文档

- [获取 RAGFlow API 密钥](./develop/acquire_ragflow_api_key.md)
- [HTTP API 参考](./references/http_api_reference.md)
- [Python API 参考](./references/python_api_reference.md)

## v0.12.0

发布于 2024 年 9 月 30 日。

### 新功能

- 提供 RAGFlow Docker 镜像的精简版，不包括内置的 BGE/BCE 嵌入或重新排序模型。
- 改进多轮对话的结果。
- 允许用户删除已添加的 LLM 提供商。
- 添加对 **OpenTTS** 和 **SparkTTS** 模型的支持。
- 在**常规**分块方法中实现 **Excel 转 HTML** 切换，允许用户将电子表格解析为 HTML 表格或按行的键值对。
- 添加智能体工具 **YahooFinance** 和 **Jin10**。
- 添加投资顾问智能体模板。

### 兼容性变更

从本版本开始，RAGFlow 提供其 Docker 镜像的精简版，以改善互联网接入有限的用户的体验。RAGFlow Docker 镜像的精简版不包括内置的 BGE/BCE 嵌入模型，大小约为 1GB；RAGFlow 的完整版约为 9GB，包括两个内置嵌入模型。

默认 Docker 镜像版本是 `nightly-slim`。以下列表阐明了各种版本之间的区别：

- `nightly-slim`：最新测试的 Docker 镜像的精简版。
- `v0.12.0-slim`：最新**官方发布**的 Docker 镜像的精简版。
- `nightly`：最新测试的 Docker 镜像的完整版。
- `v0.12.0`：最新**官方发布**的 Docker 镜像的完整版。

请参阅[升级 RAGFlow](https://ragflow.io/docs/dev/upgrade_ragflow)以获取升级说明。

### 文档

#### 新增文档

- [升级 RAGFlow](https://ragflow.io/docs/dev/upgrade_ragflow)

## v0.11.0

发布于 2024 年 9 月 14 日。

### 新功能

-  在 RAGFlow UI 中引入 AI 搜索界面。
-  通过 **FishAudio** 或 **通义千问 TTS** 支持音频输出。
-  除了 MySQL 之外，还支持使用 Postgres 进行元数据存储。
-  支持 S3 或 Azure Blob 的对象存储选项。
-  支持模型提供商：**Anthropic**、**Voyage AI** 和 **Google Cloud**。
-  支持使用 **腾讯云 ASR** 进行音频内容识别。
-  添加特定于金融的智能体组件：**问财**、**AkShare**、**YahooFinance** 和 **TuShare**。
-  添加医疗顾问智能体模板。
-  支持在以下数据集上运行检索基准测试：
    - [ms_marco_v1.1](https://huggingface.co/datasets/microsoft/ms_marco)
    - [trivia_qa](https://huggingface.co/datasets/mandarjoshi/trivia_qa)
    - [miracl](https://huggingface.co/datasets/miracl/miracl)

## v0.10.0

发布于 2024 年 8 月 26 日。

### 新功能

- 在智能体 UI 中引入文本到 SQL 模板。
- 实现智能体 API。
- 合并任务执行器的监控。
- 引入智能体工具 **GitHub**、**DeepL**、**百度翻译**、**QWeather** 和 **GoogleScholar**。
- 支持 EML 文件的分块。
- 支持更多 LLM 或模型服务：**GPT-4o-mini**、**PerfXCloud**、**TogetherAI**、**Upstage**、**Novita AI**、**01.AI**、**SiliconFlow**、**PPIO**、**讯飞星火**、**Jiekou.AI**、**百度一言**和**腾讯混元**。

## v0.9.0

发布于 2024 年 8 月 6 日。

### 新功能

- 支持 GraphRAG 作为分块方法。
- 引入智能体组件**关键词**和搜索工具，包括**百度**、**DuckDuckGo**、**PubMed**、**维基百科**、**Bing**和**Google**。
- 支持音频文件的语音转文本识别。
- 支持模型提供商 **Gemini** 和 **Groq**。
- 支持推理框架、引擎和服务，包括 **LM studio**、**OpenRouter**、**LocalAI** 和 **Nvidia API**。
- 支持在 Xinference 中使用重新排序器模型。

## v0.8.0

发布于 2024 年 7 月 8 日。

### 新功能

- 支持 Agentic RAG，支持基于图的工作流构建，用于 RAG 和智能体。
- 支持模型提供商 **Mistral**、**MiniMax**、**Bedrock** 和 **Azure OpenAI**。
- 在手动分块方法中支持 DOCX 文件。
- 在问答分块方法中支持 DOCX、MD 和 PDF 文件。

## v0.7.0

发布于 2024 年 5 月 31 日。

### 新功能

- 支持使用重新排序器模型。
- 集成重新排序器和嵌入模型：[BCE](https://github.com/netease-youdao/BCEmbedding)、[BGE](https://github.com/FlagOpen/FlagEmbedding) 和 [Jina](https://jina.ai/embeddings/)。
- 支持 LLM Baichuan 和 VolcanoArk。
- 实现 [RAPTOR](https://arxiv.org/html/2401.18059v1) 以改进文本检索。
- 在常规分块方法中支持 HTML 文件。
- 提供用于按 ID 删除文档的 HTTP 和 Python API。
- 支持 ARM64 平台。

:::danger 重要
虽然我们也在 ARM64 平台上测试 RAGFlow，但我们不为 ARM 维护 RAGFlow Docker 镜像。

如果您使用的是 ARM 平台，请遵循[此指南](./develop/build_docker_image.mdx)构建 RAGFlow Docker 镜像。
:::

### API 变更

#### HTTP API

- [删除文档](https://ragflow.io/docs/dev/http_api_reference#delete-documents)

#### Python API

- [删除文档](https://ragflow.io/docs/dev/python_api_reference#delete-documents)

## v0.6.0

发布于 2024 年 5 月 21 日。

### 新功能

- 支持流式输出。
- 提供用于检索文档数据块的 HTTP 和 Python API。
- 支持监控系统组件，包括 Elasticsearch、MySQL、Redis 和 MinIO。
- 支持在常规分块方法中禁用**布局识别**以减少文件分块时间。

### API 变更

#### HTTP API

- [检索数据块](https://ragflow.io/docs/dev/http_api_reference#retrieve-chunks)

#### Python API

- [检索数据块](https://ragflow.io/docs/dev/python_api_reference#retrieve-chunks)

## v0.5.0

发布于 2024 年 5 月 8 日。

### 新功能

- 支持 LLM DeepSeek。
