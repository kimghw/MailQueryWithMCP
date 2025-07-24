#!/usr/bin/env python3
"""
Synonym processor for query normalization
"""
from typing import Dict, List

class SynonymProcessor:
    def __init__(self):
        # Define synonym mappings
        self.synonyms = {
            # Organization synonyms
            "우리": "KR",
            "우리나라": "KR", 
            "한국": "KR",
            "대한민국": "KR",
            "Korea": "KR",
            "korea": "KR",
            
            # Action synonyms
            "회신": "응답",
            "답변": "응답",
            "리플라이": "응답",
            "reply": "응답",
            "response": "응답",
            
            # Status synonyms
            "진행중": "ongoing",
            "진행 중": "ongoing",
            "진행중인": "ongoing",
            "처리중": "ongoing",
            "미완료": "ongoing",
            
            # Time synonyms
            "오늘": "today",
            "금일": "today",
            "어제": "yesterday",
            "작일": "yesterday",
            "내일": "tomorrow",
            "명일": "tomorrow",
            
            # Document synonyms
            "메일": "mail",
            "이메일": "mail",
            "email": "mail",
            "편지": "mail",
            "아젠다": "agenda",
            "의제": "agenda",
            "안건": "agenda",
            
            # Other common synonyms
            "마감": "deadline",
            "기한": "deadline",
            "마감일": "deadline",
            "임박": "urgent",
            "긴급": "urgent",
            "시급": "urgent",
        }
        
        # Build reverse mapping for bidirectional lookup
        self.reverse_synonyms = {}
        for key, value in self.synonyms.items():
            if value not in self.reverse_synonyms:
                self.reverse_synonyms[value] = []
            self.reverse_synonyms[value].append(key)
    
    def normalize_query(self, query: str) -> str:
        """Normalize query by replacing synonyms"""
        normalized = query
        
        # Replace synonyms (longest match first to avoid partial replacements)
        sorted_synonyms = sorted(self.synonyms.items(), key=lambda x: len(x[0]), reverse=True)
        
        for synonym, canonical in sorted_synonyms:
            # Case-insensitive replacement while preserving rest of the case
            import re
            pattern = re.compile(re.escape(synonym), re.IGNORECASE)
            normalized = pattern.sub(canonical, normalized)
        
        return normalized
    
    def expand_keywords(self, keywords: List[str]) -> List[str]:
        """Expand keywords with their synonyms"""
        expanded = set(keywords)
        
        for keyword in keywords:
            keyword_lower = keyword.lower()
            
            # Add the keyword itself
            expanded.add(keyword)
            
            # Add canonical form if keyword is a synonym
            if keyword_lower in self.synonyms:
                expanded.add(self.synonyms[keyword_lower])
            
            # Add all synonyms if keyword is canonical
            if keyword in self.reverse_synonyms:
                expanded.update(self.reverse_synonyms[keyword])
            
            # Also check lowercase version
            if keyword_lower in self.reverse_synonyms:
                expanded.update(self.reverse_synonyms[keyword_lower])
        
        return list(expanded)
    
    def get_all_variants(self, term: str) -> List[str]:
        """Get all variants of a term including synonyms"""
        variants = {term, term.lower(), term.upper()}
        
        # Check if it's a synonym
        if term.lower() in self.synonyms:
            canonical = self.synonyms[term.lower()]
            variants.add(canonical)
            # Add all synonyms of the canonical form
            if canonical in self.reverse_synonyms:
                variants.update(self.reverse_synonyms[canonical])
        
        # Check if it's a canonical form
        if term in self.reverse_synonyms:
            variants.update(self.reverse_synonyms[term])
        
        return list(variants)

# Singleton instance
synonym_processor = SynonymProcessor()