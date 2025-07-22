"""Template storage schema for VectorDB"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class QueryTemplate(BaseModel):
    """Query template model for VectorDB storage"""
    
    template_id: str = Field(..., description="Unique template identifier")
    natural_questions: str = Field(..., description="Natural language question pattern")
    sql_query: str = Field(..., description="SQL query without parameters")
    sql_query_with_parameters: Optional[str] = Field(None, description="SQL query with parameters")
    keywords: List[str] = Field(default_factory=list, description="Keywords for search")
    category: str = Field(..., description="Template category")
    required_params: List[str] = Field(default_factory=list, description="Required parameters")
    optional_params: List[str] = Field(default_factory=list, description="Optional parameters")
    examples: List[Dict[str, Any]] = Field(default_factory=list, description="Usage examples")
    embedding_text: Optional[str] = Field(None, description="Text used for embedding generation")
    version: str = Field(default="1.0", description="Template version")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    active: bool = Field(default=True, description="Whether template is active")
    
    def generate_embedding_text(self) -> str:
        """Generate text for embedding from template fields"""
        texts = [
            self.natural_questions,
            f"카테고리: {self.category}",
            f"키워드: {', '.join(self.keywords)}"
        ]
        if self.examples:
            for example in self.examples[:3]:  # Limit to first 3 examples
                if 'question' in example:
                    texts.append(f"예시: {example['question']}")
        
        return " ".join(texts)


class TemplateCollection:
    """Template collection configuration for VectorDB"""
    
    name: str = "query_templates"
    
    # Vector fields
    vector_fields = {
        "embedding": {
            "dimension": 768,  # Adjust based on your embedding model
            "metric": "cosine"
        }
    }
    
    # Payload fields (searchable metadata)
    payload_fields = {
        "template_id": "keyword",
        "category": "keyword", 
        "keywords": "text[]",
        "required_params": "text[]",
        "active": "bool",
        "version": "keyword"
    }
    
    # Index configuration
    index_config = {
        "hnsw": {
            "m": 16,
            "ef_construct": 200,
            "full_scan_threshold": 10000
        }
    }