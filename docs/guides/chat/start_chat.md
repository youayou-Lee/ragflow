---
sidebar_position: 1
slug: /start_chat
sidebar_custom_props: {
  categoryIcon: LucideBot
}
---
# 开始 AI 聊天

启动基于已配置聊天助手的 AI 对话。

---

RAGFlow 中的对话基于单个或多个数据集。一旦您创建了数据集、完成了文件解析并[运行了检索测试](../dataset/run_retrieval_test.md)，就可以开始 AI 对话了。

## 开始 AI 聊天

您可以通过创建助手来开始 AI 对话。

1. 点击页面中上方的 **Chat** 选项卡 **>** **Create an assistant** 以显示**对话配置**对话框。

   > RAGFlow 为您提供了灵活性，可以为每个对话选择不同的聊天模型，同时允许您在 **系统模型设置** 中设置默认模型。

2. 更新助手特定设置：

   - **Assistant name** 是您的聊天助手的名称。每个助手对应一个具有唯一数据集组合、提示词、混合搜索配置和大模型设置的对话。
   - **Empty response**（空响应）：
     - 如果您希望将 RAGFlow 的答案**限制**在您的数据集范围内，请在此处填写响应。这样，当它未检索到答案时，将**统一**响应您在此处设置的内容。
     - 如果您希望 RAGFlow 在未从数据集检索到答案时**发挥创造力**，请将其留空，这可能会导致幻觉。
   - **Show quote**（显示引用）：这是 RAGFlow 的关键功能，默认启用。RAGFlow 不像黑盒那样工作，而是清楚地显示其响应所基于的信息来源。
   - 选择相应的数据集。您可以选择一个或多个数据集，但请确保它们使用相同的嵌入模型，否则会发生错误。

3. 更新提示词特定设置：

   - 在 **System** 中，填写大语言模型的提示词，您也可以保留默认提示词用于开始。
   - **Similarity threshold**（相似度阈值）设置每个文本块的相似度"门槛"。默认值为 0.2。相似度分数较低的文本块将被过滤掉，不会出现在最终响应中。
   - **Vector similarity weight**（向量相似度权重）默认设置为 0.3。RAGFlow 使用混合评分系统来评估不同文本块的相关性。此值设置向量相似度组件在混合评分中的权重。
     - 如果 **Rerank model** 留空，混合评分系统使用关键词相似度和向量相似度，关键词相似度组件的默认权重为 1-0.3=0.7。
     - 如果选择了 **Rerank model**，混合评分系统使用关键词相似度和重排序分数，重排序分数的默认权重为 1-0.7=0.3。
   - **Top N** 确定**最多**提供多少个文本块给大语言模型。换句话说，即使检索到更多文本块，也只有前 N 个文本块作为输入提供。
   - **Multi-turn optimization**（多轮优化）使用多轮对话中的现有上下文来增强用户查询。默认启用。启用后，它会消耗额外的大语言模型令牌，并显著增加生成答案的时间。
   - **Use knowledge graph**（使用知识图谱）表示在检索期间是否使用指定数据集中的知识图谱进行多跳问答。启用后，这将涉及跨实体、关系和社区报告文本块的迭代搜索，大大增加检索时间。
   - **Reasoning**（推理）表示是否通过 Deepseek-R1/OpenAI o1 等推理过程生成答案。启用后，聊天模型在遇到未知主题时会在问答过程中自主集成深度研究。这涉及聊天模型动态搜索外部知识并通过推理生成最终答案。
   - **Rerank model**（重排序模型）设置要使用的重排序模型。默认留空。
     - 如果 **Rerank model** 留空，混合评分系统使用关键词相似度和向量相似度，向量相似度组件的默认权重为 1-0.7=0.3。
     - 如果选择了 **Rerank model**，混合评分系统使用关键词相似度和重排序分数，重排序分数的默认权重为 1-0.7=0.3。
   - [跨语言搜索](../../references/glossary.mdx#cross-language-search)：可选
     从下拉菜单中选择一个或多个目标语言。系统的默认聊天模型随后会将您的查询翻译为所选的目标语言。这种翻译确保了跨语言的准确语义匹配，允许您无论语言差异都能检索到相关结果。
     - 选择目标语言时，请确保这些语言存在于数据集中以保证有效搜索。
     - 如果未选择目标语言，系统将仅以您的查询语言进行搜索，这可能会遗漏其他语言中的相关信息。
   - **Variable**（变量）指系统提示词中要使用的变量（键）。`{knowledge}` 是保留变量。点击 **Add** 添加更多系统提示词的变量。
      - 如果您不确定 **Variable** 背后的逻辑，请保持**原样**。
      - 从 v0.17.2 版本开始，如果您在此处添加自定义变量，传递其值的唯一方法是调用：
         - HTTP 方法 [Converse with chat assistant](../../references/http_api_reference.md#converse-with-chat-assistant)，或
         - Python 方法 [Converse with chat assistant](../../references/python_api_reference.md#converse-with-chat-assistant)。

4. 更新模型特定设置：

   - 在 **Model** 中：选择聊天模型。虽然您在 **系统模型设置** 中已经选择了默认聊天模型，但 RAGFlow 允许您为对话选择替代聊天模型。
   - **Creativity**（创造力）：**Temperature**、**Top P**、**Presence penalty** 和 **Frequency penalty** 设置的快捷方式，表示模型的自由度。从 **Improvise**（发挥）、**Precise**（精确）到 **Balance**（平衡），每个预设配置对应 **Temperature**、**Top P**、Presence penalty 和 Frequency penalty 的独特组合。
   此参数有三个选项：
      - **Improvise**：产生更具创造性的响应。
      - **Precise**：（默认）产生更保守的响应。
      - **Balance**：**Improvise** 和 **Precise** 之间的中间地带。
   - **Temperature**：模型输出的随机性级别。
   默认值为 0.1。
      - 较低的值导致更具确定性和可预测性的输出。
      - 较高的值导致更具创造性和多样化的输出。
      - 温度为零时，相同提示词会产生相同输出。
   - **Top P**：核心采样。
      - 通过设置阈值 *P* 并将采样限制为累积概率超过 *P* 的令牌，减少生成重复或不自然文本的可能性。
      - 默认值为 0.3。
   - **Presence penalty**：鼓励模型在响应中包含更多样化的令牌范围。
      - 较高的 **presence penalty** 值导致模型更有可能生成尚未包含在生成文本中的令牌。
      - 默认值为 0.4。
   - **Frequency penalty**：阻碍模型在生成文本中过于频繁地重复相同的单词或短语。
      - 较高的 **frequency penalty** 值导致模型在使用重复令牌时更加保守。
      - 默认值为 0.7。

5. 现在，让我们开始表演：

   ![chat_thermal_solution](https://raw.githubusercontent.com/infiniflow/ragflow-docs/main/images/chat_thermal_solution.jpg)

:::tip 注意

1. 点击答案上方的灯泡图标以查看扩展的系统提示词：

   ![prompt_display](https://raw.githubusercontent.com/infiniflow/ragflow-docs/main/images/prompt_display.jpg)

   *灯泡图标仅适用于当前对话。*

2. 向下滚动扩展提示词以查看每个任务消耗的时间：

   ![time_elapsed](https://raw.githubusercontent.com/infiniflow/ragflow-docs/main/images/time_elapsed.jpg)
:::

## 更新现有聊天助手的设置

![chat_setting](https://raw.githubusercontent.com/infiniflow/ragflow-docs/main/images/chat_setting.jpg)

## 将聊天功能集成到您的应用程序或网页

RAGFlow 提供 HTTP 和 Python API，供您将 RAGFlow 的功能集成到您的应用程序中。阅读以下文档了解更多信息：

- [获取 RAGFlow API 密钥](../../develop/acquire_ragflow_api_key.md)
- [HTTP API 参考](../../references/http_api_reference.md)
- [Python API 参考](../../references/python_api_reference.md)

您可以使用 iframe 将创建的聊天助手嵌入第三方网页：

1. 在继续之前，您必须[获取 API 密钥](../../develop/acquire_ragflow_api_key.md)，否则会出现错误消息。
2. 将鼠标悬停在目标聊天助手上 **>** **Edit** 以显示 **iframe** 窗口：

   ![chat-embed](https://raw.githubusercontent.com/infiniflow/ragflow-docs/main/images/embed_chat_into_webpage.jpg)

3. 复制 iframe 并将其嵌入您的网页。

![chat-embed](https://raw.githubusercontent.com/infiniflow/ragflow-docs/main/images/embedded_chat_app.jpg)
