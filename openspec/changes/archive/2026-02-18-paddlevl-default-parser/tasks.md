# Tasks: PaddleVL as Default PDF Parser

## Status

- [x] Create OpenSpec directory and files
- [x] Modify `api/utils/api_utils.py`
- [x] Modify `rag/flow/parser/parser.py`
- [x] Modify `test/testcases/configs.py`
- [x] Run verification tests

## Implementation Details

### Task 1: Modify `api/utils/api_utils.py`

**File**: `api/utils/api_utils.py`
**Line**: 370
**Change**: `"layout_recognize": "DeepDOC"` → `"layout_recognize": "PaddleOCR-VL@paddleocr"`

### Task 2: Modify `rag/flow/parser/parser.py`

**File**: `rag/flow/parser/parser.py`
**Line**: 86
**Change**: `"parse_method": "deepdoc"` → `"parse_method": "paddleocr"`

### Task 3: Modify `test/testcases/configs.py`

**File**: `test/testcases/configs.py`
**Line**: 47
**Change**: `"layout_recognize": "DeepDOC"` → `"layout_recognize": "PaddleOCR-VL@paddleocr"`

## Verification

Run the following tests to verify the changes:

```bash
# Verify PaddleOCR parser availability
uv run python -c "
from deepdoc.parser.paddleocr_parser import PaddleOCRParser
parser = PaddleOCRParser()
ok, msg = parser.check_installation()
print(f'PaddleOCR available: {ok}, {msg}')
"
```
