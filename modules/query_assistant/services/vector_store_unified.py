"""Vector store for unified query_templates collection"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
import os
import json
import requests
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, 
    Filter, FieldCondition, MatchValue
)
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from ..schema import QueryTemplate, QDRANT_COLLECTION_CONFIG

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)


class UnifiedVectorSearchResult(BaseModel):
    """Vector search result for unified collection"""
    template_id: str
    score: float
    template: QueryTemplate
    keyword_matches: List[str] = Field(default_factory=list)
    matched_question: Optional[str] = None


class VectorStoreUnified:
    """Qdrant-based vector store for unified templates collection"""
    
    def __init__(
        self, 
        qdrant_url: str = "localhost",
        qdrant_port: int = 6333,
        api_key: Optional[str] = None,
        api_base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        collection_name: str = "query_templates",  # New unified collection
        vector_size: int = 3072
    ):
        """Initialize vector store with unified collection"""
        
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("API key not provided and OPENAI_API_KEY not found in environment")
            
        self.api_base_url = api_base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.model_name = model_name or os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-large")
        self.collection_name = collection_name
        self.vector_size = vector_size
        
        # Initialize Qdrant client
        self.client = QdrantClient(host=qdrant_url, port=qdrant_port, check_compatibility=False)
        
        # HTTP session for API calls
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        })
        
        logger.info(f"Using embedding API: {self.api_base_url}")
        logger.info(f"Model: {self.model_name} ({self.vector_size} dimensions)")
        logger.info(f"Collection: {self.collection_name}")
    
    def _get_embedding(self, text: str) -> List[float]:
        """Get embedding from API"""
        try:
            url = f"{self.api_base_url}/embeddings"
            
            payload = {
                "input": text,
                "model": self.model_name
            }
            
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            
            data = response.json()
            embedding = data['data'][0]['embedding']
            
            return embedding
            
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP error getting embedding: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error getting embedding: {e}")
            raise
    
    def search(
        self, 
        query: str, 
        keywords: List[str],
        limit: int = 5,
        category: Optional[str] = None,
        score_threshold: float = 0.5
    ) -> List[UnifiedVectorSearchResult]:
        """Search for matching query templates"""
        try:
            # Generate query embedding
            query_text = f"{query} {' '.join(keywords)}"
            query_embedding = self._get_embedding(query_text)
            
            # Build filter
            filter_conditions = []
            if category:
                filter_conditions.append(
                    FieldCondition(
                        key="template_category",
                        match=MatchValue(value=category)
                    )
                )
            
            # Perform vector search
            search_results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=limit * 2,  # Get more results for keyword filtering
                with_payload=True,
                query_filter=Filter(must=filter_conditions) if filter_conditions else None
            )
            
            # Process results with keyword matching
            results = []
            for result in search_results:
                # Calculate keyword match score
                template_keywords = set(result.payload.get("keywords", []))
                query_keywords = set(keywords)
                keyword_matches = list(template_keywords.intersection(query_keywords))
                keyword_score = len(keyword_matches) / max(len(query_keywords), 1)
                
                # Combine vector and keyword scores
                combined_score = (result.score * 0.7) + (keyword_score * 0.3)
                
                if combined_score >= score_threshold:
                    # Extract parameters from payload
                    parameters_list = result.payload.get("parameters", [])
                    required_params = []
                    default_params = {}
                    query_filter = []
                    
                    for param in parameters_list:
                        if isinstance(param, dict):
                            param_name = param.get("name", "")
                            if param.get("required", False):
                                required_params.append(param_name)
                                if "default" in param:
                                    default_params[param_name] = param["default"]
                            else:
                                query_filter.append(param_name)
                    
                    # Handle individual question format
                    # Each point now represents a single question
                    question = result.payload.get("question", "")
                    
                    # Reconstruct QueryTemplate
                    template = QueryTemplate(
                        template_id=result.payload["template_id"],
                        natural_questions=question,  # Single question
                        sql_query=result.payload.get("sql_query", ""),
                        sql_query_with_parameters=result.payload.get("sql_query", ""),  # Use same as sql_query
                        keywords=result.payload.get("keywords", []),
                        category=result.payload.get("template_category", ""),
                        required_params=required_params,
                        query_filter=query_filter,
                        default_params=default_params,
                        usage_count=0,
                        related_tables=result.payload.get("target_scope", {}).get("tables", []),
                        to_agent_prompt=result.payload.get("sql_system", None),
                        template_version=result.payload.get("template_version", "1.0.0"),
                        embedding_model=self.model_name,
                        embedding_dimension=self.vector_size,
                        created_at=datetime.now()
                    )
                    
                    # The matched question is the actual question
                    matched_question = question
                    
                    results.append(UnifiedVectorSearchResult(
                        template_id=template.template_id,
                        score=combined_score,
                        template=template,
                        keyword_matches=keyword_matches,
                        matched_question=matched_question
                    ))
            
            # Sort by combined score and limit
            results.sort(key=lambda x: x.score, reverse=True)
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Error searching templates: {e}")
            return []