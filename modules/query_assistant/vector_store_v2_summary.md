# VectorStoreHTTPV2 - Unified Collection Adapter

## Overview
Created `VectorStoreHTTPV2` to work with the existing `query_templates_unified` collection in Qdrant, which has a different field structure than what the original `VectorStoreHTTP` expected.

## Problem
The original `VectorStoreHTTP` was designed for a different schema and couldn't work with the `query_templates_unified` collection because:
1. Field names were different (e.g., `template_category` vs `category`)
2. Data types were different (e.g., `natural_questions` as list vs string)
3. Parameter structure was nested differently
4. Some fields didn't exist in the unified collection

## Solution
`VectorStoreHTTPV2` provides field mapping between the unified collection structure and the QueryTemplate schema:

### Field Mappings
- `template_category` → `category`
- `natural_questions[0]` → `natural_questions` (list to string)
- `parameters` → parsed into `required_params`, `default_params`, and `query_filter`
- `sql_system` → `to_agent_prompt`
- `uploaded_at` → `created_at`

### Key Features
1. **Automatic Collection Detection**: Checks if collection exists and adapts to its vector size
2. **Field Mapping**: Translates between unified collection fields and QueryTemplate schema
3. **Parameter Extraction**: Parses the parameters list to extract required/optional params and defaults
4. **Backward Compatibility**: Maintains the same interface as original VectorStoreHTTP

## Usage
```python
from modules.query_assistant.services import VectorStoreHTTPV2

# Initialize with unified collection
vector_store = VectorStoreHTTPV2(
    collection_name="query_templates_unified",  # Default
    vector_size=3072,  # Will auto-detect from collection
)

# Search templates
results = vector_store.search(
    query="최근 아젠다 목록",
    keywords=["최근", "아젠다"],
    limit=5
)

# Process results
for result in results:
    print(f"Template: {result.template_id}")
    print(f"Score: {result.score}")
    print(f"SQL: {result.template.sql_query}")
```

## Test Results
Successfully tested with queries:
- "최근 아젠다 목록 보여줘" → Found recent_5_agendas_v2 (score: 0.567)
- "특정 패널의 아젠다 찾기" → Found panel-related templates
- "IMO 관련 아젠다" → Found IMO-related templates with keyword matching

## Files Created/Modified
1. `/home/kimghw/IACSGRAPH/modules/query_assistant/services/vector_store_http_v2.py` - New adapter implementation
2. `/home/kimghw/IACSGRAPH/modules/query_assistant/services/__init__.py` - Updated to export VectorStoreHTTPV2
3. `/home/kimghw/IACSGRAPH/modules/query_assistant/test_vector_store_v2.py` - Test script

## Notes
- The unified collection doesn't track usage statistics, so `update_usage_stats()` is a no-op
- `get_popular_templates()` returns recent templates instead of most-used
- Collection has 140 templates with 3072-dimensional vectors
- Uses OpenAI text-embedding-3-large model for embeddings