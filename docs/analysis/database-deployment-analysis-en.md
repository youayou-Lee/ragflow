# RAGFlow 数据库设计和部署分析

**文档版本：** 1.0
**最后更新：** 2025-02-09
**作者：** RAGFlow 分析团队

## 目录

1. [执行摘要](#执行摘要)
2. [数据库架构](#数据库架构)
3. [实体关系设计](#实体关系设计)
4. [部署架构](#部署架构)
5. [配置管理](#配置管理)
6. [部署指南](#部署指南)
7. [运维指南](#运维指南)
8. [故障排查](#故障排查)
9. [安全考虑](#安全考虑)

---

## 执行摘要

RAGFlow 是一个复杂的检索增强生成（RAG）引擎，采用了针对不同数据类型和访问模式优化的**多数据库架构**。本文档提供了数据库设计、部署架构和运维考虑的综合分析。

### 核心组件

- **主数据库：** MySQL 8.0.39（用户数据、元数据、配置）
- **文档存储：** Elasticsearch / Infinity / OceanBase / OpenSearch（向量嵌入、全文搜索）
- **对象存储：** MinIO（文件存储、文档、二进制文件）
- **缓存层：** Redis（会话管理、分布式锁、缓存）
- **后端 API：** 基于 Flask 的 Python 应用程序
- **前端：** React/TypeScript 配合 UmiJS 框架

### 系统要求

- **内存：** 最低 16GB，生产环境推荐 32GB+
- **磁盘：** 最低 50GB（推荐 SSD）
- **CPU：** 最低 4 核，推荐 8+
- **操作系统：** Ubuntu 24.04 / 支持 Docker 的 Linux
- **Python：** 3.10-3.12
- **Node.js：** >=18.20.4

---

## 数据库架构

### 多数据库设计

RAGFlow 使用混合持久化架构：

```mermaid
graph TB
    subgraph "应用层"
        APP[RAGFlow API 服务器]
    end

    subgraph "主数据库"
        MYSQL[(MySQL 8.0)]
        MYSQL_USER[用户管理]
        MYSQL_TENANT[租户数据]
        MYSQL_KB[知识库元数据]
        MYSQL_DIALOG[对话配置]
    end

    subgraph "文档存储"
        DOC_ENGINE[文档引擎]
        ES[(Elasticsearch)]
        INF[(Infinity)]
        OB[(OceanBase)]
        OS[(OpenSearch)]
    end

    subgraph "对象存储"
        MINIO[(MinIO)]
        MINIO_FILES[文件存储]
        MINIO_DOCS[文档文件]
    end

    subgraph "缓存层"
        REDIS[(Redis)]
        REDIS_SESSION[会话]
        REDIS_CACHE[查询缓存]
        REDIS_LOCK[分布式锁]
    end

    APP --> MYSQL
    APP --> DOC_ENGINE
    APP --> MINIO
    APP --> REDIS

    DOC_ENGINE --> ES
    DOC_ENGINE --> INF
    DOC_ENGINE --> OB
    DOC_ENGINE --> OS
```

### 数据库连接管理

RAGFlow 实现了具有自动重试机制的**强大连接池**：

```python
# 连接池配置
max_connections: 900
stale_timeout: 300 秒
retry_attempts: 5
retry_delay: 1 秒（指数退避）
```

**关键特性：**
- 连接丢失时自动重连
- 连接健康监控
- 过期连接清理
- 分布式锁支持

---

## 实体关系设计

### 核心数据模型

RAGFlow 的数据库模式围绕这些核心实体组织：

```mermaid
erDiagram
    User ||--o{ UserTenant : "属于"
    User ||--o{ Knowledgebase : "创建"
    User ||--o{ Dialog : "创建"
    User ||--o{ Document : "上传"
    Tenant ||--o{ UserTenant : "拥有成员"
    Tenant ||--o{ Knowledgebase : "拥有"
    Tenant ||--o{ TenantLLM : "配置"
    Tenant ||--o{ Dialog : "拥有"
    Knowledgebase ||--o{ Document : "包含"
    Document ||--o{ Task : "生成"
    Dialog ||--o{ Conversation : "包含"
    Dialog ||--o{ APIToken : "授权"
    LLMFactories ||--o{ LLM : "提供"

    User {
        string id PK
        string nickname UK
        string email UK
        string password
        string avatar
        string language
        string color_schema
        string timezone
        datetime last_login_time
        boolean is_superuser
    }

    Tenant {
        string id PK
        string name
        string public_key
        string llm_id
        string embd_id
        string asr_id
        string img2txt_id
        string rerank_id
        int credit
    }

    Knowledgebase {
        string id PK
        string tenant_id FK
        string name
        string language
        string description
        string embd_id
        string permission
        int doc_num
        int token_num
        int chunk_num
        float similarity_threshold
        float vector_similarity_weight
        string parser_id
        json parser_config
    }

    Document {
        string id PK
        string kb_id FK
        string parser_id
        string name
        string location
        int size
        int token_num
        int chunk_num
        float progress
        string type
        string source_type
    }

    Dialog {
        string id PK
        string tenant_id FK
        string name
        string llm_id
        string rerank_id
        json llm_setting
        json prompt_config
        float similarity_threshold
        float vector_similarity_weight
        int top_n
        int top_k
    }
```

### 关键表概览

#### 1. 用户管理表

**User**（`user`）
- 主键：`id`（32 字符字符串）
- 认证：邮箱 + 密码（哈希）
- 多语言支持：英语、中文
- 时区支持：默认 UTC+8
- 超级用户标志用于管理员权限

**UserTenant**（`user_tenant`）
- 多对多关系
- 角色：所有者、编辑者、查看者
- 基于邀请的成员资格
- 状态跟踪（活动/非活动）

#### 2. 知识库表

**Knowledgebase**（`knowledgebase`）
- 多租户隔离
- 可配置的 RAG 参数：
  - `similarity_threshold`：0.0-1.0（默认：0.2）
  - `vector_similarity_weight`：0.0-1.0（默认：0.3）
- 解析器配置（JSON）
- 高级功能：
  - GraphRAG 支持
  - RAPTOR 层次摘要
  - 思维导图生成

**Document**（`document`）
- 文件元数据和处理状态
- 进度跟踪（0.0-1.0）
- 每个文档的解析器配置
- 处理时长指标

**Task**（`task`）
- 异步文档处理
- 页面范围处理
- 优先级队列支持
- 重试机制

#### 3. 对话和会话表

**Dialog**（`dialog`）
- 每个对话的 RAG 配置
- LLM 设置（temperature、top_p、max_tokens）
- 提示工程（系统提示、开场白）
- 知识库关联
- 检索参数（top_n、top_k）

**Conversation**（`conversation`）
- 聊天历史存储
- 参考文档跟踪
- 用户识别
- 消息序列化（JSON）

#### 4. LLM 集成表

**LLMFactories**（`llm_factories`）
- 模型提供商注册表
- 按类型分类：LLM、Embedding、ASR、Image2Text
- Logo 和品牌

**LLM**（`llm`）
- 模型目录
- 厂商 + 模型名称复合键
- 模型能力和限制
- 工具支持标志

**TenantLLM**（`tenant_llm`）
- 租户特定的 API 密钥
- Token 使用跟踪
- 自定义 API 基础 URL
- 速率限制支持

---

## 部署架构

### 基础设施概览

```mermaid
graph TB
    subgraph "负载均衡器"
        NGINX[Nginx :80/:443]
    end

    subgraph "应用层"
        RAGFLOW[RAGFlow :9380]
        ADMIN[管理服务器 :9381]
        MCP[MCP 服务器 :9382]
    end

    subgraph "数据层"
        MYSQL[(MySQL :3306)]
        REDIS[(Redis :6379)]
        MINIO[(MinIO :9000)]
    end

    subgraph "文档引擎"
        ES[(Elasticsearch :9200)]
        INFINITY[(Infinity :23817)]
        OCEANBASE[(OceanBase :2881)]
    end

    subgraph "可选服务"
        TEI[TEI 嵌入 :6380]
        KIBANA[Kibana :6601]
        SANDBOX[沙箱 :9385]
    end

    NGINX --> RAGFLOW
    RAGFLOW --> MYSQL
    RAGFLOW --> REDIS
    RAGFLOW --> MINIO
    RAGFLOW --> ES
```

### 服务组件

#### 1. RAGFlow 应用容器

**镜像：** `infiniflow/ragflow:v0.23.1`

**暴露端口：**
- `80` - Web HTTP（Nginx）
- `443` - Web HTTPS（Nginx）
- `9380` - API 服务器
- `9381` - 管理服务器（可选）
- `9382` - MCP 服务器（可选）

**卷：**
- `./ragflow-logs:/ragflow/logs` - 应用日志
- `./nginx/ragflow.conf:/etc/nginx/conf.d/ragflow.conf` - Nginx 配置
- `./service_conf.yaml.template:/ragflow/conf/service_conf.yaml.template` - 服务配置

**命令选项：**
```bash
# 启用管理服务器
--enable-adminserver

# 启用 MCP 服务器
--enable-mcpserver
--mcp-host=0.0.0.0
--mcp-port=9382
--mcp-base-url=http://127.0.0.1:9380
```

#### 2. MySQL 数据库

**镜像：** `mysql:8.0.39`

**配置：**
- 最大连接数：1000
- 字符集：utf8mb4
- 认证：mysql_native_password

**环境变量：**
```bash
MYSQL_HOST=mysql
MYSQL_PORT=3306
MYSQL_DBNAME=rag_flow
MYSQL_PASSWORD=infini_rag_flow
EXPOSE_MYSQL_PORT=5455
MYSQL_MAX_PACKET=1073741824
```

**健康检查：**
```bash
mysqladmin ping -uroot -p${MYSQL_PASSWORD}
```

#### 3. Redis 缓存

**镜像：** `valkey/valkey:8`（Redis 兼容）

**配置：**
- 最大内存：128MB
- 驱逐策略：allkeys-lru
- 密码保护

**环境变量：**
```bash
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=infini_rag_flow
```

#### 4. MinIO 对象存储

**镜像：** `quay.io/minio/minio:RELEASE.2025-06-13T11-33-47Z`

**端口：**
- `9000` - API 端点
- `9001` - Web 控制台

**环境变量：**
```bash
MINIO_HOST=minio
MINIO_PORT=9000
MINIO_CONSOLE_PORT=9001
MINIO_USER=rag_flow
MINIO_PASSWORD=infini_rag_flow
```

#### 5. 文档引擎

**Elasticsearch**（默认）
```bash
ES_HOST=es01
ES_PORT=1200
ELASTIC_PASSWORD=infini_rag_flow
STACK_VERSION=8.11.3
MEM_LIMIT=8073741824
```

**Infinity**（替代）
```bash
INFINITY_HOST=infinity
INFINITY_THRIFT_PORT=23817
INFINITY_HTTP_PORT=23820
INFINITY_PSQL_PORT=5432
```

**OceanBase**（替代）
```bash
OCEANBASE_HOST=oceanbase
OCEANBASE_PORT=2881
OCEANBASE_USER=root@ragflow
OCEANBASE_PASSWORD=infini_rag_flow
OCEANBASE_DOC_DBNAME=ragflow_doc
```

---

## 配置管理

### 环境变量

#### 核心配置

```bash
# 文档引擎选择
DOC_ENGINE=elasticsearch  # elasticsearch, infinity, oceanbase, opensearch, seekdb

# 设备类型
DEVICE=cpu  # cpu, gpu

# Docker Compose 配置文件
COMPOSE_PROFILES=${DOC_ENGINE},${DEVICE}

# 服务端口
SVR_WEB_HTTP_PORT=80
SVR_WEB_HTTPS_PORT=443
SVR_HTTP_PORT=9380
ADMIN_SVR_HTTP_PORT=9381
SVR_MCP_PORT=9382

# Docker 镜像
RAGFLOW_IMAGE=infiniflow/ragflow:v0.23.1
```

#### 批处理

```bash
# 文档处理
DOC_BULK_SIZE=4  # 每批文档数
EMBEDDING_BATCH_SIZE=16  # 每批嵌入数

# 文件上传限制
MAX_CONTENT_LENGTH=1073741824  # 默认 1GB
```

#### 可选功能

```bash
# 用户注册
REGISTER_ENABLED=1  # 1=启用，0=禁用

# 嵌入服务
TEI_MODEL=Qwen/Qwen3-Embedding-0.6B
TEI_HOST=tei
TEI_PORT=6380

# 沙箱执行
SANDBOX_ENABLED=1
SANDBOX_HOST=sandbox-executor-manager
SANDBOX_EXECUTOR_MANAGER_POOL_SIZE=3
SANDBOX_MAX_MEMORY=256m
SANDBOX_TIMEOUT=10s

# 日志记录
LOG_LEVELS=ragflow.es_conn=DEBUG
```

### 服务配置模板

**`service_conf.yaml.template`**

```yaml
ragflow:
  host: 0.0.0.0
  http_port: 9380

admin:
  host: 0.0.0.0
  http_port: 9381

mysql:
  name: 'rag_flow'
  user: 'root'
  password: 'infini_rag_flow'
  host: 'mysql'
  port: 3306
  max_connections: 900
  stale_timeout: 300
  max_allowed_packet: 1073741824

minio:
  user: 'rag_flow'
  password: 'infini_rag_flow'
  host: 'minio:9000'
  bucket: ''
  prefix_path: ''

es:
  hosts: 'http://es01:9200'
  username: 'elastic'
  password: 'infini_rag_flow'

infinity:
  uri: 'infinity:23817'
  postgres_port: 5432
  db_name: 'default_db'

redis:
  db: 1
  username: ''
  password: 'infini_rag_flow'
  host: 'redis:6379'
```

---

## 部署指南

### 前提条件

```bash
# 系统要求
- 内存：最低 16GB，推荐 32GB+
- 磁盘：最低 50GB（推荐 SSD）
- CPU：最低 4 核，推荐 8+
- 操作系统：Ubuntu 24.04 / 支持 Docker 的 Linux

# 安装 Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 安装 Docker Compose
sudo apt-get update
sudo apt-get install docker-compose-plugin

# 验证安装
docker --version
docker compose version
```

### 安装步骤

#### 1. 克隆仓库

```bash
git clone https://github.com/infiniflow/ragflow.git
cd ragflow
```

#### 2. 配置环境

```bash
cd docker
cp .env .env.backup
nano .env

# 关键：生产环境更改密码
MYSQL_PASSWORD=$(openssl rand -hex 32)
MINIO_PASSWORD=$(openssl rand -hex 32)
REDIS_PASSWORD=$(openssl rand -hex 32)
ELASTIC_PASSWORD=$(openssl rand -hex 32)
```

#### 3. 启动服务

```bash
# 完整栈部署
docker compose -f docker-compose.yml up -d

# 检查服务状态
docker compose ps

# 查看日志
docker compose logs -f ragflow-cpu
```

#### 4. 验证部署

```bash
# 检查所有容器
docker compose ps

# 检查服务健康
curl http://localhost:9380/health

# 访问 Web 界面
# 打开浏览器：http://localhost
```

### 部署后配置

#### 1. 安全加固

```bash
# 生成安全密码
openssl rand -hex 32

# 使用安全密码更新 .env
# 重启服务
docker compose down
docker compose up -d
```

#### 2. 配置 SSL/TLS

```bash
# 使用 Certbot（推荐）
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com

# 更新 nginx 配置
# 路径：./nginx/ragflow.conf
```

#### 3. 配置备份

```bash
# MySQL 备份
docker compose exec mysql mysqldump -uroot -p${MYSQL_PASSWORD} rag_flow > backup.sql

# MinIO 备份
docker compose exec minio mc mirror /data /backup/minio

# Elasticsearch 快照
docker compose exec es01 curl -X PUT \
  "http://elastic:${ELASTIC_PASSWORD}@localhost:9200/_snapshot/backup_repo" \
  -H 'Content-Type: application/json' \
  -d '{"type": "fs", "settings": {"location": "/usr/share/elasticsearch/backup"}}'
```

---

## 运维指南

### 监控

#### 健康检查

```bash
# 检查所有服务
docker compose ps

# 特定服务检查
curl http://localhost:9380/health
curl http://localhost:9380/v1/system/info
```

#### 日志监控

```bash
# 实时日志
docker compose logs -f ragflow-cpu

# 特定服务日志
docker compose logs -f mysql
docker compose logs -f es01

# 按级别过滤
docker compose logs ragflow-cpu | grep ERROR
```

#### 性能监控

```bash
# 容器资源使用
docker stats

# 数据库性能
docker compose exec mysql mysqladmin -uroot -p${MYSQL_PASSWORD} processlist

# Redis 性能
docker compose exec redis redis-cli -a ${REDIS_PASSWORD} INFO

# Elasticsearch 性能
curl http://localhost:1200/_cluster/health?pretty
```

### 备份和恢复

#### 自动备份脚本

```bash
#!/bin/bash
# backup.sh - 每日备份脚本

BACKUP_DIR="/backup/ragflow/$(date +%Y%m%d)"
mkdir -p ${BACKUP_DIR}

# MySQL 备份
docker compose exec -T mysql mysqldump -uroot -p${MYSQL_PASSWORD} rag_flow \
  > ${BACKUP_DIR}/mysql_backup.sql

# MinIO 备份
docker compose exec minio mc mirror /data ${BACKUP_DIR}/minio

# 压缩备份
tar -czf ${BACKUP_DIR}.tar.gz ${BACKUP_DIR}
rm -rf ${BACKUP_DIR}

# 保留最近 7 天
find /backup/ragflow -name "*.tar.gz" -mtime +7 -delete
```

#### 恢复程序

```bash
# MySQL 恢复
docker compose down
docker compose up -d mysql
sleep 30
docker compose exec -T mysql mysql -uroot -p${MYSQL_PASSWORD} rag_flow \
  < backup/mysql_backup.sql
docker compose up -d

# MinIO 恢复
docker compose exec minio mc mirror /backup/minio /data
```

### 扩展策略

#### 水平扩展

```bash
# 扩展应用容器
docker compose up -d --scale ragflow-cpu=3

# 配置负载均衡器
# 使用上游配置更新 nginx/ragflow.conf
```

#### 垂直扩展

```bash
# 增加内存限制
MEM_LIMIT=16147459182  # 16GB

# 增加 MySQL 连接
--max_connections=2000

# 增加 Elasticsearch 堆
ES_JAVA_OPTS=-Xms16g -Xmx16g
```

---

## 故障排查

### 常见问题

#### 1. 容器启动失败

**诊断：**
```bash
docker compose logs ragflow-cpu
docker compose ps
docker inspect ragflow-cpu-1
```

**解决方案：**
```bash
# 检查端口冲突
sudo netstat -tulpn | grep LISTEN

# 检查磁盘空间
df -h

# 检查内存
free -h

# 重启服务
docker compose down
docker compose up -d
```

#### 2. 数据库连接错误

**诊断：**
```bash
docker compose logs mysql
docker compose exec mysql mysql -uroot -p${MYSQL_PASSWORD} -e "SHOW DATABASES;"
```

**解决方案：**
```bash
# 等待 MySQL 健康
docker compose ps

# 重启 MySQL
docker compose restart mysql
```

#### 3. Elasticsearch 问题

**诊断：**
```bash
docker compose logs es01
curl http://localhost:1200/_cluster/health?pretty
```

**解决方案：**
```bash
# 增加内存限制
MEM_LIMIT=16147459182

# 禁用安全（开发环境）
xpack.security.enabled=false
```

### 调试程序

#### 启用调试日志

```bash
# 在 .env 中
LOG_LEVELS=ragflow.es_conn=DEBUG,ragflow.api=DEBUG

# 重启服务
docker compose restart ragflow-cpu
```

#### 网络调试

```bash
# 测试连接
docker compose exec ragflow-cpu ping mysql
docker compose exec ragflow-cpu ping redis

# 检查 DNS 解析
docker compose exec ragflow-cpu nslookup mysql
```

---

## 安全考虑

### 默认凭据

**关键：** 生产部署前更改所有默认密码。

```bash
# 生成安全密码
MYSQL_PASSWORD=$(openssl rand -hex 32)
MINIO_PASSWORD=$(openssl rand -hex 32)
REDIS_PASSWORD=$(openssl rand -hex 32)
ELASTIC_PASSWORD=$(openssl rand -hex 32)
```

### 网络安全

```bash
# 防火墙配置
sudo ufw enable
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp
sudo ufw deny 3306/tcp  # MySQL
sudo ufw deny 6379/tcp  # Redis
sudo ufw deny 9200/tcp  # Elasticsearch
```

### SSL/TLS 配置

```nginx
# nginx/ragflow.conf
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
}
```

### 数据加密

```bash
# MySQL 静态加密
[mysqld]
early-plugin-load=keyring_file.so
keyring_file_data=/var/lib/mysql/keyring

# MinIO 加密
minio:
  command:
    - server
    - --encrypt-volume
    - /data
```

---

## 附录

### 性能调优

#### MySQL 调优

```ini
# my.cnf
[mysqld]
max_connections = 1000
innodb_buffer_pool_size = 4G
innodb_log_file_size = 512M
query_cache_size = 256M
```

#### Elasticsearch 调优

```yaml
es01:
  environment:
    - ES_JAVA_OPTS=-Xms8g -Xmx8g
    - indices.memory.index_buffer_size=30%
    - thread_pool.search.size=20
```

#### Redis 调优

```bash
# redis.conf
maxmemory 256mb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

### 支持和资源

- **文档：** https://ragflow.io/docs
- **GitHub：** https://github.com/infiniflow/ragflow
- **问题：** https://github.com/infiniflow/ragflow/issues
- **社区：** https://ragflow.io/community

---

**文档结束**

如有问题或贡献，请在 GitHub 上开启 issue。
