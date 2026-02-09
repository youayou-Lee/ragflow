# 数据迁移指南

一个常见的场景是在强大的实例（例如带有 GPU 的实例）上处理大型数据集，然后将整个 RAGFlow 服务迁移到不同的生产环境（例如仅 CPU 的服务器）。本指南介绍了如何使用我们提供的迁移脚本安全地备份和恢复数据。

## 识别您的数据

默认情况下，RAGFlow 使用 Docker 卷来存储所有持久化数据，包括数据库、上传的文件和搜索索引。您可以通过运行以下命令来查看这些卷：

```bash
docker volume ls
```

输出将类似于以下内容：

```text
DRIVER    VOLUME NAME
local     docker_esdata01
local     docker_minio_data
local     docker_mysql_data
local     docker_redis_data
```

这些卷包含了您需要迁移的所有数据。

## 步骤 1：停止 RAGFlow 服务

在开始迁移之前，您必须停止**源机器**上所有正在运行的 RAGFlow 服务。导航到项目的根目录并运行：

```bash
docker-compose -f docker/docker-compose.yml down
```

**重要：** 请*不要*使用 `-v` 标志（例如 `docker-compose down -v`），因为这将删除所有数据卷。迁移脚本包含检查，如果服务正在运行，将阻止您运行它。

## 步骤 2：备份数据

我们提供了一个方便的脚本，将所有数据卷打包到单个备份文件夹中。

要快速查看脚本的命令和选项，您可以运行：

```bash
bash docker/migration.sh help
```

要创建备份，请从项目根目录运行以下命令：

```bash
bash docker/migration.sh backup
```

这将在项目根目录中创建一个 `backup/` 文件夹，其中包含数据卷的压缩档案。

您还可以为备份文件夹指定自定义名称：

```bash
bash docker/migration.sh backup my_ragflow_backup
```

这将创建一个名为 `my_ragflow_backup/` 的文件夹。

## 步骤 3：传输备份文件夹

将整个备份文件夹（例如 `backup/` 或 `my_ragflow_backup/`）从源机器复制到**目标机器**上的 RAGFlow 项目目录。您可以使用 `scp`、`rsync` 或物理驱动器等工具进行传输。

## 步骤 4：恢复数据

在**目标机器**上，确保 RAGFlow 服务未运行。然后，使用迁移脚本从备份文件夹恢复数据。

如果您的备份文件夹名为 `backup/`，请运行：

```bash
bash docker/migration.sh restore
```

如果您使用了自定义名称，请在命令中指定它：

```bash
bash docker/migration.sh restore my_ragflow_backup
```

脚本将自动创建必要的 Docker 卷并解压数据。

**注意：** 如果脚本检测到目标机器上已存在同名的 Docker 卷，它将警告您恢复将覆盖现有数据，并在继续之前要求确认。

## 步骤 5：启动 RAGFlow 服务

恢复过程完成后，您可以在新机器上启动 RAGFlow 服务：

```bash
docker-compose -f docker/docker-compose.yml up -d
```

**注意：** 如果您之前已经通过 docker-compose 构建了服务，则可能需要像上面的指南一样为目标机器备份数据，然后运行如下命令：

```bash
# 在执行以下行之前，请通过 `sh docker/migration.sh backup backup_dir_name` 备份数据。
# !!! 这行的 -v 标志将删除原始 docker 卷
docker-compose -f docker/docker-compose.yml down -v
docker-compose -f docker/docker-compose.yml up -d
```

您的 RAGFlow 实例现在正在运行，包含来自原始机器的所有数据。
