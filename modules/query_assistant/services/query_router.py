#!/usr/bin/env python3
"""
Query Router for directing queries to appropriate handlers
- SQL Templates for structured data
- VectorDB for document/content search
"""
import re
import json
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class QueryType(Enum):
    """Query type enumeration"""
    SQL_TEMPLATE = "sql_template"
    VECTORDB = "vectordb"
    HYBRID = "hybrid"
    LLM_DIRECT = "llm_direct"


@dataclass
class QueryRoute:
    """Query routing decision"""
    query_type: QueryType
    confidence: float
    reason: str
    metadata: Dict[str, Any]


class QueryRouter:
    """Routes queries to appropriate handlers based on content analysis"""
    
    def __init__(self):
        """Initialize query router"""
        self.vectordb_patterns = self._load_vectordb_patterns()
        self.sql_patterns = self._load_sql_patterns()
        self.llm_direct_patterns = self._load_llm_direct_patterns()
        
    def _load_vectordb_patterns(self) -> List[Dict[str, str]]:
        """Load VectorDB query patterns"""
        return [
            # Document search patterns
            {"pattern": r"규정.*문서|문서.*규정", "type": "regulation_doc"},
            {"pattern": r"가이드라인|guideline", "type": "guideline"},
            {"pattern": r"절차서|procedure", "type": "procedure"},
            {"pattern": r"표준|standard", "type": "standard"},
            
            # Specific document types
            {"pattern": r"UR.*관련.*내용|UR.*규정|UR.*문서", "type": "ur_doc"},
            {"pattern": r"PR.*관련.*내용|PR.*규정|PR.*문서", "type": "pr_doc"},
            {"pattern": r"IMO.*가이드|IMO.*규정", "type": "imo_doc"},
            {"pattern": r"IACS.*절차|IACS.*문서", "type": "iacs_doc"},
            {"pattern": r"EG.*문서|Expert Group", "type": "eg_doc"},
            
            # PT related patterns
            {"pattern": r"PT.*리스트|PT.*참여|PT.*내용", "type": "pt_info"},
            {"pattern": r"진행.*중인.*PT|완료된.*PT", "type": "pt_status"},
            
            # Similar discussion patterns
            {"pattern": r"다른.*패널.*유사.*논의", "type": "similar_discussion"},
            {"pattern": r"자율운항선박.*논의|원격운항선박.*논의", "type": "ship_discussion"},
            
            # Meeting and attachment patterns (v2.8)
            {"pattern": r"첨부파일.*분석", "type": "attachment_analysis"},
            {"pattern": r"회의.*리스트|회의.*내용|회의.*결정사항", "type": "meeting_info"},
            {"pattern": r"화상회의.*결과", "type": "video_conference"},
            {"pattern": r"회의.*결과.*부합", "type": "meeting_alignment"},
            
            # Strategy and perspective patterns (v2.8)
            {"pattern": r"IACS.*전략|목표", "type": "strategy_doc"},
            {"pattern": r"GPG.*결정사항", "type": "gpg_decision"},
            {"pattern": r"관점.*갖고.*있는가", "type": "perspective_analysis"},
            
            # Cross-panel patterns (v2.8)
            {"pattern": r"다른.*패널.*같은.*이슈", "type": "cross_panel_issue"},
            
            # Content search patterns
            {"pattern": r"내용.*찾아|관련.*문서", "type": "content_search"},
            {"pattern": r"사이버.*보안.*문서", "type": "cyber_security"},
            {"pattern": r"환경.*규제.*정보", "type": "environment"},
            {"pattern": r"디지털.*전환.*가이드", "type": "digital_transform"},
        ]
    
    def _load_sql_patterns(self) -> List[Dict[str, str]]:
        """Load SQL query patterns"""
        return [
            # Agenda queries
            {"pattern": r"의제|agenda", "type": "agenda"},
            {"pattern": r"진행중|ongoing", "type": "status"},
            {"pattern": r"완료|completed", "type": "status"},
            
            # Response queries
            {"pattern": r"응답.*현황|response.*status", "type": "response"},
            {"pattern": r"미응답|no.*response", "type": "response"},
            
            # EG work patterns
            {"pattern": r"EG.*작업|EG.*진행.*사항", "type": "eg_work"},
            {"pattern": r"참여한.*기관", "type": "participation"},
            
            # Meeting attendance
            {"pattern": r"회의.*참석|참석.*가능", "type": "meeting"},
            {"pattern": r"날짜별.*참석|기관별.*참석", "type": "attendance"},
            
            # Request/clarification patterns
            {"pattern": r"답변.*요구|명확화.*요구", "type": "request"},
            {"pattern": r"다른.*기관.*요구", "type": "inter_org_request"},
            
            # Statistics
            {"pattern": r"통계|statistics", "type": "stats"},
            {"pattern": r"평균|average", "type": "stats"},
            {"pattern": r"응답률|response.*rate", "type": "stats"},
            {"pattern": r"키워드.*분석", "type": "keyword_analysis"},
            
            # Time-based
            {"pattern": r"최근|recent", "type": "time"},
            {"pattern": r"마감일|deadline", "type": "time"},
            {"pattern": r"월별|monthly", "type": "time"},
            {"pattern": r"3개월|작년|2025년", "type": "time_period"},
        ]
    
    def _load_llm_direct_patterns(self) -> List[Dict[str, str]]:
        """Load LLM direct response patterns"""
        return [
            # Technology trends
            {"pattern": r"기술개발.*동향.*분석|technology.*trend", "type": "tech_trend"},
            {"pattern": r"기술.*배경|technical.*background", "type": "tech_background"},
            
            # Analysis that requires general knowledge
            {"pattern": r"현재.*기술개발.*동향", "type": "current_tech_trend"},
            {"pattern": r"관련해서.*기술개발.*동향", "type": "related_tech_trend"},
        ]
    
    def route_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> QueryRoute:
        """
        Determine the appropriate route for a query
        
        Args:
            query: User query
            context: Additional context (e.g., extracted parameters)
            
        Returns:
            QueryRoute object with routing decision
        """
        query_lower = query.lower()
        
        # First check for LLM direct response patterns
        llm_score = self._calculate_llm_direct_score(query_lower)
        if llm_score > 0.7:
            return QueryRoute(
                query_type=QueryType.LLM_DIRECT,
                confidence=llm_score,
                reason="기술 동향이나 배경 설명은 LLM이 직접 응답",
                metadata={"matched_patterns": self._get_matched_patterns(query_lower, "llm")}
            )
        
        # Check for explicit VectorDB indicators
        vectordb_score = self._calculate_vectordb_score(query_lower)
        sql_score = self._calculate_sql_score(query_lower)
        
        # Check for hybrid indicators
        hybrid_indicators = [
            "관련된 내용",
            "관련 문서",
            "related content",
            "UR과 관련",
            "IMO 관련",
            "EG와 관련"
        ]
        
        is_hybrid = any(indicator in query_lower for indicator in hybrid_indicators)
        
        # Determine route
        if is_hybrid and vectordb_score > 0 and sql_score > 0:
            return QueryRoute(
                query_type=QueryType.HYBRID,
                confidence=0.8,
                reason="쿼리가 구조화된 데이터와 문서 검색을 모두 필요로 함",
                metadata={
                    "vectordb_score": vectordb_score,
                    "sql_score": sql_score
                }
            )
        elif vectordb_score > sql_score:
            return QueryRoute(
                query_type=QueryType.VECTORDB,
                confidence=vectordb_score,
                reason="문서 내용 검색이 필요한 쿼리",
                metadata={"matched_patterns": self._get_matched_patterns(query_lower, "vectordb")}
            )
        else:
            return QueryRoute(
                query_type=QueryType.SQL_TEMPLATE,
                confidence=sql_score if sql_score > 0 else 0.7,
                reason="구조화된 데이터 쿼리",
                metadata={"matched_patterns": self._get_matched_patterns(query_lower, "sql")}
            )
    
    def _calculate_vectordb_score(self, query: str) -> float:
        """Calculate VectorDB relevance score"""
        score = 0.0
        matched_count = 0
        
        for pattern_info in self.vectordb_patterns:
            if re.search(pattern_info["pattern"], query, re.IGNORECASE):
                score += 0.2
                matched_count += 1
        
        # Boost score for strong indicators
        strong_indicators = ["규정", "문서", "가이드라인", "절차서", "찾아줘"]
        for indicator in strong_indicators:
            if indicator in query:
                score += 0.1
        
        return min(score, 1.0)
    
    def _calculate_sql_score(self, query: str) -> float:
        """Calculate SQL template relevance score"""
        score = 0.0
        matched_count = 0
        
        for pattern_info in self.sql_patterns:
            if re.search(pattern_info["pattern"], query, re.IGNORECASE):
                score += 0.2
                matched_count += 1
        
        # Boost score for strong indicators
        strong_indicators = ["의제", "응답", "통계", "현황", "진행중"]
        for indicator in strong_indicators:
            if indicator in query:
                score += 0.1
        
        return min(score, 1.0)
    
    def _calculate_llm_direct_score(self, query: str) -> float:
        """Calculate LLM direct response relevance score"""
        score = 0.0
        
        for pattern_info in self.llm_direct_patterns:
            if re.search(pattern_info["pattern"], query, re.IGNORECASE):
                score += 0.4  # Higher weight for LLM patterns
        
        # Strong indicators for LLM direct response
        strong_indicators = ["기술개발 동향", "기술 배경", "technology trend", "technical background"]
        for indicator in strong_indicators:
            if indicator in query:
                score += 0.3
        
        return min(score, 1.0)
    
    def _get_matched_patterns(self, query: str, pattern_type: str) -> List[str]:
        """Get list of matched patterns"""
        if pattern_type == "vectordb":
            patterns = self.vectordb_patterns
        elif pattern_type == "llm":
            patterns = self.llm_direct_patterns
        else:
            patterns = self.sql_patterns
            
        matched = []
        
        for pattern_info in patterns:
            if re.search(pattern_info["pattern"], query, re.IGNORECASE):
                matched.append(pattern_info["type"])
        
        return matched
    
    def suggest_query_improvement(self, query: str, route: QueryRoute) -> Optional[str]:
        """
        Suggest query improvements based on routing decision
        
        Args:
            query: Original query
            route: Routing decision
            
        Returns:
            Suggestion for query improvement or None
        """
        if route.confidence < 0.5:
            return "쿼리를 더 구체적으로 작성해주세요. 예: '의제 검색' 또는 '규정 문서 찾기'"
        
        if route.query_type == QueryType.HYBRID:
            return "구조화된 데이터와 문서 검색을 모두 수행합니다. 더 구체적인 검색을 원하시면 목적을 명확히 해주세요."
        
        return None


# Example usage
if __name__ == "__main__":
    router = QueryRouter()
    
    test_queries = [
        # SQL Templates
        "KR이 응답하지 않은 의제",
        "월별 응답률 통계",
        "SDTP에서 진행된 EG 작업 알려줘",
        "3개월 내 주요 키워드 분석해줘",
        
        # VectorDB
        "UR 규정 문서 찾아줘",
        "IMO 가이드라인",
        "현재 진행 중인 PT 리스트",
        "{agenda}와 관련해서 UR에 관련된 내용이 뭐지?",
        
        # LLM Direct
        "{agenda}와 관련해서 현재 기술개발 동향 분석해줘",
        "{keyword}에 대한 기술 배경이 뭐지?",
        
        # Hybrid
        "최근 UR과 관련된 아젠다나 기관의 응답이 있었나?",
        "{agenda}에서 IMO 관련된 내용이 있나?"
    ]
    
    for query in test_queries:
        route = router.route_query(query)
        print(f"\n쿼리: {query}")
        print(f"라우팅: {route.query_type.value}")
        print(f"신뢰도: {route.confidence:.2f}")
        print(f"이유: {route.reason}")
        
        suggestion = router.suggest_query_improvement(query, route)
        if suggestion:
            print(f"제안: {suggestion}")