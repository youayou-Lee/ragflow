---
sidebar_position: 2
slug: /admin_cli
sidebar_custom_props: {
  categoryIcon: LucideSquareTerminal
}
---
# RAGFlow CLI

RAGFlow CLI是一个基于命令行的系统管理工具，为管理员提供了高效灵活的系统交互和控制方法。基于客户端-服务器架构，它与管理员服务实时通信，接收管理员命令并动态返回执行结果。

## 使用RAGFlow CLI

1. 确保管理员服务正在运行。

2. 安装ragflow-cli。

   ```bash
   pip install ragflow-cli==0.23.1
   ```

3. 启动CLI客户端：

   ```bash
   ragflow-cli -h 127.0.0.1 -p 9381
   ```

    您将需要输入超级用户的密码以登录。
    默认密码是admin。

    **参数：**

    - -h: RAGFlow管理员服务器主机地址

    - -p: RAGFlow管理员服务器端口

## 默认管理员帐户

- 用户名：admin@ragflow.io
- 密码：admin

## 支持的命令

命令不区分大小写，必须以分号(;)结尾。

### 服务管理命令

`LIST SERVICES;`

- 列出RAGFlow系统内所有可用的服务。

- [示例](#example-list-services)

`SHOW SERVICE <id>;`

- 显示由**id**标识的服务的详细状态信息。
- [示例](#example-show-service)

`SHOW VERSION;`

- 显示RAGFlow版本。
- [示例](#example-show-version)

### 用户管理命令

`LIST USERS;`

- 列出系统已知的所有用户。
- [示例](#example-list-users)

`SHOW USER <username>;`

- 显示由**email**指定的用户的详细信息和权限。用户名必须用单引号或双引号括起来。
- [示例](#example-show-user)

`CREATE USER <username> <password>;`

- 通过用户名和密码创建用户。用户名和密码必须用单引号或双引号括起来。
- [示例](#example-create-user)

`DROP USER <username>;`

- 从系统中删除指定的用户。请谨慎使用。
- [示例](#example-drop-user)

`ALTER USER PASSWORD <username> <new_password>;`

- 更改指定用户的密码。
- [示例](#example-alter-user-password)

`ALTER USER ACTIVE <username> <on/off>;`

- 将用户更改为活动或非活动状态。
- [示例](#example-alter-user-active)

`GENERATE KEY FOR USER <username>;`

- 为指定用户生成新的API密钥。
- [示例](#example-generate-key)

`LIST KEYS OF <username>;`

- 列出与指定用户关联的所有API密钥。
- [示例](#example-list-keys)

`DROP KEY <key> OF <username>;`

- 删除指定用户的特定API密钥。
- [示例](#example-drop-key)

### 数据和智能体命令

`LIST DATASETS OF <username>;`

- 列出与指定用户关联的数据集。
- [示例](#example-list-datasets-of-user)

`LIST AGENTS OF <username>;`

- 列出与指定用户关联的智能体。
- [示例](#example-list-agents-of-user)

### 系统信息

`SHOW VERSION;`
- 显示当前的RAGFlow版本。
- [示例](#example-show-version)

`GRANT ADMIN <username>`
- 授予指定用户管理员权限。
- [示例](#example-grant-admin)

`REVOKE ADMIN <username>`
- 撤销指定用户的管理员权限。
- [示例](#example-revoke-admin)

`LIST VARS`
- 列出所有系统设置。
- [示例](#example-list-vars)

`SHOW VAR <var_name>`
- 通过其名称或名称前缀显示特定系统配置/设置的内容。
- [示例](#example-show-var)

`SET VAR <var_name> <var_value>`
- 为指定的配置项设置值。
- [示例](#example-set-var)

`LIST CONFIGS`
- 列出所有系统配置。
- [示例](#example-list-configs)

`LIST ENVS`
- 列出管理员服务可以访问的所有系统环境。
- [示例](#example-list-environments)

### 元命令

- \? 或 \help
  显示可用命令的帮助信息。
- \q 或 \quit
  退出CLI应用程序。
- [示例](#example-meta-commands)

### 示例

<span id="example-list-services"></span>

- 列出所有可用的服务。

```
ragflow> list services;
command: list services;
Listing all services
+-------------------------------------------------------------------------------------------+-----------+----+---------------+-------+----------------+---------+
| extra                                                                                     | host      | id | name          | port  | service_type   | status  |
+-------------------------------------------------------------------------------------------+-----------+----+---------------+-------+----------------+---------+
| {}                                                                                        | 0.0.0.0   | 0  | ragflow_0     | 9380  | ragflow_server | 超时 |
| {'meta_type': 'mysql', 'password': 'infini_rag_flow', 'username': 'root'}                 | localhost | 1  | mysql         | 5455  | meta_data      | 存活   |
| {'password': 'infini_rag_flow', 'store_type': 'minio', 'user': 'rag_flow'}                | localhost | 2  | minio         | 9000  | file_store     | 存活   |
| {'password': 'infini_rag_flow', 'retrieval_type': 'elasticsearch', 'username': 'elastic'} | localhost | 3  | elasticsearch | 1200  | retrieval      | 存活   |
| {'db_name': 'default_db', 'retrieval_type': 'infinity'}                                   | localhost | 4  | infinity      | 23817 | retrieval      | 超时   |
| {'database': 1, 'mq_type': 'redis', 'password': 'infini_rag_flow'}                        | localhost | 5  | redis         | 6379  | message_queue  | 存活   |
+-------------------------------------------------------------------------------------------+-----------+----+---------------+-------+----------------+---------+

```

<span id="example-show-service"></span>

- 显示ragflow_server。

```
ragflow> show service 0;
command: show service 0;
Showing service: 0
Service ragflow_0 is alive. Detail:
Confirm elapsed: 26.0 ms.
```

- 显示mysql。

```
ragflow> show service 1;
command: show service 1;
Showing service: 1
Service mysql is alive. Detail:
+---------+----------+------------------+------+------------------+------------------------+-------+-----------------+
| command | db       | host             | id   | info             | state                  | time  | user            |
+---------+----------+------------------+------+------------------+------------------------+-------+-----------------+
| Daemon  | None     | localhost        | 5    | None             | Waiting on empty queue | 16111 | event_scheduler |
| Sleep   | rag_flow | 172.18.0.1:40046 | 1610 | None             |                        | 2     | root            |
| Query   | rag_flow | 172.18.0.1:35882 | 1629 | SHOW PROCESSLIST | init                   | 0     | root            |
+---------+----------+------------------+------+------------------+------------------------+-------+-----------------+
```

- 显示minio。

```
ragflow> show service 2;
command: show service 2;
Showing service: 2
Service minio is alive. Detail:
Confirm elapsed: 2.1 ms.
```

- 显示elasticsearch。

```
ragflow> show service 3;
command: show service 3;
Showing service: 3
Service elasticsearch is alive. Detail:
+----------------+------+--------------+---------+----------------+--------------+---------------+--------------+------------------------------+----------------------------+-----------------+-------+---------------+---------+-------------+---------------------+--------+------------+--------------------+
| cluster_name   | docs | docs_deleted | indices | indices_shards | jvm_heap_max | jvm_heap_used | jvm_versions | mappings_deduplicated_fields | mappings_deduplicated_size | mappings_fields | nodes | nodes_version | os_mem  | os_mem_used | os_mem_used_percent | status | store_size | total_dataset_size |
+----------------+------+--------------+---------+----------------+--------------+---------------+--------------+------------------------------+----------------------------+-----------------+-------+---------------+---------+-------------+---------------------+--------+------------+--------------------+
| docker-cluster | 717  | 86           | 37      | 42             | 3.76 GB      | 1.74 GB       | 21.0.1+12-29 | 6575                         | 48.0 KB                    | 8521            | 1     | ['8.11.3']    | 7.52 GB | 4.55 GB     | 61                  | green  | 4.60 MB    | 4.60 MB            |
+----------------+------+--------------+---------+----------------+--------------+---------------+--------------+------------------------------+----------------------------+-----------------+-------+---------------+---------+-------------+---------------------+--------+------------+--------------------+
```

- 显示infinity。

```
ragflow> show service 4;
command: show service 4;
Fail to show service, code: 500, message: Infinity is not in use.
```

- 显示redis。

```
ragflow> show service 5;
command: show service 5;
Showing service: 5
Service redis is alive. Detail:
+-----------------+-------------------+---------------------------+-------------------------+---------------+-------------+--------------------------+---------------------+-------------+
| blocked_clients | connected_clients | instantaneous_ops_per_sec | mem_fragmentation_ratio | redis_version | server_mode | total_commands_processed | total_system_memory | used_memory |
+-----------------+-------------------+---------------------------+-------------------------+---------------+-------------+--------------------------+---------------------+-------------+
| 0               | 2                 | 1                         | 10.41                   | 7.2.4         | standalone  | 10446                    | 30.84G              | 1.10M       |
+-----------------+-------------------+---------------------------+-------------------------+---------------+-------------+--------------------------+---------------------+-------------+
```
<span id="example-show-version"></span>

- 显示RAGFlow版本

```
ragflow> show version;
+-----------------------+
| version               |
+-----------------------+
| v0.21.0-241-gc6cf58d5 |
+-----------------------+
```

<span id="example-list-users"></span>

- 列出所有用户。

```
ragflow> list users;
command: list users;
Listing all users
+-------------------------------+----------------------+-----------+----------+
| create_date                   | email                | is_active | nickname |
+-------------------------------+----------------------+-----------+----------+
| Mon, 22 Sep 2025 10:59:04 GMT | admin@ragflow.io     | 1         | admin    |
| Sun, 14 Sep 2025 17:36:27 GMT | lynn_inf@hotmail.com | 1         | Lynn     |
+-------------------------------+----------------------+-----------+----------+
```

<span id="example-show-user"></span>

- 显示指定用户。

```
ragflow> show user "admin@ragflow.io";
command: show user "admin@ragflow.io";
Showing user: admin@ragflow.io
+-------------------------------+------------------+-----------+--------------+------------------+--------------+----------+-----------------+---------------+--------+-------------------------------+
| create_date                   | email            | is_active | is_anonymous | is_authenticated | is_superuser | language | last_login_time | login_channel | status | update_date                   |
+-------------------------------+------------------+-----------+--------------+------------------+--------------+----------+-----------------+---------------+--------+-------------------------------+
| Mon, 22 Sep 2025 10:59:04 GMT | admin@ragflow.io | 1         | 0            | 1                | True         | Chinese  | None            | None          | 1      | Mon, 22 Sep 2025 10:59:04 GMT |
+-------------------------------+------------------+-----------+--------------+------------------+--------------+----------+-----------------+---------------+--------+-------------------------------+
```

<span id="example-create-user"></span>

- 创建新用户。

```
ragflow> create user "example@ragflow.io" "psw";
command: create user "example@ragflow.io" "psw";
Create user: example@ragflow.io, password: psw, role: user
+----------------------------------+--------------------+----------------------------------+--------------+---------------+----------+
| access_token                     | email              | id                               | is_superuser | login_channel | nickname |
+----------------------------------+--------------------+----------------------------------+--------------+---------------+----------+
| 5cdc6d1e9df111f099b543aee592c6bf | example@ragflow.io | 5cdc6ca69df111f099b543aee592c6bf | False        | password      |          |
+----------------------------------+--------------------+----------------------------------+--------------+---------------+----------+
```

<span id="example-alter-user-password"></span>

- 更改用户密码。

```
ragflow> alter user password "example@ragflow.io" "newpsw";
command: alter user password "example@ragflow.io" "newpsw";
Alter user: example@ragflow.io, password: newpsw
Password updated successfully!
```

<span id="example-alter-user-active"></span>

- 更改用户活动状态，关闭。

```
ragflow> alter user active "example@ragflow.io" off;
command: alter user active "example@ragflow.io" off;
Alter user example@ragflow.io activate status, turn off.
Turn off user activate status successfully!
```

<span id="example-drop-user"></span>

- 删除用户。

```
ragflow> Drop user "example@ragflow.io";
command: Drop user "example@ragflow.io";
Drop user: example@ragflow.io
Successfully deleted user. Details:
Start to delete owned tenant.
- Deleted 2 tenant-LLM records.
- Deleted 0 langfuse records.
- Deleted 1 tenant.
- Deleted 1 user-tenant records.
- Deleted 1 user.
Delete done!
```

同时删除用户的数据。

<span id="example-generate-key"></span>

- 为用户生成API密钥。

```
admin> generate key for user "example@ragflow.io";
Generating API key for user: example@ragflow.io
+----------------------------------+-------------------------------+---------------+----------------------------------+-----------------------------------------------------+-------------+-------------+
| beta                             | create_date                   | create_time   | tenant_id                        | token                                               | update_date | update_time |
+----------------------------------+-------------------------------+---------------+----------------------------------+-----------------------------------------------------+-------------+-------------+
| Es9OpZ6hrnPGeYA3VU1xKUkj6NCb7cp- | Mon, 12 Jan 2026 15:19:11 GMT | 1768227551361 | 5d5ea8a3efc111f0a79b80fa5b90e659 | ragflow-piwVJHEk09M5UN3LS_Xx9HA7yehs3yNOc9GGsD4jzus | None        | None        |
+----------------------------------+-------------------------------+---------------+----------------------------------+-----------------------------------------------------+-------------+-------------+
```

<span id="example-list-keys"></span>

- 列出用户的所有API密钥。

```
admin> list keys of "example@ragflow.io";
Listing API keys for user: example@ragflow.io
+----------------------------------+-------------------------------+---------------+-----------+--------+----------------------------------+-----------------------------------------------------+-------------------------------+---------------+
| beta                             | create_date                   | create_time   | dialog_id | source | tenant_id                        | token                                               | update_date                   | update_time   |
+----------------------------------+-------------------------------+---------------+-----------+--------+----------------------------------+-----------------------------------------------------+-------------------------------+---------------+
| Es9OpZ6hrnPGeYA3VU1xKUkj6NCb7cp- | Mon, 12 Jan 2026 15:19:11 GMT | 1768227551361 | None      | None   | 5d5ea8a3efc111f0a79b80fa5b90e659 | ragflow-piwVJHEk09M5UN3LS_Xx9HA7yehs3yNOc9GGsD4jzus | Mon, 12 Jan 2026 15:19:11 GMT | 1768227551361 |
+----------------------------------+-------------------------------+---------------+-----------+--------+----------------------------------+-----------------------------------------------------+-------------------------------+---------------+
```

<span id="example-drop-key"></span>

- 删除用户的API密钥。

```
admin> drop key "ragflow-piwVJHEk09M5UN3LS_Xx9HA7yehs3yNOc9GGsD4jzus" of "example@ragflow.io";
Dropping API key for user: example@ragflow.io
API key deleted successfully
```

<span id="example-list-datasets-of-user"></span>

- 列出指定用户的数据集。

```
ragflow> list datasets of "lynn_inf@hotmail.com";
command: list datasets of "lynn_inf@hotmail.com";
Listing all datasets of user: lynn_inf@hotmail.com
+-----------+-------------------------------+---------+----------+---------------+------------+--------+-----------+-------------------------------+
| chunk_num | create_date                   | doc_num | language | name          | permission | status | token_num | update_date                   |
+-----------+-------------------------------+---------+----------+---------------+------------+--------+-----------+-------------------------------+
| 29        | Mon, 15 Sep 2025 11:56:59 GMT | 12      | Chinese  | test_dataset  | me         | 1      | 12896     | Fri, 19 Sep 2025 17:50:58 GMT |
| 4         | Sun, 28 Sep 2025 11:49:31 GMT | 6       | Chinese  | dataset_share | team       | 1      | 1121      | Sun, 28 Sep 2025 14:41:03 GMT |
+-----------+-------------------------------+---------+----------+---------------+------------+--------+-----------+-------------------------------+
```

<span id="example-list-agents-of-user"></span>

- 列出指定用户的智能体。

```
ragflow> list agents of "lynn_inf@hotmail.com";
command: list agents of "lynn_inf@hotmail.com";
Listing all agents of user: lynn_inf@hotmail.com
+-----------------+-------------+------------+-----------------+
| canvas_category | canvas_type | permission | title           |
+-----------------+-------------+------------+-----------------+
| agent           | None        | team       | research_helper |
+-----------------+-------------+------------+-----------------+
```

<span id="example-show-version"></span>

- 显示当前的RAGFlow版本。

```
ragflow> show version;
show_version
+-----------------------+
| version               |
+-----------------------+
| v0.23.1-24-g6f60e9f9e |
+-----------------------+
```

<span id="example-grant-admin"></span>

- 授予指定用户管理员权限。

```
ragflow> grant admin "anakin.skywalker@ragflow.io";
Grant successfully!
```

<span id="example-revoke-admin"></span>

- 撤销指定用户的管理员权限。

```
ragflow> revoke admin "anakin.skywalker@ragflow.io";
Revoke successfully!
```

<span id="example-list-vars"></span>

- 列出所有系统设置。

```
ragflow> list vars;
+-----------+---------------------+--------------+-----------+
| data_type | name                | source       | value     |
+-----------+---------------------+--------------+-----------+
| string    | default_role        | variable     | user      |
| bool      | enable_whitelist    | variable     | true      |
| string    | mail.default_sender | variable     |           |
| string    | mail.password       | variable     |           |
| integer   | mail.port           | variable     | 15        |
| string    | mail.server         | variable     | localhost |
| integer   | mail.timeout        | variable     | 10        |
| bool      | mail.use_ssl        | variable     | true      |
| bool      | mail.use_tls        | variable     | false     |
| string    | mail.username       | variable     |           |
+-----------+---------------------+--------------+-----------+
```

<span id="example-show-var"></span>

- 通过其名称或名称前缀显示特定系统配置/设置的内容。

```
ragflow> show var mail.server;
+-----------+-------------+--------------+-----------+
| data_type | name        | source       | value     |
+-----------+-------------+--------------+-----------+
| string    | mail.server | variable     | localhost |
+-----------+-------------+--------------+-----------+
```

<span id="example-set-var"></span>

- 为指定的配置项设置值。

```
ragflow> set var mail.server 127.0.0.1;
Set variable successfully
```


<span id="example-list-configs"></span>

- 列出所有系统配置。

```
ragflow> list configs;
+-------------------------------------------------------------------------------------------+-----------+----+---------------+-------+----------------+
| extra                                                                                     | host      | id | name          | port  | service_type   |
+-------------------------------------------------------------------------------------------+-----------+----+---------------+-------+----------------+
| {}                                                                                        | 0.0.0.0   | 0  | ragflow_0     | 9380  | ragflow_server |
| {'meta_type': 'mysql', 'password': 'infini_rag_flow', 'username': 'root'}                 | localhost | 1  | mysql         | 5455  | meta_data      |
| {'password': 'infini_rag_flow', 'store_type': 'minio', 'user': 'rag_flow'}                | localhost | 2  | minio         | 9000  | file_store     |
| {'password': 'infini_rag_flow', 'retrieval_type': 'elasticsearch', 'username': 'elastic'} | localhost | 3  | elasticsearch | 1200  | retrieval      |
| {'db_name': 'default_db', 'retrieval_type': 'infinity'}                                   | localhost | 4  | infinity      | 23817 | retrieval      |
| {'database': 1, 'mq_type': 'redis', 'password': 'infini_rag_flow'}                        | localhost | 5  | redis         | 6379  | message_queue  |
| {'message_queue_type': 'redis'}                                                           |           | 6  | task_executor | 0     | task_executor  |
+-------------------------------------------------------------------------------------------+-----------+----+---------------+-------+----------------+
```

<span id="example-list-environments"></span>

- 列出管理员服务可以访问的所有系统环境。

```
ragflow> list envs;
+-------------------------+------------------+
| env                     | value            |
+-------------------------+------------------+
| DOC_ENGINE              | elasticsearch    |
| DEFAULT_SUPERUSER_EMAIL | admin@ragflow.io |
| DB_TYPE                 | mysql            |
| DEVICE                  | cpu              |
| STORAGE_IMPL            | MINIO            |
+-------------------------+------------------+
```


<span id="example-meta-commands"></span>

- 显示帮助信息。

```
ragflow> \help
command: \help

Commands:
LIST SERVICES
SHOW SERVICE <service>
STARTUP SERVICE <service>
SHUTDOWN SERVICE <service>
RESTART SERVICE <service>
LIST USERS
SHOW USER <user>
DROP USER <user>
CREATE USER <user> <password>
ALTER USER PASSWORD <user> <new_password>
ALTER USER ACTIVE <user> <on/off>
LIST DATASETS OF <user>
LIST AGENTS OF <user>
CREATE ROLE <role>
DROP ROLE <role>
ALTER ROLE <role> SET DESCRIPTION <description>
LIST ROLES
SHOW ROLE <role>
GRANT <action_list> ON <function> TO ROLE <role>
REVOKE <action_list> ON <function> TO ROLE <role>
ALTER USER <user> SET ROLE <role>
SHOW USER PERMISSION <user>
SHOW VERSION
GRANT ADMIN <user>
REVOKE ADMIN <user>
GENERATE KEY FOR USER <user>
LIST KEYS OF <user>
DROP KEY <key> OF <user>

Meta Commands:
  \?, \h, \help     Show this help
  \q, \quit, \exit   Quit the CLI
```

- 退出

```
ragflow> \q
command: \q
Goodbye!
```
