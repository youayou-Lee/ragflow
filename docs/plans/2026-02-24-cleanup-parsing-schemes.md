# 清理解析方案实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 删除所有现有解析方案，保留 naive.py 作为唯一入口，合并 Layer A 功能。

**Architecture:** 将 criminal/blocks.py（Layer A Block 抽取）和 criminal/ner.py（轻量 NER）合并到 naive.py，删除其他所有解析方法。前端只保留 naive 配置。测试只保留 eval 的基础配置。

**Tech Stack:** Python, TypeScript/React, pytest

---

## Task 1: 合并 Layer A 功能到 naive.py

**Files:**
- Modify: `rag/app/naive.py`
- Reference: `rag/app/criminal/blocks.py`
- Reference: `rag/app/criminal/ner.py`

**Step 1: 在 naive.py 顶部添加 Layer A 相关导入和类定义**

在 `rag/app/naive.py` 文件顶部（现有导入之后）添加：

```python
import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List


class BlockType(str, Enum):
    """Layout element types for universal blocks."""
    HEADER = "header"
    PARAGRAPH = "paragraph"
    QA_PAIR = "qa_pair"
    TABLE = "table"
    LIST = "list"
    SEAL = "seal"
    FOOTER = "footer"


@dataclass
class UniversalBlock:
    """Universal block structure - Layer A output."""
    block_type: BlockType
    text: str
    page_no: int
    bbox: tuple[float, float, float, float]
    doc_type_hint: Optional[str] = None
    entities: Optional[dict] = None
```

**Step 2: 添加 NER 函数**

在类定义之后添加：

```python
def extract_lightweight_entities(text: str) -> Optional[dict]:
    """Extract amounts and dates from text."""
    entities = {"amounts": [], "dates": []}

    amount_patterns = [
        r'(\d+(?:,\d{3})*(?:\.\d{1,2})?)\s*[元万]',
        r'([一二三四五六七八九十百千万亿]+)\s*[元万]',
    ]
    for pattern in amount_patterns:
        entities["amounts"].extend(re.findall(pattern, text))

    date_patterns = [
        r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})',
        r'(\d{4}年\d{1,2}月\d{1,2}日?)',
        r'(\d{1,2}月\d{1,2}日)',
    ]
    for pattern in date_patterns:
        entities["dates"].extend(re.findall(pattern, text))

    entities["amounts"] = list(set(entities["amounts"]))
    entities["dates"] = list(set(entities["dates"]))

    if not entities["amounts"] and not entities["dates"]:
        return None
    return entities
```

**Step 3: 添加 Block 抽取辅助函数**

```python
POSITION_TAG_PATTERN = re.compile(
    r"^@@(\d+(?:-\d+)?)\t([\d.]+)\t([\d.]+)\t([\d.]+)\t([\d.]+)##(.*)$",
    re.DOTALL
)


def parse_position_tag(text: str) -> tuple[int, Optional[tuple], str]:
    """Parse position tag from OCR output text."""
    match = POSITION_TAG_PATTERN.match(text)
    if not match:
        return 0, None, text

    page_str, x0, x1, top, bottom, content = match.groups()
    first_page = int(page_str.split("-")[0]) - 1
    bbox = (float(x0), float(top), float(x1), float(bottom))
    return first_page, bbox, content


def infer_block_type(text: str, position: str, doc_type_hint: Optional[str] = None) -> BlockType:
    """Infer block type from text content and position."""
    text = text.strip()

    if "印章" in text or (len(text) < 10 and "章" in text):
        return BlockType.SEAL
    if text.startswith(("问：", "问:", "答：", "答:")):
        return BlockType.QA_PAIR
    if re.match(r'^\s*[\d一二三四五六七八九十]+[\.、）]', text):
        return BlockType.LIST
    if position == "first" and len(text) < 500:
        return BlockType.HEADER
    if position == "last" and len(text) < 50:
        return BlockType.FOOTER
    return BlockType.PARAGRAPH


def _get_relative_position(index: int, total: int) -> str:
    if total == 1:
        return "first"
    if index == 0:
        return "first"
    if index == total - 1:
        return "last"
    return "middle"
```

**Step 4: 添加主函数 extract_universal_blocks**

```python
def extract_universal_blocks(sections: list, doc_type_hint: Optional[str] = None) -> List[UniversalBlock]:
    """Extract universal blocks from OCR output sections."""
    if not sections:
        return []

    blocks = []
    total = len(sections)

    for index, section in enumerate(sections):
        if isinstance(section, (list, tuple)):
            if len(section) >= 2:
                content = section[0] or ""
                tag = section[1] or ""
            else:
                content = section[0] if section else ""
                tag = ""
        else:
            content = str(section)
            tag = ""

        text_with_tag = f"{tag}{content}" if tag else content
        page_no, bbox, text = parse_position_tag(text_with_tag)
        position = _get_relative_position(index, total)
        block_type = infer_block_type(text, position, doc_type_hint)
        entities = extract_lightweight_entities(text)

        block = UniversalBlock(
            block_type=block_type,
            text=text,
            page_no=page_no,
            bbox=bbox if bbox else (0.0, 0.0, 0.0, 0.0),
            doc_type_hint=doc_type_hint,
            entities=entities
        )
        blocks.append(block)

    return blocks
```

**Step 5: 验证合并成功**

Run: `uv run python -c "from rag.app.naive import extract_universal_blocks, UniversalBlock, BlockType; print('Import OK')"`

Expected: `Import OK`

**Step 6: 提交**

```bash
git add rag/app/naive.py
git commit -m "feat(naive): merge Layer A block extraction functionality

Merge criminal/blocks.py and criminal/ner.py into naive.py:
- Add BlockType enum and UniversalBlock dataclass
- Add extract_lightweight_entities for NER
- Add extract_universal_blocks as main Layer A function

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 2: 删除后端解析方法文件

**Files:**
- Delete: `rag/app/picture.py`
- Delete: `rag/app/tag.py`
- Delete: `rag/app/interrogation.py`
- Delete: `rag/app/indictment.py`
- Delete: `rag/app/scene_investigation.py`
- Delete: `rag/app/criminal/` (整个目录)

**Step 1: 删除独立解析方法文件**

```bash
rm rag/app/picture.py rag/app/tag.py rag/app/interrogation.py rag/app/indictment.py rag/app/scene_investigation.py
```

**Step 2: 删除 criminal 目录**

```bash
rm -rf rag/app/criminal/
```

**Step 3: 验证目录结构**

Run: `ls -la rag/app/`

Expected: 只剩 `__init__.py`, `naive.py`, `chunkers/`, `metadata/`, `parsers/`

**Step 4: 提交**

```bash
git add -A rag/app/
git commit -m "chore: remove unused parsing methods

Remove all parsing methods except naive.py:
- picture.py, tag.py (general methods)
- interrogation.py, indictment.py, scene_investigation.py (criminal)
- criminal/ directory (Layer A+B plugins)

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 3: 更新前端 - 删除配置组件

**Files:**
- Delete: `web/src/pages/dataset/dataset-setting/configuration/interrogation.tsx`
- Delete: `web/src/pages/dataset/dataset-setting/configuration/indictment.tsx`

**Step 1: 删除刑事案件配置组件**

```bash
rm web/src/pages/dataset/dataset-setting/configuration/interrogation.tsx
rm web/src/pages/dataset/dataset-setting/configuration/indictment.tsx
```

**Step 2: 提交**

```bash
git add -A web/src/pages/dataset/dataset-setting/configuration/
git commit -m "chore(frontend): remove criminal parser config components

Remove interrogation.tsx and indictment.tsx

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 4: 更新前端 - 修改枚举和配置映射

**Files:**
- Modify: `web/src/constants/knowledge.ts`
- Modify: `web/src/pages/dataset/dataset-setting/chunk-method-form.tsx`

**Step 1: 更新 DocumentParserType 枚举**

修改 `web/src/constants/knowledge.ts` 第 79-83 行：

```typescript
export enum DocumentParserType {
  Naive = 'naive',
}
```

**Step 2: 更新 chunk-method-form.tsx**

修改 `web/src/pages/dataset/dataset-setting/chunk-method-form.tsx`：

```typescript
import { useFormContext, useWatch } from 'react-hook-form';
import { DocumentParserType } from '@/constants/knowledge';
import { useMemo } from 'react';
import { NaiveConfiguration } from './configuration/naive';

const ConfigurationComponentMap = {
  [DocumentParserType.Naive]: NaiveConfiguration,
};

function EmptyComponent() {
  return <div></div>;
}

export function ChunkMethodForm() {
  const form = useFormContext();
  const finalParserId: DocumentParserType = useWatch({
    control: form.control,
    name: 'parser_id',
  });

  const ConfigurationComponent = useMemo(() => {
    return finalParserId
      ? ConfigurationComponentMap[finalParserId]
      : EmptyComponent;
  }, [finalParserId]);

  return (
    <section className="h-full flex flex-col">
      <div className="overflow-auto flex-1 min-h-0">
        <ConfigurationComponent></ConfigurationComponent>
      </div>
    </section>
  );
}
```

**Step 3: 验证前端构建**

Run: `cd web && bun run build`

Expected: 构建成功，无错误

**Step 4: 提交**

```bash
git add web/src/constants/knowledge.ts web/src/pages/dataset/dataset-setting/chunk-method-form.tsx
git commit -m "refactor(frontend): simplify parser type to naive only

- Remove Interrogation and Indictment from DocumentParserType
- Simplify ConfigurationComponentMap

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 5: 更新前端 - 清理语言文件

**Files:**
- Modify: `web/src/locales/zh.ts`
- Modify: `web/src/locales/en.ts`

**Step 1: 清理 zh.ts 中的解析方法描述**

搜索并删除与 interrogation、indictment 相关的描述文本。

**Step 2: 清理 en.ts 中的解析方法描述**

搜索并删除与 interrogation、indictment 相关的描述文本。

**Step 3: 提交**

```bash
git add web/src/locales/zh.ts web/src/locales/en.ts
git commit -m "chore(frontend): clean up parser method descriptions

Remove unused parser method descriptions from locale files

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 6: 删除单元测试目录

**Files:**
- Delete: `test/unit/` (整个目录)

**Step 1: 删除 unit 测试目录**

```bash
rm -rf test/unit/
```

**Step 2: 验证删除**

Run: `ls -la test/`

Expected: 只有 `eval/` 目录

**Step 3: 提交**

```bash
git add -A test/
git commit -m "chore: remove unit tests

Remove test/unit/ directory as part of parsing scheme cleanup

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 7: 清理 eval 测试目录

**Files:**
- Keep: `test/eval/config.yaml` (基础配置)
- Create: `test/eval/test_template.py` (测试模板)
- Delete: eval 目录下其他所有测试文件

**Step 1: 删除测试文件和子目录**

```bash
rm -rf test/eval/evaluator/
rm -rf test/eval/integration/
rm -rf test/eval/questions/
rm -rf test/eval/report/
rm -rf test/eval/reports/
rm test/eval/config_chenmingfei_full.yaml
rm test/eval/__init__.py
rm test/eval/models.py
rm test/eval/README.md
rm test/eval/run.py
rm test/eval/run_chenmingfei_interrogation_e2e.py
rm test/eval/run_indictment_e2e.py
rm test/eval/test_indictment_quick.py
rm test/eval/test_quick_parse.py
rm test/eval/test_single_upload.py
rm -rf test/eval/__pycache__/
```

**Step 2: 创建最小化测试模板**

创建 `test/eval/test_template.py`:

```python
"""
Test template for eval module.

This is a minimal template for future test development.
"""

import pytest


class TestTemplate:
    """Template test class for eval tests."""

    def test_placeholder(self):
        """Placeholder test - replace with actual tests."""
        # TODO: Add actual test cases
        assert True
```

**Step 3: 简化 config.yaml**

保留基础配置，删除测试用例相关内容：

```yaml
# RAGFlow Eval 测试配置

server:
  base_url: "http://127.0.0.1:9380"
  api_version: "v1"

auth:
  email: "your-email@example.com"
  # 使用加密后的密码
  password: "your-encrypted-password"

dataset:
  name_prefix: "eval_benchmark"
  embedding_model: "embedding-3@ZHIPU-AI"
  chunk_method: "naive"

chat:
  llm_model: "glm-4-flash@ZHIPU-AI"

test:
  parse_timeout: 300
  parse_interval: 5
```

**Step 4: 验证目录结构**

Run: `ls -la test/eval/`

Expected: 只有 `config.yaml` 和 `test_template.py`

**Step 5: 提交**

```bash
git add -A test/eval/
git commit -m "chore: clean up eval tests

- Remove all test files and subdirectories
- Keep minimal config.yaml with credentials
- Add test_template.py as placeholder

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 8: 最终验证

**Step 1: 验证后端导入**

Run: `uv run python -c "from rag.app.naive import extract_universal_blocks, UniversalBlock, BlockType; print('Backend OK')"`

Expected: `Backend OK`

**Step 2: 验证前端构建**

Run: `cd web && bun run build`

Expected: 构建成功

**Step 3: 验证目录结构**

Run: `find rag/app test -type f -name "*.py" | head -20`

Expected:
```
rag/app/__init__.py
rag/app/naive.py
test/eval/config.yaml
test/eval/test_template.py
```

**Step 4: 最终提交（如有遗漏）**

```bash
git status
# 如有未提交的更改
git add -A
git commit -m "chore: final cleanup for parsing scheme removal

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Summary

| Task | Description | Files Changed |
|------|-------------|---------------|
| 1 | 合并 Layer A 到 naive.py | `rag/app/naive.py` |
| 2 | 删除后端解析方法 | 删除 6 个文件 + criminal/ 目录 |
| 3 | 删除前端配置组件 | 删除 2 个 tsx 文件 |
| 4 | 更新前端枚举映射 | 2 个文件 |
| 5 | 清理语言文件 | 2 个文件 |
| 6 | 删除单元测试 | test/unit/ 目录 |
| 7 | 清理 eval 测试 | 保留 config.yaml + 模板 |
| 8 | 最终验证 | - |
