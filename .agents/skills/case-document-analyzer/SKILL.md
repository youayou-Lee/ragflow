---
name: case-document-analyzer
description: Use when analyzing legal case documents (起诉意见书, 判决书, etc.) to generate benchmark question banks with precise location tags for RAG evaluation
---

# Case Document Analyzer

## Overview

Automate the creation of benchmark question banks from legal case documents. Transforms PDF documents into structured question sets with precise location tags for RAG system evaluation.

## When to Use

- Creating benchmark question banks from legal documents
- Generating test cases for criminal RAG system evaluation
- Need precise location tags for answer verification
- Processing 起诉意见书, 判决书, or similar legal documents

## Core Workflow

### Step 1: Convert PDF to Positioned Text

Use the provided script to extract text blocks with position information:

```bash
# Basic usage - parse PDF and print blocks
uv run python .agents/skills/case-document-analyzer/pdf_to_positioned_text.py indictment.pdf

# Save output to benchmark directory
uv run python .agents/skills/case-document-analyzer/pdf_to_positioned_text.py \
    indictment.pdf \
    --output benchmark/起诉意见书/曾庆成危险驾驶案/原始数据 \
    --save-json
```

Output files:
- `blocks.json` - Simplified blocks with location tags
- `paddleocr_response.json` - Raw PaddleOCR API response

#### blocks.json Format

```json
{
  "source_file": "indictment.pdf",
  "parsed_at": "2026-02-16T12:00:00",
  "page_count": 2,
  "pages": [
    {"page_number": 1, "width": 1196, "height": 1680}
  ],
  "blocks": [
    {
      "page": 1,
      "block_id": 2,
      "label": "doc_title",
      "content": "清远市公安局清新分局",
      "bbox": [459, 177, 738, 211],
      "location_tag": "@@1\t229\t369\t88\t105##",
      "order": 1
    }
  ]
}
```

### Step 2: Location Tag Format

```
@@{page}\t{x0 // 2}\t{x1 // 2}\t{y0 // 2}\t{y1 // 2}##
```

Where:
- `page`: 1-indexed page number
- `x0, x1, y0, y1`: Block bbox coordinates divided by ZOOMIN (2)

### Step 3: Generate Question Types

Generate three question files:

| Type | File | Purpose |
|------|------|---------|
| Fact | `01-事实型题目.md` | Single-fact extraction |
| Evidence | `02-证据集合型题目.md` | Multi-source aggregation |
| Gap | `03-冲突缺口型题目.md` | Missing information detection |

### Step 4: Output Structure

```
benchmark/{document_type}/{case_name}/
├── 原始数据/
│   └── paddleocr_response.json
├── README.md
├── 01-事实型题目.md
├── 02-证据集合型题目.md
└── 03-冲突缺口型题目.md
```

## Question Format

```markdown
## N. Question Title

**问题**：Question text?

**答案**：Answer

**位置**：`@@{page}\t{x0}\t{x1}\t{y0}\t{y1}##`
**证据原文**：`Original text from document`
```

## Quick Reference

### Block to Location Tag

```python
def block_to_tag(page_idx: int, bbox: list[int]) -> str:
    page = page_idx + 1
    x0, y0, x1, y1 = [coord // 2 for coord in bbox]
    return f"@@{page}\\t{x0}\\t{x1}\\t{y0}\\t{y1}##"
```

### Common Document Elements

| Element | Typical Location |
|---------|------------------|
| 办案机关 | Page 1, doc_title block |
| 犯罪嫌疑人信息 | Page 1, first text block |
| 案发经过 | Page 1, large text block |
| 证据清单 | Page 1, numbered list |
| 法律依据 | Page 2, legal citations |

## Common Mistakes

1. **Wrong page numbering**: Tags use 1-indexed pages, but JSON uses 0-indexed page_idx
2. **Missing ZOOMIN division**: Coordinates must be divided by 2
3. **Incomplete location tags**: Always include all four coordinates
4. **Fuzzy locations**: Never use descriptions like "第二页段落", always use precise tags
