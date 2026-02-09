---
sidebar_position: 2
slug: /mcp_tools
sidebar_custom_props: {
  categoryIcon: LucideToolCase
}
---
# RAGFlow MCP工具

MCP服务器目前提供一个专用工具，用于帮助用户搜索由RAGFlow DeepDoc技术支持的相关信息：

- **检索**：使用RAGFlow检索接口从指定的`dataset_ids`和可选的`document_ids`中获取相关块，基于给定的问题。所有可用数据集的详细信息，即`id`和`description`，在工具描述中为每个单独的数据集提供。

有关更多信息，请参阅我们的[MCP服务器](https://github.com/infiniflow/ragflow/blob/main/mcp/server/server.py)的Python实现。
