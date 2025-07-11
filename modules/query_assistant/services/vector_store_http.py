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
    """Qdrant-based vector store using HTTP API for embeddings
    
    Supports multiple embedding providers through HTTP API:
    - OpenAI API
    - Azure OpenAI
    - Custom embedding servers
    """
    
    def __init__(
        self, 
        qdrant_url: str = "localhost",
        qdrant_port: int = 6333,
        api_key: Optional[str] = None,
        api_base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        collection_name: Optional[str] = None,
        vector_size: Optional[int] = None
    ):
        """Initialize vector store with HTTP embedding API
        
        Args:
            qdrant_url: Qdrant server URL
            qdrant_port: Qdrant server port
            api_key: API key for embedding service
            api_base_url: Base URL for embedding API
            model_name: Model name for embeddings
            collection_name: Custom collection name
            vector_size: Vector dimension size
        """
        # Get configuration from environment or parameters
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("API key not provided and OPENAI_API_KEY not found in environment")
            
        self.api_base_url = api_base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.model_name = model_name or os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-large")
        
        # Determine vector size based on model
        if vector_size:
            self.vector_size = vector_size
        else:
            if "text-embedding-3-large" in self.model_name:
                self.vector_size = 3072
            elif "text-embedding-3-small" in self.model_name:
                self.vector_size = 1536
            else:
                self.vector_size = 1536  # Default
        
        # Set collection name
        self.collection_name = collection_name or f"iacsgraph_queries_{self.model_name.replace('-', '_')}"
        
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
    
    def _get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for multiple texts"""
        try:
            url = f"{self.api_base_url}/embeddings"
            
            payload = {
                "input": texts,
                "model": self.model_name
            }
            
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            
            data = response.json()
            embeddings = [item['embedding'] for item in data['data']]
            
            # Log usage if available
            usage = data.get('usage', {})
            if usage:
                logger.info(f"Batch embedding: {len(texts)} texts, {usage.get('total_tokens', 0)} tokens")
            
            return embeddings
            
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP error getting batch embeddings: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error getting batch embeddings: {e}")
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
            
            # Get embeddings in batch (more efficient)
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
                        "default_params": template.default_params,
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
                        id=result.payload["template_id"],
                        natural_query=result.payload["natural_query"],
                        sql_template=result.payload["sql_template"],
                        keywords=result.payload["keywords"],
                        category=result.payload["category"],
                        required_params=result.payload["required_params"],
                        optional_params=result.payload["optional_params"],
                        default_params=result.payload.get("default_params", {}),
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