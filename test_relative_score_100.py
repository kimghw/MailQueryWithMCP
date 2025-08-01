#!/usr/bin/env python3
"""
100개 질의에 대한 Relative Score 계산 테스트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.common.parsers.query_parameter_extractor import QueryParameterExtractor
import json
from collections import defaultdict

def calculate_relative_score(params):
    """파라미터를 기반으로 relative_score 계산"""
    key_fields = ['organization', 'date_range', 'keywords', 'intent', 
                  'committee', 'agenda_base', 'agenda_base_version']
    
    filled_count = 0
    for field in key_fields:
        if field == 'keywords':
            # keywords는 normalized_query를 분석해서 추출 (간단한 방식)
            if params.get('normalized_query'):
                keywords = params['normalized_query'].split()
                if len(keywords) > 0:
                    filled_count += 1
        elif params.get(field) is not None:
            filled_count += 1
    
    relative_score = round((filled_count / len(key_fields)) * 0.2, 3)
    return relative_score, filled_count

def analyze_queries():
    """100개 질의 분석"""
    # QueryParameterExtractor 초기화
    extractor = QueryParameterExtractor()
    
    # 100개 테스트 케이스
    test_cases = [
        # 아젠다 관련 (15개)
        {"query": "최근 아젠다 목록 보여줘", "expected_category": "agenda"},
        {"query": "어제 등록된 아젠다 조회", "expected_category": "agenda"},
        {"query": "오늘 아젠다 뭐 있어?", "expected_category": "agenda"},
        {"query": "IMO 관련 아젠다 찾아줘", "expected_category": "agenda"},
        {"query": "한국선급 아젠다 목록", "expected_category": "agenda"},
        {"query": "긴급 아젠다 있나요?", "expected_category": "agenda"},
        {"query": "마감일 임박한 아젠다", "expected_category": "agenda"},
        {"query": "내일까지 처리해야 하는 아젠다", "expected_category": "agenda"},
        {"query": "진행중인 아젠다 보여줘", "expected_category": "agenda"},
        {"query": "완료된 아젠다 목록", "expected_category": "agenda"},
        {"query": "이번 주 아젠다 현황", "expected_category": "agenda"},
        {"query": "지난주 등록된 아젠다들", "expected_category": "agenda"},
        {"query": "의장이 만든 아젠다", "expected_category": "agenda"},
        {"query": "환경 관련 아젠다 조회", "expected_category": "agenda"},
        {"query": "안전 관련 아젠다 목록", "expected_category": "agenda"},
        
        # 메일 관련 (15개)
        {"query": "의장이 보낸 메일 목록", "expected_category": "mail"},
        {"query": "어제 받은 이메일들", "expected_category": "mail"},
        {"query": "오늘 온 메일 보여줘", "expected_category": "mail"},
        {"query": "IMO에서 온 편지", "expected_category": "mail"},
        {"query": "한국선급에서 보낸 메일", "expected_category": "mail"},
        {"query": "긴급 메일 있어?", "expected_category": "mail"},
        {"query": "읽지 않은 이메일", "expected_category": "mail"},
        {"query": "중요 표시된 메일들", "expected_category": "mail"},
        {"query": "회의 관련 메일 조회", "expected_category": "mail"},
        {"query": "승인 요청 메일들", "expected_category": "mail"},
        {"query": "이번 주 받은 메일", "expected_category": "mail"},
        {"query": "지난달 메일 통계", "expected_category": "mail"},
        {"query": "첨부파일 있는 메일", "expected_category": "mail"},
        {"query": "답장 필요한 메일들", "expected_category": "mail"},
        {"query": "전체 메일 목록 조회", "expected_category": "mail"},
        
        # 문서/문서제출 관련 (15개)
        {"query": "IMO 문서 목록", "expected_category": "document"},
        {"query": "제출된 문서 현황", "expected_category": "document"},
        {"query": "오늘 제출한 문서들", "expected_category": "document"},
        {"query": "문서 제출 마감일 확인", "expected_category": "document"},
        {"query": "한국선급 제출 문서", "expected_category": "document"},
        {"query": "미제출 문서 목록", "expected_category": "document"},
        {"query": "승인된 문서들 조회", "expected_category": "document"},
        {"query": "반려된 문서 확인", "expected_category": "document"},
        {"query": "검토중인 문서 현황", "expected_category": "document"},
        {"query": "이번 달 제출 문서", "expected_category": "document"},
        {"query": "환경 관련 제출 문서", "expected_category": "document"},
        {"query": "안전 규정 문서 목록", "expected_category": "document"},
        {"query": "기술 문서 제출 현황", "expected_category": "document"},
        {"query": "위원회별 문서 통계", "expected_category": "document"},
        {"query": "최근 업데이트된 문서", "expected_category": "document"},
        
        # 응답/의견서 관련 (10개)
        {"query": "한국선급 응답 현황", "expected_category": "response"},
        {"query": "의견서 제출 상태", "expected_category": "response"},
        {"query": "미응답 항목 조회", "expected_category": "response"},
        {"query": "오늘 제출한 의견서", "expected_category": "response"},
        {"query": "응답 대기중인 건들", "expected_category": "response"},
        {"query": "승인된 의견서 목록", "expected_category": "response"},
        {"query": "반려된 응답 확인", "expected_category": "response"},
        {"query": "이번 주 응답 통계", "expected_category": "response"},
        {"query": "위원회별 응답 현황", "expected_category": "response"},
        {"query": "긴급 응답 필요 항목", "expected_category": "response"},
        
        # 위원회/조직 관련 (10개)
        {"query": "MSC 위원회 정보", "expected_category": "committee"},
        {"query": "MEPC 회의 일정", "expected_category": "committee"},
        {"query": "위원회별 담당자 목록", "expected_category": "committee"},
        {"query": "한국선급 소속 위원", "expected_category": "committee"},
        {"query": "위원회 참석 현황", "expected_category": "committee"},
        {"query": "소위원회 구성 정보", "expected_category": "committee"},
        {"query": "위원회별 안건 통계", "expected_category": "committee"},
        {"query": "다음 회의 일정 확인", "expected_category": "committee"},
        {"query": "위원회 의장 정보", "expected_category": "committee"},
        {"query": "작업반 구성원 조회", "expected_category": "committee"},
        
        # 일정/마감일 관련 (10개)
        {"query": "오늘 일정 확인", "expected_category": "schedule"},
        {"query": "내일 예정된 회의", "expected_category": "schedule"},
        {"query": "이번 주 마감일", "expected_category": "schedule"},
        {"query": "다음 달 주요 일정", "expected_category": "schedule"},
        {"query": "연간 회의 계획", "expected_category": "schedule"},
        {"query": "마감 임박 항목들", "expected_category": "schedule"},
        {"query": "지연된 일정 확인", "expected_category": "schedule"},
        {"query": "휴일 일정 조회", "expected_category": "schedule"},
        {"query": "반복 일정 목록", "expected_category": "schedule"},
        {"query": "일정 충돌 확인", "expected_category": "schedule"},
        
        # 통계/분석 관련 (10개)
        {"query": "월별 문서 제출 통계", "expected_category": "statistics"},
        {"query": "위원회별 활동 분석", "expected_category": "statistics"},
        {"query": "응답률 통계 조회", "expected_category": "statistics"},
        {"query": "아젠다 처리 현황", "expected_category": "statistics"},
        {"query": "메일 수신 통계", "expected_category": "statistics"},
        {"query": "참여율 분석 보고", "expected_category": "statistics"},
        {"query": "연도별 실적 비교", "expected_category": "statistics"},
        {"query": "부서별 성과 지표", "expected_category": "statistics"},
        {"query": "프로젝트 진행률", "expected_category": "statistics"},
        {"query": "리스크 분석 현황", "expected_category": "statistics"},
        
        # 검색/조회 관련 (10개)
        {"query": "김철수가 작성한 문서", "expected_category": "search"},
        {"query": "환경 규제 관련 자료", "expected_category": "search"},
        {"query": "2024년 회의록 찾기", "expected_category": "search"},
        {"query": "승인 대기 항목들", "expected_category": "search"},
        {"query": "최근 변경사항 조회", "expected_category": "search"},
        {"query": "키워드로 문서 검색", "expected_category": "search"},
        {"query": "담당자별 업무 현황", "expected_category": "search"},
        {"query": "프로젝트 관련 자료", "expected_category": "search"},
        {"query": "규정 변경 이력", "expected_category": "search"},
        {"query": "참조 문서 목록", "expected_category": "search"},
        
        # 알림/리마인더 (5개)
        {"query": "오늘 알림 목록", "expected_category": "notification"},
        {"query": "마감일 리마인더", "expected_category": "notification"},
        {"query": "중요 공지사항", "expected_category": "notification"},
        {"query": "시스템 알림 확인", "expected_category": "notification"},
        {"query": "업데이트 알림", "expected_category": "notification"}
    ]
    
    # 결과 저장
    results = []
    category_stats = defaultdict(lambda: {'count': 0, 'total_score': 0, 'filled_fields': []})
    
    print("=" * 80)
    print("100개 질의에 대한 Relative Score 계산")
    print("=" * 80)
    print()
    
    for idx, test_case in enumerate(test_cases, 1):
        query = test_case['query']
        category = test_case['expected_category']
        
        # 파라미터 추출
        params = extractor.extract_parameters(query)
        
        # relative_score 계산
        score, filled_count = calculate_relative_score(params)
        
        # 결과 저장
        result = {
            'index': idx,
            'query': query,
            'category': category,
            'relative_score': score,
            'filled_count': filled_count,
            'extracted_params': {
                'organization': params.get('organization'),
                'organization_code': params.get('organization_code'),
                'date_range': params.get('date_range'),
                'committee': params.get('committee'),
                'agenda_base': params.get('agenda_base'),
                'agenda_base_version': params.get('agenda_base_version'),
                'status': params.get('status'),
                'limit': params.get('limit')
            }
        }
        results.append(result)
        
        # 카테고리별 통계
        category_stats[category]['count'] += 1
        category_stats[category]['total_score'] += score
        category_stats[category]['filled_fields'].append(filled_count)
        
        # 상세 출력 (처음 5개와 마지막 5개만)
        if idx <= 5 or idx > 95:
            print(f"[{idx:3d}] {query}")
            print(f"      Score: {score} (필드: {filled_count}/7)")
            if params.get('organization'):
                print(f"      - organization: {params['organization']}")
            if params.get('committee'):
                print(f"      - committee: {params['committee']}")
            if params.get('date_range'):
                print(f"      - date_range: 있음")
            if params.get('status'):
                print(f"      - status: {params['status']}")
            print()
    
    # 카테고리별 통계 출력
    print("\n" + "=" * 80)
    print("카테고리별 Relative Score 통계")
    print("=" * 80)
    print(f"{'카테고리':<15} {'쿼리수':>8} {'평균점수':>10} {'평균필드수':>12}")
    print("-" * 80)
    
    total_queries = 0
    total_score_sum = 0
    
    for category, stats in sorted(category_stats.items()):
        avg_score = stats['total_score'] / stats['count']
        avg_fields = sum(stats['filled_fields']) / len(stats['filled_fields'])
        print(f"{category:<15} {stats['count']:>8} {avg_score:>10.3f} {avg_fields:>12.1f}")
        total_queries += stats['count']
        total_score_sum += stats['total_score']
    
    print("-" * 80)
    overall_avg = total_score_sum / total_queries
    print(f"{'전체':<15} {total_queries:>8} {overall_avg:>10.3f}")
    
    # Score 분포 분석
    print("\n" + "=" * 80)
    print("Relative Score 분포")
    print("=" * 80)
    
    score_distribution = defaultdict(int)
    for result in results:
        score_range = f"{result['relative_score']:.3f}"
        score_distribution[score_range] += 1
    
    for score, count in sorted(score_distribution.items()):
        bar = '█' * (count // 2) if count > 0 else ''
        print(f"Score {score}: {count:3d} {bar}")
    
    # 결과를 JSON 파일로 저장 (datetime 객체를 문자열로 변환)
    json_results = []
    for result in results:
        json_result = result.copy()
        if json_result['extracted_params'].get('date_range'):
            # datetime 객체를 문자열로 변환
            date_range = json_result['extracted_params']['date_range']
            if isinstance(date_range, dict):
                if 'start' in date_range:
                    date_range['start'] = str(date_range['start'])
                if 'end' in date_range:
                    date_range['end'] = str(date_range['end'])
        json_results.append(json_result)
    
    output_data = {
        'total_queries': len(test_cases),
        'results': json_results,
        'category_statistics': {k: {'count': v['count'], 'total_score': v['total_score'], 
                                   'avg_score': v['total_score'] / v['count'],
                                   'avg_fields': sum(v['filled_fields']) / len(v['filled_fields'])}
                               for k, v in category_stats.items()},
        'overall_average_score': overall_avg,
        'score_distribution': dict(score_distribution)
    }
    
    with open('relative_score_analysis.json', 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n결과가 'relative_score_analysis.json'에 저장되었습니다.")
    
    return results

if __name__ == "__main__":
    analyze_queries()