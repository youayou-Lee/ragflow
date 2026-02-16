# Indictment Chunker Specification

> **背景**：RAGFlow 已有讯问笔录 Parser (`rag/app/interrogation.py`)，本 spec 定义起诉意见书的结构化切分。

## ADDED Requirements

### Requirement: Chunker shall identify section triggers

The system SHALL recognize legal document section trigger phrases and split content accordingly.

#### Scenario: Split by standard triggers
- **WHEN** text contains trigger phrases like "经依法侦查查明", "认定上述犯罪事实的证据如下", "综上所述", "本院认为"
- **THEN** the system SHALL create section chunks at each trigger
- **AND** chunk_type SHALL be "section"

#### Scenario: Create section with nested paragraphs
- **WHEN** a section exceeds 800 characters
- **THEN** the system SHALL split into paragraph chunks within the section
- **AND** paragraph chunks SHALL have chunk_type="paragraph"

### Requirement: Chunk shall identify evidence items

The system SHALL optionally create evidence_item chunks for numbered evidence lists.

#### Scenario: Extract numbered evidence items
- **WHEN** text contains patterns like "1. [evidence]" or "（一）[evidence]"
- **THEN** the system SHALL create evidence_item chunks with chunk_type="evidence_item"

### Requirement: Chunk shall include position metadata

Each section/paragraph chunk SHALL include precise position information.

#### Scenario: Calculate position for section chunk
- **WHEN** a section chunk is created
- **THEN** bbox_union SHALL encompass all blocks in the section
- **AND** page_range SHALL indicate [start_page, end_page]
- **AND** block_refs SHALL list all constituent block references

### Requirement: Chunker shall follow existing pattern

The indictment chunker SHALL follow the same pattern as the existing interrogation parser.

#### Scenario: Output format matches interrogation parser
- **WHEN** chunks are generated
- **THEN** output format SHALL match `rag/app/interrogation.py` structure
- **AND** chunk_type field SHALL use values: section | paragraph | evidence_item
- **AND** position_int field SHALL follow existing format [page, left, right, top, bottom]
- **NOTE** page value is 1-indexed (actual_page + 1), see `rag/nlp/__init__.py:841`
