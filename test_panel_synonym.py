#!/usr/bin/env python3
"""
패널 동의어 처리 및 committee 필드 추출 테스트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.common.services.synonym_service import SynonymService
from modules.common.parsers.query_parameter_extractor import QueryParameterExtractor

def test_panel_synonyms():
    """패널 동의어 처리 테스트"""
    print("=" * 60)
    print("패널 동의어 처리 테스트")
    print("=" * 60)
    
    # SynonymService 초기화
    synonym_service = SynonymService()
    
    # 테스트 케이스
    test_cases = [
        "디지털 기술 패널의 최신 아젠다를 보여줘",
        "PL의 최근 회의록",
        "디지털 패널 관련 문서",
        "SDTP 패널의 응답 현황",
        "GPG의 아젠다 목록",
        "디지털 기술 패널과 GPG의 공동 작업"
    ]
    
    print("\n1. SynonymService 정규화 테스트:")
    print("-" * 40)
    for query in test_cases:
        normalized = synonym_service.normalize_text(query)
        print(f"원본: {query}")
        print(f"정규화: {normalized}")
        print()

def test_committee_extraction():
    """Committee 필드 추출 테스트"""
    print("\n" + "=" * 60)
    print("Committee 필드 추출 테스트")
    print("=" * 60)
    
    # QueryParameterExtractor 초기화
    extractor = QueryParameterExtractor()
    
    # 테스트 케이스
    test_cases = [
        "디지털 기술 패널의 최신 아젠다를 보여줘",
        "PL의 최근 회의록",
        "디지털 패널 관련 문서",
        "SDTP 패널의 응답 현황",
        "GPG의 아젠다 목록",
        "디지털 기술 패널과 GPG의 공동 작업",
        "한국선급의 응답 현황",  # committee 없음
        "PL25016a 아젠다 상세"   # agenda는 있지만 committee 없음
    ]
    
    print("\n2. QueryParameterExtractor committee 추출 테스트:")
    print("-" * 40)
    for query in test_cases:
        params = extractor.extract_parameters(query)
        print(f"Query: {query}")
        print(f"추출된 파라미터:")
        
        # 주요 필드만 출력
        if params.get('committee'):
            print(f"  - committee: {params['committee']}")
        if params.get('agenda_panel'):
            print(f"  - agenda_panel: {params['agenda_panel']}")
        if params.get('organization'):
            print(f"  - organization: {params['organization']}")
        if params.get('agenda_code'):
            print(f"  - agenda_code: {params['agenda_code']}")
        
        # 정규화된 쿼리도 확인
        print(f"  - normalized_query: {params['normalized_query']}")
        print()

def test_relative_score():
    """Relative Score 계산 테스트"""
    print("\n" + "=" * 60)
    print("Relative Score 계산 시뮬레이션")
    print("=" * 60)
    
    # 다양한 파라미터 조합 테스트
    test_params = [
        {
            "name": "모든 필드 채워짐",
            "params": {
                'organization': 'KR',
                'date_range': {'start': '2025-01-01', 'end': '2025-01-31'},
                'keywords': ['디지털', '기술', '패널'],
                'intent': 'search',
                'committee': 'SDTP',
                'agenda_base': 'PL25016',
                'agenda_base_version': 'PL25016a'
            }
        },
        {
            "name": "일부 필드만 채워짐",
            "params": {
                'organization': 'KR',
                'keywords': ['응답', '현황'],
                'intent': 'list',
                'committee': None,
                'agenda_base': None,
                'agenda_base_version': None,
                'date_range': None
            }
        },
        {
            "name": "최소 필드만 채워짐",
            "params": {
                'keywords': ['아젠다'],
                'intent': 'search'
            }
        }
    ]
    
    print("\n3. Relative Score 계산:")
    print("-" * 40)
    
    for test in test_params:
        params = test['params']
        key_fields = ['organization', 'date_range', 'keywords', 'intent', 
                      'committee', 'agenda_base', 'agenda_base_version']
        
        filled_count = 0
        for field in key_fields:
            if field == 'keywords':
                if params.get(field) and len(params[field]) > 0:
                    filled_count += 1
            elif params.get(field) is not None:
                filled_count += 1
        
        relative_score = round((filled_count / len(key_fields)) * 0.2, 3)
        
        print(f"테스트: {test['name']}")
        print(f"  채워진 필드: {filled_count}/7")
        print(f"  Relative Score: {relative_score}")
        print(f"  파라미터: {params}")
        print()

if __name__ == "__main__":
    # 모든 테스트 실행
    test_panel_synonyms()
    test_committee_extraction()
    test_relative_score()
    
    print("\n" + "=" * 60)
    print("테스트 완료!")
    print("=" * 60)