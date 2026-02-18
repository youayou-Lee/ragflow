# Default Parser Specification (Delta)

> **Background**: Current RAGFlow uses DeepDoc engine as the default PDF parser.
> This spec changes the default parser to PaddleVL for better legal document processing.

## ADDED Requirements

### Requirement: System shall use PaddleVL as default PDF parser

The system SHALL use PaddleVL (PaddleOCR-VL) as the default parser for PDF documents.

#### Scenario: Default parser configuration
- **WHEN** a new dataset is created without explicit parser_config
- **THEN** the system SHALL set layout_recognize to "PaddleOCR-VL@paddleocr"
- **AND** PDF documents SHALL be parsed using PaddleVL engine

#### Scenario: Backward compatibility
- **WHEN** user explicitly sets layout_recognize to "DeepDOC"
- **THEN** the system SHALL respect user configuration
- **AND** use DeepDoc engine for that dataset

## MODIFIED Requirements

### Requirement: Parser configuration defaults

The default parser configuration for the "naive" chunk method SHALL use PaddleVL.

| Field | Old Value | New Value |
|-------|-----------|-----------|
| `layout_recognize` | `"DeepDOC"` | `"PaddleOCR-VL@paddleocr"` |
| `parse_method` (PDF) | `"deepdoc"` | `"paddleocr"` |
