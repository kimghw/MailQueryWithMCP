#!/usr/bin/env python3
"""
Test 100 diverse queries against the query templates
Analyze failures and low confidence matches
"""
import json
import sys
import os
from pathlib import Path
from typing import List, Dict, Any

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from modules.query_assistant.services.query_matcher import QueryMatcher
# from modules.common.services.synonym_service import SynonymService  # Not needed - QueryMatcher has its own

def generate_test_queries() -> List[Dict[str, Any]]:
    """Generate 100 diverse test queries based on database schema"""
    queries = [
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
    
    return queries

def analyze_results(test_results: List[Dict]) -> Dict[str, Any]:
    """Analyze test results and generate summary"""
    total = len(test_results)
    matched = sum(1 for r in test_results if r['matched'])
    high_confidence = sum(1 for r in test_results if r['matched'] and r['confidence'] > 0.7)
    medium_confidence = sum(1 for r in test_results if r['matched'] and 0.5 <= r['confidence'] <= 0.7)
    low_confidence = sum(1 for r in test_results if r['matched'] and r['confidence'] < 0.5)
    
    # Category accuracy
    category_stats = {}
    for result in test_results:
        category = result['expected_category']
        if category not in category_stats:
            category_stats[category] = {'total': 0, 'matched': 0, 'correct': 0}
        
        category_stats[category]['total'] += 1
        if result['matched']:
            category_stats[category]['matched'] += 1
            # Check if category matches (simplified check)
            if result['best_match']:
                # best_match contains 'category' field directly
                match_category = result['best_match'].get('category', '').lower()
                if category in match_category:
                    category_stats[category]['correct'] += 1
    
    return {
        'total_queries': total,
        'matched_queries': matched,
        'match_rate': matched / total * 100,
        'high_confidence': high_confidence,
        'medium_confidence': medium_confidence,
        'low_confidence': low_confidence,
        'unmatched': total - matched,
        'category_stats': category_stats
    }

def main():
    print("="*80)
    print("100 Query Test with Individual Question Embeddings")
    print("="*80)
    
    # Initialize services
    query_matcher = QueryMatcher()  # Uses built-in synonym service
    
    # Generate test queries
    test_queries = generate_test_queries()
    print(f"\nTesting {len(test_queries)} queries...")
    
    # Run tests
    test_results = []
    failures = []
    
    for i, test_case in enumerate(test_queries, 1):
        query = test_case['query']
        expected_category = test_case['expected_category']
        
        try:
            # Suppress debug output to avoid validation errors
            os.environ['SUPPRESS_DEBUG'] = '1'
            
            # Process query
            matches = query_matcher.find_best_matches(
                query=query,
                top_k=3,
                return_similar=False
            )
            
            # Restore debug output
            os.environ.pop('SUPPRESS_DEBUG', None)
            
            if matches and len(matches) > 0:
                best_match = matches[0]
                confidence = best_match.get('similarity', 0.0)
                
                result = {
                    'query': query,
                    'expected_category': expected_category,
                    'matched': True,
                    'confidence': confidence,
                    'best_match': best_match,
                    'keywords': best_match.get('keyword_matches', [])
                }
                
                if confidence < 0.5:
                    failures.append(result)
                    
            else:
                result = {
                    'query': query,
                    'expected_category': expected_category,
                    'matched': False,
                    'confidence': 0.0,
                    'best_match': None,
                    'keywords': []
                }
                failures.append(result)
            
            test_results.append(result)
            
            # Progress indicator
            if i % 10 == 0:
                print(f"  Processed {i}/{len(test_queries)} queries...")
                
        except Exception as e:
            print(f"Error processing query '{query}': {e}")
            test_results.append({
                'query': query,
                'expected_category': expected_category,
                'matched': False,
                'confidence': 0.0,
                'best_match': None,
                'error': str(e)
            })
    
    # Analyze results
    print("\n" + "="*80)
    print("RESULTS SUMMARY")
    print("="*80)
    
    summary = analyze_results(test_results)
    
    print(f"\nOverall Performance:")
    print(f"  Total queries: {summary['total_queries']}")
    print(f"  Matched: {summary['matched_queries']} ({summary['match_rate']:.1f}%)")
    print(f"  Unmatched: {summary['unmatched']}")
    
    print(f"\nConfidence Distribution:")
    print(f"  High (>0.7): {summary['high_confidence']}")
    print(f"  Medium (0.5-0.7): {summary['medium_confidence']}")
    print(f"  Low (<0.5): {summary['low_confidence']}")
    
    print(f"\nCategory Performance:")
    for category, stats in summary['category_stats'].items():
        match_rate = stats['matched'] / stats['total'] * 100 if stats['total'] > 0 else 0
        print(f"  {category}: {stats['matched']}/{stats['total']} ({match_rate:.1f}%)")
    
    # Show failures
    print(f"\n{'='*80}")
    print(f"FAILED OR LOW CONFIDENCE MATCHES ({len(failures)} total)")
    print(f"{'='*80}")
    
    for i, failure in enumerate(failures[:20], 1):  # Show first 20
        print(f"\n{i}. Query: \"{failure['query']}\"")
        print(f"   Expected category: {failure['expected_category']}")
        print(f"   Keywords: {failure['keywords'][:5]}")
        
        if failure['matched']:
            match = failure['best_match']
            print(f"   Matched with low confidence ({failure['confidence']:.3f}):")
            print(f"   - Template: {match.get('template_id', 'N/A')}")
            print(f"   - Question: {match.get('matched_question', 'N/A')[:100]}...")
        else:
            print(f"   No match found")
    
    # Save detailed results
    with open('test_results_individual_questions.json', 'w', encoding='utf-8') as f:
        json.dump({
            'summary': summary,
            'detailed_results': test_results,
            'failures': failures
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\nDetailed results saved to: test_results_individual_questions.json")

if __name__ == "__main__":
    main()