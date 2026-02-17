<div align="center">
<a href="https://github.com/infiniflow/ragflow">
<img src="web/src/assets/logo-with-text.svg" width="350" alt="ragflow logo">
</a>
</div>

<h1 align="center">刑事案件 RAG 检索系统</h1>

<p align="center">
  <strong>面向刑事案卷的智能问答系统 - 任何结论必须被原文证据支持</strong>
</p>

<p align="center">
    <a href="./README.md"><img alt="README" src="https://img.shields.io/badge/版本-1.0.0-blue"></a>
    <a href="https://github.com/infiniflow/ragflow/blob/main/LICENSE">
        <img height="21" src="https://img.shields.io/badge/License-Apache--2.0-ffffff?labelColor=d4eaf7&color=2e6cc4" alt="license">
    </a>
    <a href="./README-RAGFlow-Original.md"><img alt="原始 RAGFlow 文档" src="https://img.shields.io/badge/RAGFlow-原始文档-green"></a>
</p>

---

## 一句话定义

面向刑事案件扫描版案卷 PDF，构建"**可检索、可追溯引用、可强制校验**"的 RAG 问答系统：**任何结论必须被原文证据支持，并能点击跳转到 PDF 页内高亮位置**。

---

## 核心特性

### 精准引用，拒绝幻觉

- **Answer Gate 强制校验**：LLM 输出必须通过引用校验，无证据返回"材料未显示"
- **数值严格落地**：答案中的金额、日期、浓度等数值必须在证据原文中逐字出现
- **可追溯引用**：每条证据带页码 + 坐标，支持点击跳转高亮

### 专业文书解析

- **讯问/询问笔录**：自动识别 Q&A 对，保持问答完整性
- **起诉意见书**：按法定章节切分，支持结构化检索
- **PaddleVL OCR**：高精度扫描版 PDF 解析，保留版面坐标

### 高效检索

- **混合检索**：向量检索 + BM25 关键词检索融合
- **精确过滤**：支持按案件 ID、文书类型过滤
- **Block 引用**：检索结果包含原始 block 坐标，前端可精确定位

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                     刑事案件 RAG 系统架构                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │ 扫描版 PDF  │ -> │ PaddleVL   │ -> │ Block 入库  │     │
│  │ 案卷文件    │    │ OCR 解析    │    │ (带坐标)    │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
│                                                │            │
│                     ┌──────────────────────────┘            │
│                     ▼                                       │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │ 起诉意见书  │    │ 讯问笔录    │    │ 索引构建    │     │
│  │ Chunker    │    │ Chunker    │    │ (向量+BM25) │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
│                                                │            │
│                     ┌──────────────────────────┘            │
│                     ▼                                       │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │ 用户问题    │ -> │ 混合检索    │ -> │ LLM 生成    │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
│                                                │            │
│                     ┌──────────────────────────┘            │
│                     ▼                                       │
│  ┌─────────────┐    ┌─────────────┐                         │
│  │ Answer Gate │ -> │ 结构化答案  │                         │
│  │ 强制校验    │    │ + 可追溯引用│                         │
│  └─────────────┘    └─────────────┘                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 快速开始

### 前提条件

- CPU >= 4 核
- RAM >= 16 GB
- Disk >= 50 GB
- Docker >= 24.0.0 & Docker Compose >= v2.26.1
- Python 3.10-3.12

### 启动服务器

1. **克隆仓库**

```bash
git clone https://github.com/your-org/criminal-rag.git
cd criminal-rag
```

2. **配置环境变量**

```bash
cp docker/.env.example docker/.env
# 编辑 docker/.env 配置必要的环境变量
```

3. **启动 Docker 服务**

```bash
cd docker
docker compose -f docker-compose.yml up -d
```

4. **确认服务器状态**

```bash
docker logs -f docker-ragflow-cpu-1
```

5. **访问系统**

浏览器打开 `http://localhost` 即可使用。

---

## 使用流程

### 1. 创建知识库

- 输入知识库名称
- 选择嵌入模型（推荐使用已授权的模型）

### 2. 上传案卷文件

- 支持扫描版 PDF
- 系统自动识别文书类型（讯问笔录/起诉意见书）
- 自动触发对应解析逻辑

### 3. 提问与检索

- 输入自然语言问题
- 系统返回：结论 + 证据引用 + 推理说明
- 点击引用可跳转到 PDF 对应位置

### 4. 引用校验

- 所有结论必须有证据支撑
- 数值必须在原文中逐字出现
- 无证据自动返回"材料未显示"

---

## 核心功能模块

### Answer Gate 校验器

```python
# 校验规则
1. chunk_id 必须存在于检索结果或库中
2. excerpt 必须为 chunk.text 的子串
3. 结论中的数值必须在 excerpt 中逐字出现
4. page_index/bbox 必须来自 chunk 元数据
```

### 起诉意见书 Chunker

```python
# Section 触发词
- "经依法侦查查明"
- "认定上述犯罪事实的证据如下"
- "综上所述"
# 段落切分
- section 内按 800 字分割
- 保留 block_refs 用于精确定位
```

### 讯问笔录 Chunker

```python
# Q&A 识别
- 识别 "问：" 和 "答：" 前缀
- 以 1 个问 + 其后的 n 个答为一个 chunk
- 保持问答上下文完整性
```

---

## 验收指标

| 指标 | 阈值 | 定义 |
|---|---|---|
| Citation Precision | ≥ 98% | 引用摘录必须包含支撑该结论的事实/数值 |
| Numeric/Date Grounding | = 100% | 答案中数值必须在证据摘录中逐字出现 |
| Retrieval Recall@20 | ≥ 95% | 金标问题的关键证据 chunk 在 Top-20 检索结果中出现 |
| OOD "材料未显示" 触发正确率 | ≥ 95% | 对题库外问题应答为"材料未显示/引用不足" |

---

## 技术栈

### 后端
- Python 3.10-3.12
- Flask (API 服务器)
- Elasticsearch / Infinity (向量+关键词索引)
- PaddleOCR-VL (PDF OCR + 版面分析)

### 前端
- React + TypeScript
- UmiJS 框架
- Ant Design + shadcn/ui 组件

### 部署
- Docker + Docker Compose
- MinIO (对象存储)
- MySQL (关系数据)
- Redis (缓存)

---

## 项目结构

```
criminal-rag/
├── api/                    # 后端 API
│   ├── apps/              # Flask 蓝图模块
│   │   ├── kb_app.py      # 知识库管理
│   │   ├── dialog_app.py  # 对话处理
│   │   └── chunk_app.py   # 分块管理
│   └── db/services/       # 业务服务层
├── rag/                   # RAG 核心逻辑
│   ├── app/              # 文档解析器
│   │   ├── interrogation.py  # 讯问笔录 Chunker
│   │   └── indictment.py     # 起诉意见书 Chunker
│   ├── answer_gate/      # Answer Gate 校验器
│   │   └── validator.py
│   └── nlp/              # NLP 工具
│       └── search.py     # 检索逻辑
├── deepdoc/              # 文档解析
│   └── parser/           # 解析器
│       └── paddleocr_parser.py
├── web/                  # 前端代码
│   └── src/             # React 组件
├── docker/              # Docker 配置
├── docs/                # 文档
│   ├── 刑事案件RAG检索系统prd.md
│   └── 第一阶段开发汇总.md
└── openspec/            # 变更管理
    └── changes/         # PR 提案和设计
```

---

## 开发指南

### 后端开发

```bash
# 安装依赖
uv sync --python 3.12 --all-extras
uv run download_deps.py
pre-commit install

# 启动依赖服务
docker compose -f docker/docker-compose-base.yml up -d

# 启动后端
source .venv/bin/activate
export PYTHONPATH=$(pwd)
bash docker/launch_backend_service.sh

# 运行测试
uv run pytest test/unit/ -v
```

### 前端开发

```bash
cd web
bun install
bun run dev        # 开发服务器
bun run build      # 生产构建
```

---

## 版本历史

### v1.0.0 (2026-02-17)

**已完成功能**:
- PR-1: Schema 扩展 (block_refs, bbox_union)
- PR-2: 起诉意见书 Chunker
- PR-3: Answer Gate 校验器
- PR-4: 检索扩展 (返回 block_refs)
- PR-6: PaddleVL 作为默认 PDF 解析器

**进行中**:
- PR-5: 集成测试
- 自动检测文书类型解析方案
- Benchmark 检索测试

---

## 文档

- [产品需求文档 (PRD)](./docs/刑事案件RAG检索系统prd.md)
- [第一阶段开发汇总](./docs/第一阶段开发汇总.md)
- [RAGFlow 原始文档](./README-RAGFlow-Original.md)

---

## 致谢

本项目基于 [RAGFlow](https://github.com/infiniflow/ragflow) 开源项目进行二次开发，感谢 RAGFlow 团队的优秀工作。

---

## 许可证

Apache-2.0 License
