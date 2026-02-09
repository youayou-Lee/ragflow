---
sidebar_position: 8
slug: /construct_knowledge_graph
sidebar_custom_props: {
  categoryIcon: LucideWandSparkles
}
---
# 构建知识图谱

为您的数据集生成知识图谱。

---

为了增强多跳问答，RAGFlow 在数据提取和索引之间添加了知识图谱构建步骤，如下图所示。此步骤从您指定的分块方法生成的现有分块中创建额外的分块。

![Image](https://github.com/user-attachments/assets/1ec21d8e-f255-4d65-9918-69b72dfa142b)

从 v0.16.0 开始，RAGFlow 支持在数据集上构建知识图谱，允许您在数据集中的多个文件之间构建*统一*的图谱。当新上传的文件开始解析时，生成的图谱将自动更新。

:::danger 警告
构建知识图谱需要大量内存、计算资源和令牌。
:::

## 应用场景

知识图谱对于涉及*嵌套*逻辑的多跳问答特别有用。当您对书籍或具有复杂实体和关系的作品进行问答时，它们的性能优于传统的提取方法。

:::tip 注意
RAPTOR（递归抽象处理用于树组织检索）也可用于多跳问答任务。有关详细信息，请参阅[启用 RAPTOR](./enable_raptor.md)。您可以使用其中一种或两种方法，但请确保您了解所涉及的内存、计算和令牌成本。
:::

## 先决条件

系统的默认聊天模型用于生成知识图谱。在继续之前，请确保您已正确配置聊天模型：

![Set default models](https://raw.githubusercontent.com/infiniflow/ragflow-docs/main/images/set_default_models.jpg)

## 配置

### 实体类型（*必需*）

要从数据集中提取的实体类型。默认类型为：**organization**（组织）、**person**（人员）、**event**（事件）和 **category**（类别）。添加或删除类型以适应您的特定数据集。

### 方法

用于构建知识图谱的方法：

- **General**（常规）：使用 [GraphRAG](https://github.com/microsoft/graphrag) 提供的提示词提取实体和关系。
- **Light**（轻量）：（默认）使用 [LightRAG](https://github.com/HKUDS/LightRAG) 提供的提示词提取实体和关系。此选项消耗更少的令牌、内存和计算资源。

### 实体解析

是否启用实体解析。您可以将其视为实体去重开关。启用后，大语言模型将合并相似的实体 - 例如，"2025"和"2025 年"，或"IT"和"信息技术" - 以构建更有效的图谱。

- （默认）禁用实体解析。
- 启用实体解析。此选项消耗更多令牌。

### 社区报告

在知识图谱中，社区是由关系链接的实体集群。您可以让大语言模型为每个社区生成一个摘要，称为社区报告。有关更多信息，请参阅[此处](https://www.microsoft.com/en-us/research/blog/graphrag-improving-global-search-via-dynamic-community-selection/)。这表示是否生成社区报告：

- 生成社区报告。此选项消耗更多令牌。
- （默认）不生成社区报告。

## 快速开始

1. 导航到数据集的 **配置** 页面并更新：

   - 实体类型：*必需* - 指定要生成的知识图谱中的实体类型。您不必坚持使用默认值，但需要为您的文档自定义它们。
   - 方法：*可选*
   - 实体解析：*可选*
   - 社区报告：*可选*
   *现在已设置数据集的默认知识图谱配置。*

2. 导航到数据集的 **Files** 页面，点击页面右上角的 **Generate** 按钮，然后从下拉菜单中选择 **Knowledge graph** 以启动知识图谱生成过程。

   *您可以在下拉菜单中点击暂停按钮以在必要时停止构建过程。*

3. 返回 **配置** 页面：

   *一旦生成知识图谱，**Knowledge graph** 字段将从 `Not generated` 更改为 `Generated at a specific timestamp`。您可以点击该字段右侧的回收站按钮将其删除。*

4. 要使用创建的知识图谱，请执行以下操作之一：

   - 在聊天应用的 **Chat setting** 面板中，打开 **Use knowledge graph** 开关。
   - 如果您使用智能体，请点击 **Retrieval** 智能体组件以指定数据集并打开 **Use knowledge graph** 开关。

## 常见问题

### 删除相关文件时知识图谱会自动更新吗？

不会。知识图谱*不会*更新，*直到*您为数据集重新生成知识图谱。

### 如何删除已生成的知识图谱？

在数据集的 **配置** 页面上，找到 **Knowledge graph** 字段并点击该字段右侧的回收站按钮。

### 创建的知识图谱存储在哪里？

创建的知识图谱的所有分块都存储在 RAGFlow 的文档引擎中：Elasticsearch 或 [Infinity](https://github.com/infiniflow/infinity)。

### 如何导出创建的知识图谱？

不支持导出创建的知识图谱。如果您仍然认为此功能至关重要，请[提出问题](https://github.com/infiniflow/ragflow/issues)解释您的用例及其重要性。
