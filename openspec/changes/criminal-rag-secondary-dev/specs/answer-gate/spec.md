# Answer Gate Specification

## ADDED Requirements

### Requirement: Gate shall validate citation existence

The system SHALL verify that all chunk_ids referenced in the answer exist in the provided raw_chunks.

#### Scenario: Validate valid chunk references
- **WHEN** answer contains evidences with valid chunk_ids
- **THEN** the system SHALL confirm each chunk_id exists in raw_chunks
- **AND** validation SHALL pass

#### Scenario: Reject invalid chunk references
- **WHEN** answer contains a chunk_id not in raw_chunks
- **THEN** the system SHALL return status="citation_insufficient"
- **AND** conclusion SHALL be set to null

### Requirement: Gate shall validate excerpt substring match

The system SHALL verify that each excerpt is an exact substring of the referenced chunk's text.

#### Scenario: Validate exact excerpt match
- **WHEN** evidence excerpt is a substring of chunk.text
- **THEN** validation SHALL pass for that evidence

#### Scenario: Reject non-matching excerpt
- **WHEN** evidence excerpt is NOT a substring of chunk.text
- **THEN** the system SHALL reject that evidence

### Requirement: Gate shall validate numeric grounding

The system SHALL verify that all numbers/dates/amounts in the conclusion appear verbatim in the evidence excerpts.

#### Scenario: Validate numeric values in conclusion
- **WHEN** conclusion contains numeric values (金额/日期/浓度等)
- **THEN** each value SHALL appear verbatim in at least one evidence excerpt

#### Scenario: Reject ungrounded numeric values
- **WHEN** conclusion contains a numeric value not in any excerpt
- **THEN** the system SHALL return status="citation_insufficient"

### Requirement: Gate shall enforce no-evidence response

The system SHALL return a structured "no_evidence" response when no valid citations exist.

#### Scenario: Return no_evidence when raw_chunks is empty
- **WHEN** raw_chunks is empty or null
- **THEN** the system SHALL return status="no_evidence"
- **AND** conclusion SHALL be null
- **AND** evidences SHALL be empty array

### Requirement: Gate shall validate coordinate provenance

The system SHALL verify that page_index and bbox in evidences come from chunk metadata.

#### Scenario: Validate coordinate provenance
- **WHEN** evidence contains page_index and bbox
- **THEN** values SHALL match the referenced chunk's position_int data
