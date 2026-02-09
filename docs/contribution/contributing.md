---
sidebar_position: 1
slug: /contributing
sidebar_custom_props: {
  categoryIcon: LucideBookA
}
---
# 贡献指南

RAGFlow社区贡献者的一般指南。

---

本文档提供了向RAGFlow提交贡献的指南和主要注意事项。

- 要报告错误，请与我们提交[GitHub issue](https://github.com/infiniflow/ragflow/issues/new/choose)。
- 如有其他问题，您可以在[讨论](https://github.com/orgs/infiniflow/discussions)中探索现有讨论或发起新讨论。

## 您可以贡献什么

下面的列表提到了您可以做出的一些贡献，但这不是一个完整的列表。

- 提议或实现新功能
- 修复错误
- 添加测试用例或演示
- 发布博客或教程
- 更新现有文档、代码或注释
- 建议更友好的错误代码

## 提交拉取请求（PR）

### 一般工作流程

1. Fork我们的GitHub仓库。
2. 将您的fork克隆到本地计算机：
`git clone git@github.com:<yourname>/ragflow.git`
3. 创建本地分支：
`git checkout -b my-branch`
4. 在提交消息中提供充分的信息
`git commit -m '在提交消息中提供充分信息'`
5. 将更改提交到本地分支，并推送到GitHub：（包括必要的提交消息）
`git push origin my-branch.`
6. 提交拉取请求以供审查。

### 在提交PR之前

- 考虑将大型PR拆分为多个较小的、独立的PR，以保持可跟踪的开发历史。
- 确保您的PR只解决一个问题，或者保持任何不相关的更改较小。
- 在贡献新功能时添加测试用例。它们证明您的代码正常运行，并防止未来更改可能产生的问题。

### 描述您的PR

- 确保您的PR标题简洁明了，提供所有必需的信息。
- 如果适用，请在PR描述中引用相应的GitHub issue。
- 在您的描述中包含有关*重大更改*或*API更改*的充分设计细节。

### 审查和合并PR

确保您的PR在合并之前通过所有持续集成（CI）测试。
