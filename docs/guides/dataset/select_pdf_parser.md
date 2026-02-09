---
sidebar_position: -3
slug: /select_pdf_parser
sidebar_custom_props: {
  categoryIcon: LucideFileText
}
---
# 选择 PDF 解析器

选择视觉模型来解析您的 PDF。

---

RAGFlow 不是一刀切的。它为灵活性而构建，支持更深入的自定义以适应更复杂的用例。从 v0.17.0 开始，RAGFlow 将 DeepDoc 特定的数据提取任务与分块方法分离**对于 PDF 文件**。这种分离使您能够自主选择视觉模型用于 OCR（光学字符识别）、TSR（表格结构识别）和 DLR（文档布局识别）任务，以平衡速度和性能以适应您的特定用例。如果您的 PDF 仅包含纯文本，您可以选择跳过这些任务，选择 **Naive** 选项以减少总体解析时间。

![data extraction](https://raw.githubusercontent.com/infiniflow/ragflow-docs/main/images/data_extraction.jpg)

## 先决条件

- PDF 解析器下拉菜单仅在您选择与 PDF 兼容的分块方法时出现，包括：
  - **General**
  - **Manual**
  - **Paper**
  - **Book**
  - **Laws**
  - **Presentation**
  - **One**
- 要使用第三方视觉模型解析 PDF，请确保您已在 **Model providers** 页面上的 **Set default models** 下设置了默认 VLM。

## 快速开始

1. 在数据集的 **配置** 页面上，选择一个分块方法，例如 **General**。

   _**PDF parser** 下拉菜单出现。_

2. 选择最适合您的场景的选项：

- DeepDoc：（默认）默认视觉模型，对 PDF 执行 OCR、TSR 和 DLR 任务，但可能耗时。
- Naive：如果您的*所有* PDF 都是纯文本，则跳过 OCR、TSR 和 DLR 任务。
- [MinerU](https://github.com/opendatalab/MinerU):（实验性）一种将 PDF 转换为机器可读格式的开源工具。
- [Docling](https://github.com/docling-project/docling):（实验性）一种用于生成 AI 的开源文档处理工具。
- 来自特定模型提供商的第三方视觉模型。

:::danger 重要
从 v0.22.0 开始，RAGFlow 包括 MinerU（≥ 2.6.3）作为多后端的可选 PDF 解析器。请注意，RAGFlow 仅充当 MinerU 的*远程客户端*，调用 MinerU API 解析文档并读取返回的文件。要使用此功能：
:::

1. 准备一个可访问的 MinerU API 服务（FastAPI 服务器）。
2. 在 **.env** 文件中或从 UI 中的 **Model providers** 页面，将 RAGFlow 配置为 MinerU 的远程客户端：
   - `MINERU_APISERVER`：MinerU API 端点（例如，`http://mineru-host:8886`）。
   - `MINERU_BACKEND`：MinerU 后端：
      - `"pipeline"`（默认）
      - `"vlm-http-client"`
      - `"vlm-transformers"`
      - `"vlm-vllm-engine"`
      - `"vlm-mlx-engine"`
      - `"vlm-vllm-async-engine"`
      - `"vlm-lmdeploy-engine"`。
   - `MINERU_SERVER_URL`：（可选）下游 vLLM HTTP 服务器（例如，`http://vllm-host:30000`）。适用于 `MINERU_BACKEND` 设置为 `"vlm-http-client"` 时。
   - `MINERU_OUTPUT_DIR`：（可选）用于在摄入前保存 MinerU API 服务输出的本地目录（zip/JSON）。
   - `MINERU_DELETE_OUTPUT`：使用临时目录时是否删除临时输出：
     - `1`：删除。
     - `0`：保留。
3. 在 Web UI 中，导航到数据集的 **配置** 页面并找到 **Ingestion pipeline** 部分：
   - 如果您决定从 **Built-in** 下拉菜单中选择分块方法，请确保它支持 PDF 解析，然后从 **PDF parser** 下拉菜单中选择 **MinerU**。
   - 如果您改用自定义摄入流程，请在 **Parser** 组件的 **PDF parser** 部分选择 **MinerU**。

:::note
所有 MinerU 环境变量都是可选的。设置后，这些值将用于在首次使用时为租户自动配置 MinerU OCR 模型。为了避免自动配置，请跳过环境变量设置，仅从 UI 中的 **Model providers** 页面配置 MinerU。
:::

:::caution 警告
第三方视觉模型标记为**实验性**，因为我们尚未针对上述数据提取任务对这些模型进行全面测试。
:::

## 常见问题

### 我应该何时选择 DeepDoc 或第三方视觉模型作为 PDF 解析器？

如果您的 PDF 包含格式化或基于图像的文本而不是纯文本，请使用视觉模型提取数据。DeepDoc 是默认的视觉模型，但可能很耗时。您也可以根据您的需求和硬件能力选择轻量级或高性能的 VLM。

### 我可以选择视觉模型来解析我的 DOCX 文件吗？

不，您不能。此下拉菜单仅适用于 PDF。要使用此功能，请先将您的 DOCX 文件转换为 PDF。
