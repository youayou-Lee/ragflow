---
sidebar_position: 4
slug: /message_component
sidebar_custom_props: {
  categoryIcon: LucideMessageSquareReply
}
---
# 消息组件

一个发送静态或动态消息的组件。

---

作为工作流的最终组件,消息组件返回工作流的最终数据输出,并附带预定义的消息内容。如果提供多个消息,系统将随机选择一条消息。

## 配置

### 状态

整个工作流完成时返回的 HTTP 状态码(`200` ~ `399`)。仅当您在 [开始](./begin.md) 组件中选择 **最终响应** 作为 **执行模式** 时可用。

### 消息

要发送的消息。点击 `(x)` 或输入 `/` 以快速插入变量。

点击 **+ 添加消息** 添加消息选项。当提供多个消息时,**消息**组件随机选择一条发送。

### 保存到记忆

将对话保存到指定的记忆。展开下拉列表以选择所有可用的记忆或指定的记忆:


![](https://raw.githubusercontent.com/infiniflow/ragflow-docs/main/images/save_to_memory.png)
