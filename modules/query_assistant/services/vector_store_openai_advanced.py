"""Advanced Vector store with OpenAI's latest embedding models"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
import os
import numpy as np
import openai
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


class VectorStoreOpenAIAdvanced:
    """Advanced Qdrant vector store with OpenAI's latest embedding models
    
    Supports:
    - text-embedding-3-small (1536 dims, fast & efficient)
    - text-embedding-3-large (3072 dims, best performance)
    - Dimension reduction for cost optimization
    """
    
    # Model configurations
    MODEL_CONFIGS = {
        "text-embedding-3-small": {
            "default_dim": 1536,
            "max_dim": 1536,
            "reduced_dims": [512, 1024],
            "price_per_1k": 0.00002
        },
        "text-embedding-3-large": {
            "default_dim": 3072,
            "max_dim": 3072,
            "reduced_dims": [256, 512, 1024, 1536],
            "price_per_1k": 0.00013
        },
        # Legacy model for comparison
        "text-embedding-ada-002": {
            "default_dim": 1536,
            "max_dim": 1536,
            "reduced_dims": [],
            "price_per_1k": 0.0001
        }
    }
    
    def __init__(
        self, 
        qdrant_url: str = "localhost",
        qdrant_port: int = 6333,
        openai_api_key: str = None,
        model_name: str = "text-embedding-3-small",
        dimensions: Optional[int] = None,
        collection_name: Optional[str] = None
    ):
        """Initialize advanced vector store
        
        Args:
            qdrant_url: Qdrant server URL
            qdrant_port: Qdrant server port
            openai_api_key: OpenAI API key (optional, uses env var if not provided)
            model_name: Model name (text-embedding-3-small, text-embedding-3-large)
            dimensions: Custom dimensions (for dimension reduction)
            collection_name: Custom collection name
        """
        # Validate model
        if model_name not in self.MODEL_CONFIGS:
            raise ValueError(f"Unsupported model: {model_name}. Choose from {list(self.MODEL_CONFIGS.keys())}")
        
        self.model_name = model_name
        self.model_config = self.MODEL_CONFIGS[model_name]
        
        # Set dimensions
        if dimensions:
            if dimensions > self.model_config["max_dim"]:
                raise ValueError(f"Dimensions {dimensions} exceeds max {self.model_config['max_dim']} for {model_name}")
            self.vector_size = dimensions
        else:
            self.vector_size = self.model_config["default_dim"]
        
        # Collection name includes model and dimension info
        if collection_name:
            self.collection_name = collection_name
        else:
            model_suffix = model_name.replace("text-embedding-", "").replace("-", "_")
            self.collection_name = f"iacsgraph_queries_{model_suffix}_{self.vector_size}d"
        
        # Initialize OpenAI
        if openai_api_key:
            openai.api_key = openai_api_key
        else:
            openai.api_key = os.environ.get("OPENAI_API_KEY")
            if not openai.api_key:
                raise ValueError("OpenAI API key not provided and OPENAI_API_KEY not found in environment")
        
        # Initialize Qdrant client
        self.client = QdrantClient(host=qdrant_url, port=qdrant_port)
        
        # Log configuration
        logger.info(f"Using model: {self.model_name} with {self.vector_size} dimensions")
        logger.info(f"Collection: {self.collection_name}")
        logger.info(f"Estimated cost: ${self.model_config['price_per_1k']}/1K tokens")
        
        # Ensure collection exists
        self._ensure_collection()
        
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
        """Get embedding from OpenAI with dimension reduction if configured"""
        try:
            # Prepare request params
            params = {
                "input": text,
                "model": self.model_name
            }
            
            # Add dimensions parameter if using reduction
            if self.vector_size < self.model_config["default_dim"]:
                params["dimensions"] = self.vector_size
                logger.debug(f"Using dimension reduction: {self.model_config['default_dim']} → {self.vector_size}")
            
            response = openai.Embedding.create(**params)
            embedding = response['data'][0]['embedding']
            
            # Verify dimension
            if len(embedding) != self.vector_size:
                raise ValueError(f"Expected {self.vector_size} dimensions, got {len(embedding)}")
            
            return embedding
            
        except Exception as e:
            logger.error(f"Error getting OpenAI embedding: {e}")
            raise
    
    def _get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for multiple texts with dimension reduction"""
        try:
            # Prepare request params
            params = {
                "input": texts,
                "model": self.model_name
            }
            
            # Add dimensions parameter if using reduction
            if self.vector_size < self.model_config["default_dim"]:
                params["dimensions"] = self.vector_size
            
            response = openai.Embedding.create(**params)
            embeddings = [item['embedding'] for item in response['data']]
            
            # Log token usage for cost estimation
            usage = response.get('usage', {})
            if usage:
                tokens = usage.get('total_tokens', 0)
                cost = (tokens / 1000) * self.model_config['price_per_1k']
                logger.info(f"Batch embedding: {len(texts)} texts, {tokens} tokens, ${cost:.4f}")
            
            return embeddings
            
        except Exception as e:
            logger.error(f"Error getting OpenAI embeddings batch: {e}")
            raise
            
    def index_templates(self, templates: List[QueryTemplate]) -> bool:
        """Index query templates into vector store"""
        try:
            points = []
            texts_to_embed = []
            
            # Prepare texts for batch embedding
            for template in templates:
                text_to_embed = f"{template.natural_query} {' '.join(template.keywords)}"
                texts_to_embed.append(text_to_embed)
            
            # Get embeddings in batch
            embeddings = self._get_embeddings_batch(texts_to_embed)
            
            # Create points
            for i, (template, embedding) in enumerate(zip(templates, embeddings)):
                point = PointStruct(
                    id=i,
                    vector=embedding,
                    payload={
                        "template_id": template.id,
                        "natural_query": template.natural_query,
                        "sql_template": template.sql_template,
                        "keywords": template.keywords,
                        "category": template.category,
                        "required_params": template.required_params,
                        "optional_params": template.optional_params,
                        "usage_count": template.usage_count,
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
            
            logger.info(f"Indexed {len(templates)} templates with {self.model_name} ({self.vector_size}D)")
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
                        id=result.payload["template_id"],
                        natural_query=result.payload["natural_query"],
                        sql_template=result.payload["sql_template"],
                        keywords=result.payload["keywords"],
                        category=result.payload["category"],
                        required_params=result.payload["required_params"],
                        optional_params=result.payload["optional_params"],
                        usage_count=result.payload["usage_count"],
                        created_at=datetime.fromisoformat(result.payload["created_at"]),
                        last_used=datetime.fromisoformat(result.payload["last_used"]) 
                                  if result.payload.get("last_used") else None
                    )
                    
                    results.append(VectorSearchResult(
                        template_id=template.id,
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
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model configuration"""
        return {
            "model": self.model_name,
            "dimensions": self.vector_size,
            "max_dimensions": self.model_config["max_dim"],
            "dimension_reduction": self.vector_size < self.model_config["default_dim"],
            "price_per_1k_tokens": self.model_config["price_per_1k"],
            "collection": self.collection_name,
            "available_dimensions": [self.model_config["default_dim"]] + self.model_config["reduced_dims"]
        }
    
    def estimate_cost(self, num_texts: int, avg_tokens_per_text: int = 50) -> Dict[str, float]:
        """Estimate embedding cost"""
        total_tokens = num_texts * avg_tokens_per_text
        cost = (total_tokens / 1000) * self.model_config["price_per_1k"]
        
        return {
            "num_texts": num_texts,
            "estimated_tokens": total_tokens,
            "estimated_cost_usd": cost,
            "model": self.model_name,
            "price_per_1k_tokens": self.model_config["price_per_1k"]
        }