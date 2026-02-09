---
sidebar_position: 20
slug: /sandbox_quickstart
sidebar_custom_props: {
  categoryIcon: LucideCodesandbox
}
---
# 沙箱快速入门

一个安全的、可插拔的代码执行后端,专为 RAGFlow 和其他需要隔离代码执行环境的应用程序而设计。

## 功能:

- 无缝 RAGFlow 集成 — 开箱即用,与 RAGFlow 的代码组件配合使用。
- 高安全性 — 使用 gVisor 进行系统调用级别的沙箱隔离以隔离执行。
- 可定制的沙箱 — 轻松修改 seccomp 配置文件以定制系统调用限制。
- 可插拔运行时支持 — 可扩展以支持任何编程语言运行时。
- 开发者友好 — 使用方便的 Makefile 快速设置。

## 架构

架构由每个支持的语言运行时的隔离 Docker 基础镜像组成,由执行器管理器服务管理。执行器管理器使用 gVisor 进行系统调用拦截和可选的 seccomp 配置文件进行增强的系统调用过滤来编排沙箱代码执行。

## 前提条件

- 与 gVisor 兼容的 Linux 发行版。
- gVisor 已安装并配置。
- Docker 版本 25.0 或更高(API 1.44+)。确保您的执行器管理器镜像附带 Docker CLI `29.1.0` 或更高版本,以保持与最新 Docker 守护程序的兼容性。
- Docker Compose 版本 2.26.1 或更高版本(类似于 RAGFlow 要求)。
- uv 包和项目管理器已安装。
- (可选) GNU Make 用于简化的命令行管理。

:::tip 注意
错误消息 `client version 1.43 is too old. Minimum supported API version is 1.44` 表示您的执行器管理器镜像的内置 Docker CLI 版本低于所使用的 Docker 守护程序要求的 `29.1.0`。要解决此问题,请从 Docker Hub 拉取最新的 `infiniflow/sandbox-executor-manager:latest` 或在 `./sandbox/executor_manager` 中重新构建它。
:::

## 构建 Docker 基础镜像

沙箱使用隔离的基础镜像来实现安全的容器化执行环境。

手动构建基础镜像:

```bash
docker build -t sandbox-base-python:latest ./sandbox_base_image/python
docker build -t sandbox-base-nodejs:latest ./sandbox_base_image/nodejs
```

或者,使用 Makefile 一次构建所有基础镜像:

```bash
make build
```

接下来,构建执行器管理器镜像:

```bash
docker build -t sandbox-executor-manager:latest ./executor_manager
```

## 与 RAGFlow 一起运行

1. 验证 gVisor 已正确安装并运行。

2. 配置位于 docker/.env 的 .env 文件:

- 取消注释沙箱相关的环境变量。
- 在文件底部启用沙箱配置文件。

3. 将以下条目添加到您的 /etc/hosts 文件以解析执行器管理器服务:

    ```bash
    127.0.0.1 es01 infinity mysql minio redis sandbox-executor-manager
    ```

4. 像往常一样启动 RAGFlow 服务。

## 独立运行

### 手动设置

1. 初始化环境变量:

    ```bash
    cp .env.example .env
    ```

2. 使用 Docker Compose 启动沙箱服务:

    ```bash
    docker compose -f docker-compose.yml up
    ```

3. 测试沙箱设置:

    ```bash
    source .venv/bin/activate
    export PYTHONPATH=$(pwd)
    uv pip install -r executor_manager/requirements.txt
    uv run tests/sandbox_security_tests_full.py
    ```

### 使用 Makefile

使用单个命令运行所有设置、构建、启动和测试:

```bash
make
```

### 监控

要跟踪执行器管理器容器的日志:

```bash
docker logs -f sandbox-executor-manager
```

或使用 Makefile 快捷方式:

```bash
make logs
```
