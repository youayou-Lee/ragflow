---
sidebar_position: 4
slug: /enable_table_of_contents
sidebar_custom_props: {
  categoryIcon: LucideTableOfContents
}
---
# 提取目录

从文档中提取目录（TOC）以提供长上下文 RAG 并提高检索性能。

---

在索引期间，此技术使用大语言模型提取和生成章节信息，这些信息被添加到每个分块中以提供足够的全局上下文。在检索阶段，它首先使用搜索匹配的分块，然后根据目录结构补充缺失的分块。这解决了分块碎片化和上下文不足导致的问题，提高了答案质量。

:::danger 警告
启用目录提取需要大量内存、计算资源和令牌。
:::

## 先决条件

系统的默认聊天模型用于汇总聚类内容。在继续之前，请确保您已正确配置聊天模型：

![Set default models](https://raw.githubusercontent.com/infiniflow/ragflow-docs/main/images/set_default_models.jpg)

## 快速开始

1. 导航到 **配置** 页面。

2. 启用 **TOC Enhance**。

3. 要在检索期间使用此技术，请执行以下操作之一：

   - 在聊天应用的 **Chat setting** 面板中，打开 **TOC Enhance** 开关。
   - 如果您使用智能体，请点击 **Retrieval** 智能体组件以指定数据集并打开 **TOC Enhance** 开关。

## 常见问题

### 启用 `TOC Enhance` 后，以前解析的文件会使用目录增强功能进行搜索吗？

不会。只有在启用 **TOC Enhance** 之后解析的文件才会使用目录增强功能进行搜索。要将此功能应用于启用 **TOC Enhance** 之前解析的文件，必须重新解析它们。
