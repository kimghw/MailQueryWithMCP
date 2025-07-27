"""Services for Query Assistant module"""

# Export the vector stores
from .vector_store import VectorStore, VectorSearchResult

# Backward compatibility aliases
VectorStoreUnified = VectorStore
UnifiedVectorSearchResult = VectorSearchResult

__all__ = ['VectorStore', 'VectorSearchResult', 'VectorStoreUnified', 'UnifiedVectorSearchResult']