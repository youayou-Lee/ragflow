# Auto-Detect Document Parser Implementation

## Overview

This document summarizes the implementation of automatic document parser detection for the Criminal RAG system. The feature automatically detects document types and selects appropriate parsers, eliminating the need for users to manually choose parsing methods when creating knowledge bases or uploading documents.

## Implementation Date

2026-02-18

## Modified Files

| File | Type | Description |
|------|------|-------------|
| `web/src/pages/datasets/dataset-dataflow-creating-dialog.tsx` | Modified | Simplified dialog by removing ParseTypeItem, keeping only name and embd_id |
| `test/testcases/test_rag/__init__.py` | New | Test package initialization |
| `test/testcases/test_rag/test_classifier.py` | New | Classifier unit tests (27 test cases) |
| `test/testcases/test_auto_detect/__init__.py` | New | Test package initialization |
| `test/testcases/test_auto_detect/test_auto_classify.py` | New | Integration tests (6 test cases) |
| `test/testcases/README.md` | New | Test documentation |
| `.env.test` | New | Test environment configuration (not committed) |
| `.env.test.example` | New | Template for test environment configuration |

## Implementation Details

### Frontend Simplification

Removed the following components from `dataset-dataflow-creating-dialog.tsx`:
- `ParseTypeItem` - Parser type selection
- `DataFlowItem` - Data flow configuration
- `DataExtractKnowledgeItem` - Knowledge extraction settings
- `TeamItem` - Team selection

The dialog now only requires:
- `name` - Knowledge base name
- `embd_id` - Embedding model ID

### Classification Logic

The `DocumentClassifier` class in `rag/app/classifier.py` implements a three-tier classification strategy:

1. **Rule-based Classification** (`_rule_classify`)
   - Uses regex patterns to match document keywords
   - High confidence (1.0) when matched
   - Supports: interrogation records, indictments, judgments, legal regulations

2. **LLM-based Classification** (`_classify_by_llm`)
   - Falls back to LLM when rules don't match
   - Requires sufficient text length (>50 chars) and tenant_id
   - Medium confidence when successful

3. **Fallback Classification** (`_fallback_classify`)
   - Returns `naive` parser when all else fails
   - Zero confidence

### Test Structure

```
test/testcases/
├── test_rag/
│   ├── __init__.py
│   └── test_classifier.py       # 27 unit tests
├── test_auto_detect/
│   ├── __init__.py
│   └── test_auto_classify.py    # 6 integration tests
└── README.md                    # Test documentation
```

## Test Results

| Test Module | Tests | Status |
|-------------|-------|--------|
| `test_rag/test_classifier.py` | 27 | All passed |
| `test_auto_detect/test_auto_classify.py` | 6 | All passed |
| **Total** | **33** | **All passed** |

### Test Categories

**Unit Tests (test_classifier.py):**
- `TestExtractTextSample` - Text extraction from various file formats
- `TestRuleBasedClassification` - Pattern matching classification
- `TestFallbackClassification` - Fallback to naive parser
- `TestLLMClassification` - LLM-based classification edge cases
- `TestDocumentClassifier` - Main classify method behavior
- `TestDocumentPatterns` - Pattern configuration validation

**Integration Tests (test_auto_classify.py):**
- `TestAutoClassifyIntegration` - End-to-end document upload and classification
- `TestClassificationWithoutAPIKey` - Direct classifier tests without server
- `TestKnowledgeBaseCreation` - KB creation without parser_id

## Configuration

### Environment Variables

Create `.env.test` file in project root (copy from `.env.test.example`):

```bash
# Test API Keys for LLM Fallback Testing
DEEPSEEK_API_KEY=your-deepseek-key-here
ZHIPU_AI_API_KEY=your-zhipuai-key-here

# RAGFlow Integration Test Configuration
RAGFLOW_HOST=http://localhost:9380
RAGFLOW_API_KEY=your-ragflow-api-key-here
```

### Getting RAGFlow API Key

```bash
# Via Docker MySQL
docker exec docker-mysql-1 mysql -uroot -pinfini_rag_flow rag_flow \
  -e "SELECT token FROM api_token LIMIT 1;"
```

## Running Tests

```bash
# Load environment variables
source .env.test

# Run all auto-detect tests
uv run pytest test/testcases/test_rag/test_classifier.py \
              test/testcases/test_auto_detect/test_auto_classify.py -v

# Run only unit tests (no server required)
uv run pytest test/testcases/test_rag/test_classifier.py -v

# Run only integration tests (requires running RAGFlow server)
uv run pytest test/testcases/test_auto_detect/test_auto_classify.py -v

# Run tests without API requirements
uv run pytest test/testcases/test_auto_detect/test_auto_classify.py::TestClassificationWithoutAPIKey -v
```

## Related Documents

- [Test Documentation](../../test/testcases/README.md)
- [Criminal Benchmark Test](./2025-02-18-criminal-benchmark-test.md)
- [Benchmark Optimization Summary](./2026-02-18-benchmark-optimization-summary.md)
