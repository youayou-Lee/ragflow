---
sidebar_position: 3
slug: /switch_doc_engine
sidebar_custom_props: {
  categoryIcon: LucideShuffle
}
---
# 切换文档引擎

将您的文档引擎从Elasticsearch切换到Infinity。

---

RAGFlow默认使用Elasticsearch来存储全文和向量。要切换到[Infinity](https://github.com/infiniflow/infinity/)，请按照以下步骤操作：

:::caution 警告
在Linux/arm64机器上切换到Infinity尚未得到官方支持。
:::

1. 停止所有正在运行的容器：

   ```bash
   $ docker compose -f docker/docker-compose.yml down -v
   ```

:::caution 警告
`-v`将删除docker容器卷，现有数据将被清除。
:::

2. 将**docker/.env**中的`DOC_ENGINE`设置为`infinity`。

3. 启动容器：

   ```bash
   $ docker compose -f docker-compose.yml up -d
   ```
