#!/usr/bin/env python3
"""
Unified Query matcher with synonym support and flexible return options
Uses VectorDB for template retrieval
"""
import os
from typing import List, Dict, Optional, Tuple, Union
from pathlib import Path

from .vector_store_unified import VectorStoreUnified
from ...common.services.synonym_service import SynonymService
from ...common.parsers import QueryParameterExtractor

class QueryMatcher:
    def __init__(self):
        self.synonym_service = SynonymService()
        self.parameter_extractor = QueryParameterExtractor()
        
        # Initialize VectorStore with configuration
        self.vector_store = VectorStoreUnified(
            qdrant_url=os.getenv("QDRANT_URL", "localhost"),
            qdrant_port=int(os.getenv("QDRANT_PORT", 6333)),
            api_key=os.getenv("OPENAI_API_KEY"),
            api_base_url=os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1"),
            model_name=os.getenv("EMBEDDING_MODEL", "text-embedding-3-large"),
            collection_name="query_templates"  # Use new unified collection with 174 templates
        )
        
        self.similarity_threshold = 0.4  # Lowered threshold for better matching
        self.similarity_tolerance = 0.03  # 3% tolerance for similar results
        
    def find_best_matches(
        self, 
        query: str, 
        top_k: int = 3,
        return_similar: bool = False,
        category: Optional[str] = None
    ) -> Union[List[Dict], Tuple[List[Dict], List[Dict]]]:
        """
        Find best matching templates with synonym support using VectorDB
        
        Args:
            query: User query
            top_k: Number of top matches to return
            return_similar: If True, returns (primary_match, similar_matches) like v3
                          If False, returns simple list like v2
            category: Optional category filter
                          
        Returns:
            If return_similar=False: List of top matches (v2 behavior)
            If return_similar=True: Tuple of (primary_matches, similar_matches) (v3 behavior)
        """
        # Don't normalize query - use original query only
        # normalized_query = self.synonym_service.normalize_text(query)
        normalized_query = query
        
        # Extract parameters and keywords
        extracted_params = self.parameter_extractor.extract_parameters(query)
        keywords = extracted_params.get('keywords', [])
        
        # If no keywords extracted, try to extract from query
        if not keywords:
            # Simple keyword extraction from query
            import re
            words = re.findall(r'\w+', query)
            keywords = [w for w in words if len(w) > 1]  # Filter out single characters
        
        # Don't expand keywords - use original keywords only
        # expanded_keywords = self.synonym_service.expand_keywords(keywords)
        expanded_keywords = keywords  # Use original keywords without expansion
        
        # Only print debug if not suppressed
        if os.environ.get('SUPPRESS_DEBUG') != '1':
            print(f"[DEBUG] Query: {query}")
            print(f"[DEBUG] Keywords: {keywords}")
            # print(f"[DEBUG] Expanded keywords: {expanded_keywords}")
        
        # Search in VectorDB
        try:
            # Search with both original and normalized query
            search_results = self.vector_store.search(
                query=query,
                keywords=expanded_keywords,
                limit=top_k * 2,  # Get more results for filtering
                category=category,
                score_threshold=self.similarity_threshold
            )
            
            # If normalized query is different, also search with it
            if normalized_query != query:
                normalized_results = self.vector_store.search(
                    query=normalized_query,
                    keywords=expanded_keywords,
                    limit=top_k * 2,
                    category=category,
                    score_threshold=self.similarity_threshold
                )
                
                # Merge results and deduplicate
                seen_ids = {r.template_id for r in search_results}
                for result in normalized_results:
                    if result.template_id not in seen_ids:
                        search_results.append(result)
                        seen_ids.add(result.template_id)
            
            # Convert to expected format
            similarities = []
            for result in search_results:
                # V3 format: result has matched_question and category directly
                matched_question = result.matched_question if hasattr(result, 'matched_question') else ""
                category = result.category if hasattr(result, 'category') else ""
                
                # Extract template data if available
                template = result.template if hasattr(result, 'template') else None
                
                # Extract parameters
                parameters = []
                if template and hasattr(template, 'required_params'):
                    parameters = template.required_params
                
                # Calculate keyword boost based on keyword matches
                keyword_boost = len(result.keyword_matches) * 0.1 if result.keyword_matches else 0.0
                keyword_boost = min(keyword_boost, 0.5)  # Cap at 0.5
                
                similarities.append({
                    'template_id': result.template_id,
                    'similarity': float(result.score),
                    'base_similarity': float(result.score - keyword_boost),  # Estimate base similarity
                    'keyword_boost': float(keyword_boost),
                    'template_name': result.template_id,
                    'matched_question': matched_question,
                    'description': f"Template for {category or result.template_id}",
                    'parameters': parameters,
                    'template': template,  # Include full template object if available
                    'keyword_matches': result.keyword_matches
                })
            
            # Sort by similarity
            similarities.sort(key=lambda x: x['similarity'], reverse=True)
            
            # Return based on format preference
            if not return_similar:
                # V2 behavior: simple list
                return similarities[:top_k]
            else:
                # V3 behavior: separate primary and similar matches
                if not similarities:
                    return ([], [])
                
                # Primary match is the top scorer
                primary_matches = [similarities[0]] if similarities else []
                
                # Find similar matches (within tolerance of top score)
                similar_matches = []
                if similarities:
                    top_score = similarities[0]['similarity']
                    for match in similarities[1:]:
                        # Calculate percentage difference
                        score_diff = (top_score - match['similarity']) / top_score if top_score > 0 else 1.0
                        if score_diff <= self.similarity_tolerance:
                            similar_matches.append(match)
                        else:
                            # Since sorted, no need to check further
                            break
                
                return (primary_matches, similar_matches)
        
        except Exception as e:
            print(f"Error searching templates: {e}")
            import traceback
            traceback.print_exc()
            return ([], []) if return_similar else []
    
    # Convenience methods for backward compatibility
    def find_best_match(self, query: str, top_k: int = 3) -> List[Dict]:
        """V2 compatible method - returns simple list"""
        return self.find_best_matches(query, top_k, return_similar=False)