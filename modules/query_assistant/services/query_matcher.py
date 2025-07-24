#!/usr/bin/env python3
"""
Query matcher using vector similarity
"""
import json
import sqlite3
import numpy as np
from typing import List, Dict, Optional
from pathlib import Path
from sklearn.metrics.pairwise import cosine_similarity

# Use real embedding service
from .embedding_service import EmbeddingService

class QueryMatcher:
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.db_path = Path(__file__).parent.parent.parent.parent / "data/iacsgraph.db"
        self._template_cache = {}
        self._embedding_cache = {}
        
    def find_best_match(self, query: str, top_k: int = 3) -> List[Dict]:
        """Find best matching templates for a query"""
        # Get query embedding
        query_embedding = self.embedding_service.get_embedding(query)
        if query_embedding is None:
            return []
        
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
            sims = cosine_similarity([query_embedding], template_embeddings)[0]
            max_sim = np.max(sims)
            
            # Boost similarity if keywords match
            keyword_boost = self._calculate_keyword_boost(query, template_data['keywords'])
            final_similarity = max_sim * (1 + keyword_boost)
            
            similarities.append({
                'template_id': template_id,
                'similarity': float(final_similarity),
                'base_similarity': float(max_sim),
                'keyword_boost': keyword_boost,
                'matched_question_idx': int(np.argmax(sims)),
                'category': template_data['category']
            })
        
        # Sort by similarity
        similarities.sort(key=lambda x: x['similarity'], reverse=True)
        
        # Filter by threshold
        threshold = 0.7
        filtered = [s for s in similarities if s['base_similarity'] >= threshold]
        
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
        matched_keywords = sum(1 for kw in keywords if kw.lower() in query_lower)
        
        if matched_keywords == 0:
            return 0.0
        
        # Boost: 0.1 for first keyword, 0.05 for additional
        return 0.1 + (matched_keywords - 1) * 0.05
    
    def get_template_details(self, template_id: str) -> Optional[Dict]:
        """Get full template details"""
        if not self._template_cache:
            self._load_templates()
        
        return self._template_cache.get(template_id)