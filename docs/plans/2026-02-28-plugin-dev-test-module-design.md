# 文书解析 Plugin 开发测试模块设计

## 背景

当前开发新的文书解析 Plugin 时存在以下问题：
1. 手动测试需要上传文件、登录、等待 PaddleOCR API 返回、查看 chunk 结果，繁琐低效
2. 需要指定测试账户、知识库、特定文件
3. 频繁调用 PaddleOCR API，但其实只需要调用一次，利用 cache 测试专有文书解析方案即可

## 目标

为 AI 辅助开发 Plugin 提供快速验证工具，支持：
- 一次 OCR 调用，缓存结果
- 快速测试 Plugin 逻辑
- 不依赖完整后端环境

## 设计方案

### 文件结构

```
test/
└── test_plugin_dev.py    # 新增：Plugin 开发测试工具
```

### 核心流程

```
PDF 文件 → 检查 .ocr.json 缓存 → (有缓存直接用 / 无缓存调 API 并保存)
         ↓
    PaddleOCRParser (Layer A)
         ↓
    sections (带位置标签的文本)
         ↓
    Plugin (Layer B)
         ↓
    chunks → 格式化输出
```

### 命令行接口

```bash
uv run python test/test_plugin_dev.py <pdf_path> --doc-type <type> [--json] [--refresh]
```

| 参数 | 说明 |
|------|------|
| `pdf_path` | PDF 文件路径（必需） |
| `--doc-type` | 文书类型，如 `interrogation_record`、`indictment_opinion`（必需） |
| `--json` | 输出 JSON 格式（可选） |
| `--refresh` | 强制重新调用 OCR API，更新缓存（可选） |

### 缓存机制

- **位置**：与 PDF 同目录，文件名 `<pdf_stem>.ocr.json`
- **示例**：`讯问笔录_sample.pdf` → `讯问笔录_sample.ocr.json`
- **内容**：PaddleOCR API 的原始 `result` 字段

### 输出格式

#### 默认格式（人类可读）

```
=== Plugin Test Result ===
PDF: 讯问笔录_sample.pdf
Doc Type: interrogation_record
Total Chunks: 5
Using Cache: true

--- Chunk 1 [header_info] ---
Pages: 1
Text:
讯问笔录

--- Chunk 2 [qa_pair] ---
Pages: 1-2
Text:
问：你叫什么名字？
答：我叫张三。
```

#### JSON 格式（`--json`）

```json
{
  "pdf_path": "讯问笔录_sample.pdf",
  "doc_type": "interrogation_record",
  "total_chunks": 5,
  "using_cache": true,
  "chunks": [
    {
      "chunk_id": "1",
      "chunk_type": "header_info",
      "page_range": [1, 1],
      "text": "讯问笔录"
    }
  ]
}
```

### 代码结构

```python
# test/test_plugin_dev.py

def main():
    """命令行入口，解析参数并执行测试"""
    ...

def load_or_create_ocr_cache(pdf_path: Path) -> dict:
    """
    加载或创建 OCR 缓存。
    - 存在缓存：直接加载 .ocr.json
    - 无缓存：调用 PaddleOCR API 并保存
    """
    ...

def run_layer_a(cached_result: dict) -> list[UniversalBlock]:
    """执行 Layer A：从缓存结果提取 UniversalBlock"""
    ...

def run_layer_b(blocks: list[UniversalBlock], doc_type: str) -> list[Chunk]:
    """执行 Layer B：调用 Plugin 生成 Chunks"""
    ...

def format_output_human(result: dict) -> str:
    """格式化为人类可读文本"""
    ...

def format_output_json(result: dict) -> str:
    """格式化为 JSON"""
    ...

if __name__ == "__main__":
    main()
```

### 依赖

- `deepdoc.parser.paddleocr_parser.PaddleOCRParser` - OCR 解析
- `rag.app.naive.extract_universal_blocks` - Layer A
- `rag.app.criminal.router.route_to_plugin` - Layer B
- `argparse` - 命令行参数解析

### CLAUDE.md 更新

在 CLAUDE.md 中添加测试工具使用文档，包括：
- 命令行使用方式
- 支持的文书类型列表
- OCR 缓存机制说明
- 开发新 Plugin 的推荐流程

## 使用场景

AI 开发新 Plugin 时的典型工作流：

1. 准备样本 PDF 文件
2. 运行测试工具获取当前输出
3. 修改 Plugin 代码
4. 再次运行测试工具验证修改效果
5. 重复 3-4 直到满意
