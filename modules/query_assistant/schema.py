"""Schema definitions for Query Assistant module"""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


class QueryTemplate(BaseModel):
    """SQL query template with metadata"""
    template_id: str = Field(..., description="템플릿 고유 식별자")
    natural_questions: str = Field(..., description="자연어 질의 패턴")
    sql_query: str = Field(..., description="SQL 쿼리")
    sql_query_with_parameters: str = Field(..., description="파라미터화된 SQL 쿼리")
    keywords: List[str] = Field(default_factory=list, description="매칭용 키워드 목록")
    category: str = Field(..., description="템플릿 분류")
    required_params: List[str] = Field(default_factory=list, description="필수 파라미터 목록")
    default_params: Dict[str, Any] = Field(default_factory=dict, description="필수 파라미터의 초기 값")
    query_filter: List[str] = Field(default_factory=list, description="선택적 파라미터 목록")
    usage_count: int = Field(default=0, description="파라미터 기본값 매핑")
    created_at: datetime = Field(default_factory=datetime.now, description="템플릿 생성 시각")
    related_tables: List[str] = Field(default_factory=list, description="관련 테이블 목록")
    last_used: Optional[datetime] = Field(default=None, description="최종 사용 시각")
    to_agent_prompt: Optional[str] = Field(default=None, description="예외 처리 시 LLM에 전달할 프롬프트")
    
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