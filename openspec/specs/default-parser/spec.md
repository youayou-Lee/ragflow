# Default Parser Specification

## Overview

This specification defines the default PDF parser configuration for RAGFlow.

## Requirements

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

### Requirement: Parser configuration defaults

The default parser configuration for the "naive" chunk method SHALL use PaddleVL.

| Field | Default Value |
|-------|---------------|
| `layout_recognize` | `"PaddleOCR-VL@paddleocr"` |
| `parse_method` (PDF) | `"paddleocr"` |

## Environment Requirements

The PaddleVL parser requires the following environment variables:
- `PADDLEOCR_API_URL`: PaddleOCR service URL
- `PADDLEOCR_ACCESS_TOKEN`: PaddleOCR authentication token
- `PADDLEOCR_ALGORITHM`: Algorithm type (default: `PaddleOCR-VL`)
