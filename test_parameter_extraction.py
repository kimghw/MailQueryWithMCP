#!/usr/bin/env python3
"""
필수 파라미터 추출 테스트
- agenda_base_version
- agenda_base  
- organization_code
- organization
"""

import sys
sys.path.append('/home/kimghw/IACSGRAPH')

from modules.common.parsers import QueryParameterExtractor
from pprint import pprint


def test_parameter_extraction():
    """파라미터 추출 테스트"""
    
    # 추출기 초기화
    extractor = QueryParameterExtractor()
    
    # 테스트 케이스
    test_cases = [
        # 케이스 1: 전체 아젠다 코드와 한글 조직명
        "PL25016a 한국선급 응답 현황",
        
        # 케이스 2: 영문 조직명
        "Show me Korean Register response for PL25016b",
        
        # 케이스 3: 조직 코드 직접 사용
        "KR의 PL25016c 응답 상태",
        
        # 케이스 4: 다양한 조직명 표현
        "로이드선급의 PL25016a 아젠다 검토",
        
        # 케이스 5: 미국선급 
        "ABS response for agenda PL25016a",
        
        # 케이스 6: 중국선급
        "중국선급협회 PL25016b 검토 결과",
        
        # 케이스 7: 일본선급
        "ClassNK의 PL25016c 승인 여부",
        
        # 케이스 8: 응답 코드 포함
        "PL25016aKRa 상태 확인"
    ]
    
    print("=" * 80)
    print("필수 파라미터 추출 테스트")
    print("=" * 80)
    
    for i, query in enumerate(test_cases, 1):
        print(f"\n테스트 {i}: {query}")
        print("-" * 60)
        
        # 파라미터 추출
        params = extractor.extract_parameters(query)
        
        # 필수 4개 파라미터만 표시
        required_params = {
            'agenda_base': params.get('agenda_base'),
            'agenda_base_version': params.get('agenda_base_version'),
            'organization_code': params.get('organization_code'),
            'organization': params.get('organization')
        }
        
        print("추출된 필수 파라미터:")
        for key, value in required_params.items():
            print(f"  - {key}: {value}")
        
        # 추가 정보
        print("\n기타 추출 정보:")
        other_params = {
            'agenda_code': params.get('agenda_code'),
            'response_org': params.get('response_org'),
            'normalized_query': params.get('normalized_query')
        }
        for key, value in other_params.items():
            if value:
                print(f"  - {key}: {value}")


def test_edge_cases():
    """엣지 케이스 테스트"""
    print("\n" + "=" * 80)
    print("엣지 케이스 테스트")
    print("=" * 80)
    
    extractor = QueryParameterExtractor()
    
    edge_cases = [
        # 아젠다 코드 없음
        "한국선급 응답 현황",
        
        # 조직명 없음
        "PL25016a 응답 상태",
        
        # 버전 없음
        "PL25016 KR 응답",
        
        # 여러 조직 언급
        "KR과 ABS의 PL25016a 비교",
        
        # 복잡한 표현
        "지난달 프랑스선급(BV)이 제출한 PL25016b 아젠다"
    ]
    
    for i, query in enumerate(edge_cases, 1):
        print(f"\n엣지 케이스 {i}: {query}")
        print("-" * 60)
        
        params = extractor.extract_parameters(query)
        
        required_params = {
            'agenda_base': params.get('agenda_base'),
            'agenda_base_version': params.get('agenda_base_version'),
            'organization_code': params.get('organization_code'),
            'organization': params.get('organization')
        }
        
        print("추출된 필수 파라미터:")
        for key, value in required_params.items():
            status = "✓" if value else "✗"
            print(f"  {status} {key}: {value}")


if __name__ == "__main__":
    test_parameter_extraction()
    test_edge_cases()