---
sidebar_position: -10
slug: /configure_knowledge_base
sidebar_custom_props: {
  categoryIcon: LucideCog
}
---
# 配置数据集

RAGFlow 的大多数聊天助手和智能体都基于数据集。RAGFlow 的每个数据集都作为知识源，将从本地计算机上传的文件和在 RAGFlow 文件系统中生成的文件引用*解析*为未来 AI 聊天的真实"知识"。本指南演示了数据集功能的一些基本用法，涵盖以下主题：

- 创建数据集
- 配置数据集
- 搜索数据集
- 删除数据集

## 创建数据集

拥有多个数据集，您可以构建更灵活、多样化的问答系统。要创建您的第一个数据集：

![create dataset](https://raw.githubusercontent.com/infiniflow/ragflow-docs/main/images/create_knowledge_base.jpg)

_每次创建数据集时，都会在 **root/.knowledgebase** 目录中生成一个同名的文件夹。_

## 配置数据集

以下屏幕截图显示了数据集的配置页面。正确配置数据集对于未来的 AI 聊天至关重要。例如，选择错误的嵌入模型或分块方法会导致聊天中出现意外的语义丢失或答案不匹配。

![dataset configuration](https://raw.githubusercontent.com/infiniflow/ragflow-docs/main/images/configure_knowledge_base.jpg)

本节涵盖以下主题：

- 选择分块方法
- 选择嵌入模型
- 上传文件
- 解析文件
- 干预文件解析结果
- 运行检索测试

### 选择分块方法

RAGFlow 提供多种内置分块模板，便于对不同布局的文件进行分块并确保语义完整性。从 **Parse type** 下的 **Built-in** 分块方法下拉菜单中，您可以选择适合文件布局和格式的默认模板。下表显示了每个支持的分块模板的描述和兼容的文件格式：

| **模板** | 描述                                                                   | 文件格式                                                                                             |
|--------------|-------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------|
| General      | 文件根据预设的分块令牌数连续分块。         | MD, MDX, DOCX, XLSX, XLS (Excel 97-2003), PPT, PDF, TXT, JPEG, JPG, PNG, TIF, GIF, CSV, JSON, EML, HTML |
| Q&A          | 检索相关信息并生成答案以响应问题。 | XLSX, XLS (Excel 97-2003), CSV/TXT                                                                      |
| Resume       | 仅限企业版。您也可以在 demo.ragflow.io 上试用。          | DOCX, PDF, TXT                                                                                          |
| Manual       |                                                                               | PDF                                                                                                     |
| Table        | 表格模式使用 TSI 技术进行高效数据解析。                | XLSX, XLS (Excel 97-2003), CSV/TXT                                                                      |
| Paper        |                                                                               | PDF                                                                                                     |
| Book         |                                                                               | DOCX, PDF, TXT                                                                                          |
| Laws         |                                                                               | DOCX, PDF, TXT                                                                                          |
| Presentation |                                                                               | PDF, PPTX                                                                                               |
| Picture      |                                                                               | JPEG, JPG, PNG, TIF, GIF                                                                                |
| One          | 每个文档作为一个整体（一个）进行分块。                            | DOCX, XLSX, XLS (Excel 97-2003), PDF, TXT                                                               |
| Tag          | 数据集作为其他数据集的标签集。                            | XLSX, CSV/TXT                                                                                           |

您也可以在 **Files** 页面上更改文件的分块方法。

![change chunking method](https://raw.githubusercontent.com/infiniflow/ragflow-docs/main/images/change_chunking_method.jpg)

<details>
  <summary>从 v0.21.0 开始，RAGFlow 支持摄入流程以实现自定义数据摄入和清洗工作流程。</summary>

  要使用自定义数据流程：

  1. 在 **Agent** 页面上，点击 **+ Create agent** > **Create from blank**。
  2. 选择 **Ingestion pipeline** 并在弹出窗口中为数据流程命名，然后点击 **Save** 显示数据流程画布。
  3. 更新数据流程后，点击画布右上角的 **Save**。
  4. 导航到数据集的 **配置** 页面，在 **Ingestion pipeline** 中选择 **Choose pipeline**。

     *您保存的数据流程将出现在下面的下拉菜单中。*

</details>

### 选择嵌入模型

嵌入模型将分块转换为嵌入。一旦数据集有分块，就无法更改。要切换到不同的嵌入模型，必须删除数据集中的所有现有分块。显而易见的原因是我们*必须*确保特定数据集中的文件使用*相同*的嵌入模型转换为嵌入（确保它们在同一嵌入空间中进行比较）。

:::danger 重要
某些嵌入模型针对特定语言进行了优化，如果用于嵌入其他语言的文档，性能可能会受到影响。
:::

### 上传文件

- RAGFlow 的文件系统允许您将文件链接到多个数据集，在这种情况下，每个目标数据集都持有对该文件的引用。
- 在 **Knowledge Base** 中，您还可以选择从本地计算机将单个文件或文件夹（批量上传）上传到数据集，在这种情况下，数据集持有文件副本。

虽然直接将文件上传到数据集似乎更方便，但我们*强烈*建议将文件上传到 RAGFlow 的文件系统，然后将它们链接到目标数据集。这样，您可以避免永久删除上传到数据集的文件。

### 解析文件

文件解析是数据集配置中的一个关键主题。RAGFlow 中文件解析的含义是双重的：根据文件布局对文件进行分块，并在这些分块上构建嵌入和全文（关键词）索引。选择分块方法和嵌入模型后，您可以开始解析文件：

![parse file](https://raw.githubusercontent.com/infiniflow/ragflow-docs/main/images/parse_file.jpg)

- 如上所示，RAGFlow 允许您为特定文件使用不同的分块方法，提供超出默认方法的灵活性。
- 如上所示，RAGFlow 允许您启用或禁用单个文件，为基于数据集的 AI 聊天提供更精细的控制。

### 干预文件解析结果

RAGFlow 具有可见性和可解释性，允许您查看分块结果并在必要时进行干预。为此：

1. 点击完成文件解析的文件以查看分块结果：

   _您将被带到 **Chunk** 页面：_

   ![chunks](https://raw.githubusercontent.com/infiniflow/ragflow-docs/main/images/file_chunks.jpg)

2. 将鼠标悬停在每个快照上以快速查看每个分块。

3. 双击分块文本以添加关键词、问题、标签或在必要时进行*手动*更改：

   ![update chunk](https://raw.githubusercontent.com/infiniflow/ragflow-docs/main/images/add_keyword_question.jpg)

:::caution 注意
您可以向文件分块添加关键词以提高其包含这些关键词的查询的排名。此操作会增加其关键词权重，并可以改善其在搜索列表中的位置。
:::

4. 在检索测试中，在 **Test text** 中问一个快速问题，以再次检查您的配置是否有效：

   _正如您从下面的内容中看到的，RAGFlow 以真实的引用响应。_

   ![retrieval test](https://raw.githubusercontent.com/infiniflow/ragflow-docs/main/images/retrieval_test.jpg)

### 运行检索测试

RAGFlow 在其聊天中使用全文搜索和向量搜索的多次召回。在设置 AI 聊天之前，请考虑调整以下参数以确保预期信息始终出现在答案中：

- 相似度阈值：相似度低于阈值的分块将被过滤。默认设置为 0.2。
- 向量相似度权重：向量相似度对整体评分的贡献百分比。默认设置为 0.3。

有关详细信息，请参阅[运行检索测试](./run_retrieval_test.md)。

## 搜索数据集

截至 RAGFlow v0.23.1，搜索功能仍然处于基本形式，仅支持按名称搜索数据集。

![search dataset](https://raw.githubusercontent.com/infiniflow/ragflow-docs/main/images/search_datasets.jpg)

## 删除数据集

您可以删除数据集。将鼠标悬停在目标数据集卡片的三个点上，会出现 **Delete** 选项。删除数据集后，**root/.knowledge** 目录下的关联文件夹将自动删除。结果是：

- 直接上传到数据集的文件已消失；
- 您在 RAGFlow 文件系统中创建的文件引用已消失，但关联文件仍然存在。

![delete dataset](https://raw.githubusercontent.com/infiniflow/ragflow-docs/main/images/delete_datasets.jpg)
