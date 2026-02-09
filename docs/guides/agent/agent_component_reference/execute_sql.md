---
sidebar_position: 25
slug: /execute_sql
sidebar_custom_props: {
  categoryIcon: RagSql
}
---
# 执行 SQL 工具

一个在指定关系数据库上执行 SQL 查询的工具。

---

**执行 SQL** 工具使您能够连接到关系数据库并运行 SQL 查询,无论是直接输入还是通过系统的 Text2SQL 功能通过 **智能体**组件生成。

## 前提条件

- 正确配置并运行的数据库实例。
- 数据库必须是以下类型之一:
  - MySQL
  - PostgreSQL
  - MariaDB
  - Microsoft SQL Server

## 示例

您可以将 **智能体**组件与 **执行 SQL** 工具配对,**智能体**生成 SQL 语句,**执行 SQL** 工具处理数据库连接和查询执行。可以在下面的 **SQL 助手**智能体模板中找到此设置的示例:

![](https://raw.githubusercontent.com/infiniflow/ragflow-docs/main/images/exeSQL.jpg)

## 配置

### SQL 语句

此文本输入字段允许您编写静态 SQL 查询,例如 `SELECT * FROM my_table`,以及使用变量的动态 SQL 查询。

:::tip 注意
点击 **(x)** 或输入 `/` 插入变量。
:::

对于动态 SQL 查询,您可以在 SQL 查询中包含变量,例如 `SELECT * FROM /sys.query`;如果将 **智能体**组件与 **执行 SQL** 工具配对以生成 SQL 任务(请参阅 [示例](#examples) 部分),则可以直接将该 **智能体**的输出 `content` 插入到此字段中。

### 数据库类型

支持的数据库类型。目前,以下数据库类型可用:

- MySQL
- PostgreSQL
- MariaDB
- Microsoft SQL Server (Mssql)

### 数据库

仅当您选择 **拆分**作为方法时出现。

### 用户名

具有数据库访问权限的用户名。

### 主机

数据库服务器的 IP 地址。

### 端口

数据库服务器监听的端口号。

### 密码

数据库用户的密码。

### 最大记录数

SQL 查询返回的最大记录数,以控制响应大小并提高效率。默认为 `1024`。

### 输出

**执行 SQL** 工具提供两个输出变量:

- `formalized_content`: 一个字符串。如果您在 **消息**组件中引用此变量,返回的记录将以表格形式显示。
- `json`: 一个对象数组。如果您在 **消息**组件中引用此变量,返回的记录将以键值对的形式呈现。
