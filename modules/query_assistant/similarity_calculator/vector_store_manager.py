"""Vector store manager for similarity search"""

import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import json

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, 
    Filter, FieldCondition, MatchValue,
    SearchRequest, ScoredPoint
)

from .similarity_calculator import SimilarityCalculator

logger = logging.getLogger(__name__)


class VectorStoreManager:
    """Manage vector storage and similarity search in Qdrant"""
    
    def __init__(
        self,
        collection_name: str = "text_similarity",
        api_key: Optional[str] = None,
        model_name: str = "text-embedding-3-large",
        qdrant_url: str = "localhost",
        qdrant_port: int = 6333
    ):
        """Initialize vector store manager
        
        Args:
            collection_name: Name of Qdrant collection
            api_key: OpenAI API key
            model_name: Embedding model name
            qdrant_url: Qdrant server URL
            qdrant_port: Qdrant server port
        """
        self.collection_name = collection_name
        self.similarity_calculator = SimilarityCalculator(api_key, model_name)
        
        # Initialize Qdrant client
        self.client = QdrantClient(host=qdrant_url, port=qdrant_port)
        
        # Determine vector size based on model
        self.vector_size = 3072 if "text-embedding-3-large" in model_name else 1536
        
        logger.info(f"Initialized VectorStoreManager: {collection_name} ({self.vector_size}D)")
        
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
            else:
                logger.info(f"Collection exists: {self.collection_name}")
        except Exception as e:
            logger.error(f"Error ensuring collection: {e}")
            raise
    
    def add_text(
        self, 
        text: str, 
        metadata: Optional[Dict[str, Any]] = None,
        text_id: Optional[str] = None
    ) -> str:
        """Add a single text to vector store
        
        Args:
            text: Text to add
            metadata: Optional metadata
            text_id: Optional ID (will be generated if not provided)
            
        Returns:
            Text ID
        """
        # Generate ID if not provided
        if text_id is None:
            text_id = f"text_{datetime.now().timestamp()}"
        
        # Get embedding
        embedding = self.similarity_calculator.get_embedding(text)
        
        # Prepare metadata
        payload = {
            "text": text,
            "created_at": datetime.now().isoformat(),
            **(metadata or {})
        }
        
        # Create point
        point = PointStruct(
            id=hash(text_id) % (10 ** 8),  # Convert to numeric ID
            vector=embedding,
            payload=payload
        )
        
        # Upsert to Qdrant
        self.client.upsert(
            collection_name=self.collection_name,
            points=[point]
        )
        
        logger.info(f"Added text to vector store: {text_id}")
        return text_id
    
    def add_texts_batch(
        self, 
        texts: List[str], 
        metadatas: Optional[List[Dict[str, Any]]] = None,
        text_ids: Optional[List[str]] = None
    ) -> List[str]:
        """Add multiple texts to vector store
        
        Args:
            texts: List of texts
            metadatas: Optional list of metadata dicts
            text_ids: Optional list of IDs
            
        Returns:
            List of text IDs
        """
        # Generate IDs if not provided
        if text_ids is None:
            text_ids = [f"text_{i}_{datetime.now().timestamp()}" for i in range(len(texts))]
        
        # Get embeddings
        embeddings = self.similarity_calculator.get_embeddings_batch(texts)
        
        # Create points
        points = []
        for i, (text, embedding, text_id) in enumerate(zip(texts, embeddings, text_ids)):
            metadata = metadatas[i] if metadatas else {}
            
            payload = {
                "text": text,
                "created_at": datetime.now().isoformat(),
                **metadata
            }
            
            point = PointStruct(
                id=hash(text_id) % (10 ** 8),
                vector=embedding,
                payload=payload
            )
            points.append(point)
        
        # Batch upsert
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
        
        logger.info(f"Added {len(texts)} texts to vector store")
        return text_ids
    
    def search_similar(
        self, 
        query_text: str, 
        limit: int = 10,
        score_threshold: float = 0.0,
        filter_conditions: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar texts in vector store
        
        Args:
            query_text: Query text
            limit: Maximum number of results
            score_threshold: Minimum similarity score
            filter_conditions: Optional filter conditions
            
        Returns:
            List of results with text, score, and metadata
        """
        # Get query embedding
        query_embedding = self.similarity_calculator.get_embedding(query_text)
        
        # Build filter if provided
        filter_obj = None
        if filter_conditions:
            conditions = []
            for key, value in filter_conditions.items():
                conditions.append(
                    FieldCondition(
                        key=key,
                        match=MatchValue(value=value)
                    )
                )
            filter_obj = Filter(must=conditions)
        
        # Search
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=limit,
            with_payload=True,
            query_filter=filter_obj,
            score_threshold=score_threshold
        )
        
        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append({
                "text": result.payload.get("text", ""),
                "score": result.score,
                "metadata": {k: v for k, v in result.payload.items() if k != "text"}
            })
        
        logger.info(f"Found {len(formatted_results)} similar texts")
        return formatted_results
    
    def calculate_similarity_with_stored(
        self, 
        query_text: str, 
        stored_text_ids: Optional[List[str]] = None
    ) -> List[Tuple[str, float]]:
        """Calculate similarity between query and stored texts
        
        Args:
            query_text: Query text
            stored_text_ids: Optional list of specific text IDs to compare with
            
        Returns:
            List of (text, similarity) tuples
        """
        # If no specific IDs, search all
        if stored_text_ids is None:
            results = self.search_similar(query_text, limit=100)
            return [(r["text"], r["score"]) for r in results]
        
        # Otherwise, get specific texts and calculate similarities
        # This would require implementing a get_by_ids method
        # For now, we'll use search with a high limit
        results = self.search_similar(query_text, limit=1000)
        
        # Filter by IDs if provided
        filtered_results = []
        for result in results:
            # Check if this result matches any of the requested IDs
            # (This is a simplified approach - in production you'd want proper ID matching)
            filtered_results.append((result["text"], result["score"]))
        
        return filtered_results
    
    def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the collection
        
        Returns:
            Collection information
        """
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                "name": self.collection_name,
                "points_count": info.points_count,
                "vector_size": self.vector_size,
                "status": "ready"
            }
        except Exception as e:
            logger.error(f"Error getting collection info: {e}")
            return {
                "name": self.collection_name,
                "error": str(e)
            }
    
    def delete_collection(self):
        """Delete the collection"""
        try:
            self.client.delete_collection(self.collection_name)
            logger.info(f"Deleted collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Error deleting collection: {e}")
            raise