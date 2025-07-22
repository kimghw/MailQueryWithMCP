"""Similarity calculator for text embeddings"""

import numpy as np
from typing import List, Dict, Tuple, Optional, Any
import logging
import requests
from sklearn.metrics.pairwise import cosine_similarity
import os

logger = logging.getLogger(__name__)


class SimilarityCalculator:
    """Calculate similarity between text embeddings"""
    
    def __init__(self, api_key: Optional[str] = None, model_name: str = "text-embedding-3-large"):
        """Initialize similarity calculator
        
        Args:
            api_key: OpenAI API key
            model_name: Embedding model name
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
            
        self.model_name = model_name
        self.api_base_url = "https://api.openai.com/v1"
        
        # Set up session
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        })
        
        logger.info(f"Initialized SimilarityCalculator with model: {model_name}")
    
    def get_embedding(self, text: str) -> List[float]:
        """Get embedding for a single text
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
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
            
        except Exception as e:
            logger.error(f"Error getting embedding: {e}")
            raise
    
    def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for multiple texts
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
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
            
            # Log usage
            usage = data.get('usage', {})
            if usage:
                logger.info(f"Embeddings generated: {len(texts)} texts, {usage.get('total_tokens', 0)} tokens")
            
            return embeddings
            
        except Exception as e:
            logger.error(f"Error getting batch embeddings: {e}")
            raise
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate cosine similarity between two texts
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Cosine similarity score (0-1)
        """
        logger.info(f"Calculating similarity between:\n  Text1: {text1[:50]}...\n  Text2: {text2[:50]}...")
        
        # Get embeddings
        embeddings = self.get_embeddings_batch([text1, text2])
        
        # Calculate cosine similarity
        similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
        
        logger.info(f"Similarity score: {similarity:.4f}")
        return similarity
    
    def calculate_pairwise_similarities(self, texts: List[str]) -> Dict[str, Any]:
        """Calculate pairwise similarities between multiple texts
        
        Args:
            texts: List of texts
            
        Returns:
            Dictionary containing:
                - similarity_matrix: NxN numpy array of similarities
                - texts: Original texts
                - pairs: List of (i, j, similarity) tuples sorted by similarity
        """
        n = len(texts)
        logger.info(f"Calculating pairwise similarities for {n} texts")
        
        # Get embeddings for all texts
        embeddings = self.get_embeddings_batch(texts)
        
        # Calculate similarity matrix
        similarity_matrix = cosine_similarity(embeddings)
        
        # Extract pairs with similarities (excluding self-similarities)
        pairs = []
        for i in range(n):
            for j in range(i + 1, n):
                pairs.append((i, j, similarity_matrix[i][j]))
        
        # Sort by similarity (descending)
        pairs.sort(key=lambda x: x[2], reverse=True)
        
        logger.info(f"Calculated {len(pairs)} pairwise similarities")
        
        return {
            "similarity_matrix": similarity_matrix,
            "texts": texts,
            "pairs": pairs
        }
    
    def find_most_similar(self, query_text: str, candidate_texts: List[str], top_k: int = 5) -> List[Tuple[int, str, float]]:
        """Find most similar texts to a query
        
        Args:
            query_text: Query text
            candidate_texts: List of candidate texts
            top_k: Number of top results to return
            
        Returns:
            List of (index, text, similarity) tuples
        """
        logger.info(f"Finding top {top_k} similar texts to: {query_text[:50]}...")
        
        # Get embeddings
        all_texts = [query_text] + candidate_texts
        embeddings = self.get_embeddings_batch(all_texts)
        
        query_embedding = embeddings[0]
        candidate_embeddings = embeddings[1:]
        
        # Calculate similarities
        similarities = cosine_similarity([query_embedding], candidate_embeddings)[0]
        
        # Get top k
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            results.append((idx, candidate_texts[idx], similarities[idx]))
        
        logger.info(f"Top similarity: {results[0][2]:.4f}" if results else "No results")
        
        return results
    
    def print_similarity_matrix(self, similarity_data: Dict[str, Any], max_text_length: int = 30):
        """Pretty print similarity matrix
        
        Args:
            similarity_data: Output from calculate_pairwise_similarities
            max_text_length: Maximum text length for display
        """
        matrix = similarity_data["similarity_matrix"]
        texts = similarity_data["texts"]
        n = len(texts)
        
        # Truncate texts for display
        display_texts = [t[:max_text_length] + "..." if len(t) > max_text_length else t for t in texts]
        
        print("\n=== Similarity Matrix ===\n")
        
        # Print header
        print(" " * (max_text_length + 5), end="")
        for i in range(n):
            print(f"[{i}]".ljust(8), end="")
        print()
        
        # Print rows
        for i in range(n):
            print(f"[{i}] {display_texts[i]:<{max_text_length}}", end="  ")
            for j in range(n):
                if i == j:
                    print("1.0000".ljust(8), end="")
                else:
                    print(f"{matrix[i][j]:.4f}".ljust(8), end="")
            print()
        
        # Print top pairs
        print("\n=== Top Similar Pairs ===\n")
        pairs = similarity_data["pairs"][:10]  # Top 10 pairs
        
        for i, j, sim in pairs:
            print(f"[{i}] vs [{j}]: {sim:.4f}")
            print(f"  Text {i}: {texts[i][:50]}...")
            print(f"  Text {j}: {texts[j][:50]}...")
            print()