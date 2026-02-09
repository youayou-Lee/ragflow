---
sidebar_position: 20
slug: /migrate_to_single_bucket_mode
---

# 从多存储桶迁移到单存储桶模式

默认情况下，RAGFlow为每个知识库（数据集）创建一个存储桶，为每个用户文件夹创建一个存储桶。这在以下情况下可能会有问题：

- 您的云提供商按存储桶收费
- 您的IAM策略限制存储桶创建
- 您希望将所有数据组织在具有目录结构的单个存储桶中

**单存储桶模式**允许您配置RAGFlow使用具有目录结构的单个存储桶，而不是多个存储桶。

:::info 荣誉
本文档由我们的社区贡献者[arogan178](https://github.com/arogan178)贡献。我们可能不会积极维护本文档。
:::

## 工作原理

### 默认模式（多存储桶）

```
bucket: kb_12345/
  └── document_1.pdf
bucket: kb_67890/
  └── document_2.pdf
bucket: folder_abc/
  └── file_3.txt
```

### 单存储桶模式（带有prefix_path）

```
bucket: ragflow-bucket/
  └── ragflow/
      ├── kb_12345/
      │   └── document_1.pdf
      ├── kb_67890/
      │   └── document_2.pdf
      └── folder_abc/
          └── file_3.txt
```

## 配置

### MinIO配置

编辑您的`service_conf.yaml`或设置环境变量：

```yaml
minio:
  user: "your-access-key"
  password: "your-secret-key"
  host: "minio.example.com:443"
  bucket: "ragflow-bucket" # 默认存储桶名称
  prefix_path: "ragflow" # 可选的前缀路径
```

或使用环境变量：

```bash
export MINIO_USER=your-access-key
export MINIO_PASSWORD=your-secret-key
export MINIO_HOST=minio.example.com:443
export MINIO_BUCKET=ragflow-bucket
export MINIO_PREFIX_PATH=ragflow
```

### S3配置（已支持）

```yaml
s3:
  access_key: "your-access-key"
  secret_key: "your-secret-key"
  endpoint_url: "https://s3.amazonaws.com"
  bucket: "my-ragflow-bucket"
  prefix_path: "production"
  region: "us-east-1"
```

## IAM策略示例

使用单存储桶模式时，您只需要一个存储桶的权限：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:*"],
      "Resource": [
        "arn:aws:s3:::ragflow-bucket",
        "arn:aws:s3:::ragflow-bucket/*"
      ]
    }
  ]
}
```

## 从多存储桶迁移到单存储桶

如果您正在从多存储桶模式迁移到单存储桶模式：

1. 为新配置**设置环境变量**
2. **重启RAGFlow**服务
3. **迁移现有数据**（可选）：

```bash
# 使用mc（MinIO客户端）的示例
mc alias set old-minio http://old-minio:9000 ACCESS_KEY SECRET_KEY
mc alias set new-minio https://new-minio:443 ACCESS_KEY SECRET_KEY

# 列出所有知识库存储桶
mc ls old-minio/ | grep kb_ | while read -r line; do
    bucket=$(echo $line | awk '{print $5}')
    # 将每个存储桶复制到新结构
    mc cp --recursive old-minio/$bucket/ new-minio/ragflow-bucket/ragflow/$bucket/
done
```

## 在模式之间切换

### 启用单存储桶模式

```yaml
minio:
  bucket: "my-single-bucket"
  prefix_path: "ragflow"
```

### 禁用（使用多存储桶模式）

```yaml
minio:
  # 将bucket和prefix_path留空或注释掉
  # bucket: ''
  # prefix_path: ''
```

## 故障排除

### 问题：访问被拒绝错误

**解决方案**：确保您的IAM策略授予对配置中指定的存储桶的访问权限。

### 问题：切换模式后找不到文件

**解决方案**：模式之间的路径结构会发生变化。您需要迁移现有数据。

### 问题：HTTPS连接失败

**解决方案**：确保在MinIO连接中设置了`secure: True`（端口443自动处理）。

## 支持的存储后端

- ✅ **MinIO** - 完全支持单存储桶模式
- ✅ **AWS S3** - 完全支持单存储桶模式
- ✅ **阿里云OSS** - 完全支持单存储桶模式
- ✅ **Azure Blob** - 使用基于容器的结构（不同的范式）
- ⚠️ **OpenDAL** - 取决于底层存储后端

## 性能考虑

- **单存储桶模式**对于存储桶列出操作可能具有稍好的性能
- **多存储桶模式**为大型部署提供更好的隔离和组织
- 根据您的特定要求和基础设施约束进行选择
