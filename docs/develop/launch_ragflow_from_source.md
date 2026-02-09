---
sidebar_position: 2
slug: /launch_ragflow_from_source
sidebar_custom_props: {
  categoryIcon: LucideMonitorPlay
}
---
# 从源代码启动服务

解释如何从源代码设置RAGFlow服务的指南。通过遵循本指南，您将能够使用源代码进行调试。

## 目标受众

已经添加新功能或修改现有代码并希望使用源代码进行调试的开发者，*前提是*他们的机器已设置了目标部署环境。

## 先决条件

- CPU &ge; 4核
- RAM &ge; 16 GB
- 磁盘 &ge; 50 GB
- Docker &ge; 24.0.0 & Docker Compose &ge; v2.26.1

:::tip 注意
如果您尚未在本地计算机（Windows、Mac或Linux）上安装Docker，请参阅[安装Docker引擎](https://docs.docker.com/engine/install/)指南。
:::

## 从源代码启动服务

要从源代码启动RAGFlow服务：

### 克隆RAGFlow仓库

```bash
git clone https://github.com/infiniflow/ragflow.git
cd ragflow/
```

### 安装Python依赖

1. 安装uv：

   ```bash
   pipx install uv
   ```

2. 安装RAGFlow服务的Python依赖：

   ```bash
   uv sync --python 3.12 --frozen
   ```
   *创建了一个名为`.venv`的虚拟环境，所有Python依赖都安装到新环境中。*

   如果您需要对RAGFlow服务运行测试，请安装测试依赖：

   ```bash
   uv sync --python 3.12 --group test --frozen && uv pip install sdk/python --group test
   ```

### 启动第三方服务

以下命令使用Docker Compose启动"基础"服务（MinIO、Elasticsearch、Redis和MySQL）：

```bash
docker compose -f docker/docker-compose-base.yml up -d
```

### 更新第三方服务的`host`和`port`设置

1. 将以下行添加到`/etc/hosts`以将**docker/service_conf.yaml.template**中指定的所有主机解析为`127.0.0.1`：

   ```
   127.0.0.1       es01 infinity mysql minio redis
   ```

2. 在**docker/service_conf.yaml.template**中，将mysql端口更新为`5455`，将es端口更新为`1200`，如**docker/.env**中指定的那样。

### 启动RAGFlow后端服务

1. 注释掉**docker/entrypoint.sh**中的`nginx`行。

   ```
   # /usr/sbin/nginx
   ```

2. 激活Python虚拟环境：

   ```bash
   source .venv/bin/activate
   export PYTHONPATH=$(pwd)
   ```

3. **可选：**如果您无法访问HuggingFace，请设置HF_ENDPOINT环境变量以使用镜像站点：

   ```bash
   export HF_ENDPOINT=https://hf-mirror.com
   ```

4. 检查**conf/service_conf.yaml**中的配置，确保所有主机和端口都正确设置。

5. 运行**entrypoint.sh**脚本以启动后端服务：

   ```shell
   JEMALLOC_PATH=$(pkg-config --variable=libdir jemalloc)/libjemalloc.so;
   LD_PRELOAD=$JEMALLOC_PATH python rag/svr/task_executor.py 1;
   ```
   ```shell
   python api/ragflow_server.py;
   ```

### 启动RAGFlow前端服务

1. 导航到`web`目录并安装前端依赖：

   ```bash
   cd web
   npm install
   ```

2. 将**vite.config.ts**中的`server.proxy.target`更新为`http://127.0.0.1:9380`：

   ```bash
   vim vite.config.ts
   ```

3. 启动RAGFlow前端服务：

   ```bash
   npm run dev
   ```

   *出现以下消息，显示前端服务的IP地址和端口号：*

   ![](https://github.com/user-attachments/assets/0daf462c-a24d-4496-a66f-92533534e187)

### 访问RAGFlow服务

在Web浏览器中，输入`http://127.0.0.1:<PORT>/`，确保端口号与上面屏幕截图中显示的端口号匹配。

### 开发完成后停止RAGFlow服务

1. 停止RAGFlow前端服务：
   ```bash
   pkill npm
   ```

2. 停止RAGFlow后端服务：
   ```bash
   pkill -f "docker/entrypoint.sh"
   ```
