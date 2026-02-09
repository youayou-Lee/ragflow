---
sidebar_position: 3
slug: /implement_deep_research
sidebar_custom_props: {
  categoryIcon: LucideScanSearch
}
---
# 实现深度研究

为智能体推理实现深度研究。

---

从 v0.17.0 开始,RAGFlow 支持在 AI 聊天中集成智能体推理。下图说明了 RAGFlow 深度研究的工作流程:

![Image](https://github.com/user-attachments/assets/f65d4759-4f09-4d9d-9549-c0e1fe907525)

要激活此功能:

1. 在 **聊天设置** 中启用 **推理** 切换。

![chat_reasoning](https://raw.githubusercontent.com/infiniflow/ragflow-docs/main/images/chat_reasoning.jpg)

2. 输入正确的 Tavily API 密钥以利用基于 Tavily 的 Web 搜索:

![chat_tavily](https://raw.githubusercontent.com/infiniflow/ragflow-docs/main/images/chat_tavily.jpg)

*以下是集成深度研究的对话截图:*

![Image](https://github.com/user-attachments/assets/165b88ff-1f5d-4fb8-90e2-c836b25e32e9)
