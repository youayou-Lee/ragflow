# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在此代码库中工作时提供指导。

## 项目概述

本项目是基于 RAGFlow 二次开发的法律领域 RAG（检索增强生成）引擎。专注于法律文档的智能处理与检索，包括：
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
- **文档处理**: 使用 PaddleOCR API 进行 OCR 识别，支持法律文书的精准解析
- **法律文档解析**: `rag/app/criminal/` - 刑事案件文档专用解析器
- **LLM 集成**: `rag/llm/` - 对话、嵌入、重排序的模型抽象
  - `chat_model.py` - 对话模型
  - `embedding_model.py` - 向量嵌入模型
  - `rerank_model.py` - 重排序模型
  - `ocr_model.py` - OCR 模型
  - `cv_model.py` - 计算机视觉模型
- **RAG 流水线**: `rag/flow/` - 分块、解析、分词
  - `extractor/` - 信息提取器
  - `tokenizer/` - 分词器
  - `hierarchical_merger/` - 层次合并器
- **图 RAG**: `rag/graphrag/` - 知识图谱构建和查询
- **高级 RAG**: `rag/advanced_rag/` - 高级检索增强生成功能

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

# 运行后端
./start_backend.sh

# 运行测试
uv run pytest

# 代码检查
ruff check
ruff format
```

### 前端开发
```bash
cd web
bun install
bun run dev        # 开发服务器
bun run build      # 生产构建
bun run lint       # ESLint
bun run test       # Jest 测试
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


## 开发环境要求

- Python 3.10-3.12
- Node.js >=18.20.4
- Docker & Docker Compose
- uv 包管理器（Python）
- bun 包管理器（前端）
- 16GB+ 内存，50GB+ 磁盘空间

## 文书解析 Plugin 开发测试

### 测试工具

使用 `test/test_plugin_dev.py` 快速验证 Plugin 解析结果：

```bash
# 使用样本文件（推荐，无需指定路径）
uv run python test/test_plugin_dev.py --sample interrogation --doc-type interrogation_record
uv run python test/test_plugin_dev.py --sample indictment --doc-type indictment_opinion

# 列出可用样本
uv run python test/test_plugin_dev.py --list-samples

# 使用指定 PDF 文件
uv run python test/test_plugin_dev.py <pdf_path> --doc-type <doc_type>

# JSON 输出（便于 AI 解析）
uv run python test/test_plugin_dev.py --sample interrogation --doc-type interrogation_record --json
```

### 样本文件位置

样本文件存放在 `/home/you/cs/proj/Superyou/SampleData/` 目录：
- `interrogation/` - 讯问笔录样本（1.pdf - 5.pdf）
- `indictment/` - 起诉意见书样本

### 支持的文书类型

| doc_type | 说明 | Plugin |
|----------|------|--------|
| `interrogation_record` | 讯问/询问笔录 | InterrogationPlugin |
| `indictment_opinion` | 起诉意见书 | IndictmentPlugin |

### OCR 缓存机制

- 缓存文件：与 PDF 同目录，`<pdf_stem>.ocr.json`
- 首次运行调用 PaddleOCR API 并保存缓存
- 后续运行直接使用缓存，无需等待 API

### 开发新 Plugin 流程

1. 准备样本 PDF 文件（放入 `SampleData/<type>/` 目录）
2. 运行测试工具获取当前输出
3. 修改 Plugin 代码
4. 再次运行测试工具验证修改效果
5. 重复 3-4 直到满意
