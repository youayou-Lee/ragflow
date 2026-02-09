---
sidebar_position: 1
slug: /llm_api_key_setup
sidebar_custom_props: {
  categoryIcon: LucideKey
}
---
# 配置模型 API 密钥

RAGFlow 需要 API 密钥才能与在线 AI 模型交互。本指南提供有关在 RAGFlow 中设置模型 API 密钥的信息。

## 获取模型 API 密钥

RAGFlow 支持大多数主流 LLM。请参阅[支持的模型](../../references/supported_models.mdx)以获取完整列表。您需要在线申请模型 API 密钥。请注意，大多数 LLM 提供商会为新创建的账户提供试用额度，这将在几个月后到期，或提供一定数量的免费配额。

:::note
如果您发现您的在线 LLM 不在列表中，请不要感到失望。列表正在不断扩充，您可以向我们[提交功能请求](https://github.com/infiniflow/ragflow/issues/new?assignees=&labels=feature+request&projects=&template=feature_request.yml&title=%5BFeature+Request%5D%3A+)！或者，如果您有定制或本地部署的模型，可以[使用 Ollama、Xinference 或 LocalAI 将它们绑定到 RAGFlow](./deploy_local_llm.mdx)。
:::

## 配置模型 API 密钥

您有两种选择来配置模型 API 密钥：

- 在启动 RAGFlow 之前在 **service_conf.yaml.template** 中配置。
- 在登录 RAGFlow 后在**模型提供商**页面上配置。

### 在启动 RAGFlow 之前配置模型 API 密钥

1. 导航到 **./docker/ragflow**。
2. 找到条目 **user_default_llm**：
   - 使用您选择的 LLM 更新 `factory`。
   - 使用您的密钥更新 `api_key`。
   - 如果您使用代理连接到远程服务，请更新 `base_url`。
3. 重启系统以使更改生效。
4. 登录 RAGFlow。
   _登录 RAGFlow 后，您将在**模型提供商**页面上的**已添加模型**下看到您选择的模型。_

### 在登录 RAGFlow 后配置模型 API 密钥

:::caution 警告
登录 RAGFlow 后，通过 **service_conf.yaml.template** 文件配置模型 API 密钥将不再生效。
:::

登录 RAGFlow 后，您*只能*在**模型提供商**页面上配置 API 密钥：

1. 点击页面右上角的您的徽标 **>** **模型提供商**。
2. 在**待添加模型**下找到您的模型卡并点击**添加模型**。
3. 粘贴您的模型 API 密钥。
4. 如果您使用代理连接到远程服务，请填写您的基础 URL。
5. 点击**确定**确认您的更改。
