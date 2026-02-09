---
sidebar_position: 1
slug: /launch_mcp_server
sidebar_custom_props: {
  categoryIcon: LucideTvMinimalPlay
}
---
# 启动RAGFlow MCP服务器

从源代码或通过Docker启动MCP服务器。

---

RAGFlow模型上下文协议（MCP）服务器被设计为一个独立的组件，用于补充RAGFlow服务器。请注意，MCP服务器必须与正常运行运行的RAGFlow服务器一起运行。

MCP服务器可以以自托管模式（默认）或主机模式启动：

- **自托管模式**：
  在自托管模式下启动MCP服务器时，您必须提供API密钥以向RAGFlow服务器验证MCP服务器。在此模式下，MCP服务器只能访问RAGFlow服务器上指定租户的数据集。
- **主机模式**：
  在主机模式下，每个MCP客户端可以访问他们在RAGFlow服务器上的自己的数据集。但是，每个客户端请求必须包含有效的API密钥以向RAGFlow服务器验证客户端。

一旦建立连接，MCP服务器以MCP HTTP+SSE（服务器发送事件）模式与其客户端通信，单向实时将响应从RAGFlow服务器推送到其客户端。

## 先决条件

1. 确保RAGFlow已升级到v0.18.0或更高版本。
2. 准备好您的RAGFlow API密钥。请参阅[获取RAGFlow API密钥](../acquire_ragflow_api_key.md)。

:::tip 信息
如果您希望在不升级RAGFlow的情况下试用我们的MCP服务器，社区贡献者[yiminghub2024](https://github.com/yiminghub2024)👏在[这里](#launch-an-mcp-server-without-upgrading-ragflow)分享了他们推荐的步骤。
:::

## 启动MCP服务器

您可以从源代码或通过Docker启动MCP服务器。

### 从源代码启动

1. 确保RAGFlow服务器v0.18.0+正常运行。
2. 启动MCP服务器：


```bash
# 启动MCP服务器以在自托管模式下工作，运行以下任一命令
uv run mcp/server/server.py --host=127.0.0.1 --port=9382 --base-url=http://127.0.0.1:9380 --api-key=ragflow-xxxxx
# uv run mcp/server/server.py --host=127.0.0.1 --port=9382 --base-url=http://127.0.0.1:9380 --mode=self-host --api-key=ragflow-xxxxx

# 要启动MCP服务器以在主机模式下工作，请改为运行以下命令：
# uv run mcp/server/server.py --host=127.0.0.1 --port=9382 --base-url=http://127.0.0.1:9380 --mode=host
```

其中：

- `host`：MCP服务器的主机地址。
- `port`：MCP服务器的监听端口。
- `base_url`：运行的RAGFlow服务器的地址。
- `mode`：启动模式。
  - `self-host`：（默认）自托管模式。
  - `host`：主机模式。
- `api_key`：在自托管模式下需要，用于向RAGFlow服务器验证MCP服务器。有关获取API密钥的说明，请参阅[此处](../acquire_ragflow_api_key.md)。

### 传输方式

RAGFlow MCP服务器支持两种传输方式：传统的SSE传输（在`/sse`提供服务），于2024年11月5日引入，于2025年3月26日弃用，以及可流式HTTP传输（在`/mcp`提供服务）。默认情况下，传统的SSE传输和带有JSON响应的可流式HTTP传输都已启用。要禁用任一传输，请使用标志`--no-transport-sse-enabled`或`--no-transport-streamable-http-enabled`。要禁用可流式HTTP传输的JSON响应，请使用`--no-json-response`标志。

### 从Docker启动

#### 1. 启用MCP服务器

MCP服务器被设计为一个可选组件，用于补充RAGFlow服务器，默认情况下禁用。要启用MCP服务器：

1. 导航到**docker/docker-compose.yml**。
2. 取消注释`services.ragflow.command`部分，如下所示：

```yaml {6-13}
  services:
    ragflow:
      ...
      image: ${RAGFLOW_IMAGE}
      # 设置MCP服务器的示例配置：
      command:
        - --enable-mcpserver
        - --mcp-host=0.0.0.0
        - --mcp-port=9382
        - --mcp-base-url=http://127.0.0.1:9380
        - --mcp-script-path=/ragflow/mcp/server/server.py
        - --mcp-mode=self-host
        - --mcp-host-api-key=ragflow-xxxxxxx
        # RAGFlow MCP服务器的可选传输标志。
        # 如果您将`mcp-mode`设置为`host`，则必须添加--no-transport-streamable-http-enabled标志，因为主机模式下尚未支持可流式HTTP传输。
        # 默认情况下，传统的SSE传输和带有JSON响应的可流式HTTP传输都已启用。
        # 要禁用特定传输或可流式HTTP传输的JSON响应，请使用相应的标志：
        #   - --no-transport-sse-enabled # 禁用传统的SSE端点(/sse)
        #   - --no-transport-streamable-http-enabled # 禁用可流式HTTP传输（在/mcp端点提供服务）
        #   - --no-json-response # 禁用可流式HTTP传输的JSON响应
```

其中：

- `mcp-host`：MCP服务器的主机地址。
- `mcp-port`：MCP服务器的监听端口。
- `mcp-base-url`：运行的RAGFlow服务器的地址。
- `mcp-script-path`：MCP服务器主脚本的文件路径。
- `mcp-mode`：启动模式。
  - `self-host`：（默认）自托管模式。
  - `host`：主机模式。
- `mcp-host-api_key`：在自托管模式下需要，用于向RAGFlow服务器验证MCP服务器。有关获取API密钥的说明，请参阅[此处](../acquire_ragflow_api_key.md)。

:::tip 信息
如果您将`mcp-mode`设置为`host`，则必须添加`--no-transport-streamable-http-enabled`标志，因为主机模式下尚未支持可流式HTTP传输。
:::

#### 2. 启动带有MCP服务器的RAGFlow服务器

运行`docker compose -f docker-compose.yml up`以启动RAGFlow服务器以及MCP服务器。

*以下ASCII艺术图确认成功启动：*

```bash
  docker-ragflow-cpu-1  | Starting MCP Server on 0.0.0.0:9382 with base URL http://127.0.0.1:9380...
  docker-ragflow-cpu-1  | Starting 1 task executor(s) on host 'dd0b5e07e76f'...
  docker-ragflow-cpu-1  | 2025-04-18 15:41:18,816 INFO     27 ragflow_server log path: /ragflow/logs/ragflow_server.log, log levels: {'peewee': 'WARNING', 'pdfminer': 'WARNING', 'root': 'INFO'}
  docker-ragflow-cpu-1  |
  docker-ragflow-cpu-1  | __  __  ____ ____       ____  _____ ______     _______ ____
  docker-ragflow-cpu-1  | |  \/  |/ ___|  _ \     / ___|| ____|  _ \ \   / / ____|  _ \
  docker-ragflow-cpu-1  | | |\/| | |   | |_) |    \___ \|  _| | |_) \ \ / /|  _| | |_) |
  docker-ragflow-cpu-1  | | |  | | |___|  __/      ___) | |___|  _ < \ V / | |___|  _ <
  docker-ragflow-cpu-1  | |_|  |_|\____|_|        |____/|_____|_| \_\ \_/  |_____|_| \_\
  docker-ragflow-cpu-1  |
  docker-ragflow-cpu-1  | MCP launch mode: self-host
  docker-ragflow-cpu-1  | MCP host: 0.0.0.0
  docker-ragflow-cpu-1  | MCP port: 9382
  docker-ragflow-cpu-1  | MCP base_url: http://127.0.0.1:9380
  docker-ragflow-cpu-1  | INFO:     Started server process [26]
  docker-ragflow-cpu-1  | INFO:     Waiting for application startup.
  docker-ragflow-cpu-1  | INFO:     Application startup complete.
  docker-ragflow-cpu-1  | INFO:     Uvicorn running on http://0.0.0.0:9382 (Press CTRL+C to quit)
  docker-ragflow-cpu-1  | 2025-04-18 15:41:20,469 INFO     27 found 0 gpus
  docker-ragflow-cpu-1  | 2025-04-18 15:41:23,263 INFO     27 init database on cluster mode successfully
  docker-ragflow-cpu-1  | 2025-04-18 15:41:25,318 INFO     27 load_model /ragflow/rag/res/deepdoc/det.onnx uses CPU
  docker-ragflow-cpu-1  | 2025-04-18 15:41:25,367 INFO     27 load_model /ragflow/rag/res/deepdoc/rec.onnx uses CPU
  docker-ragflow-cpu-1  |         ____   ___    ______ ______ __
  docker-ragflow-cpu-1  |        / __ \ /   |  / ____// ____// /____  _      __
  docker-ragflow-cpu-1  |       / /_/ // /| | / / __ / /_   / // __ \| | /| / /
  docker-ragflow-cpu-1  |      / _, _// ___ |/ /_/ // __/  / // /_/ /| |/ |/ /
  docker-ragflow-cpu-1  |     /_/ |_|/_/  |_|\____//_/    /_/ \____/ |__/|__/
  docker-ragflow-cpu-1  |
  docker-ragflow-cpu-1  |
  docker-ragflow-cpu-1  | 2025-04-18 15:41:29,088 INFO     27 RAGFlow version: v0.18.0-285-gb2c299fa full
  docker-ragflow-cpu-1  | 2025-04-18 15:41:29,088 INFO     27 project base: /ragflow
  docker-ragflow-cpu-1  | 2025-04-18 15:41:29,088 INFO     27 Current configs, from /ragflow/conf/service_conf.yaml:
  docker-ragflow-cpu-1  |  ragflow: {'host': '0.0.0.0', 'http_port': 9380}
  ...
  docker-ragflow-cpu-1  |  * Running on all addresses (0.0.0.0)
  docker-ragflow-cpu-1  |  * Running on http://127.0.0.1:9380
  docker-ragflow-cpu-1  |  * Running on http://172.19.0.6:9380
  docker-ragflow-cpu-1  |   ______           __      ______                     __
  docker-ragflow-cpu-1  |  /_  __/___ ______/ /__   / ____/  _____  _______  __/ /_____  _____
  docker-ragflow-cpu-1  |   / / / __ `/ ___/ //_/  / __/ | |/_/ _ \/ ___/ / / / __/ __ \/ ___/
  docker-ragflow-cpu-1  |  / / / /_/ (__  ) ,<    / /____>  </  __/ /__/ /_/ / /_/ /_/ / /
  docker-ragflow-cpu-1  | /_/  \__,_/____/_/|_|  /_____/_/|_|\___/\___/\__,_/\__/\____/_/
  docker-ragflow-cpu-1  |
  docker-ragflow-cpu-1  | 2025-04-18 15:41:34,501 INFO     32 TaskExecutor: RAGFlow version: v0.18.0-285-gb2c299fa full
  docker-ragflow-cpu-1  | 2025-04-18 15:41:34,501 INFO     32 Use Elasticsearch http://es01:9200 as the doc engine.
  ...
```

#### 在不升级RAGFlow的情况下启动MCP服务器

:::info 荣誉
本部分由我们的社区贡献者[yiminghub2024](https://github.com/yiminghub2024)贡献。👏
:::

1. 准备所有MCP特定的文件和目录。
   i. 将[mcp/](https://github.com/infiniflow/ragflow/tree/main/mcp)目录复制到您的本地工作目录。
   ii. 在本地复制[docker/docker-compose.yml](https://github.com/infiniflow/ragflow/blob/main/docker/docker-compose.yml)。
   iii. 在本地复制[docker/entrypoint.sh](https://github.com/infiniflow/ragflow/blob/main/docker/entrypoint.sh)。
   iv. 使用`uv`安装所需的依赖：
       - 运行`uv add mcp`或
       - 在本地复制[pyproject.toml](https://github.com/infiniflow/ragflow/blob/main/pyproject.toml)并运行`uv sync --python 3.12`。
2. 编辑**docker-compose.yml**以启用MCP（默认情况下禁用）。
3. 启动MCP服务器：

```bash
docker compose -f docker-compose.yml up -d
```

### 检查MCP服务器状态

运行以下命令以检查RAGFlow服务器和MCP服务器的日志：

```bash
docker logs docker-ragflow-cpu-1
```

## 安全注意事项

由于MCP技术仍处于早期阶段，尚未建立身份验证或授权的官方最佳实践，RAGFlow目前使用[API密钥](./acquire_ragflow_api_key.md)来验证前面描述的操作的身份。但是，在公共环境中，这种临时解决方案可能会使您的MCP服务器暴露于潜在的网络攻击。因此，在运行本地SSE服务器时，建议仅绑定到localhost（`127.0.0.1`），而不是绑定到所有接口（`0.0.0.0`）。

有关进一步指导，请参阅[官方MCP文档](https://modelcontextprotocol.io/docs/concepts/transports#security-considerations)。

## 常见问题

### 何时使用API密钥进行身份验证？

API密钥的使用取决于MCP服务器的运行模式。

- **自托管模式**（默认）：
  在自托管模式下启动MCP服务器时，您应该在启动时提供API密钥以向RAGFlow服务器验证它：
  - 如果从源代码启动，请在命令中包含API密钥。
  - 如果从Docker启动，请在**docker/docker-compose.yml**中更新API密钥。
- **主机模式**：
  如果您的RAGFlow MCP服务器在主机模式下工作，请在客户端请求的`headers`中包含API密钥，以向RAGFlow服务器验证您的客户端。示例可在[此处](https://github.com/infiniflow/ragflow/blob/main/mcp/client/client.py)获得。
