#!/usr/bin/env python3
"""
하이브리드 검색 테스트
"""

import sys
sys.path.append('/home/kimghw/IACSGRAPH')

# Import path 수정
sys.path.insert(0, '/home/kimghw/IACSGRAPH/modules/query_assistant/services')
from hybrid_search import (
    HybridSearchConfig, HybridSearchStrategy, prepare_search_query
)
# 직접 import
sys.path.insert(0, '/home/kimghw/IACSGRAPH/modules/common/parsers')
sys.path.insert(0, '/home/kimghw/IACSGRAPH/modules/query_assistant/services')
from query_parameter_extractor import QueryParameterExtractor
from keyword_expander import KeywordExpander


def test_hybrid_search_preparation():
    """하이브리드 검색 준비 테스트"""
    
    # 컴포넌트 초기화
    extractor = QueryParameterExtractor()
    expander = KeywordExpander()
    
    # 테스트 쿼리
    test_queries = [
        "한국선급의 PL25016a 승인 현황",
        "Show me ABS response for agenda PL25016b",
        "로이드선급 최근 아젠다 검토 결과"
    ]
    
    print("=" * 80)
    print("하이브리드 검색 준비 테스트")
    print("=" * 80)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n테스트 {i}: {query}")
        print("-" * 60)
        
        # 1. 파라미터 추출
        params = extractor.extract_parameters(query)
        print(f"\n추출된 파라미터:")
        print(f"  - organization: {params.get('organization')}")
        print(f"  - organization_code: {params.get('organization_code')}")
        print(f"  - agenda_base: {params.get('agenda_base')}")
        print(f"  - agenda_base_version: {params.get('agenda_base_version')}")
        
        # 2. 키워드 확장
        expansion = expander.expand_query(query)
        print(f"\n키워드 확장:")
        print(f"  - 원본 키워드: {expansion.original_keywords[:5]}")
        print(f"  - 확장된 키워드: {expansion.expanded_keywords[:10]}")
        
        # 3. 검색 쿼리 준비
        search_data = prepare_search_query(
            query=query,
            extracted_params=params,
            expanded_keywords=expansion.expanded_keywords
        )
        
        print(f"\n검색 데이터:")
        print(f"  - 검색 텍스트: {search_data['search_text']}")
        print(f"  - 중요 키워드: {search_data['important_keywords']}")
        print(f"  - 필터: {search_data['filters']}")


def test_scoring_strategy():
    """점수 계산 전략 테스트"""
    
    print("\n" + "=" * 80)
    print("점수 계산 전략 테스트")
    print("=" * 80)
    
    # 하이브리드 검색 전략 초기화
    config = HybridSearchConfig(
        vector_weight=0.6,
        keyword_weight=0.4,
        exact_match_boost=2.0
    )
    strategy = HybridSearchStrategy(config)
    
    # 테스트 케이스
    test_cases = [
        {
            "name": "높은 벡터 유사도, 낮은 키워드 매칭",
            "vector_score": 0.85,
            "keyword_score": 0.2,
            "query_keywords": ["agenda", "response", "KR"],
            "template_keywords": ["agenda", "status", "organization"],
            "match_count": 1
        },
        {
            "name": "낮은 벡터 유사도, 높은 키워드 매칭",
            "vector_score": 0.4,
            "keyword_score": 0.8,
            "query_keywords": ["agenda", "response", "approved", "KR"],
            "template_keywords": ["agenda", "response", "approved", "KR", "status"],
            "match_count": 4
        },
        {
            "name": "균형잡힌 점수",
            "vector_score": 0.65,
            "keyword_score": 0.6,
            "query_keywords": ["PL25016a", "response", "status"],
            "template_keywords": ["PL25016", "response", "decision", "status"],
            "match_count": 2
        }
    ]
    
    for case in test_cases:
        print(f"\n{case['name']}:")
        print(f"  - 벡터 점수: {case['vector_score']:.2f}")
        print(f"  - 키워드 점수: {case['keyword_score']:.2f}")
        
        # 하이브리드 점수 계산
        hybrid_score = strategy.calculate_hybrid_score(
            case['vector_score'],
            case['keyword_score']
        )
        print(f"  - 하이브리드 점수: {hybrid_score:.2f}")
        
        # 포함 여부 결정
        should_include = strategy.should_include_result(
            case['vector_score'],
            case['keyword_score'],
            hybrid_score,
            case['match_count']
        )
        print(f"  - 포함 여부: {'✓' if should_include else '✗'}")
        
        # 키워드 점수 재계산
        recalc_keyword_score = strategy.calculate_keyword_score(
            case['query_keywords'],
            case['template_keywords']
        )
        print(f"  - 재계산된 키워드 점수: {recalc_keyword_score:.2f}")


if __name__ == "__main__":
    test_hybrid_search_preparation()
    test_scoring_strategy()