---
sidebar_position: -6
slug: /auto_metadata
sidebar_custom_props: {
   categoryIcon: LucideFileCodeCorner
}
---
# 自动提取元数据

自动从上传的文件中提取元数据。

---

RAGFlow v0.23.0 引入了自动元数据功能，该功能使用大语言模型自动为文件生成元数据，无需手动输入。在典型的 RAG 流程中，元数据有两个关键用途：

- 在检索阶段：过滤不相关的文档，缩小搜索范围以提高检索准确性。
- 在生成阶段：如果检索到文本块，其关联的元数据也会传递给大语言模型，提供有关源文档的更丰富上下文信息以辅助答案生成。


:::danger 警告
启用目录提取需要大量内存、计算资源和令牌。
:::



## 操作步骤

1. 在数据集的 **配置** 页面上，选择一个索引模型，该模型将用于为该数据集生成知识图谱、RAPTOR、自动元数据、自动关键词和自动问题功能。

![](https://raw.githubusercontent.com/infiniflow/ragflow-docs/main/images/indexing_model.png)


2. 点击 **Auto metadata** **>** **Settings** 进入自动元数据生成规则的配置页面。

   _出现自动生成元数据规则的配置页面。_

![](https://raw.githubusercontent.com/infiniflow/ragflow-docs/main/images/auto_metadata_settings.png)

3. 点击 **+** 添加新字段并进入配置页面。

![](https://raw.githubusercontent.com/infiniflow/ragflow-docs/main/images/metadata_field_settings.png)

4. 输入字段名称，例如 Author，并在 Description 部分添加描述和示例。这为大语言模型（LLM）提供了上下文，以便更准确地提取值。如果留空，大语言模型将仅根据字段名称提取值。

5. 要限制大语言模型从预定义列表中生成元数据，请启用"限制为定义的值"模式并手动添加允许的值。大语言模型将仅从此预设范围内生成结果。

6. 配置完成后，在配置页面上打开自动元数据开关。所有新上传的文件在解析时都将应用这些规则。对于已处理的文件，必须重新解析它们以触发元数据生成。然后您可以使用过滤功能检查文件的元数据生成状态。

![](https://raw.githubusercontent.com/infiniflow/ragflow-docs/main/images/enable_auto_metadata.png)

