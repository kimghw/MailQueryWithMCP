"""Schema definitions for Query Assistant module"""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


class QueryTemplate(BaseModel):
    """SQL query template with metadata"""
    id: str = Field(..., description="Unique identifier for the template")
    natural_query: str = Field(..., description="Natural language query pattern")
    sql_template: str = Field(..., description="SQL template with placeholders")
    keywords: List[str] = Field(default_factory=list, description="Keywords for matching")
    required_params: List[str] = Field(default_factory=list, description="Required parameters")
    optional_params: List[str] = Field(default_factory=list, description="Optional parameters with defaults")
    default_params: Dict[str, Any] = Field(default_factory=dict, description="Default values for parameters")
    category: str = Field(..., description="Query category (agenda, response, statistics, etc.)")
    usage_count: int = Field(default=0, description="Number of times this template has been used")
    created_at: datetime = Field(default_factory=datetime.now)
    last_used: Optional[datetime] = Field(default=None)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class QueryExpansion(BaseModel):
    """Query expansion and analysis results"""
    original_keywords: List[str] = Field(..., description="Keywords extracted from user query")
    expanded_keywords: List[str] = Field(..., description="Expanded keywords including synonyms")
    missing_params: List[str] = Field(default_factory=list, description="Missing required parameters")
    suggestions: List[str] = Field(default_factory=list, description="Suggested clarifications")
    confidence_score: float = Field(default=0.0, description="Confidence in query understanding")


class QueryResult(BaseModel):
    """Query execution result"""
    query_id: str = Field(..., description="ID of the template used")
    executed_sql: str = Field(..., description="Actual SQL executed")
    parameters: Dict[str, Any] = Field(..., description="Parameters used in query")
    results: List[Dict[str, Any]] = Field(default_factory=list, description="Query results")
    execution_time: float = Field(..., description="Query execution time in seconds")
    error: Optional[str] = Field(default=None, description="Error message if any")
    validation_info: Optional[Dict[str, Any]] = Field(default=None, description="Parameter validation info")


class VectorSearchResult(BaseModel):
    """Vector search result with relevance score"""
    template_id: str
    score: float
    template: QueryTemplate
    keyword_matches: List[str] = Field(default_factory=list)


# Qdrant collection configuration
QDRANT_COLLECTION_CONFIG = {
    "name": "iacsgraph_queries_openai",
    "vector_size": 3072,  # OpenAI text-embedding-3-large default dimension
    "distance": "Cosine",
    "payload_schema": {
        "natural_query": "text",
        "sql_template": "text", 
        "keywords": "keyword[]",
        "category": "keyword",
        "required_params": "keyword[]",
        "optional_params": "keyword[]",
        "usage_count": "integer"
    }
}


# Default parameters for optional fields
DEFAULT_PARAMS = {
    "limit": 20,
    "days": 30,
    "status": "all",
    "min_responses": 0,
    # Common required params defaults
    "period": "30일",
    "organization": "KR",
    "keyword": "",
    "priority": "high",
    "period_format": "%Y-%m"
}