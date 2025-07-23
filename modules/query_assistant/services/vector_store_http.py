"""Vector store implementation using HTTP API for embeddings"""

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

from ..schema import QueryTemplate, VectorSearchResult, QDRANT_COLLECTION_CONFIG

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)


class VectorStoreHTTP:
    """Qdrant-based vector store using HTTP API for embeddings"""
    
    def __init__(
        self, 
        qdrant_url: str = "localhost",
        qdrant_port: int = 6333,
        api_key: Optional[str] = None,
        api_base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        collection_name: Optional[str] = None,
        vector_size: Optional[int] = None,
        use_dimension_reduction: bool = False  # 새로운 파라미터
    ):
        """Initialize vector store with HTTP embedding API
        
        Args:
            qdrant_url: Qdrant server URL
            qdrant_port: Qdrant server port
            api_key: API key for embedding service
            api_base_url: Base URL for embedding API
            model_name: Model name for embeddings
            collection_name: Custom collection name
            vector_size: Vector dimension size (None for default, or specific size for reduction)
            use_dimension_reduction: Whether to use dimension reduction for cost savings
        """
        # 기존 설정
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("API key not provided and OPENAI_API_KEY not found in environment")
            
        self.api_base_url = api_base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.model_name = model_name or os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-large")
        
        # 모델별 기본 차원 및 축소 가능 차원 정의
        self.model_configs = {
            "text-embedding-3-large": {
                "default_dim": 3072,
                "allowed_dims": [256, 512, 1024, 1536, 3072]
            },
            "text-embedding-3-small": {
                "default_dim": 1536,
                "allowed_dims": [512, 1024, 1536]
            },
            "text-embedding-ada-002": {
                "default_dim": 1536,
                "allowed_dims": [1536]  # 축소 불가
            }
        }
        
        # 차원 설정 로직 개선
        if self.model_name in self.model_configs:
            config = self.model_configs[self.model_name]
            default_dim = config["default_dim"]
            
            if vector_size and use_dimension_reduction:
                # 차원 축소 요청시 유효성 검사
                if vector_size in config["allowed_dims"] and vector_size < default_dim:
                    self.vector_size = vector_size
                    self.use_dimension_reduction = True
                    logger.info(f"Dimension reduction enabled: {default_dim} → {vector_size}")
                else:
                    logger.warning(f"Invalid dimension {vector_size} for {self.model_name}. Using default.")
                    self.vector_size = default_dim
                    self.use_dimension_reduction = False
            else:
                self.vector_size = vector_size or default_dim
                self.use_dimension_reduction = False
        else:
            # 알 수 없는 모델
            self.vector_size = vector_size or 1536
            self.use_dimension_reduction = False
        
        # 컬렉션 이름에 차원 정보 포함
        if collection_name:
            self.collection_name = collection_name
        else:
            model_suffix = self.model_name.replace("text-embedding-", "").replace("-", "_")
            self.collection_name = f"iacsgraph_queries_{model_suffix}_{self.vector_size}d"
        
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
        if self.use_dimension_reduction:
            logger.info(f"Cost reduction: ~{self._calculate_cost_reduction()}% savings")
        logger.info(f"Collection: {self.collection_name}")
        
        # Ensure collection exists
        self._ensure_collection()
    
    def _calculate_cost_reduction(self) -> int:
        """차원 축소로 인한 비용 절감률 계산"""
        if not self.use_dimension_reduction:
            return 0
        
        config = self.model_configs.get(self.model_name, {})
        default_dim = config.get("default_dim", self.vector_size)
        
        # OpenAI는 차원에 비례해서 과금
        reduction = (1 - self.vector_size / default_dim) * 100
        return int(reduction)
    
    def _ensure_collection(self):
        """Create collection if it doesn't exist"""
        try:
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            if self.collection_name not in collection_names:
                logger.info(f"Creating collection: {self.collection_name}")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE
                    )
                )
        except Exception as e:
            logger.error(f"Error ensuring collection: {e}")
            raise
    
    def _get_embedding(self, text: str) -> List[float]:
        """Get embedding from API with dimension reduction support"""
        try:
            url = f"{self.api_base_url}/embeddings"
            
            payload = {
                "input": text,
                "model": self.model_name
            }
            
            # 차원 축소 파라미터 추가
            if self.use_dimension_reduction and "text-embedding-3" in self.model_name:
                payload["dimensions"] = self.vector_size
                logger.debug(f"Requesting {self.vector_size}D embedding (reduced from default)")
            
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            
            data = response.json()
            embedding = data['data'][0]['embedding']
            
            # 차원 검증
            if len(embedding) != self.vector_size:
                logger.warning(f"Expected {self.vector_size}D, got {len(embedding)}D")
            
            return embedding
            
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP error getting embedding: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error getting embedding: {e}")
            raise
    
    def _get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for multiple texts with dimension reduction"""
        try:
            url = f"{self.api_base_url}/embeddings"
            
            payload = {
                "input": texts,
                "model": self.model_name
            }
            
            # 차원 축소 파라미터 추가
            if self.use_dimension_reduction and "text-embedding-3" in self.model_name:
                payload["dimensions"] = self.vector_size
            
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            
            data = response.json()
            embeddings = [item['embedding'] for item in data['data']]
            
            # 사용량 및 비용 로깅
            usage = data.get('usage', {})
            if usage:
                tokens = usage.get('total_tokens', 0)
                estimated_cost = self._estimate_cost(tokens)
                logger.info(
                    f"Batch embedding: {len(texts)} texts, {tokens} tokens, "
                    f"~${estimated_cost:.4f} (saved {self._calculate_cost_reduction()}%)"
                )
            
            return embeddings
            
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP error getting batch embeddings: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error getting batch embeddings: {e}")
            raise
    
    def _estimate_cost(self, tokens: int) -> float:
        """토큰 수를 기반으로 비용 추정"""
        # 모델별 가격 (1M 토큰당)
        prices = {
            "text-embedding-3-small": 0.02,
            "text-embedding-3-large": 0.13,
            "text-embedding-ada-002": 0.10
        }
        
        base_price = prices.get(self.model_name, 0.10)
        
        # 차원 축소시 비용도 비례해서 감소
        if self.use_dimension_reduction and self.model_name in self.model_configs:
            config = self.model_configs[self.model_name]
            reduction_factor = self.vector_size / config["default_dim"]
            base_price *= reduction_factor
        
        return (tokens / 1_000_000) * base_price
            
    def index_templates(self, templates: List[QueryTemplate]) -> bool:
        """Index query templates into vector store"""
        try:
            points = []
            texts_to_embed = []
            
            # Prepare texts for batch embedding
            for template in templates:
                text_to_embed = f"{template.natural_questions} {' '.join(template.keywords)}"
                texts_to_embed.append(text_to_embed)
            
            # Get embeddings in batch (more efficient)
            embeddings = self._get_embeddings_batch(texts_to_embed)
            
            # Create points
            for i, (template, embedding) in enumerate(zip(templates, embeddings)):
                point = PointStruct(
                    id=i,
                    vector=embedding,
                    payload={
                        "template_id": template.template_id,
                        "natural_questions": template.natural_questions,
                        "sql_query": template.sql_query,
                        "sql_query_with_parameters": template.sql_query_with_parameters,
                        "keywords": template.keywords,
                        "category": template.category,
                        "required_params": template.required_params,
                        "query_filter": template.query_filter,
                        "default_params": template.default_params,
                        "usage_count": template.usage_count,
                        "related_tables": template.related_tables,
                        "to_agent_prompt": template.to_agent_prompt,
                        "template_version": template.template_version,
                        "embedding_model": template.embedding_model,
                        "embedding_dimension": template.embedding_dimension,
                        "created_at": template.created_at.isoformat(),
                        "last_used": template.last_used.isoformat() if template.last_used else None
                    }
                )
                points.append(point)
            
            # Upsert points
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            
            logger.info(f"Indexed {len(templates)} templates successfully with {self.model_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error indexing templates: {e}")
            return False
    
    def search(
        self, 
        query: str, 
        keywords: List[str],
        limit: int = 5,
        category: Optional[str] = None,
        score_threshold: float = 0.5
    ) -> List[VectorSearchResult]:
        """Search for matching query templates using hybrid search"""
        try:
            # Generate query embedding
            query_text = f"{query} {' '.join(keywords)}"
            query_embedding = self._get_embedding(query_text)
            
            # Build filter
            filter_conditions = []
            if category:
                filter_conditions.append(
                    FieldCondition(
                        key="category",
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
                    # Reconstruct QueryTemplate
                    template = QueryTemplate(
                        template_id=result.payload["template_id"],
                        natural_questions=result.payload["natural_questions"],
                        sql_query=result.payload["sql_query"],
                        sql_query_with_parameters=result.payload["sql_query_with_parameters"],
                        keywords=result.payload["keywords"],
                        category=result.payload["category"],
                        required_params=result.payload["required_params"],
                        query_filter=result.payload["query_filter"],
                        default_params=result.payload.get("default_params", {}),
                        usage_count=result.payload["usage_count"],
                        related_tables=result.payload.get("related_tables", []),
                        to_agent_prompt=result.payload.get("to_agent_prompt"),
                        template_version=result.payload.get("template_version", "1.0.0"),
                        embedding_model=result.payload.get("embedding_model", "text-embedding-3-large"),
                        embedding_dimension=result.payload.get("embedding_dimension", 3072),
                        created_at=datetime.fromisoformat(result.payload["created_at"]),
                        last_used=datetime.fromisoformat(result.payload["last_used"]) 
                                  if result.payload.get("last_used") else None
                    )
                    
                    results.append(VectorSearchResult(
                        template_id=template.template_id,
                        score=combined_score,
                        template=template,
                        keyword_matches=keyword_matches
                    ))
            
            # Sort by combined score and limit
            results.sort(key=lambda x: x.score, reverse=True)
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Error searching templates: {e}")
            return []
    
    def update_usage_stats(self, template_id: str) -> bool:
        """Update usage statistics for a template"""
        try:
            # Search for the template by payload
            results = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="template_id",
                            match=MatchValue(value=template_id)
                        )
                    ]
                ),
                limit=1,
                with_payload=True
            )
            
            records, _ = results
            if not records:
                logger.warning(f"Template not found: {template_id}")
                return False
            
            # Update payload
            point_id = records[0].id
            payload = records[0].payload
            payload["usage_count"] = payload.get("usage_count", 0) + 1
            payload["last_used"] = datetime.now().isoformat()
            
            # Update point
            self.client.set_payload(
                collection_name=self.collection_name,
                payload=payload,
                points=[point_id]
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating usage stats: {e}")
            return False
    
    def get_popular_templates(self, limit: int = 10) -> List[QueryTemplate]:
        """Get most frequently used templates"""
        try:
            # Scroll through all points
            records, _ = self.client.scroll(
                collection_name=self.collection_name,
                limit=1000,  # Get all templates
                with_payload=True
            )
            
            # Sort by usage count
            sorted_records = sorted(
                records, 
                key=lambda x: x.payload.get("usage_count", 0), 
                reverse=True
            )
            
            # Convert to QueryTemplate objects
            templates = []
            for record in sorted_records[:limit]:
                template = QueryTemplate(
                    id=record.payload["template_id"],
                    natural_query=record.payload["natural_query"],
                    sql_template=record.payload["sql_template"],
                    keywords=record.payload["keywords"],
                    category=record.payload["category"],
                    required_params=record.payload["required_params"],
                    optional_params=record.payload["optional_params"],
                    usage_count=record.payload["usage_count"],
                    created_at=datetime.fromisoformat(record.payload["created_at"]),
                    last_used=datetime.fromisoformat(record.payload["last_used"]) 
                              if record.payload.get("last_used") else None
                )
                templates.append(template)
            
            return templates
            
        except Exception as e:
            logger.error(f"Error getting popular templates: {e}")
            return []
    
    def delete_collection(self):
        """Delete the collection (use with caution)"""
        try:
            self.client.delete_collection(collection_name=self.collection_name)
            logger.info(f"Deleted collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Error deleting collection: {e}")
            raise