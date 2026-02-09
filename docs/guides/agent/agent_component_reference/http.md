---
sidebar_position: 30
slug: /http_request_component
sidebar_custom_props: {
  categoryIcon: RagHTTP
}
---
# HTTP 请求组件

一个调用远程服务的组件。

---

**HTTP 请求**组件允许您通过提供 URL 和 HTTP 方法来访问远程 API 或服务,然后接收响应。您可以自定义标头、参数、代理和超时设置,并使用 GET 和 POST 等常用方法。它对于在工作流中与外部系统交换数据很有用。

## 前提条件

- 可访问的远程 API 或服务。
- 如果目标服务需要身份验证,则向请求标头添加 Token 或凭据。

## 配置

### URL

*必需*。完整的请求地址,例如: http://api.example.com/data。

### 方法

要选择的 HTTP 请求方法。可用选项:

- GET
- POST
- PUT

### 超时

请求的最大等待时间(以秒为单位)。默认为 `60`。

### 标头

可以在此处设置自定义 HTTP 标头,例如:

```http
{
  "Accept": "application/json",
  "Cache-Control": "no-cache",
  "Connection": "keep-alive"
}
```

### 代理

可选。用于此请求的代理服务器地址。

### 清理 HTML

`Boolean`: 是否从返回的结果中删除 HTML 标签并仅保留纯文本。

### 参数

*可选*。随 HTTP 请求发送的参数。支持键值对:

- 要使用动态系统变量分配值,请将其设置为变量。
- 要在某些条件下覆盖这些动态值并改用固定的静态值,值是合适的选择。


:::tip 注意
- 对于 GET 请求,这些参数附加到 URL 的末尾。
- 对于 POST/PUT 请求,它们作为请求正文发送。
:::

#### 示例设置

![](https://raw.githubusercontent.com/infiniflow/ragflow-docs/main/images/http_settings.png)

#### 示例响应

```html
{ "args": { "App": "RAGFlow", "Query": "How to do?", "Userid": "241ed25a8e1011f0b979424ebc5b108b" }, "headers": { "Accept": "/", "Accept-Encoding": "gzip, deflate, br, zstd", "Cache-Control": "no-cache", "Host": "httpbin.org", "User-Agent": "python-requests/2.32.2", "X-Amzn-Trace-Id": "Root=1-68c9210c-5aab9088580c130a2f065523" }, "origin": "185.36.193.38", "url": "https://httpbin.org/get?Userid=241ed25a8e1011f0b979424ebc5b108b&App=RAGFlow&Query=How+to+do%3F" }
```

### 输出

HTTP 请求组件输出的全局变量名称,可由工作流中的其他组件引用。

- `Result`: `string` 远程服务返回的响应。

## 示例

这是一个使用示例:工作流从 **开始**组件通过 **HTTP Request_0** 组件向 `https://httpbin.org/get` 发送 GET 请求,将参数传递给服务器,最后通过 **Message_0** 组件输出结果。

![](https://raw.githubusercontent.com/infiniflow/ragflow-docs/main/images/http_usage.PNG)
