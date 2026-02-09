---
sidebar_position: 0
slug: /admin_service
sidebar_custom_props: {
  categoryIcon: LucideActivity
}
---
# 管理员服务

管理员服务是RAGFlow系统的核心后端管理服务，通过集中的API接口提供全面的系统管理功能，用于管理和控制整个平台。采用客户端-服务器架构，它支持通过Web UI和管理员CLI进行访问和操作，确保管理任务的灵活高效执行。

管理员服务的核心功能包括实时监控RAGFlow服务器及其关键依赖组件（如MySQL、Elasticsearch、Redis和MinIO）的运行状态，以及全功能的用户管理。在管理员模式下，它支持查看用户信息、创建用户、更新密码、修改激活状态和执行完整的用户数据删除等关键操作。即使禁用Web管理界面，这些功能仍可通过管理员CLI访问，确保系统始终受到控制。

凭借其统一的接口设计，管理员服务将可视化管理与管理员操作的效率和稳定性结合在一起，是RAGFlow系统可靠运行和安全管理的坚实基础。

## 启动管理员服务

### 从源代码启动

1. 在启动管理员服务之前，请确保RAGFlow系统已经启动。

2. 从源代码启动：

   ```bash
   python admin/server/admin_server.py
   ```

   服务将启动并监听来自CLI的传入连接。

### 使用Docker镜像

1. 启动前，请配置`docker_compose.yml`文件以启用管理员服务器：

   ```bash
   command:
     - --enable-adminserver
   ```

2. 启动容器，服务将启动并监听来自CLI的传入连接。
