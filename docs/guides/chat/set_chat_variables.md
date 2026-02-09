---
sidebar_position: 4
slug: /set_chat_variables
sidebar_custom_props: {
  categoryIcon: LucideVariable
}
---
# 设置变量

设置要与 LLM 的系统提示一起使用的变量。

---

为聊天模型配置系统提示时,变量在增强灵活性和可重用性方面起着重要作用。使用变量,您可以动态调整要发送给模型的系统提示。在 RAGFlow 的上下文中,如果您在 **聊天设置** 中定义了变量,除了系统保留变量 `{knowledge}` 之外,您需要从 RAGFlow 的 [HTTP API](../../references/http_api_reference.md#converse-with-chat-assistant) 或通过其 [Python SDK](../../references/python_api_reference.md#converse-with-chat-assistant) 传递它们的值。

:::danger 重要
在 RAGFlow 中,变量与系统提示密切相关。当您在 **变量** 部分添加变量时,请将其包含在系统提示中。反之,删除变量时,请确保将其从系统提示中删除;否则,将发生错误。
:::

## 在哪里设置变量

![](https://raw.githubusercontent.com/infiniflow/ragflow-docs/main/images/chat_variables.jpg)

## 1. 管理变量

在 **变量** 部分中,您可以添加、删除或更新变量。

### `{knowledge}` - 保留变量

`{knowledge}` 是系统的保留变量,表示从 **助手设置** 选项卡下的 **知识库** 指定的数据集中检索的块。如果您的聊天助手与某些数据集相关联,您可以保持原样。

:::info 注意
目前,`{knowledge}` 是设置为可选还是强制没有区别,但请注意这种设计将在适当的时候更新。
:::

从 v0.17.0 开始,您可以启动不指定数据集的 AI 聊天。在这种情况下,我们建议删除 `{knowledge}` 变量以避免不必要的引用,并保持 **空响应** 字段为空以避免错误。

### 自定义变量

除了 `{knowledge}` 之外,您还可以定义自己的变量以与系统提示配对。要使用这些自定义变量,必须通过 RAGFlow 的官方 API 传递它们的值。**可选** 切换确定这些变量在相应 API 中是否是必需的:

- **禁用**(默认):变量是强制性的,必须提供。
- **启用**:变量是可选的,如果不需要可以省略。

## 2. 更新系统提示

在 **变量** 部分中添加或删除变量后,请确保您的更改反映在系统提示中以避免不一致或错误。以下是一个示例:

```
您是一个智能助手。请通过总结指定数据集的块来回答问题...

您的答案应遵循专业和 {style} 的风格。

...

这是知识库:
{knowledge}
以上是知识库。
```

:::tip 注意
如果您删除了 `{knowledge}`,请确保彻底审查并更新整个系统提示以获得最佳结果。
:::

## API

传递在 **聊天配置** 对话框中定义的自定义变量值的*唯一*方法是调用 RAGFlow 的 [HTTP API](../../references/http_api_reference.md#converse-with-chat-assistant) 或通过其 [Python SDK](../../references/python_api_reference.md#converse-with-chat-assistant)。

### HTTP API

请参阅 [与聊天助手对话](../../references/http_api_reference.md#converse-with-chat-assistant)。以下是一个示例:

```json {9}
curl --request POST \
     --url http://{address}/api/v1/chats/{chat_id}/completions \
     --header 'Content-Type: application/json' \
     --header 'Authorization: Bearer <YOUR_API_KEY>' \
     --data-binary '
     {
          "question": "xxxxxxxxx",
          "stream": true,
          "style":"hilarious"
     }'
```

### Python API

请参阅 [与聊天助手对话](../../references/python_api_reference.md#converse-with-chat-assistant)。以下是一个示例:

```python {18}
from ragflow_sdk import RAGFlow

rag_object = RAGFlow(api_key="<YOUR_API_KEY>", base_url="http://<YOUR_BASE_URL>:9380")
assistant = rag_object.list_chats(name="Miss R")
assistant = assistant[0]
session = assistant.create_session()

print("\n==================== Miss R =====================\n")
print("您好。有什么我可以帮助您的吗?")

while True:
    question = input("\n==================== 用户 =====================\n> ")
    style = input("请输入您喜欢的风格(例如:正式、非正式、幽默): ")

    print("\n==================== Miss R =====================\n")

    cont = ""
    for ans in session.ask(question, stream=True, style=style):
        print(ans.content[len(cont):], end='', flush=True)
        cont = ans.content
```

