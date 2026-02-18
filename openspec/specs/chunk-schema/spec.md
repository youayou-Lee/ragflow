# Chunk Schema Specification (Delta)

> **背景**：RAGFlow 已有 chunk_type 字段（由 `rag/app/interrogation.py` 实现），本 spec 定义新增字段。

## ADDED Requirements

### Requirement: Chunk shall reference source blocks

Each chunk SHALL include block_refs to trace back to original parsed blocks.

#### Scenario: Store block references
- **WHEN** a chunk is created from parsed blocks
- **THEN** block_refs SHALL contain array of {page_index, block_id} objects
- **AND** block_refs SHALL enable precise highlighting

### Requirement: Chunk shall have unified bounding box

Each chunk SHALL include bbox_union representing the spatial extent of all constituent content.

#### Scenario: Calculate bbox_union
- **WHEN** a chunk spans multiple blocks
- **THEN** bbox_union SHALL be [x1, y1, x2, y2] encompassing all blocks
- **AND** coordinates SHALL be in PDF coordinate system

### Requirement: Chunk shall support page range

Each chunk SHALL include page_range indicating span across pages.

#### Scenario: Store page range
- **WHEN** a chunk spans pages 2-3
- **THEN** page_range SHALL be [2, 3]
- **AND** single-page chunks SHALL have page_range [n, n]
