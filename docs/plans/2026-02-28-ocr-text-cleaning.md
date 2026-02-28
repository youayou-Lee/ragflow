# OCR Text Cleaning Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add OCR text cleaning to remove page numbers, line numbers, LaTeX formatting, underlines, and duplicate text from interrogation records.

**Architecture:** Two-layer cleaning approach:
- Layer A: Universal cleaning rules (page numbers, OCR line numbers, LaTeX, whitespace)
- Layer B Plugin: Document-specific rules (underlines for forms, duplicate detection)

**Tech Stack:** Python 3.12, regex, pytest

---

## Task 1: Create TextCleaner Base Module (Layer A)

**Files:**
- Create: `rag/app/criminal/text_cleaner.py`
- Test: `test/unit_test/rag/app/criminal/test_text_cleaner.py`

**Step 1: Write the failing test for page number removal**

```python
# test/unit_test/rag/app/criminal/test_text_cleaner.py

import pytest
from rag.app.criminal.text_cleaner import TextCleaner


class TestTextCleanerPageNumbers:
    """Test page number removal."""

    def setup_method(self):
        self.cleaner = TextCleaner()

    def test_remove_simple_page_number(self):
        """Remove '第 X 页 共 Y 页' pattern."""
        text = "这是正文内容\n第 6 页 共 8 页\n继续的内容"
        result = self.cleaner.clean(text)
        assert "第 6 页 共 8 页" not in result
        assert "这是正文内容" in result
        assert "继续的内容" in result

    def test_remove_page_number_no_spaces(self):
        """Remove '第X页共Y页' pattern without spaces."""
        text = "内容第6页共8页更多内容"
        result = self.cleaner.clean(text)
        assert "第6页共8页" not in result

    def test_remove_page_number_with_extra_spaces(self):
        """Remove '第  X  页  共  Y  页' with multiple spaces."""
        text = "内容第  6  页  共  8  页更多内容"
        result = self.cleaner.clean(text)
        assert "页  共" not in result
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest test/unit_test/rag/app/criminal/test_text_cleaner.py -v
```
Expected: FAIL with "ModuleNotFoundError" or "ImportError"

**Step 3: Write minimal implementation**

```python
# rag/app/criminal/text_cleaner.py

import re
from typing import Protocol


class TextCleaner:
    """
    OCR text cleaner for Layer A.

    Handles universal cleaning rules applicable to all document types:
    - Page numbers (第 X 页 共 Y 页)
    - OCR line numbers
    - LaTeX formatting
    - Whitespace normalization
    """

    # Page number pattern: 第 X 页 共 Y 页 (with variable spaces)
    PAGE_NUMBER_PATTERN = re.compile(
        r'第\s*\d+\s*页\s*共\s*\d+\s*页'
    )

    def clean(self, text: str) -> str:
        """
        Apply all cleaning rules to text.

        Args:
            text: Raw OCR text

        Returns:
            Cleaned text
        """
        if not text:
            return text

        text = self._remove_page_numbers(text)
        text = self._normalize_whitespace(text)

        return text.strip()

    def _remove_page_numbers(self, text: str) -> str:
        """Remove page number patterns like '第 6 页 共 8 页'."""
        return self.PAGE_NUMBER_PATTERN.sub('', text)

    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace: multiple spaces to single, multiple newlines to double."""
        # Multiple spaces to single space
        text = re.sub(r'[^\S\n]+', ' ', text)
        # Multiple newlines to double newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest test/unit_test/rag/app/criminal/test_text_cleaner.py -v
```
Expected: 3 PASS

**Step 5: Commit**

```bash
git add rag/app/criminal/text_cleaner.py test/unit_test/rag/app/criminal/test_text_cleaner.py
git commit -m "feat(criminal): add TextCleaner with page number removal

- Add TextCleaner class for Layer A universal cleaning
- Remove '第 X 页 共 Y 页' page number patterns
- Normalize whitespace
- Add unit tests

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 2: Add OCR Line Number Removal

**Files:**
- Modify: `rag/app/criminal/text_cleaner.py`
- Modify: `test/unit_test/rag/app/criminal/test_text_cleaner.py`

**Step 1: Write the failing tests**

```python
# Add to test/unit_test/rag/app/criminal/test_text_cleaner.py

class TestTextCleanerLineNumbers:
    """Test OCR line number removal."""

    def setup_method(self):
        self.cleaner = TextCleaner()

    def test_remove_standalone_line_number(self):
        """Remove standalone 3-digit numbers (OCR line numbers)."""
        text = "307\n这是正文内容"
        result = self.cleaner.clean(text)
        assert result == "这是正文内容"

    def test_remove_line_number_with_leading_zero(self):
        """Remove line numbers like 012, 013."""
        text = "内容\n012\n更多内容"
        result = self.cleaner.clean(text)
        assert "012" not in result

    def test_preserve_numbers_in_text(self):
        """Preserve numbers that are part of content."""
        text = "金额42000元，电话13750173434"
        result = self.cleaner.clean(text)
        assert "42000" in result
        assert "13750173434" in result

    def test_remove_line_number_at_end(self):
        """Remove line number at end of line."""
        text = "这是正文内容\n110"
        result = self.cleaner.clean(text)
        assert result == "这是正文内容"

    def test_preserve_page_references(self):
        """Preserve meaningful page references like '第1页'."""
        text = "见第1页的证据"
        result = self.cleaner.clean(text)
        assert "第1页" in result
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest test/unit_test/rag/app/criminal/test_text_cleaner.py::TestTextCleanerLineNumbers -v
```
Expected: FAIL

**Step 3: Implement line number removal**

```python
# Modify rag/app/criminal/text_cleaner.py

class TextCleaner:
    # ... existing code ...

    # OCR line number pattern: standalone 3-digit number on its own line
    # Matches numbers like 307, 012, 110, 909 at start/end of text or on own line
    LINE_NUMBER_PATTERN = re.compile(
        r'(?:^|\n)\s*\d{3}\s*(?=\n|$)'
    )

    def clean(self, text: str) -> str:
        """Apply all cleaning rules to text."""
        if not text:
            return text

        text = self._remove_page_numbers(text)
        text = self._remove_line_numbers(text)
        text = self._normalize_whitespace(text)

        return text.strip()

    def _remove_line_numbers(self, text: str) -> str:
        """
        Remove standalone OCR line numbers.

        These are 3-digit numbers that appear on their own line,
        typically at corners of scanned pages (e.g., 307, 012, 110).
        """
        return self.LINE_NUMBER_PATTERN.sub('\n', text)
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest test/unit_test/rag/app/criminal/test_text_cleaner.py -v
```
Expected: All PASS

**Step 5: Commit**

```bash
git add rag/app/criminal/text_cleaner.py test/unit_test/rag/app/criminal/test_text_cleaner.py
git commit -m "feat(criminal): add OCR line number removal to TextCleaner

- Remove standalone 3-digit numbers (OCR artifacts)
- Preserve numbers that are part of content
- Add comprehensive tests

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 3: Add LaTeX Format Conversion

**Files:**
- Modify: `rag/app/criminal/text_cleaner.py`
- Modify: `test/unit_test/rag/app/criminal/test_text_cleaner.py`

**Step 1: Write the failing tests**

```python
# Add to test/unit_test/rag/app/criminal/test_text_cleaner.py

class TestTextCleanerLatex:
    """Test LaTeX format conversion."""

    def setup_method(self):
        self.cleaner = TextCleaner()

    def test_convert_underline_text(self):
        """Convert $ \\underline{\\text{内容}} $ to plain text."""
        text = "$ \\underline{\\text{这是下划线内容}} $"
        result = self.cleaner.clean(text)
        assert result == "这是下划线内容"

    def test_convert_underline_in_sentence(self):
        """Convert LaTeX underline within sentence."""
        text = "开始 $ \\underline{\\text{中间内容}} $ 结束"
        result = self.cleaner.clean(text)
        assert "中间内容" in result
        assert "\\underline" not in result

    def test_convert_paren_underline(self):
        """Convert \\(\\underline{\\text{...}}\\) format."""
        text = "\\(\\underline{\\text{这是内容}}\\)"
        result = self.cleaner.clean(text)
        assert "这是内容" in result

    def test_convert_multiple_latex(self):
        """Convert multiple LaTeX expressions."""
        text = "第一 $ \\underline{\\text{A}} $ 第二 $ \\underline{\\text{B}} $"
        result = self.cleaner.clean(text)
        assert "A" in result
        assert "B" in result
        assert "\\underline" not in result
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest test/unit_test/rag/app/criminal/test_text_cleaner.py::TestTextCleanerLatex -v
```
Expected: FAIL

**Step 3: Implement LaTeX conversion**

```python
# Modify rag/app/criminal/text_cleaner.py

class TextCleaner:
    # ... existing code ...

    # LaTeX underline patterns
    # Pattern 1: $ \underline{\text{content}} $
    LATEX_UNDERLINE_DOLLAR = re.compile(
        r'\$\s*\\underline\s*\{\\text\s*\{([^}]+)\}\}\s*\$'
    )
    # Pattern 2: \( \underline{\text{content}} \)
    LATEX_UNDERLINE_PAREN = re.compile(
        r'\\\(\s*\\underline\s*\{\\text\s*\{([^}]+)\}\}\s*\\\)'
    )

    def clean(self, text: str) -> str:
        """Apply all cleaning rules to text."""
        if not text:
            return text

        text = self._remove_page_numbers(text)
        text = self._remove_line_numbers(text)
        text = self._convert_latex(text)
        text = self._normalize_whitespace(text)

        return text.strip()

    def _convert_latex(self, text: str) -> str:
        """
        Convert LaTeX formatting to plain text.

        Handles:
        - $ \\underline{\\text{content}} $ -> content
        - \\(\\underline{\\text{content}}\\) -> content
        """
        text = self.LATEX_UNDERLINE_DOLLAR.sub(r'\1', text)
        text = self.LATEX_UNDERLINE_PAREN.sub(r'\1', text)
        return text
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest test/unit_test/rag/app/criminal/test_text_cleaner.py -v
```
Expected: All PASS

**Step 5: Commit**

```bash
git add rag/app/criminal/text_cleaner.py test/unit_test/rag/app/criminal/test_text_cleaner.py
git commit -m "feat(criminal): add LaTeX format conversion to TextCleaner

- Convert $ \\underline{\\text{...}} $ to plain text
- Convert \\(\\underline{\\text{...}}\\) to plain text
- Add comprehensive tests

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 4: Add Underline Filler Removal (Plugin Layer)

**Files:**
- Modify: `rag/app/criminal/plugins/interrogation_plugin.py`
- Modify: `test/unit_test/rag/app/criminal/plugins/test_interrogation_plugin.py`

**Step 1: Write the failing tests**

```python
# Add to test/unit_test/rag/app/criminal/plugins/test_interrogation_plugin.py

class TestInterrogationPluginUnderlineCleaning:
    """Test underline filler removal in InterrogationPlugin."""

    def test_remove_underline_fillers(self):
        """Remove ___ filler patterns."""
        from rag.app.criminal.plugins.interrogation_plugin import InterrogationPlugin

        plugin = InterrogationPlugin()

        # Test internal cleaning method
        text = "地点___ 清远市公安局"
        result = plugin._clean_text(text)
        assert "___" not in result
        assert "清远市公安局" in result

    def test_remove_multiple_underline_groups(self):
        """Remove multiple groups of underlines."""
        from rag.app.criminal.plugins.interrogation_plugin import InterrogationPlugin

        plugin = InterrogationPlugin()

        text = "讯问人（签名）___、___、___"
        result = plugin._clean_text(text)
        # Should have no underlines
        assert "___" not in result

    def test_preserve_single_underscore(self):
        """Preserve single underscore in identifiers."""
        from rag.app.criminal.plugins.interrogation_plugin import InterrogationPlugin

        plugin = InterrogationPlugin()

        text = "微信ID: wxid_wb67ftqi5p9722"
        result = plugin._clean_text(text)
        assert "wxid_wb67ftqi5p9722" in result

    def test_clean_standalone_underlines(self):
        """Remove standalone underline lines."""
        from rag.app.criminal.plugins.interrogation_plugin import InterrogationPlugin

        plugin = InterrogationPlugin()

        text = "正文内容\n___\n\n___\n更多内容"
        result = plugin._clean_text(text)
        assert result.count("___") == 0
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest test/unit_test/rag/app/criminal/plugins/test_interrogation_plugin.py::TestInterrogationPluginUnderlineCleaning -v
```
Expected: FAIL with AttributeError

**Step 3: Implement underline removal in plugin**

```python
# Modify rag/app/criminal/plugins/interrogation_plugin.py

import re
from typing import List

from .base import Chunk, DocumentPlugin, plugin_registry
from rag.app.naive import UniversalBlock, BlockType
from rag.app.criminal.text_cleaner import TextCleaner


logger = logging.getLogger(__name__)


@plugin_registry.register("interrogation_record")
class InterrogationPlugin(DocumentPlugin):
    """Plugin for handling interrogation record documents."""

    # Underline filler pattern: 2 or more consecutive underscores
    UNDERLINE_FILLER_PATTERN = re.compile(r'_{2,}')

    def __init__(self):
        self._base_cleaner = TextCleaner()

    @property
    def doc_type(self) -> str:
        return "interrogation_record"

    @property
    def priority(self) -> int:
        return 10

    def _clean_text(self, text: str) -> str:
        """
        Clean text with plugin-specific rules.

        Applies:
        1. Base TextCleaner (Layer A rules)
        2. Plugin-specific rules (underline fillers, etc.)

        Args:
            text: Raw text to clean

        Returns:
            Cleaned text
        """
        # Apply base cleaning
        text = self._base_cleaner.clean(text)

        # Remove underline fillers (___)
        text = self.UNDERLINE_FILLER_PATTERN.sub('', text)

        # Clean up resulting whitespace
        text = re.sub(r'[^\S\n]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)

        return text.strip()

    # ... rest of the class remains the same ...
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest test/unit_test/rag/app/criminal/plugins/test_interrogation_plugin.py::TestInterrogationPluginUnderlineCleaning -v
```
Expected: All PASS

**Step 5: Commit**

```bash
git add rag/app/criminal/plugins/interrogation_plugin.py test/unit_test/rag/app/criminal/plugins/test_interrogation_plugin.py
git commit -m "feat(criminal): add underline filler removal to InterrogationPlugin

- Add _clean_text method with plugin-specific cleaning
- Remove ___ filler patterns while preserving single underscores
- Integrate with base TextCleaner

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 5: Add Duplicate Text Detection (Plugin Layer)

**Files:**
- Modify: `rag/app/criminal/plugins/interrogation_plugin.py`
- Modify: `test/unit_test/rag/app/criminal/plugins/test_interrogation_plugin.py`

**Step 1: Write the failing tests**

```python
# Add to test/unit_test/rag/app/criminal/plugins/test_interrogation_plugin.py

class TestInterrogationPluginDuplicateRemoval:
    """Test duplicate text removal in InterrogationPlugin."""

    def test_remove_consecutive_duplicate_sentence(self):
        """Remove consecutive duplicate sentences."""
        from rag.app.criminal.plugins.interrogation_plugin import InterrogationPlugin

        plugin = InterrogationPlugin()

        text = "这是第一句。这是第二句。这是第二句。这是第三句。"
        result = plugin._clean_text(text)
        # Should have only one "这是第二句"
        assert result.count("这是第二句") == 1

    def test_remove_duplicate_paragraph(self):
        """Remove duplicate paragraphs (OCR re-scan issue)."""
        from rag.app.criminal.plugins.interrogation_plugin import InterrogationPlugin

        plugin = InterrogationPlugin()

        text = "这是段落内容。这是段落内容。继续的内容。"
        result = plugin._clean_text(text)
        assert result.count("这是段落内容") == 1

    def test_preserve_intentional_repetition(self):
        """Preserve intentional repetition like '是是是'."""
        from rag.app.criminal.plugins.interrogation_plugin import InterrogationPlugin

        plugin = InterrogationPlugin()

        text = "问：你是否同意？答：是是是。"
        result = plugin._clean_text(text)
        assert "是是是" in result

    def test_preserve_short_duplicates(self):
        """Preserve short duplicates that might be meaningful."""
        from rag.app.criminal.plugins.interrogation_plugin import InterrogationPlugin

        plugin = InterrogationPlugin()

        text = "没有没有没有，我没有。"
        result = plugin._clean_text(text)
        # Short phrases like "没有" repeated should be preserved
        assert "没有" in result
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest test/unit_test/rag/app/criminal/plugins/test_interrogation_plugin.py::TestInterrogationPluginDuplicateRemoval -v
```
Expected: FAIL

**Step 3: Implement duplicate removal**

```python
# Modify rag/app/criminal/plugins/interrogation_plugin.py

class InterrogationPlugin(DocumentPlugin):
    # ... existing code ...

    # Minimum length for duplicate detection (chars)
    # Shorter phrases might be intentional repetition
    MIN_DUPLICATE_LENGTH = 15

    def _clean_text(self, text: str) -> str:
        """
        Clean text with plugin-specific rules.
        """
        # Apply base cleaning
        text = self._base_cleaner.clean(text)

        # Remove underline fillers
        text = self.UNDERLINE_FILLER_PATTERN.sub('', text)

        # Remove duplicate text (OCR re-scan issue)
        text = self._remove_duplicates(text)

        # Clean up whitespace
        text = re.sub(r'[^\S\n]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)

        return text.strip()

    def _remove_duplicates(self, text: str) -> str:
        """
        Remove consecutive duplicate text segments.

        This handles OCR issues where the same text is recognized multiple times.
        Only removes duplicates longer than MIN_DUPLICATE_LENGTH to preserve
        intentional repetition.

        Args:
            text: Text to process

        Returns:
            Text with consecutive duplicates removed
        """
        if len(text) < self.MIN_DUPLICATE_LENGTH * 2:
            return text

        # Split into sentences/segments
        segments = re.split(r'([。！？\n])', text)

        result = []
        prev_segment = ""

        for segment in segments:
            # Skip if same as previous (and long enough to be OCR error)
            if (len(segment) >= self.MIN_DUPLICATE_LENGTH and
                segment == prev_segment):
                continue

            result.append(segment)
            prev_segment = segment

        return ''.join(result)
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest test/unit_test/rag/app/criminal/plugins/test_interrogation_plugin.py::TestInterrogationPluginDuplicateRemoval -v
```
Expected: All PASS

**Step 5: Commit**

```bash
git add rag/app/criminal/plugins/interrogation_plugin.py test/unit_test/rag/app/criminal/plugins/test_interrogation_plugin.py
git commit -m "feat(criminal): add duplicate text removal to InterrogationPlugin

- Remove consecutive duplicate segments (OCR re-scan issue)
- Preserve intentional short repetitions
- Only remove duplicates longer than 15 chars

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 6: Integrate Text Cleaning into Transform Pipeline

**Files:**
- Modify: `rag/app/criminal/plugins/interrogation_plugin.py`

**Step 1: Update transform method to use cleaning**

```python
# Modify rag/app/criminal/plugins/interrogation_plugin.py

    def transform(self, blocks: List[UniversalBlock]) -> List[Chunk]:
        """
        Transform blocks into header_info and qa_pair chunks.

        Output structure:
        1. header_info (1 chunk): All content before the first Q/A pair
        2. qa_pair (N chunks): Each Q/A pair as a separate chunk
        """
        if not blocks:
            return []

        chunks = []

        # Phase 1: Collect header_info blocks (before first "问：")
        header_blocks: List[UniversalBlock] = []
        first_qa_found = False

        for block in blocks:
            # Clean the text before processing
            text = self._clean_text(block.text).strip()

            # Skip empty blocks after cleaning
            if not text:
                continue

            # Check if this starts a Q/A section
            if text.startswith(("问：", "问:")):
                first_qa_found = True
                break

            # Collect header info blocks (store cleaned text)
            header_blocks.append(block)

        # ... rest of the method, applying _clean_text to all text ...

    def _create_chunk(
        self,
        blocks: List[UniversalBlock],
        chunk_type: str,
        text_override: str = None
    ) -> Chunk | None:
        """Create a chunk from blocks with text cleaning."""
        if not blocks:
            return None

        # Build text from blocks if not provided
        if text_override:
            text = self._clean_text(text_override)
        else:
            text_parts = []
            for b in blocks:
                t = self._clean_text(b.text).strip()
                if t:
                    text_parts.append(t)
            text = "\n".join(text_parts)

        if not text:
            return None

        # ... rest of the method remains the same ...
```

**Step 2: Run all plugin tests**

```bash
uv run pytest test/unit_test/rag/app/criminal/plugins/test_interrogation_plugin.py -v
```
Expected: All PASS

**Step 3: Commit**

```bash
git add rag/app/criminal/plugins/interrogation_plugin.py
git commit -m "feat(criminal): integrate text cleaning into InterrogationPlugin transform

- Apply _clean_text to all text in transform pipeline
- Clean header_info and qa_pair chunks
- Skip empty blocks after cleaning

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 7: Integration Test with Real PDF

**Files:**
- Manual test with test_plugin_dev.py

**Step 1: Run test tool to verify cleaning**

```bash
uv run python test/test_plugin_dev.py --sample interrogation --doc-type interrogation_record --json
```

**Step 2: Verify output**

Check that the output:
- [ ] No "第 X 页 共 Y 页" patterns
- [ ] No standalone 3-digit numbers (307, 012, etc.)
- [ ] No LaTeX formatting (`\underline`, `\text`)
- [ ] No underline fillers (___)
- [ ] Reduced duplicate text
- [ ] Clean whitespace

**Step 3: Compare before/after**

Save output and compare with original to verify improvements.

---

## Task 8: Update Documentation

**Files:**
- Modify: `docs/criminal-parser-architecture.md`

**Step 1: Add TextCleaner section to architecture doc**

Add to `docs/criminal-parser-architecture.md`:

```markdown
## Text Cleaning

### Two-Layer Cleaning Architecture

| Layer | Location | Purpose | Rules |
|-------|----------|---------|-------|
| Layer A | `text_cleaner.py` | Universal rules | Page numbers, OCR line numbers, LaTeX, whitespace |
| Layer B | Plugin `_clean_text()` | Document-specific | Underline fillers, duplicate detection |

### TextCleaner (Layer A)

Located at `rag/app/criminal/text_cleaner.py`.

**Cleaning rules:**
1. Page numbers: `第 X 页 共 Y 页` → removed
2. OCR line numbers: standalone 3-digit numbers → removed
3. LaTeX formatting: `$ \underline{\text{...}} $` → plain text
4. Whitespace: normalized to single spaces

### Plugin-Specific Cleaning (Layer B)

Each plugin can override `_clean_text()` for document-specific rules.

**InterrogationPlugin rules:**
1. Underline fillers: `___` → removed
2. Duplicate text: consecutive duplicates >15 chars → removed
```

**Step 2: Commit**

```bash
git add docs/criminal-parser-architecture.md
git commit -m "docs(criminal): add text cleaning documentation

- Document two-layer cleaning architecture
- List Layer A and Layer B cleaning rules
- Explain TextCleaner usage

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Summary

| Task | Description | Files Changed |
|------|-------------|---------------|
| 1 | Create TextCleaner base module | `text_cleaner.py`, `test_text_cleaner.py` |
| 2 | Add OCR line number removal | same |
| 3 | Add LaTeX format conversion | same |
| 4 | Add underline filler removal | `interrogation_plugin.py` |
| 5 | Add duplicate text detection | same |
| 6 | Integrate into transform pipeline | same |
| 7 | Integration test | manual |
| 8 | Update documentation | `criminal-parser-architecture.md` |

## Test Commands

```bash
# Run all text cleaner tests
uv run pytest test/unit_test/rag/app/criminal/test_text_cleaner.py -v

# Run all interrogation plugin tests
uv run pytest test/unit_test/rag/app/criminal/plugins/test_interrogation_plugin.py -v

# Run integration test
uv run python test/test_plugin_dev.py --sample interrogation --doc-type interrogation_record --json
```
