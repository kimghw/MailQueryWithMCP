#!/usr/bin/env python3
"""
Query matcher with synonym support
"""
import json
import sqlite3
import numpy as np
from typing import List, Dict, Optional
from pathlib import Path
from sklearn.metrics.pairwise import cosine_similarity

# Use real embedding service
from .embedding_service import EmbeddingService
from .synonym_processor import synonym_processor

class QueryMatcherV2:
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.db_path = Path(__file__).parent.parent.parent.parent / "data/iacsgraph.db"
        self._template_cache = {}
        self._embedding_cache = {}
        self.similarity_threshold = 0.5  # v2.5 threshold
        
    def find_best_match(self, query: str, top_k: int = 3) -> List[Dict]:
        """Find best matching templates for a query with synonym support"""
        # Normalize query with synonyms
        normalized_query = synonym_processor.normalize_query(query)
        
        # Get embeddings for both original and normalized queries
        query_embedding = self.embedding_service.get_embedding(query)
        if query_embedding is None:
            return []
            
        normalized_embedding = None
        if normalized_query != query:
            normalized_embedding = self.embedding_service.get_embedding(normalized_query)
        
        # Load all templates if not cached
        if not self._template_cache:
            self._load_templates()
        
        # Calculate similarities
        similarities = []
        for template_id, template_data in self._template_cache.items():
            # Get embeddings for all natural questions
            template_embeddings = []
            for question in template_data['natural_questions']:
                if question not in self._embedding_cache:
                    emb = self.embedding_service.get_embedding(question)
                    if emb is not None:
                        self._embedding_cache[question] = emb
                
                if question in self._embedding_cache:
                    template_embeddings.append(self._embedding_cache[question])
            
            if not template_embeddings:
                continue
            
            # Calculate max similarity across all questions
            template_embeddings = np.array(template_embeddings)
            
            # Try both original and normalized query
            sims_original = cosine_similarity([query_embedding], template_embeddings)[0]
            max_sim = np.max(sims_original)
            matched_idx = int(np.argmax(sims_original))
            
            if normalized_embedding is not None:
                sims_normalized = cosine_similarity([normalized_embedding], template_embeddings)[0]
                max_sim_normalized = np.max(sims_normalized)
                if max_sim_normalized > max_sim:
                    max_sim = max_sim_normalized
                    matched_idx = int(np.argmax(sims_normalized))
            
            # Calculate keyword boost with expanded keywords
            expanded_keywords = synonym_processor.expand_keywords(template_data['keywords'])
            keyword_boost = self._calculate_keyword_boost(query, expanded_keywords)
            
            # Also check normalized query for keywords
            if normalized_query != query:
                keyword_boost_normalized = self._calculate_keyword_boost(normalized_query, expanded_keywords)
                keyword_boost = max(keyword_boost, keyword_boost_normalized)
            
            final_similarity = max_sim * (1 + keyword_boost)
            
            similarities.append({
                'template_id': template_id,
                'similarity': float(final_similarity),
                'base_similarity': float(max_sim),
                'keyword_boost': keyword_boost,
                'matched_question_idx': matched_idx,
                'category': template_data['category'],
                'normalized_query': normalized_query if normalized_query != query else None
            })
        
        # Sort by similarity
        similarities.sort(key=lambda x: x['similarity'], reverse=True)
        
        # Filter by threshold
        filtered = [s for s in similarities if s['base_similarity'] >= self.similarity_threshold]
        
        return filtered[:top_k]
    
    def _load_templates(self):
        """Load templates from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT template_id, natural_questions, keywords, category,
                   sql_query_with_parameters, required_params, optional_params
            FROM query_templates
            WHERE template_id LIKE '%_v2'
        """)
        
        for row in cursor.fetchall():
            template_id, questions, keywords_json, category, sql_query, req_params, opt_params = row
            
            self._template_cache[template_id] = {
                'natural_questions': questions.split(' | '),
                'keywords': json.loads(keywords_json) if keywords_json else [],
                'category': category,
                'sql_query': sql_query,
                'required_params': json.loads(req_params) if req_params else [],
                'optional_params': json.loads(opt_params) if opt_params else []
            }
        
        conn.close()
    
    def _calculate_keyword_boost(self, query: str, keywords: List[str]) -> float:
        """Calculate keyword matching boost"""
        if not keywords:
            return 0.0
        
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        matched_keywords = 0
        for kw in keywords:
            kw_lower = kw.lower()
            # Check exact match or word match
            if kw_lower in query_lower or kw_lower in query_words:
                matched_keywords += 1
        
        if matched_keywords == 0:
            return 0.0
        
        # Boost: 0.2 for first keyword, 0.1 for additional (increased from 0.1/0.05)
        return 0.2 + (matched_keywords - 1) * 0.1
    
    def get_template_details(self, template_id: str) -> Optional[Dict]:
        """Get full template details"""
        if not self._template_cache:
            self._load_templates()
        
        return self._template_cache.get(template_id)