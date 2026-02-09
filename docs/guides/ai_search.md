---
sidebar_position: 2
slug: /ai_search
sidebar_custom_props: {
  categoryIcon: LucideSearch
}
---
# 搜索

进行 AI 搜索。

---

AI 搜索是使用预定义检索策略(加权关键字相似性和加权向量相似性的混合搜索)和系统默认聊天模型的单轮 AI 对话。它不涉及高级 RAG 策略,如知识图谱、自动关键字或自动问题。相关块按其相似性分数降序列在聊天模型响应下方。

![Create search app](https://raw.githubusercontent.com/infiniflow/ragflow-docs/main/images/create_search_app.jpg)

![Search view](https://raw.githubusercontent.com/infiniflow/ragflow-docs/main/images/search_view.jpg)

:::tip 注意
调试聊天助手时,您可以使用 AI 搜索作为参考来验证您的模型设置和检索策略。
:::

## 前提条件

- 确保您已在 **模型提供商** 页面上配置了系统默认模型。
- 确保预期的数据集已正确配置,预期的文档已完成文件解析。

## 常见问题

### AI 搜索和 AI 聊天的主要区别?

聊天是多轮 AI 对话,您可以定义检索策略(可以使用加权重排序分数替换混合搜索中的加权向量相似性)并选择您的聊天模型。在 AI 聊天中,您可以为您的特定情况配置高级 RAG 策略,例如知识图谱、自动关键字和自动问题。检索的块不会与答案一起显示。
