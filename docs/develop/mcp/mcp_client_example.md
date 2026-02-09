---
sidebar_position: 3
slug: /mcp_client
sidebar_custom_props: {
  categoryIcon: LucideBookMarked
}

---
# RAGFlow MCP客户端示例

Python和curl MCP客户端示例。

------

## 示例MCP Python客户端

我们在[这里](https://github.com/infiniflow/ragflow/blob/main/mcp/client/client.py)提供了一个用于测试的*原型*MCP客户端示例。

:::info 重要
如果您的MCP服务器在主机模式下运行，请在异步连接时在客户端的`headers`中包含您获取的API密钥：

```python
async with sse_client("http://localhost:9382/sse", headers={"api_key": "YOUR_KEY_HERE"}) as streams:
    # 您的其余代码...
```

或者，为了符合[OAuth 2.1第5节](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-12#section-5)，您可以改为运行以下代码来连接到您的MCP服务器：

```python
async with sse_client("http://localhost:9382/sse", headers={"Authorization": "YOUR_KEY_HERE"}) as streams:
    # 您的其余代码...
```
:::

## 使用curl与RAGFlow MCP服务器交互

当通过HTTP请求与MCP服务器交互时，请遵循以下初始化序列：

1. **客户端发送带有协议版本和功能的`initialize`请求**。
2. **服务器回复`initialize`响应**，包括支持的协议和功能。
3. **客户端使用`initialized`通知确认准备就绪**。
   _客户端和服务器之间建立了连接，可以进一步进行操作（例如工具列表）。_

:::tip 注意
有关此初始化过程的更多信息，请参阅[此处](https://modelcontextprotocol.io/docs/concepts/architecture#1-initialization)。
:::

在以下部分中，我们将引导您完成完整的工具调用过程。

### 1. 获取会话ID

每个与MCP服务器的curl请求都必须包含会话ID：

```bash
$ curl -N -H "api_key: YOUR_API_KEY" http://127.0.0.1:9382/sse
```

:::tip 注意
有关获取API密钥的信息，请参阅[此处](../acquire_ragflow_api_key.md)。
:::

#### 传输

传输将流式传输工具结果、服务器响应和保活ping等消息。

_服务器返回会话ID：_

```bash
event: endpoint
data: /messages/?session_id=5c6600ef61b845a788ddf30dceb25c54
```

### 2. 发送`initialize`请求

客户端发送带有协议版本和功能的`initialize`请求：

```bash
session_id="5c6600ef61b845a788ddf30dceb25c54" && \

curl -X POST "http://127.0.0.1:9382/messages/?session_id=$session_id" \
  -H "api_key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "1.0",
      "capabilities": {},
      "clientInfo": {
        "name": "ragflow-mcp-client",
        "version": "0.1"
      }
    }
  }' && \
```

#### 传输

_服务器回复`initialize`响应，包括支持的协议和功能：_

```bash
event: message
data: {"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2025-03-26","capabilities":{"experimental":{"headers":{"host":"127.0.0.1:9382","user-agent":"curl/8.7.1","accept":"*/*","api_key":"ragflow-xxxxxxxxxxxx","accept-encoding":"gzip"}},"tools":{"listChanged":false}},"serverInfo":{"name":"docker-ragflow-cpu-1","version":"1.9.4"}}}
```

### 3. 确认准备就绪

客户端使用`initialized`通知确认准备就绪：

```bash
curl -X POST "http://127.0.0.1:9382/messages/?session_id=$session_id" \
  -H "api_key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "notifications/initialized",
    "params": {}
  }' && \
```

 _客户端和服务器之间建立了连接，可以进一步进行操作（例如工具列表）。_

### 4. 工具列表

```bash
curl -X POST "http://127.0.0.1:9382/messages/?session_id=$session_id" \
  -H "api_key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/list",
    "params": {}
  }' && \
```

#### 传输

```bash
event: message
data: {"jsonrpc":"2.0","id":3,"result":{"tools":[{"name":"ragflow_retrieval","description":"从RAGFlow检索接口根据问题检索相关块，使用指定的dataset_ids和可选的document_ids。以下是所有可用数据集的列表，包括其描述和ID。如果您不确定哪些数据集与问题相关，只需将所有数据集ID传递给函数。","inputSchema":{"type":"object","properties":{"dataset_ids":{"type":"array","items":{"type":"string"}},"document_ids":{"type":"array","items":{"type":"string"}},"question":{"type":"string"}},"required":["dataset_ids","question"]}}]}}

```

### 5. 工具调用

```bash
curl -X POST "http://127.0.0.1:9382/messages/?session_id=$session_id" \
  -H "api_key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 4,
    "method": "tools/call",
    "params": {
      "name": "ragflow_retrieval",
      "arguments": {
        "question": "如何安装neovim？",
        "dataset_ids": ["DATASET_ID_HERE"],
        "document_ids": []
      }
    }
  }'
```

#### 传输

```bash
event: message
data: {"jsonrpc":"2.0","id":4,"result":{...}}

```

### 完整的curl示例

```bash
session_id="YOUR_SESSION_ID" && \

# 步骤1：初始化请求
curl -X POST "http://127.0.0.1:9382/messages/?session_id=$session_id" \
  -H "api_key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "1.0",
      "capabilities": {},
      "clientInfo": {
        "name": "ragflow-mcp-client",
        "version": "0.1"
      }
    }
  }' && \

sleep 2 && \

# 步骤2：已初始化通知
curl -X POST "http://127.0.0.1:9382/messages/?session_id=$session_id" \
  -H "api_key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "notifications/initialized",
    "params": {}
  }' && \

sleep 2 && \

# 步骤3：工具列表
curl -X POST "http://127.0.0.1:9382/messages/?session_id=$session_id" \
  -H "api_key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/list",
    "params": {}
  }' && \

sleep 2 && \

# 步骤4：工具调用
curl -X POST "http://127.0.0.1:9382/messages/?session_id=$session_id" \
  -H "api_key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 4,
    "method": "tools/call",
    "params": {
      "name": "ragflow_retrieval",
      "arguments": {
        "question": "如何安装neovim？",
        "dataset_ids": ["DATASET_ID_HERE"],
        "document_ids": []
      }
    }
  }'

```
