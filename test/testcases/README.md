# RAGFlow 测试用例

本目录包含 RAGFlow 项目的自动化测试用例。

## 目录结构

```
test/testcases/
├── conftest.py              # pytest 配置和共享 fixtures
├── configs.py               # 测试配置
├── test_rag/                # RAG 模块单元测试
│   └── test_classifier.py   # 文档分类器测试
├── test_auto_detect/        # 自动检测功能集成测试
│   └── test_auto_classify.py
├── test_benchmark/          # 基准测试
├── test_http_api/           # HTTP API 测试
├── test_sdk_api/            # SDK API 测试
└── test_web_api/            # Web API 测试
```

## 环境配置

### 1. 环境变量

测试所需的 API Key 和配置统一在项目根目录的 `.env.test` 文件中：

```bash
# 复制并编辑环境变量文件
cp .env.test.example .env.test  # 如果有示例文件
```

**关键配置项：**

| 变量名 | 说明 | 获取方式 |
|--------|------|----------|
| `RAGFLOW_HOST` | RAGFlow 服务地址 | 默认 `http://localhost:9380` |
| `RAGFLOW_API_KEY` | RAGFlow API Token | 从数据库 `api_token` 表获取 |
| `ZHIPU_AI_API_KEY` | 智谱 AI API Key | 从智谱 AI 控制台获取 |

### 2. 获取 RAGFlow API Token

API Token 存储在 MySQL 数据库中，获取方式：

```bash
# 方式1: 通过 Docker 执行 SQL
docker exec docker-mysql-1 mysql -uroot -pinfini_rag_flow rag_flow \
  -e "SELECT token FROM api_token LIMIT 1;"

# 方式2: 通过 MySQL 客户端连接
mysql -h 127.0.0.1 -P 5455 -uroot -pinfini_rag_flow rag_flow
> SELECT token FROM api_token LIMIT 1;
```

**注意：** API Token 是静态的，除非手动重新生成。如果 Token 失效，请重新从数据库获取。

## 运行测试

### 加载环境变量

```bash
# 加载 .env.test 中的环境变量
export $(grep -v '^#' .env.test | xargs)
```

### 按优先级运行测试

测试按优先级标记为 `p1`（冒烟）、`p2`（核心）、`p3`（完整）：

```bash
# 运行 p1 级别测试（冒烟测试）
uv run pytest test/testcases --level p1

# 运行 p2 级别测试（核心功能，默认）
uv run pytest test/testcases --level p2

# 运行 p3 级别测试（全部测试）
uv run pytest test/testcases --level p3
```

### 运行特定测试模块

```bash
# 运行文档分类器单元测试
uv run pytest test/testcases/test_rag/test_classifier.py -v

# 运行自动检测集成测试
uv run pytest test/testcases/test_auto_detect/test_auto_classify.py -v

# 运行不需要 API 的测试
uv run pytest test/testcases/test_auto_detect/test_auto_classify.py::TestClassificationWithoutAPIKey -v
```

### 运行单个测试

```bash
uv run pytest test/testcases/test_rag/test_classifier.py::TestRuleBasedClassification -v
```

## 测试标记说明

| 标记 | 说明 | 运行级别 |
|------|------|----------|
| `@pytest.mark.p1` | 高优先级/冒烟测试 | `--level p1` 及以上 |
| `@pytest.mark.p2` | 中优先级/核心功能 | `--level p2` 及以上 |
| `@pytest.mark.p3` | 低优先级/完整测试 | `--level p3` |

## 常见问题

### Q: 测试被跳过（deselected）？

A: 确保测试类或方法有正确的优先级标记（`p1`/`p2`/`p3`）。

### Q: API 测试失败？

A: 检查以下几点：
1. RAGFlow 服务是否在运行：`docker ps | grep ragflow`
2. 环境变量是否正确加载：`echo $RAGFLOW_API_KEY`
3. API Token 是否有效（从数据库重新获取）

### Q: 如何添加新的测试？

1. 在相应的目录下创建 `test_*.py` 文件
2. 添加 `@pytest.mark.p1/p2/p3` 标记
3. 运行测试验证

## 相关文档

- [项目 CLAUDE.md](../../CLAUDE.md) - 项目开发指南
- [测试数据 benchmark/](../../benchmark/README.md) - 测试数据说明
