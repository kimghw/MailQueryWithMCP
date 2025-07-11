"""Keyword expansion service for query understanding"""

import re
import logging
from typing import List, Set, Dict, Any
from ..schema import QueryExpansion

logger = logging.getLogger(__name__)


class KeywordExpander:
    """Expand user queries with domain-specific keywords and synonyms"""
    
    def __init__(self):
        """Initialize keyword expander with domain knowledge"""
        
        # Korean-English mappings
        self.kr_en_map = {
            "아젠다": ["agenda", "안건"],
            "응답": ["response", "답변", "회신"],
            "기관": ["organization", "org", "부서"],
            "응답률": ["response rate", "답변율"],
            "상태": ["status", "state"],
            "결정": ["decision", "결정사항"],
            "승인": ["approved", "approve", "허가"],
            "반려": ["rejected", "reject", "거부"],
            "미결정": ["pending", "대기", "보류"],
            "최근": ["recent", "latest", "최신"],
            "통계": ["statistics", "stats", "분석"],
            "비교": ["compare", "comparison", "대조"],
            "검색": ["search", "find", "찾기"],
            "목록": ["list", "리스트"],
            "요약": ["summary", "정리", "개요"],
            "보고서": ["report", "리포트"],
            "주간": ["weekly", "주별"],
            "월간": ["monthly", "월별"],
            "평균": ["average", "avg", "mean"],
            "중요": ["important", "priority", "중요도"],
            "긴급": ["urgent", "emergency", "급한"]
        }
        
        # Organization names
        self.organizations = {
            "KRSDTP": ["한국연구재단", "연구재단", "NRF"],
            "KOMDTP": ["해양수산부", "해수부"],
            "KMDTP": ["기상청"],
            "GMDTP": ["지질자원연구원", "지자연"],
            "BMDTP": ["생명공학연구원", "생명연"],
            "PLDTP": ["극지연구소", "극지연"]
        }
        
        # Time-related keywords
        self.time_keywords = {
            "오늘": ["today", "현재"],
            "어제": ["yesterday", "전날"],
            "이번주": ["this week", "금주"],
            "지난주": ["last week", "전주"],
            "이번달": ["this month", "금월"],
            "지난달": ["last month", "전월"],
            "올해": ["this year", "금년"],
            "작년": ["last year", "전년"]
        }
        
        # Query intent patterns
        self.intent_patterns = {
            "statistics": ["통계", "분석", "비율", "퍼센트", "statistics", "analysis", "rate"],
            "list": ["목록", "리스트", "보여", "표시", "list", "show", "display"],
            "search": ["검색", "찾", "포함", "search", "find", "contain"],
            "summary": ["요약", "정리", "개요", "summary", "overview"],
            "comparison": ["비교", "대조", "차이", "compare", "versus", "difference"]
        }
        
    def expand_query(self, user_query: str) -> QueryExpansion:
        """Expand user query with related keywords and analyze intent"""
        # Normalize query
        normalized_query = user_query.lower().strip()
        
        # Extract original keywords
        original_keywords = self._extract_keywords(normalized_query)
        
        # Expand keywords
        expanded_keywords = self._expand_keywords(original_keywords, normalized_query)
        
        # Detect missing parameters
        missing_params = self._detect_missing_params(normalized_query, expanded_keywords)
        
        # Generate suggestions
        suggestions = self._generate_suggestions(missing_params, expanded_keywords)
        
        # Calculate confidence score
        confidence_score = self._calculate_confidence(
            original_keywords, 
            expanded_keywords,
            missing_params
        )
        
        return QueryExpansion(
            original_keywords=list(original_keywords),
            expanded_keywords=list(expanded_keywords),
            missing_params=missing_params,
            suggestions=suggestions,
            confidence_score=confidence_score
        )
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract meaningful keywords from query"""
        # Remove common words
        stopwords = {
            "은", "는", "이", "가", "을", "를", "의", "에", "와", "과",
            "으로", "로", "에서", "부터", "까지", "이나", "나", "도",
            "the", "a", "an", "is", "are", "was", "were", "what", "how",
            "please", "주세요", "해주세요", "보여주세요", "알려주세요"
        }
        
        # Tokenize (simple approach - can be improved with proper tokenizer)
        words = re.findall(r'\w+', query)
        
        # Filter out stopwords and short words
        keywords = [
            word for word in words 
            if word not in stopwords and len(word) > 1
        ]
        
        return keywords
    
    def _expand_keywords(self, keywords: List[str], full_query: str) -> Set[str]:
        """Expand keywords with synonyms and related terms"""
        expanded = set(keywords)
        
        # Check Korean-English mappings
        for keyword in keywords:
            # Direct mapping
            if keyword in self.kr_en_map:
                expanded.update(self.kr_en_map[keyword])
            
            # Reverse mapping
            for kr, en_list in self.kr_en_map.items():
                if keyword in en_list:
                    expanded.add(kr)
                    expanded.update(en_list)
        
        # Check organization names
        for org_code, org_names in self.organizations.items():
            for org_name in org_names:
                if org_name in full_query:
                    expanded.add(org_code)
                    expanded.add("organization")
                    expanded.add("기관")
        
        # Check time keywords
        for time_kr, time_en_list in self.time_keywords.items():
            if time_kr in full_query:
                expanded.add(time_kr)
                expanded.update(time_en_list)
        
        # Detect query intent
        for intent, intent_keywords in self.intent_patterns.items():
            for intent_kw in intent_keywords:
                if intent_kw in full_query:
                    expanded.add(intent)
                    expanded.update(intent_keywords)
                    break
        
        # Add numeric patterns
        if re.search(r'\d+', full_query):
            expanded.add("number")
            expanded.add("숫자")
        
        return expanded
    
    def _detect_missing_params(
        self, 
        query: str, 
        keywords: Set[str]
    ) -> List[str]:
        """Detect potentially missing parameters"""
        missing = []
        
        # Check if query mentions organization but doesn't specify which
        org_mentioned = any(
            kw in keywords 
            for kw in ["organization", "기관", "부서"]
        )
        org_specified = any(
            org in query 
            for org in self.organizations.keys()
        )
        
        if org_mentioned and not org_specified:
            missing.append("organization")
        
        # Check if query mentions time but doesn't specify period
        time_mentioned = any(
            kw in keywords
            for kw in ["최근", "recent", "기간", "period"]
        )
        time_specified = re.search(r'\d+\s*(일|주|개월|년|days?|weeks?|months?)', query)
        
        if time_mentioned and not time_specified:
            missing.append("period")
        
        # Check if query mentions status but doesn't specify which
        status_mentioned = any(
            kw in keywords
            for kw in ["상태", "status", "결정"]
        )
        status_specified = any(
            status in query
            for status in ["승인", "반려", "미결정", "approved", "rejected", "pending"]
        )
        
        if status_mentioned and not status_specified:
            missing.append("status")
        
        return missing
    
    def _generate_suggestions(
        self, 
        missing_params: List[str],
        keywords: Set[str]
    ) -> List[str]:
        """Generate helpful suggestions for user"""
        suggestions = []
        
        if "organization" in missing_params:
            suggestions.append(
                "어느 기관을 조회하시겠습니까? " +
                "(예: KRSDTP, KOMDTP, KMDTP 등)"
            )
        
        if "period" in missing_params:
            suggestions.append(
                "조회 기간을 지정해주세요. " +
                "(예: 최근 7일, 30일, 3개월 등)"
            )
        
        if "status" in missing_params:
            suggestions.append(
                "어떤 상태의 아젠다를 조회하시겠습니까? " +
                "(승인/반려/미결정)"
            )
        
        # Intent-based suggestions
        if "search" in keywords and "keyword" not in keywords:
            suggestions.append(
                "검색할 키워드를 입력해주세요. " +
                "(큰따옴표로 감싸면 정확히 매칭됩니다)"
            )
        
        return suggestions
    
    def _calculate_confidence(
        self,
        original_keywords: List[str],
        expanded_keywords: Set[str],
        missing_params: List[str]
    ) -> float:
        """Calculate confidence score for query understanding"""
        # Base score
        score = 1.0
        
        # Penalize for missing parameters
        score -= len(missing_params) * 0.2
        
        # Reward for keyword expansion
        expansion_ratio = len(expanded_keywords) / max(len(original_keywords), 1)
        score += min(expansion_ratio * 0.1, 0.3)
        
        # Ensure score is between 0 and 1
        return max(0.0, min(1.0, score))