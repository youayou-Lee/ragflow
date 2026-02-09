---
sidebar_position: 7
slug: /enable_raptor
sidebar_custom_props: {
  categoryIcon: LucideNetwork
}
---
# 启用 RAPTOR

一种用于长上下文知识检索和摘要的递归抽象方法，在广泛的语义理解和精细细节之间取得平衡。

---

RAPTOR（递归抽象处理用于树组织检索）是[2024 年论文](https://arxiv.org/html/2401.18059v1)中引入的一种增强文档预处理技术。旨在解决多跳问答问题，RAPTOR 对文档分块执行递归聚类和摘要，以构建分层树结构。这实现了跨长文档的更具上下文感知的检索。RAGFlow v0.6.0 将 RAPTOR 集成用于文档聚类，作为其数据预处理流程的一部分，位于数据提取和索引之间，如下图所示。

![document_clustering](https://raw.githubusercontent.com/infiniflow/ragflow-docs/main/images/document_clustering_as_preprocessing.jpg)

我们使用这种新方法的测试在需要复杂、多步推理的问答任务中展示了最先进（SOTA）的结果。通过将 RAPTOR 检索与我们内置的分块方法和/或其他检索增强生成（RAG）方法相结合，您可以进一步提高问答准确性。

:::danger 警告
启用 RAPTOR 需要大量内存、计算资源和令牌。
:::

## 基本原理

原始文档被分成分块后，分块按语义相似性进行聚类，而不是按其在文本中的原始顺序。然后，聚类的分块由系统的默认聊天模型摘要为更高级别的分块。此过程递归应用，形成一个树结构，具有从下到上的各种摘要级别。如下图所示，初始分块形成叶节点（以蓝色显示）并递归摘要为根节点（以橙色显示）。

![raptor](https://raw.githubusercontent.com/infiniflow/ragflow-docs/main/images/clustering_and_summarizing.jpg)

递归聚类和摘要捕获了广泛的理解（通过根节点）以及多跳问答所需的精细细节（通过叶节点）。

## 应用场景

对于涉及复杂、多步推理的多跳问答任务，问题与其答案之间通常存在语义差距。因此，使用问题进行搜索往往无法检索到有助于正确答案的相关分块。RAPTOR 通过为聊天模型提供更丰富、更具上下文感知和相关性的分块来总结，从而实现了全面的了解而不丢失细粒度细节，解决了这一挑战。

:::tip 注意
知识图谱也可用于多跳问答任务。有关详细信息，请参阅[构建知识图谱](./construct_knowledge_graph.md)。您可以使用其中一种或两种方法，但请确保您了解所涉及的内存、计算和令牌成本。
:::

## 先决条件

系统的默认聊天模型用于汇总聚类内容。在继续之前，请确保您已正确配置聊天模型：

![Set default models](https://raw.githubusercontent.com/infiniflow/ragflow-docs/main/images/set_default_models.jpg)

## 配置

RAPTOR 功能默认禁用。要启用它，请在数据集的 **配置** 页面上手动打开 **Use RAPTOR to enhance retrieval** 开关。

### 提示词

以下提示词将*递归*应用于聚类摘要，`{cluster_content}` 作为内部参数。我们建议您暂时保持原样。设计将适时更新。

```
Please summarize the following paragraphs... Paragraphs as following:
      {cluster_content}
The above is the content you need to summarize.
```

### 最大令牌数

每个生成的摘要分块的最大令牌数。默认为 256，最大限制为 2048。

### 阈值

在 RAPTOR 中，分块按其语义相似性进行聚类。**Threshold** 参数设置分块组合在一起所需的最小相似度。

默认为 0.1，最大限制为 1。较高的 **Threshold** 意味着每个聚类中的分块较少，较低的阈值意味着分块较多。

### 最大聚类数

要创建的最大聚类数。默认为 64，最大限制为 1024。

### 随机种子

随机种子。点击 **+** 更改种子值。

## 快速开始

1. 导航到数据集的 **配置** 页面并更新：

   - 提示词：*可选* - 我们建议您暂时保持原样，直到您了解其背后的机制。
   - 最大令牌数：*可选*
   - 阈值：*可选*
   - 最大聚类数：*可选*

2. 导航到数据集的 **Files** 页面，点击页面右上角的 **Generate** 按钮，然后从下拉菜单中选择 **RAPTOR** 以启动 RAPTOR 构建过程。

   *您可以在下拉菜单中点击暂停按钮以在必要时停止构建过程。*

3. 返回 **配置** 页面：

   *当生成 RAPTOR 分层树结构时，**RAPTOR** 字段从 `Not generated` 更改为 `Generated at a specific timestamp`。您可以点击该字段右侧的回收站按钮将其删除。*

4. 一旦生成了 RAPTOR 分层树结构，您的聊天助手和 **Retrieval** 智能体组件将默认使用它进行检索。
