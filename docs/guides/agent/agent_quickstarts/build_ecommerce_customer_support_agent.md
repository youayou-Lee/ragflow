---
sidebar_position: 3
slug: /ecommerce_customer_support_agent
sidebar_custom_props: {
  categoryIcon: LucideStethoscope
}
---

# 构建电子商务客户支持智能体

此快速入门指南指导您构建一个智能电子商务客户支持智能体。该智能体使用 RAGFlow 的工作流和智能体框架自动处理常见的客户请求,例如产品比较、使用说明和安装预订—提供快速、准确和上下文感知的响应。在以下部分中,我们将引导您完成构建电子商务客户支持智能体的过程,如下图所示:

![](https://raw.githubusercontent.com/infiniflow/ragflow-docs/main/images/ecommerce_cs_agent_entirety.PNG)

## 前提条件

- 示例数据集(可从 [Hugging Face](https://huggingface.co/datasets/InfiniFlow/Ecommerce-Customer-Service-Workflow) 获取)。

## 过程

### 准备数据集

1. 确保已下载上述示例数据集。
2. 创建两个数据集:
   - 产品信息
   - 用户指南
3. 将相应的文档上传到每个数据集。
4. 在两个数据集的配置页面上,选择 **手动** 作为分块方法。
   *RAGFlow 通过在"最小标题"级别分割文档来保持内容完整性,将文本和相关图形保持在一起。*

### 创建智能体应用

1. 导航到 **智能体** 页面,创建一个智能体应用以进入智能体画布。
   _画布上将出现一个 **开始** 组件。_
2. 在 **开始** 组件中配置问候消息,例如:

   ```
   您好!有什么我可以帮助您的吗?
   ```

### 添加分类组件

![](https://raw.githubusercontent.com/infiniflow/ragflow-docs/main/images/add_categorize.png)

此 **分类** 组件使用 LLM 识别用户意图并将对话路由到正确的工作流。

### 构建产品功能比较工作流

![](https://raw.githubusercontent.com/infiniflow/ragflow-docs/main/images/feature_comparison_workflow.png)

1. 添加一个名为"功能比较知识库"的 **检索** 组件,并将其连接到"产品信息"数据集。
2. 在 **检索** 组件之后添加一个名为"功能比较智能体"的 **智能体** 组件。
3. 配置智能体的系统提示:
   ```
   您是产品规格比较助手。通过确认型号并以结构化格式清晰呈现差异来帮助用户比较产品。
   ```
4. 配置用户提示:
   ```
   用户的查询是 /(开始 输入) sys.query
   模式是 /(功能比较知识库) formalized_content
   ```

### 构建产品用户指南工作流

![](https://raw.githubusercontent.com/infiniflow/ragflow-docs/main/images/product_user_guide_workflow.png)

1. 添加一个名为"使用指南知识库"的 **检索** 组件,并将其链接到"用户指南"数据集。
2. 添加一个名为"使用指南智能体"的智能体组件。
3. 设置其系统提示:
   ```
   您是产品使用指南助手。为设置、操作和故障排除提供分步说明。
   ```
4. 设置用户提示:
   ```
   用户的查询是 /(开始 输入) sys.query
   模式是 /(使用指南知识库) formalized_content
   ```

### 构建安装预订助手

![](https://raw.githubusercontent.com/infiniflow/ragflow-docs/main/images/installation_booking_assistant.png)

1. 添加一个名为"安装预订智能体"的 **智能体** 组件。
2. 配置其系统提示以收集三个详细信息:
   - 联系电话
   - 首选安装时间
   - 安装地址

   *一旦收集完所有三个信息,智能体应确认它们并通知用户技术人员将致电。*

3. 设置用户提示:
   ```
   用户的查询是 /(开始 输入) sys.query

4. 在三个智能体分支之后连接一个 **消息** 组件。
   *此组件向用户显示最终响应。*

   ![](https://raw.githubusercontent.com/infiniflow/ragflow-docs/main/images/reply_message.png)

5. 点击 **保存** → **运行** 查看执行结果并验证每个查询是否正确路由和回答。
6. 您可以通过询问以下内容来测试工作流:
   - 产品比较问题
   - 使用指导问题
   - 安装预订请求


