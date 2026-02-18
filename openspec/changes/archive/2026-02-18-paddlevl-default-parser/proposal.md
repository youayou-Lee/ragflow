# Proposal: PaddleVL as Default PDF Parser

## Summary

Change the default PDF parser from DeepDoc to PaddleVL (PaddleOCR-VL) for better legal document processing.

## Motivation

1. **统一解析方案**: 法律文书的扫描件需要 PaddleVL 的高精度版面分析
2. **简化配置**: 避免每次创建数据集时都需要手动配置 `parser_config`
3. **一致性**: 确保 PDF 文档使用相同的解析器，便于调试和维护

## Current State

- Default `layout_recognize = "DeepDOC"` in `api/utils/api_utils.py`
- Default `parse_method = "deepdoc"` in `rag/flow/parser/parser.py`

## Proposed Changes

1. Change `layout_recognize` default to `"PaddleOCR-VL@paddleocr"`
2. Change `parse_method` default to `"paddleocr"`
3. Update test configurations accordingly

## Impact

- All new datasets will use PaddleVL by default
- Existing datasets are not affected
- Users can still explicitly select DeepDoc if needed
