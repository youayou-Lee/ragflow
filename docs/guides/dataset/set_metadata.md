---
sidebar_position: -7
slug: /set_metadata
sidebar_custom_props: {
  categoryIcon: LucideCode
}
---
# 设置元数据

手动为上传的文件添加元数据

---

在数据集的 **Dataset** 页面上，您可以为任何上传的文件添加元数据。这种方法使您能够将 URL、作者、日期等额外信息"标记"到现有文件。在 AI 驱动的聊天中，此信息将与检索到的分块一起发送到大语言模型进行内容生成。

例如，如果您有一个 HTML 文件的数据集，并希望大语言模型在响应查询时引用源 URL，请为每个文件的元数据添加一个 `"url"` 参数。

![Set metadata](https://raw.githubusercontent.com/infiniflow/ragflow-docs/main/images/set_metadata.jpg)

:::tip 注意
确保您的元数据采用 JSON 格式，否则您的更新将不会应用。
:::

![Input metadata](https://raw.githubusercontent.com/infiniflow/ragflow-docs/main/images/input_metadata.jpg)

## 相关 API

[检索分块](../../references/http_api_reference.md#retrieve-chunks)

## 常见问题

### 我可以一次为多个文档设置元数据吗？

从 v0.23.0 开始，您可以单独为每个文档设置元数据，也可以让大语言模型为多个文件自动生成元数据。有关详细信息，请参阅[提取元数据](./auto_metadata.md)。
