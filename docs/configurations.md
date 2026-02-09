---
sidebar_position: 1
slug: /configurations
sidebar_custom_props: {
  sidebarIcon: LucideCog
}
---
# 配置

通过Docker部署RAGFlow的配置。

## 指南

在进行系统配置时，您需要管理以下文件：

- [.env](https://github.com/infiniflow/ragflow/blob/main/docker/.env)：包含Docker的重要环境变量。
- [service_conf.yaml.template](https://github.com/infiniflow/ragflow/blob/main/docker/service_conf.yaml.template)：配置后端服务。它指定RAGFlow的系统级配置，由其API服务器和任务执行器使用。容器启动时，将基于此模板文件生成`service_conf.yaml`文件。此过程会替换模板内的任何环境变量，允许根据容器环境进行动态配置。
- [docker-compose.yml](https://github.com/infiniflow/ragflow/blob/main/docker/docker-compose.yml)：用于启动RAGFlow服务的Docker Compose文件。

要更新默认的HTTP服务端口（80），请转到[docker-compose.yml](https://github.com/infiniflow/ragflow/blob/main/docker/docker-compose.yml)并将`80:80`更改为`<YOUR_SERVING_PORT>:80`。

:::tip 注意
对上述配置的更新需要重新启动所有容器才能生效：

```bash
docker compose -f docker/docker-compose.yml up -d
```

:::

## Docker Compose

- **docker-compose.yml**
  为RAGFlow及其依赖项设置环境。
- **docker-compose-base.yml**
  为RAGFlow的依赖项设置环境：Elasticsearch/[Infinity](https://github.com/infiniflow/infinity)、MySQL、MinIO和Redis。

:::danger 重要
我们不积极维护**docker-compose-CN-oc9.yml**、**docker-compose-macos.yml**，因此使用它们的风险自负。但是，欢迎您提交拉取请求来改进它们。
:::

## Docker环境变量

[.env](https://github.com/infiniflow/ragflow/blob/main/docker/.env)文件包含Docker的重要环境变量。

### Elasticsearch

- `STACK_VERSION`
  Elasticsearch的版本。默认为`8.11.3`。
- `ES_PORT`
  用于将Elasticsearch服务暴露给主机的端口，允许从主机**外部**访问Docker容器内运行的服务。默认为`1200`。
- `ELASTIC_PASSWORD`
  Elasticsearch的密码。

### Kibana

- `KIBANA_PORT`
  用于将Kibana服务暴露给主机的端口，允许从主机**外部**访问Docker容器内运行的服务。默认为`6601`。
- `KIBANA_USER`
  Kibana的用户名。默认为`rag_flow`。
- `KIBANA_PASSWORD`
  Kibana的密码。默认为`infini_rag_flow`。

### 资源管理

- `MEM_LIMIT`
  *特定*Docker容器在运行时可以使用的最大内存量（以字节为单位）。默认为`8073741824`。

### MySQL

- `MYSQL_PASSWORD`
  MySQL的密码。
- `MYSQL_PORT`
  从RAGFlow容器连接MySQL的端口。默认为`3306`。如果您使用外部MySQL，请更改此端口。
- `EXPOSE_MYSQL_PORT`
  用于将MySQL服务暴露给主机的端口，允许从主机**外部**访问Docker容器内运行的MySQL数据库。默认为`5455`。

### MinIO

RAGFlow利用MinIO作为其对象存储解决方案，利用其可扩展性来存储和管理所有上传的文件。

- `MINIO_CONSOLE_PORT`
  用于将MinIO控制台界面暴露给主机的端口，允许从主机**外部**访问Docker容器内运行的基于Web的控制台。默认为`9001`。
- `MINIO_PORT`
  用于将MinIO API服务暴露给主机的端口，允许从主机**外部**访问Docker容器内运行的MinIO对象存储服务。默认为`9000`。
- `MINIO_USER`
  MinIO的用户名。
- `MINIO_PASSWORD`
  MinIO的密码。

### Redis

- `REDIS_PORT`
  用于将Redis服务暴露给主机的端口，允许从主机**外部**访问Docker容器内运行的Redis服务。默认为`6379`。
- `REDIS_USERNAME`
  使用Redis 6+身份验证时的可选Redis ACL用户名。
- `REDIS_PASSWORD`
  Redis的密码。

### RAGFlow

- `SVR_HTTP_PORT`
  用于将RAGFlow的HTTP API服务暴露给主机的端口，允许从主机**外部**访问Docker容器内运行的服务。默认为`9380`。
- `RAGFLOW-IMAGE`
  Docker镜像版本。默认为`infiniflow/ragflow:v0.23.1`（不包含嵌入模型的RAGFlow Docker镜像）。

:::tip 注意
如果您无法下载RAGFlow Docker镜像，请尝试以下镜像。

- 对于`nightly`版本：
  - `RAGFLOW_IMAGE=swr.cn-north-4.myhuaweicloud.com/infiniflow/ragflow:nightly`或，
  - `RAGFLOW_IMAGE=registry.cn-hangzhou.aliyuncs.com/infiniflow/ragflow:nightly`。
:::

### 嵌入服务

- `TEI_MODEL`
  text-embeddings-inference服务的嵌入模型。允许的值包括`Qwen/Qwen3-Embedding-0.6B`（默认）、`BAAI/bge-m3`和`BAAI/bge-small-en-v1.5`之一。

- `TEI_PORT`
  用于将text-embeddings-inference服务暴露给主机的端口，允许从主机**外部**访问Docker容器内运行的text-embeddings-inference服务。默认为`6380`。

### 时区

- `TZ`
  本地时区。默认为`Asia/Shanghai`。

### Hugging Face镜像站点

- `HF_ENDPOINT`
  huggingface.co的镜像站点。默认情况下禁用。如果您对主要Hugging Face域名的访问受限，可以取消注释此行。

### MacOS

- `MACOS`
  macOS的优化。默认情况下禁用。如果您的操作系统是macOS，可以取消注释此行。

### 用户注册

- `REGISTER_ENABLED`
  - `1`：（默认）启用用户注册。
  - `0`：禁用用户注册。

## 服务配置

[service_conf.yaml.template](https://github.com/infiniflow/ragflow/blob/main/docker/service_conf.yaml.template)指定RAGFlow的系统级配置，由其API服务器和任务执行器使用。

### `ragflow`

- `host`：Docker容器内API服务器的IP地址。默认为`0.0.0.0`。
- `port`：Docker容器内API服务器的服务端口。默认为`9380`。

### `mysql`

- `name`：MySQL数据库名称。默认为`rag_flow`。
- `user`：MySQL的用户名。
- `password`：MySQL的密码。
- `port`：Docker容器内MySQL的服务端口。默认为`3306`。
- `max_connections`：MySQL数据库的最大并发连接数。默认为`100`。
- `stale_timeout`：超时时间（以秒为单位）。

### `minio`

- `user`：MinIO的用户名。
- `password`：MinIO的密码。
- `host`：Docker容器内MinIO的服务IP*和*端口。默认为`minio:9000`。

### `redis`

- `host`：Docker容器内Redis的服务IP*和*端口。默认为`redis:6379`。
- `db`：要使用的Redis数据库索引。默认为`1`。
- `username`：可选的Redis ACL用户名（Redis 6+）。
- `password`：指定Redis用户的密码。

### `oauth`

使用第三方帐户注册或登录RAGFlow的OAuth配置。

- `<channel>`：自定义频道ID。
  - `type`：身份验证类型，选项包括`oauth2`、`oidc`、`github`。默认为`oauth2`，当提供`issuer`参数时，默认为`oidc`。
  - `icon`：图标ID，选项包括`github`、`sso`，默认为`sso`。
  - `display_name`：频道名称，默认为频道ID的标题大小写格式。
  - `client_id`：必需，分配给客户端应用程序的唯一标识符。
  - `client_secret`：必需，客户端应用程序的密钥，用于与身份验证服务器通信。
  - `authorization_url`：获取用户授权的基础URL。
  - `token_url`：交换授权代码并获取访问令牌的URL。
  - `userinfo_url`：获取用户信息（用户名、电子邮件等）的URL。
  - `issuer`：身份提供者的基础URL。OIDC客户端可以通过`issuer`动态获取身份提供者的元数据（`authorization_url`、`token_url`、`userinfo_url`）。
  - `scope`：请求的权限范围，以空格分隔的字符串。例如，`openid profile email`。
  - `redirect_uri`：必需，身份验证服务器在身份验证流程期间重定向以返回结果的URI。必须与在身份验证服务器注册的回调URI匹配。格式：`https://your-app.com/v1/user/oauth/callback/<channel>`。对于本地配置，您可以直接使用`http://127.0.0.1:80/v1/user/oauth/callback/<channel>`。

:::tip 注意
以下是配置各种第三方身份验证方法的最佳实践。您可以为Ragflow配置一个或多个第三方身份验证方法：
```yaml
oauth:
  oauth2:
    display_name: "OAuth2"
    client_id: "your_client_id"
    client_secret: "your_client_secret"
    authorization_url: "https://your-oauth-provider.com/oauth/authorize"
    token_url: "https://your-oauth-provider.com/oauth/token"
    userinfo_url: "https://your-oauth-provider.com/oauth/userinfo"
    redirect_uri: "https://your-app.com/v1/user/oauth/callback/oauth2"

  oidc:
    display_name: "OIDC"
    client_id: "your_client_id"
    client_secret: "your_client_secret"
    issuer: "https://your-oauth-provider.com/oidc"
    scope: "openid email profile"
    redirect_uri: "https://your-app.com/v1/user/oauth/callback/oidc"

  github:
    # https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/creating-an-oauth-app
    type: "github"
    icon: "github"
    display_name: "Github"
    client_id: "your_client_id"
    client_secret: "your_client_secret"
    redirect_uri: "https://your-app.com/v1/user/oauth/callback/github"
```
:::

### `user_default_llm`

新RAGFlow用户使用的默认LLM。默认情况下禁用。要启用此功能，请在**service_conf.yaml.template**中取消注释相应的行。

- `factory`：LLM供应商。可用选项：
  - `"OpenAI"`
  - `"DeepSeek"`
  - `"Moonshot"`
  - `"Tongyi-Qianwen"`
  - `"VolcEngine"`
  - `"ZHIPU-AI"`
- `api_key`：指定LLM的API密钥。您需要在线申请您的模型API密钥。
- `allowed_factories`：如果设置了此项，用户将只能添加此列表中的供应商。
  - `"OpenAI"`
  - `"DeepSeek"`
  - `"Moonshot"`

:::tip 注意
如果您在此处未设置默认LLM，请在RAGFlow UI的**设置**页面上配置默认LLM。
:::
