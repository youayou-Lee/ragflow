# Retrieval API Specification (Delta)

## ADDED Requirements

### Requirement: Retrieval shall return block references

The retrieval API SHALL include block_refs in the returned chunk structure.

#### Scenario: Include block_refs in retrieval result
- **WHEN** retrieval returns chunks
- **THEN** each chunk SHALL include block_refs array
- **AND** block_refs SHALL contain {page_index, block_id} objects

### Requirement: Retrieval shall support doc_type filtering

The retrieval API SHALL support filtering by document type.

#### Scenario: Filter by doc_type
- **WHEN** retrieval request includes doc_type filter
- **THEN** results SHALL only include chunks from documents of specified type
- **AND** valid doc_types SHALL be: indictment_opinion | interrogation_record

### Requirement: Retrieval shall include raw_chunks in response

The retrieval API SHALL return raw_chunks for answer validation.

#### Scenario: Return raw_chunks for validation
- **WHEN** retrieval completes for a question
- **THEN** response SHALL include raw_chunks array
- **AND** each raw_chunk SHALL have chunk_id, page_range, bbox_union, text
