---
sidebar_position: -5
slug: /manage_metadata
sidebar_custom_props: {
  categoryIcon: LucideCode
}
---
# 管理元数据

为您的数据集和单个文档管理元数据。

---

从 v0.23.0 开始，RAGFlow 允许您在数据集级别和单个文件级别管理元数据。


## 操作步骤

1. 点击数据集中的 **Metadata** 以访问 **Manage Metadata** 页面。

![](https://raw.githubusercontent.com/infiniflow/ragflow-docs/main/images/click_metadata.png)


2. 在 **Manage Metadata** 页面上，您可以执行以下任一操作：
   - 编辑值：您可以修改现有值。如果您将两个值重命名为相同，它们将自动合并。
   - 删除：您可以删除特定值或整个字段。这些更改将应用于所有关联的文件。

   _出现自动生成元数据规则的配置页面。_

![](https://raw.githubusercontent.com/infiniflow/ragflow-docs/main/images/manage_metadata.png)

3. 要管理单个文件的元数据，请导航至文件的详细信息页面，如下所示。点击解析方法（例如 **General**），然后选择 **Set Metadata** 以查看或编辑文件的元数据。在这里，您可以为此特定文件添加、删除或修改元数据字段。您在此处所做的任何编辑都将反映在知识库主元数据管理页面上的全局统计中。

![](https://raw.githubusercontent.com/infiniflow/ragflow-docs/main/images/set_metadata.png)
![](https://raw.githubusercontent.com/infiniflow/ragflow-docs/main/images/edit_metadata.png)

4. 过滤功能在两个级别运行：知识库管理和检索。在数据集中，点击 Filter 按钮以查看现有元数据字段下每个值关联的文件数量。通过选择特定值，您可以显示所有链接的文件。

![](https://raw.githubusercontent.com/infiniflow/ragflow-docs/main/images/filter_metadata.png)

5. 在检索阶段也支持元数据过滤。例如，在 Chat 中，您可以在配置知识库后设置元数据过滤规则：

![](https://raw.githubusercontent.com/infiniflow/ragflow-docs/main/images/metadata_filtering_rules.png)

-   **Automatic** 模式：系统根据用户的查询和知识库中的现有元数据自动过滤文档。
-   **Semi-automatic** 模式：用户首先在字段级别（例如，对于 **Author**）定义过滤范围，然后系统在该预设范围内自动过滤。
-   **Manual** 模式：用户手动设置精确的、特定于值的过滤条件，支持 **Equals**（等于）、**Not equals**（不等于）、**In**（包含）、**Not in**（不包含）等运算符。



