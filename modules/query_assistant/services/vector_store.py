"""Vector store for query templates with individual embeddings"""

import json
import os
import uuid
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import requests
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from ..schema import QueryTemplate, QDRANT_COLLECTION_CONFIG

load_dotenv()
logger = logging.getLogger(__name__)


class VectorSearchResult(BaseModel):
    """Vector search result"""
    template_id: str
    score: float
    template: QueryTemplate
    keyword_matches: List[str] = Field(default_factory=list)
    matched_question: Optional[str] = None
    embedding_type: Optional[str] = None
    matched_text: Optional[str] = None


class VectorStore:
    """Vector store for templates with individual embeddings per question/component"""
    
    def __init__(
        self,
        qdrant_url: str = None,
        qdrant_port: int = None,
        api_key: Optional[str] = None,
        collection_name: str = "query_templates_unified",
        embedding_model: str = "text-embedding-3-large",
        vector_size: int = 3072
    ):
        self.qdrant_url = qdrant_url or os.getenv('QDRANT_URL', 'localhost')
        self.qdrant_port = qdrant_port or int(os.getenv('QDRANT_PORT', 6333))
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        self.vector_size = vector_size
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        
        if not self.api_key:
            raise ValueError("OpenAI API key is required for embeddings")
        
        # Initialize Qdrant client
        self.client = QdrantClient(
            url=self.qdrant_url, 
            port=self.qdrant_port,
            check_compatibility=False
        )
        
    def create_collection(self, recreate: bool = False):
        """Create or recreate the collection"""
        try:
            if recreate:
                self.client.delete_collection(self.collection_name)
                logger.info(f"Deleted existing collection: {self.collection_name}")
        except:
            pass
            
        # Check if collection exists
        try:
            self.client.get_collection(self.collection_name)
            logger.info(f"Collection {self.collection_name} already exists")
        except:
            # Create new collection
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE
                )
            )
            logger.info(f"Created collection: {self.collection_name}")
        
    def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for multiple texts in one API call"""
        if not texts:
            return []
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "input": texts,
            "model": self.embedding_model
        }
        
        response = requests.post(
            "https://api.openai.com/v1/embeddings",
            headers=headers,
            json=data
        )
        response.raise_for_status()
        
        # Extract embeddings in order
        embeddings = []
        for item in response.json()['data']:
            embeddings.append(item['embedding'])
        
        return embeddings
        
    def _get_embedding(self, text: str) -> List[float]:
        """Get embedding for a single text"""
        return self.get_embeddings_batch([text])[0]
        
    def search(
        self, 
        query: str, 
        keywords: List[str] = None,
        category: Optional[str] = None,
        limit: int = 5,
        score_threshold: float = 0.3
    ) -> List[VectorSearchResult]:
        """Search for matching query templates with individual embeddings"""
        try:
            # Generate query embedding
            if keywords:
                query_text = f"{query} {' '.join(keywords)}"
            else:
                query_text = query
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
            
            # Perform vector search - get more results since same template has multiple embeddings
            search_results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=limit * 5,  # Get more results since we have multiple embeddings per template
                with_payload=True,
                query_filter=Filter(must=filter_conditions) if filter_conditions else None
            )
            
            # Group results by template_id and keep the highest score for each
            template_scores = {}
            for result in search_results:
                template_id = result.payload.get("template_id")
                if not template_id:
                    continue
                    
                # Calculate keyword match score
                template_keywords = set(result.payload.get("keywords", []))
                query_keywords = set(keywords) if keywords else set()
                keyword_matches = list(template_keywords.intersection(query_keywords))
                
                # Enhanced keyword scoring: consider both match ratio and absolute matches
                if query_keywords:
                    match_ratio = len(keyword_matches) / len(query_keywords)
                    # Give bonus for multiple keyword matches
                    match_bonus = min(len(keyword_matches) * 0.1, 0.3)  # Up to 0.3 bonus
                    keyword_score = min(match_ratio + match_bonus, 1.0)  # Cap at 1.0
                else:
                    keyword_score = 0
                
                # Use only vector score when no keywords available
                if not keywords:
                    combined_score = result.score  # 100% vector similarity
                    if result.score > 0.3:  # Debug high scoring results
                        logger.info(f"[HIGH SCORE] Query match - Template: {template_id}, Vector: {result.score:.3f}, Keywords: None")
                else:
                    # Always use 100% vector, 0% keyword
                    combined_score = (result.score * 1.0) + (keyword_score * 0.0)  # 100% vector, 0% keyword
                    
                    if result.score > 0.3:  # Debug high scoring results
                        logger.info(f"[HIGH SCORE] Query match - Template: {template_id}, Vector: {result.score:.3f}, Keyword: {keyword_score:.3f}, Combined: {combined_score:.3f}")
                
                # Keep the highest score for each template
                if template_id not in template_scores or combined_score > template_scores[template_id]['score']:
                    template_scores[template_id] = {
                        'result': result,
                        'score': combined_score,
                        'keyword_matches': keyword_matches,
                        'embedding_type': result.payload.get('embedding_type', ''),
                        'matched_text': result.payload.get('embedded_text', '')
                    }
            
            # Process unique templates with best scores
            results = []
            for template_data in sorted(template_scores.values(), key=lambda x: x['score'], reverse=True):
                result = template_data['result']
                combined_score = template_data['score']
                
                if combined_score >= score_threshold:
                    # Create QueryTemplate from payload
                    parameters_list = result.payload.get("parameters", [])
                    
                    # Convert parameters to list of SqlParameters
                    parameters = []
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
                    
                    # Extract questions
                    natural_questions = result.payload.get("natural_questions", [])
                    
                    # Extract SQL query
                    sql_query = result.payload.get("sql_query", "")
                    sql_system = result.payload.get("sql_system", "")
                    
                    # Get related tables
                    tables = result.payload.get("related_tables", [])
                    
                    # Create template matching the existing schema
                    template = QueryTemplate(
                        template_id=result.payload.get("template_id", ""),
                        natural_questions=" | ".join(natural_questions),  # Join questions as string
                        sql_query=sql_query,
                        sql_query_with_parameters=sql_query,  # Same as sql_query for now
                        keywords=result.payload.get("keywords", []),
                        category=result.payload.get("template_category", ""),
                        required_params=required_params,
                        default_params=default_params,
                        query_filter=query_filter,
                        usage_count=0,
                        created_at=datetime.now(),
                        related_tables=tables,
                        to_agent_prompt=sql_system,
                        template_version=result.payload.get("template_version", "1.0.0"),
                        embedding_model=self.embedding_model,
                        embedding_dimension=self.vector_size
                    )
                    
                    # Add parameters to template if available
                    if hasattr(template, '__dict__'):
                        template.__dict__['parameters'] = parameters_list
                    
                    # Create search result
                    search_result = VectorSearchResult(
                        template_id=template.template_id,
                        score=combined_score,
                        template=template,
                        keyword_matches=template_data['keyword_matches'],
                        matched_question=result.payload.get('embedded_question', ''),
                        embedding_type=template_data['embedding_type'],
                        matched_text=template_data['matched_text']
                    )
                    
                    results.append(search_result)
            
            # Sort by combined score and limit
            results.sort(key=lambda x: x.score, reverse=True)
            return results[:limit]
        
        except Exception as e:
            logger.error(f"Error searching templates: {e}")
            return []
    
    def search_by_vector(
        self,
        vector: List[float],
        top_k: int = 10,
        score_threshold: float = 0.0,
        category: Optional[str] = None
    ) -> List[VectorSearchResult]:
        """Search using pre-computed vector"""
        
        # Set up filters
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
            query_vector=vector,
            limit=top_k * 5,  # Get more results since we have multiple embeddings per template
            with_payload=True,
            query_filter=Filter(must=filter_conditions) if filter_conditions else None
        )
        
        # Group results by template_id
        template_scores = {}
        for result in search_results:
            template_id = result.payload.get("template_id")
            if not template_id:
                continue
            
            # Keep the highest score for each template
            if template_id not in template_scores or result.score > template_scores[template_id]['score']:
                template_scores[template_id] = {
                    'result': result,
                    'score': result.score,
                    'embedding_type': result.payload.get('embedding_type', ''),
                    'matched_text': result.payload.get('embedded_text', '')
                }
        
        # Process unique templates
        results = []
        for template_data in sorted(template_scores.values(), key=lambda x: x['score'], reverse=True):
            result = template_data['result']
            
            if template_data['score'] >= score_threshold:
                # Create QueryTemplate from payload
                parameters_list = result.payload.get("parameters", [])
                
                # Extract template fields
                natural_questions = result.payload.get("natural_questions", [])
                sql_query = result.payload.get("sql_query", "")
                tables = result.payload.get("related_tables", [])
                
                # Create template - handle natural_questions as string
                template = QueryTemplate(
                    template_id=result.payload.get("template_id"),
                    category=result.payload.get("template_category", ""),
                    natural_questions=natural_questions[0] if natural_questions else "",  # Take first question
                    sql_query=sql_query,
                    sql_query_with_parameters=result.payload.get("sql_query_with_parameters", sql_query),
                    keywords=result.payload.get("keywords", []),
                    required_params=result.payload.get("required_params", []),
                    default_params=result.payload.get("default_params", {}),
                    query_filter=result.payload.get("query_filter", []),
                    parameters=parameters_list,
                    related_tables=tables
                )
                
                # Create search result
                search_result = VectorSearchResult(
                    template_id=template.template_id,
                    score=template_data['score'],
                    template=template,
                    keyword_matches=[],
                    matched_question=template_data.get('matched_text', ''),
                    embedding_type=template_data['embedding_type']
                )
                
                results.append(search_result)
        
        return results[:top_k]
    
        
    def get_template_count(self) -> int:
        """Get count of templates in collection"""
        info = self.client.get_collection(self.collection_name)
        return info.points_count
    
    def update_usage_count(self, template_id: str):
        """Update usage count for a template (placeholder for compatibility)"""
        # This would need to be implemented if usage tracking is needed
        logger.debug(f"Usage count update requested for {template_id}")
        pass
    
    def get_popular_templates(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get popular templates (placeholder for compatibility)"""
        # This would need to be implemented based on usage tracking
        return []