---
sidebar_position: 1
slug: /agent_introduction
sidebar_custom_props: {
  categoryIcon: LucideBookOpenText
}
---
# 简介

关键概念、基本操作、智能体编辑器快速浏览。

---

:::danger 已弃用！
新版本即将推出。
:::

## 关键概念

智能体和 RAG 是互补的技术，在业务应用中相互增强各自的能力。RAGFlow v0.8.0 引入了智能体机制，在前端提供无代码工作流编辑器，在后端提供全面的基于图的任务编排框架。该机制建立在 RAGFlow 现有的 RAG 解决方案之上，旨在编排查询意图分类、对话引导和查询重写等搜索技术，以：

- 提供更高的检索能力，并
- 适应更复杂的场景。

## 创建智能体

:::tip 注意

在继续之前，请确保：

1. 您已正确设置了要使用的 LLM。有关更多信息，请参阅[配置您的 API 密钥](../models/llm_api_key_setup.md)或[部署本地 LLM](../models/deploy_local_llm.mdx)指南。
2. 您已配置数据集并正确解析了相应的文件。有关更多信息，请参阅[配置数据集](../dataset/configure_knowledge_base.md)指南。

:::

点击页面中顶部的**智能体**选项卡以显示**智能体**页面。如以下屏幕截图所示，此页面上的卡片代表已创建的智能体，您可以继续编辑它们。

![Agent_list](https://raw.githubusercontent.com/infiniflow/ragflow-docs/main/images/agent_list.jpg)

我们还提供了针对不同业务场景的模板。您可以从我们的智能体模板之一生成智能体，或从头开始创建：

1. 点击 **+ 创建智能体**以显示**智能体模板**页面：

   ![agent_template](https://raw.githubusercontent.com/infiniflow/ragflow-docs/main/images/agent_template_list.jpg)

2. 要从头开始创建智能体，请点击**创建智能体**。或者，要从我们的模板之一创建智能体，请点击所需的卡片，例如**深度研究**，在弹出对话框中命名您的智能体，然后点击**确定**确认。

   *您现在将被带到**无代码工作流编辑器**页面。*

   ![add_component](https://raw.githubusercontent.com/infiniflow/ragflow-docs/main/images/add_component.jpg)

3. 点击**开始**组件上的**+**按钮以在工作流中选择所需的组件。
4. 点击**保存**以应用对智能体的更改。
