#!/usr/bin/env python3
"""
Embedding service for text vectorization
"""
import os
import json
import hashlib
import numpy as np
from pathlib import Path
from typing import Optional, List
import openai
from functools import lru_cache

class EmbeddingService:
    def __init__(self):
        self.model = "text-embedding-3-large"
        self.dimension = 1536
        self.cache_dir = Path(__file__).parent / ".embedding_cache"
        self.cache_dir.mkdir(exist_ok=True)
        
        # Initialize OpenAI client
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        openai.api_key = api_key
        self.client = openai.OpenAI(api_key=api_key)
    
    def get_embedding(self, text: str) -> Optional[np.ndarray]:
        """Get embedding for text with caching"""
        # Check cache first
        cache_key = self._get_cache_key(text)
        cached = self._load_from_cache(cache_key)
        if cached is not None:
            return cached
        
        try:
            # Get embedding from OpenAI
            response = self.client.embeddings.create(
                model=self.model,
                input=text,
                dimensions=self.dimension
            )
            
            embedding = np.array(response.data[0].embedding)
            
            # Cache the result
            self._save_to_cache(cache_key, embedding)
            
            return embedding
            
        except Exception as e:
            print(f"Error getting embedding for '{text[:50]}...': {str(e)}")
            return None
    
    def get_embeddings_batch(self, texts: List[str]) -> List[Optional[np.ndarray]]:
        """Get embeddings for multiple texts"""
        results = []
        
        # Check cache for all texts
        uncached_texts = []
        uncached_indices = []
        
        for i, text in enumerate(texts):
            cache_key = self._get_cache_key(text)
            cached = self._load_from_cache(cache_key)
            if cached is not None:
                results.append(cached)
            else:
                results.append(None)
                uncached_texts.append(text)
                uncached_indices.append(i)
        
        # Get embeddings for uncached texts
        if uncached_texts:
            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=uncached_texts,
                    dimensions=self.dimension
                )
                
                for idx, embedding_data in enumerate(response.data):
                    embedding = np.array(embedding_data.embedding)
                    original_idx = uncached_indices[idx]
                    results[original_idx] = embedding
                    
                    # Cache the result
                    cache_key = self._get_cache_key(uncached_texts[idx])
                    self._save_to_cache(cache_key, embedding)
                    
            except Exception as e:
                print(f"Error getting batch embeddings: {str(e)}")
        
        return results
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text"""
        content = f"{self.model}:{self.dimension}:{text}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _load_from_cache(self, cache_key: str) -> Optional[np.ndarray]:
        """Load embedding from cache"""
        cache_file = self.cache_dir / f"{cache_key}.npy"
        if cache_file.exists():
            try:
                return np.load(cache_file)
            except:
                return None
        return None
    
    def _save_to_cache(self, cache_key: str, embedding: np.ndarray):
        """Save embedding to cache"""
        cache_file = self.cache_dir / f"{cache_key}.npy"
        try:
            np.save(cache_file, embedding)
        except:
            pass
    
    def clear_cache(self):
        """Clear embedding cache"""
        for cache_file in self.cache_dir.glob("*.npy"):
            cache_file.unlink()
        print(f"Cleared {len(list(self.cache_dir.glob('*.npy')))} cached embeddings")