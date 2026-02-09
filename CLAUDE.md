# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在此代码库中工作时提供指导。

## 项目概述

RAGFlow 是一个基于深度文档理解的开源 RAG（检索增强生成）引擎。它是一个全栈应用，包括：
- Python 后端（基于 Flask 的 API 服务器）
- React/TypeScript 前端（使用 UmiJS 构建）
- 微服务架构，Docker 部署
- 多种数据存储（MySQL、Elasticsearch/Infinity、Redis、MinIO）

## 架构

### 后端 (`/api/`)
- **主服务器**: `api/ragflow_server.py` - Flask 应用程序入口点
- **应用模块**: `api/apps/` 中的模块化 Flask 蓝图，实现不同功能：
  - `kb_app.py` - 知识库管理
  - `dialog_app.py` - 对话/聊天处理
  - `document_app.py` - 文档处理
  - `canvas_app.py` - 智能体工作流画布
  - `file_app.py` - 文件上传/管理
  - `chunk_app.py` - 文档分块处理
  - `conversation_app.py` - 会话管理
  - `user_app.py` - 用户管理
  - `tenant_app.py` - 租户管理
  - `llm_app.py` - LLM 模型管理
  - `mcp_server_app.py` - MCP 服务器
  - `evaluation_app.py` - 评估功能
  - `search_app.py` - 搜索功能
  - `connector_app.py` - 数据连接器
- **服务层**: 业务逻辑在 `api/db/services/`
- **数据模型**: 数据库模型在 `api/db/db_models.py`

### 核心处理 (`/rag/`)
- **文档处理**: `deepdoc/` - PDF 解析、OCR、布局分析
- **LLM 集成**: `rag/llm/` - 对话、嵌入、重排序的模型抽象
  - `chat_model.py` - 对话模型
  - `embedding_model.py` - 向量嵌入模型
  - `rerank_model.py` - 重排序模型
  - `ocr_model.py` - OCR 模型
  - `cv_model.py` - 计算机视觉模型
  - `tts_model.py` - 文本转语音模型
- **RAG 流水线**: `rag/flow/` - 分块、解析、分词
  - `extractor/` - 信息提取器
  - `tokenizer/` - 分词器
  - `hierarchical_merger/` - 层次合并器
- **图 RAG**: `rag/graphrag/` - 知识图谱构建和查询
- **高级 RAG**: `rag/advanced_rag/` - 高级检索增强生成功能

### 智能体系统 (`/agent/`)
- **组件**: 模块化工作流组件 (`agent/component/`)
  - `base.py` - 组件基类
  - `llm.py` - LLM 组件
  - `retrieval.py` - 检索组件
  - `categorize.py` - 分类组件
  - `switch.py` - 条件分支
  - `loop.py` - 循环控制
  - `begin.py` - 开始组件
  - `message.py` - 消息处理
  - `exit_loop.py` - 退出循环
- **画布**: `canvas.py` - 图形化工作流定义和执行
- **工具**: 外部 API 集成（Tavily、Wikipedia、SQL 执行等）
- **沙箱**: `sandbox/` - 安全的代码执行环境
- **模板**: 预构建的智能体工作流

### 前端 (`/web/`)
- React/TypeScript with UmiJS 框架
- Ant Design + shadcn/ui 组件
- Zustand 状态管理
- Tailwind CSS 样式

## 常用开发命令

### 后端开发
```bash
# 安装 Python 依赖
uv sync --python 3.12 --all-extras
uv run download_deps.py
pre-commit install

# 启动依赖服务
docker compose -f docker/docker-compose-base.yml up -d

# 运行后端（需要服务先运行）
source .venv/bin/activate
export PYTHONPATH=$(pwd)
bash docker/launch_backend_service.sh

# 运行测试
uv run pytest

# 代码检查
ruff check
ruff format
```

### 前端开发
```bash
cd web
npm install
npm run dev        # 开发服务器
npm run build      # 生产构建
npm run lint       # ESLint
npm run test       # Jest 测试
```

### Docker 开发
```bash
# Docker 完整栈
cd docker
docker compose -f docker-compose.yml up -d

# 检查服务器状态
docker logs -f ragflow-server

# 重新构建镜像
docker build --platform linux/amd64 -f Dockerfile -t infiniflow/ragflow:nightly .
```

## 关键配置文件

- `docker/.env` - Docker 部署的环境变量
- `docker/service_conf.yaml.template` - 后端服务配置
- `pyproject.toml` - Python 依赖和项目配置
- `web/package.json` - 前端依赖和脚本

## 测试

- **Python**: pytest，支持标记（p1/p2/p3 优先级）
- **前端**: Jest + React Testing Library
- **API 测试**: `test/` 和 `sdk/python/test/` 中的 HTTP API 和 SDK 测试

## 数据库引擎

RAGFlow 支持在 Elasticsearch（默认）和 Infinity 之间切换：
- 在 `docker/.env` 中设置 `DOC_ENGINE=infinity` 使用 Infinity
- 需要重启容器：`docker compose down -v && docker compose up -d`

## 开发环境要求

- Python 3.10-3.12
- Node.js >=18.20.4
- Docker & Docker Compose
- uv 包管理器
- 16GB+ 内存，50GB+ 磁盘空间
