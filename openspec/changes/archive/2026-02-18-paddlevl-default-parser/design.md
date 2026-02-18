# Design: PaddleVL as Default PDF Parser

## Overview

This design document describes the changes needed to make PaddleVL the default PDF parser in RAGFlow.

## Files Modified

| File | Change |
|------|--------|
| `api/utils/api_utils.py` | Change `layout_recognize` default from `"DeepDOC"` to `"PaddleOCR-VL@paddleocr"` |
| `rag/flow/parser/parser.py` | Change `parse_method` default from `"deepdoc"` to `"paddleocr"` |
| `test/testcases/configs.py` | Update `DEFAULT_PARSER_CONFIG` to use PaddleVL |

## API Changes

### `get_parser_config()` in `api/utils/api_utils.py`

The `key_mapping["naive"]["layout_recognize"]` default value changes:

```python
# Before
"layout_recognize": "DeepDOC"

# After
"layout_recognize": "PaddleOCR-VL@paddleocr"
```

### `ParserParam` in `rag/flow/parser/parser.py`

The `setups["pdf"]["parse_method"]` default value changes:

```python
# Before
"parse_method": "deepdoc"

# After
"parse_method": "paddleocr"
```

## Backward Compatibility

- Users can still explicitly set `layout_recognize` to `"DeepDOC"` or other options
- Existing datasets retain their current parser configuration
- No database migration required

## Environment Requirements

Ensure the following environment variables are configured:
- `PADDLEOCR_API_URL`: PaddleOCR service URL
- `PADDLEOCR_ACCESS_TOKEN`: PaddleOCR authentication token
