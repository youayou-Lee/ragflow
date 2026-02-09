---
sidebar_position: -8
slug: /set_context_window
sidebar_custom_props: {
   categoryIcon: LucideListChevronsUpDown
}
---
# 设置上下文窗口大小

为图像和表格设置上下文窗口大小以提高长上下文 RAG 性能。

---

RAGFlow 利用内置的 DeepDoc 以及外部文档模型（如 MinerU 和 Docling）来解析文档布局。在以前的版本中，基于文档布局提取的图像和表格被视为独立的分块。因此，如果搜索查询不直接与图像或表格的内容匹配，这些元素将不会被检索到。然而，现实世界的文档经常将图表和表格与周围的文本交织在一起，这些文本通常描述它们。因此，基于此上下文文本召回图表是一项基本能力。

为了解决这一问题，RAGFlow 0.23.0 引入了 **Image & table context window**（图像和表格上下文窗口）功能。受专注于研究的开源多模态 RAG 项目 RAG-Anything 的关键原则启发，此功能允许基于用户可配置的窗口大小将周围的文本和相邻的视觉元素组合成单个分块。这确保它们被一起检索，显著提高了图表和表格的召回准确性。

## 操作步骤

1. 在数据集的 **配置** 页面上，找到 **Image & table context window** 滑块：

![](https://raw.githubusercontent.com/infiniflow/ragflow-docs/main/images/image_table_context_window.png)


2. 根据您的需要调整上下文令牌的数量。

   *红框中的数字表示将从图像/表格上方和下方捕获大约 **N 个令牌**的文本，并将其作为上下文信息插入到图像或表格分块中。捕获过程在标点符号处智能优化边界以保持语义完整性。*

