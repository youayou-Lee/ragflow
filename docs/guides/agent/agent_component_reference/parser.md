---
sidebar_position: 30
slug: /parser_component
sidebar_custom_props: {
  categoryIcon: LucideFilePlay
}
---
# 解析器组件

一个为数据集设置解析规则的组件。

---

**解析器**组件在摄入流水线画布上自动填充,并且是所有摄入流水线工作流中必需的。就像传统 ETL 过程中的 **提取** 阶段一样,摄入流水线中的 **解析器** 组件定义了各种文件类型如何解析为结构化数据。点击该组件以显示其配置面板。在此配置面板中,您可以为各种文件类型设置解析规则。

## 配置

在配置面板中,您可以添加多个解析器并设置相应的解析规则或删除不需要的解析器。请确保您的解析器集涵盖所有必需的文件类型;否则,当您在数据集的 **文件** 页面上选择此摄入流水线时将发生错误。

**解析器** 组件支持解析以下文件类型:

| 文件类型     | 文件格式              |
|---------------|--------------------------|
| PDF           | PDF                      |
| 电子表格   | XLSX, XLS, CSV           |
| 图片         | PNG, JPG, JPEG, GIF, TIF |
| 邮件         | EML                      |
| 文本和标记 | TXT, MD, MDX, HTML, JSON |
| Word          | DOCX                     |
| PowerPoint    | PPTX, PPT                |
| 音频         | MP3, WAV                 |
| 视频         | MP4, AVI, MKV            |

### PDF 解析器

PDF 解析器的输出是 `json`。在 PDF 解析器中,选择最适合您的 PDF 的解析方法。

- DeepDoc:(默认)默认的视觉模型,对复杂的 PDF 执行 OCR、TSR 和 DLR 任务,但可能耗时。
- Naive: 如果您的所有 PDF 都是纯文本,则跳过 OCR、TSR 和 DLR 任务。
- [MinerU](https://github.com/opendatalab/MinerU):(实验性)一种将 PDF 转换为机器可读格式的开源工具。
- [Docling](https://github.com/docling-project/docling):(实验性)一种面向生成式 AI 的开源文档处理工具。
- 来自特定模型提供商的第三方视觉模型。

:::danger 重要
从 v0.22.0 开始,RAGFlow 包括 MinerU(&ge; 2.6.3)作为多后端的可选 PDF 解析器。请注意,RAGFlow 仅充当 MinerU 的*远程客户端*,调用 MinerU API 来解析文档并读取返回的文件。要使用此功能:
:::

1. 准备一个可访问的 MinerU API 服务(FastAPI 服务器)。
2. 在 **.env** 文件中或从 UI 中的 **模型提供商** 页面,将 RAGFlow 配置为 MinerU 的远程客户端:
   - `MINERU_APISERVER`: MinerU API 端点(例如,`http://mineru-host:8886`)。
   - `MINERU_BACKEND`: MinerU 后端:
      - `"pipeline"`(默认)
      - `"vlm-http-client"`
      - `"vlm-transformers"`
      - `"vlm-vllm-engine"`
      - `"vlm-mlx-engine"`
      - `"vlm-vllm-async-engine"`
      - `"vlm-lmdeploy-engine"`。
   - `MINERU_SERVER_URL`:(可选)下游 vLLM HTTP 服务器(例如,`http://vllm-host:30000`)。当 `MINERU_BACKEND` 设置为 `"vlm-http-client"` 时适用。
   - `MINERU_OUTPUT_DIR`:(可选)用于在摄入之前保存 MinerU API 服务输出(zip/JSON)的本地目录。
   - `MINERU_DELETE_OUTPUT`: 使用临时目录时是否删除临时输出:
     - `1`: 删除。
     - `0`: 保留。
3. 在 Web UI 中,导航到数据集的 **配置** 页面并找到 **摄入流水线** 部分:
   - 如果您决定使用 **内置** 下拉菜单中的分块方法,请确保它支持 PDF 解析,然后从 **PDF 解析器** 下拉菜单中选择 **MinerU**。
   - 如果您改用自定义摄入流水线,请在 **解析器** 组件的 **PDF 解析器** 部分中选择 **MinerU**。

:::note
所有 MinerU 环境变量都是可选的。设置后,这些值将用于在首次使用时为租户自动配置 MinerU OCR 模型。要避免自动配置,请跳过环境变量设置,仅从 UI 的 **模型提供商** 页面配置 MinerU。
:::

:::caution 警告
第三方视觉模型标记为 **实验性**,因为我们尚未针对上述数据提取任务对这些模型进行充分测试。
:::

### 电子表格解析器

电子表格解析器输出 `html`,保留原始布局和表格结构。如果您的数据集不包含电子表格,则可以删除此解析器。

### 图片解析器

图片解析器默认使用原生 OCR 模型进行文本提取。您可以选择替代的 VLM 模型,前提是您在 **模型提供商** 页面上对其进行了正确配置。

### 邮件解析器

使用邮件解析器,您可以选择要从邮件中解析的字段,例如 **主题** 和 **正文**。然后,解析器将从这些指定字段中提取文本。

### 文本和标记解析器

文本和标记解析器自动删除所有格式标签(例如,来自 HTML 和 Markdown 文件的标签),仅输出干净的纯文本。

### Word 解析器

Word 解析器输出 `json`,保留原始文档结构信息,包括标题、段落、表格、页眉和页脚。

### PowerPoint (PPT) 解析器

PowerPoint 解析器将 PowerPoint 文件中的内容提取到 `json` 中,单独处理每张幻灯片并区分其标题、正文和备注。

### 音频解析器

音频解析器将音频文件转录为文本。要使用此解析器,您必须首先在 **模型提供商** 页面上配置 ASR 模型。

### 视频解析器

视频解析器将视频文件转录为文本。要使用此解析器,您必须首先在 **模型提供商** 页面上配置 VLM 模型。

## 输出

**解析器**组件输出的全局变量名称,可由摄入流水线中的后续组件引用。

| 变量名称 | 类型            |
|---------------|-----------------|
| `markdown`    | `string`        |
| `text`        | `string`        |
| `html`        | `string`        |
| `json`        | `Array<Object>` |
