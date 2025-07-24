#!/usr/bin/env python3
"""Mock embedding service for 1536 dimensions"""
import numpy as np
import hashlib

class MockEmbeddingService:
    def __init__(self):
        self.dimension = 1536
        
    def get_embedding(self, text: str) -> np.ndarray:
        """Get mock embedding using hash"""
        text_hash = hashlib.md5(text.encode()).digest()
        embedding = np.zeros(self.dimension)
        
        for i in range(min(len(text_hash), self.dimension)):
            embedding[i] = text_hash[i] / 255.0
        
        words = text.lower().split()
        for i, word in enumerate(words[:100]):
            word_hash = hash(word) % self.dimension
            embedding[word_hash] += 0.1
        
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
            
        return embedding