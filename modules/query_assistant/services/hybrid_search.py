"""
Enhanced Hybrid Search for Vector DB
벡터 유사도와 키워드 검색을 효과적으로 결합
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class HybridSearchConfig:
    """하이브리드 검색 설정"""
    vector_weight: float = 0.6  # 벡터 유사도 가중치
    keyword_weight: float = 0.4  # 키워드 매칭 가중치
    
    # 키워드 매칭 옵션
    exact_match_boost: float = 2.0  # 정확히 일치하는 키워드 부스트
    partial_match_ratio: float = 0.5  # 부분 일치 비율
    
    # 필터링 옵션
    min_keyword_matches: int = 1  # 최소 키워드 매칭 수
    use_synonym_expansion: bool = True  # 동의어 확장 사용
    
    # 점수 임계값
    vector_threshold: float = 0.3  # 벡터 유사도 최소값
    keyword_threshold: float = 0.2  # 키워드 점수 최소값
    combined_threshold: float = 0.4  # 최종 점수 최소값


class HybridSearchStrategy:
    """하이브리드 검색 전략"""
    
    def __init__(self, config: Optional[HybridSearchConfig] = None):
        self.config = config or HybridSearchConfig()
    
    def calculate_keyword_score(
        self, 
        query_keywords: List[str],
        template_keywords: List[str],
        exact_matches: List[str] = None
    ) -> float:
        """
        키워드 매칭 점수 계산
        
        Args:
            query_keywords: 쿼리에서 추출한 키워드
            template_keywords: 템플릿의 키워드
            exact_matches: 정확히 일치하는 키워드
            
        Returns:
            키워드 매칭 점수 (0.0 ~ 1.0)
        """
        if not query_keywords:
            return 0.0
        
        query_set = set(k.lower() for k in query_keywords)
        template_set = set(k.lower() for k in template_keywords)
        
        # 교집합 계산
        matches = query_set.intersection(template_set)
        match_count = len(matches)
        
        # 정확히 일치하는 키워드에 보너스
        if exact_matches:
            exact_set = set(k.lower() for k in exact_matches)
            exact_count = len(matches.intersection(exact_set))
            match_count += exact_count * (self.config.exact_match_boost - 1)
        
        # Jaccard 유사도 계산
        union_size = len(query_set.union(template_set))
        if union_size == 0:
            return 0.0
        
        jaccard_score = match_count / union_size
        
        # 쿼리 키워드 커버리지
        coverage_score = len(matches) / len(query_set)
        
        # 최종 점수: Jaccard와 커버리지의 조합
        return (jaccard_score * 0.5) + (coverage_score * 0.5)
    
    def calculate_hybrid_score(
        self,
        vector_score: float,
        keyword_score: float,
        additional_factors: Dict[str, float] = None
    ) -> float:
        """
        하이브리드 점수 계산
        
        Args:
            vector_score: 벡터 유사도 점수 (0.0 ~ 1.0)
            keyword_score: 키워드 매칭 점수 (0.0 ~ 1.0)
            additional_factors: 추가 점수 요소
            
        Returns:
            최종 하이브리드 점수
        """
        # 기본 가중 평균
        base_score = (
            vector_score * self.config.vector_weight + 
            keyword_score * self.config.keyword_weight
        )
        
        # 추가 요소 적용
        if additional_factors:
            # 카테고리 매칭
            if 'category_match' in additional_factors:
                base_score *= (1 + additional_factors['category_match'] * 0.2)
            
            # 최근 사용 부스트
            if 'recency_boost' in additional_factors:
                base_score *= (1 + additional_factors['recency_boost'] * 0.1)
            
            # 사용 빈도 부스트
            if 'usage_boost' in additional_factors:
                base_score *= (1 + additional_factors['usage_boost'] * 0.1)
        
        return min(base_score, 1.0)  # 최대 1.0으로 제한
    
    def should_include_result(
        self,
        vector_score: float,
        keyword_score: float,
        combined_score: float,
        keyword_match_count: int
    ) -> bool:
        """
        검색 결과 포함 여부 결정
        
        Returns:
            포함 여부
        """
        # 최소 임계값 체크
        if combined_score < self.config.combined_threshold:
            return False
        
        # 벡터 점수가 매우 높으면 키워드 무관하게 포함
        if vector_score >= 0.8:
            return True
        
        # 키워드가 많이 일치하면 벡터 점수가 낮아도 포함
        if keyword_match_count >= self.config.min_keyword_matches:
            return True
        
        # 개별 임계값 체크
        return (
            vector_score >= self.config.vector_threshold and
            keyword_score >= self.config.keyword_threshold
        )
    
    def rank_results(
        self,
        results: List[Tuple[Dict, float, float, int]]
    ) -> List[Tuple[Dict, float]]:
        """
        검색 결과 순위 결정
        
        Args:
            results: [(템플릿, 벡터점수, 키워드점수, 매칭수), ...]
            
        Returns:
            [(템플릿, 최종점수), ...] 정렬된 결과
        """
        scored_results = []
        
        for template, vector_score, keyword_score, match_count in results:
            # 추가 요소 계산
            additional_factors = {}
            
            # 사용 빈도 기반 부스트
            usage_count = template.get('usage_count', 0)
            if usage_count > 0:
                additional_factors['usage_boost'] = min(usage_count / 100, 0.5)
            
            # 최종 점수 계산
            final_score = self.calculate_hybrid_score(
                vector_score, 
                keyword_score,
                additional_factors
            )
            
            # 필터링
            if self.should_include_result(
                vector_score, keyword_score, final_score, match_count
            ):
                scored_results.append((template, final_score))
        
        # 점수 기준 정렬
        scored_results.sort(key=lambda x: x[1], reverse=True)
        
        return scored_results


def prepare_search_query(
    query: str,
    extracted_params: Dict[str, any],
    expanded_keywords: List[str]
) -> Dict[str, any]:
    """
    검색 쿼리 준비
    
    Args:
        query: 원본 사용자 쿼리
        extracted_params: 추출된 파라미터
        expanded_keywords: 확장된 키워드
        
    Returns:
        검색에 사용할 데이터
    """
    # 검색용 텍스트 구성
    search_text_parts = [query]
    
    # 추출된 파라미터 추가
    if extracted_params.get('organization'):
        search_text_parts.append(extracted_params['organization'])
    
    if extracted_params.get('agenda_base'):
        search_text_parts.append(extracted_params['agenda_base'])
    
    # 중요 키워드 강조
    important_keywords = []
    for keyword in expanded_keywords:
        if any(term in keyword.lower() for term in ['agenda', 'response', 'approved']):
            important_keywords.append(keyword)
    
    return {
        'search_text': ' '.join(search_text_parts),
        'keywords': expanded_keywords,
        'important_keywords': important_keywords,
        'filters': {
            'organization': extracted_params.get('organization_code'),
            'agenda_base': extracted_params.get('agenda_base')
        }
    }