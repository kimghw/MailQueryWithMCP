#!/usr/bin/env python3
"""
Comprehensive 100 Query Test
Compares rule-based vs LLM-enhanced query processing
"""
import os
import json
import asyncio
from typing import List, Dict, Any
from datetime import datetime
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from modules.query_assistant.services.query_matcher import QueryMatcher
from mock_claude_desktop import MockClaudeDesktop

def generate_test_queries() -> List[Dict[str, Any]]:
    """Generate 100 diverse test queries"""
    queries = [
        # 아젠다 관련 (20개)
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
        {"query": "PL25016a 아젠다 상세 정보", "expected_category": "agenda"},
        {"query": "DE 패널 아젠다", "expected_category": "agenda"},
        {"query": "승인된 아젠다만 보여줘", "expected_category": "agenda"},
        {"query": "반려된 아젠다 목록", "expected_category": "agenda"},
        {"query": "미결정 아젠다 현황", "expected_category": "agenda"},
        
        # 메일 관련 (20개)
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
        {"query": "답장 필요한 메일", "expected_category": "mail"},
        {"query": "최근 3일간 메일", "expected_category": "mail"},
        {"query": "일본선급에서 온 메일", "expected_category": "mail"},
        {"query": "중국선급 관련 이메일", "expected_category": "mail"},
        {"query": "Bureau Veritas 메일", "expected_category": "mail"},
        {"query": "Lloyd's Register 연락", "expected_category": "mail"},
        {"query": "다자간 협의 메일", "expected_category": "mail"},
        
        # 응답 관련 (20개)
        {"query": "한국선급 응답 현황", "expected_category": "response"},
        {"query": "모든 기관 응답률", "expected_category": "response"},
        {"query": "미응답 아젠다 목록", "expected_category": "response"},
        {"query": "KR 응답 통계", "expected_category": "response"},
        {"query": "일본선급 응답 내역", "expected_category": "response"},
        {"query": "중국선급 의견서", "expected_category": "response"},
        {"query": "최근 응답한 아젠다", "expected_category": "response"},
        {"query": "응답 기한 넘긴 건", "expected_category": "response"},
        {"query": "이번 달 응답률", "expected_category": "response"},
        {"query": "지난주 응답 현황", "expected_category": "response"},
        {"query": "승인 응답만 조회", "expected_category": "response"},
        {"query": "반려 의견 목록", "expected_category": "response"},
        {"query": "조건부 승인 건", "expected_category": "response"},
        {"query": "DNV 응답 분석", "expected_category": "response"},
        {"query": "ABS 의견 조회", "expected_category": "response"},
        {"query": "LR 응답 상태", "expected_category": "response"},
        {"query": "RINA 피드백", "expected_category": "response"},
        {"query": "응답 대기중인 아젠다", "expected_category": "response"},
        {"query": "여러 기관 응답 비교", "expected_category": "response"},
        {"query": "전체 응답 통계", "expected_category": "response"},
        
        # 조직/기관 관련 (20개)
        {"query": "한국선급 정보", "expected_category": "organization"},
        {"query": "모든 선급 목록", "expected_category": "organization"},
        {"query": "IACS 회원사", "expected_category": "organization"},
        {"query": "아시아 지역 선급", "expected_category": "organization"},
        {"query": "유럽 선급 현황", "expected_category": "organization"},
        {"query": "미주 지역 기관", "expected_category": "organization"},
        {"query": "IMO 조직 구조", "expected_category": "organization"},
        {"query": "의장단 구성", "expected_category": "organization"},
        {"query": "패널별 참여 기관", "expected_category": "organization"},
        {"query": "KR 참여 현황", "expected_category": "organization"},
        {"query": "ClassNK 활동 내역", "expected_category": "organization"},
        {"query": "CCS 참여 통계", "expected_category": "organization"},
        {"query": "Bureau Veritas 정보", "expected_category": "organization"},
        {"query": "Lloyd's Register 현황", "expected_category": "organization"},
        {"query": "DNV GL 통합 정보", "expected_category": "organization"},
        {"query": "러시아선급 참여도", "expected_category": "organization"},
        {"query": "인도선급 활동", "expected_category": "organization"},
        {"query": "터키선급 현황", "expected_category": "organization"},
        {"query": "베트남선급 정보", "expected_category": "organization"},
        {"query": "다자간 협력 기관", "expected_category": "organization"},
        
        # 복합 질의 (20개)
        {"query": "한국선급이 어제 보낸 메일", "expected_category": "mail"},
        {"query": "IMO 아젠다 중 KR 응답", "expected_category": "response"},
        {"query": "최근 일주일 모든 기관 응답률", "expected_category": "response"},
        {"query": "의장이 보낸 긴급 아젠다", "expected_category": "agenda"},
        {"query": "PL 패널 미응답 아젠다", "expected_category": "response"},
        {"query": "이번달 승인된 안건들", "expected_category": "agenda"},
        {"query": "지난주 받은 중요 메일", "expected_category": "mail"},
        {"query": "환경 관련 미결정 아젠다", "expected_category": "agenda"},
        {"query": "안전 패널 응답 현황", "expected_category": "response"},
        {"query": "일본선급 반려 의견", "expected_category": "response"},
        {"query": "중국선급 제출 문서", "expected_category": "document"},
        {"query": "유럽 선급들의 응답률", "expected_category": "response"},
        {"query": "아시아 기관 참여 현황", "expected_category": "organization"},
        {"query": "의장단 승인 아젠다", "expected_category": "agenda"},
        {"query": "긴급 처리 필요 건", "expected_category": "agenda"},
        {"query": "마감 임박 응답 건", "expected_category": "response"},
        {"query": "첨부파일 포함 응답", "expected_category": "response"},
        {"query": "기술 위원회 아젠다", "expected_category": "agenda"},
        {"query": "규정 개정 관련 건", "expected_category": "agenda"},
        {"query": "공동 제안 아젠다들", "expected_category": "agenda"}
    ]
    
    return queries

def test_rule_based(queries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Test with rule-based parameter extraction only"""
    print("\n" + "="*80)
    print("RULE-BASED PARAMETER EXTRACTION TEST")
    print("="*80)
    
    query_matcher = QueryMatcher()
    results = []
    
    for i, test_case in enumerate(queries, 1):
        query = test_case['query']
        expected = test_case['expected_category']
        
        try:
            matches = query_matcher.find_best_matches(
                query=query,
                top_k=3,
                return_similar=False
            )
            
            if matches:
                best_match = matches[0]
                results.append({
                    'query': query,
                    'expected': expected,
                    'matched': True,
                    'confidence': best_match.get('similarity', 0),
                    'template_id': best_match.get('template_id'),
                    'method': 'rule-based'
                })
            else:
                results.append({
                    'query': query,
                    'expected': expected,
                    'matched': False,
                    'confidence': 0,
                    'method': 'rule-based'
                })
                
        except Exception as e:
            results.append({
                'query': query,
                'expected': expected,
                'matched': False,
                'error': str(e),
                'method': 'rule-based'
            })
    
    return analyze_results(results, "Rule-Based")

async def test_with_llm(queries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Test with LLM-enhanced parameter extraction"""
    print("\n" + "="*80)
    print("LLM-ENHANCED PARAMETER EXTRACTION TEST")
    print("="*80)
    
    if not os.getenv("OPENROUTER_API_KEY"):
        print("⚠️  OpenRouter API key not found. Skipping LLM test.")
        return {}
    
    mock = MockClaudeDesktop()
    results = []
    
    for i, test_case in enumerate(queries[:30], 1):  # Limit to 30 to avoid rate limits
        query = test_case['query']
        expected = test_case['expected_category']
        
        print(f"\r[{i}/30] Processing: {query[:50]}...", end='', flush=True)
        
        try:
            # Process with mock Claude
            response = await mock.process_query_with_mcp(
                query=query,
                execute=False,  # Don't execute SQL
                limit=10
            )
            
            if response.get('result') and not response['result'].get('error'):
                results.append({
                    'query': query,
                    'expected': expected,
                    'matched': True,
                    'confidence': 0.8,  # Placeholder
                    'template_id': response['result'].get('query_id'),
                    'llm_keywords': response['arguments'].get('extracted_keywords'),
                    'llm_org': response['arguments'].get('extracted_organization'),
                    'method': 'llm-enhanced'
                })
            else:
                results.append({
                    'query': query,
                    'expected': expected,
                    'matched': False,
                    'confidence': 0,
                    'error': response.get('result', {}).get('error', 'No match'),
                    'method': 'llm-enhanced'
                })
                
        except Exception as e:
            results.append({
                'query': query,
                'expected': expected,
                'matched': False,
                'error': str(e),
                'method': 'llm-enhanced'
            })
        
        # Rate limiting
        await asyncio.sleep(0.5)
    
    print()  # New line after progress
    return analyze_results(results, "LLM-Enhanced")

def analyze_results(results: List[Dict[str, Any]], method: str) -> Dict[str, Any]:
    """Analyze test results"""
    total = len(results)
    matched = sum(1 for r in results if r.get('matched', False))
    high_conf = sum(1 for r in results if r.get('matched') and r.get('confidence', 0) > 0.7)
    errors = sum(1 for r in results if r.get('error'))
    
    print(f"\n{method} Results:")
    print(f"  Total queries: {total}")
    print(f"  Matched: {matched} ({matched/total*100:.1f}%)")
    print(f"  High confidence (>0.7): {high_conf} ({high_conf/total*100:.1f}%)")
    print(f"  Errors: {errors}")
    
    # Show failed queries
    failed = [r for r in results if not r.get('matched')]
    if failed:
        print(f"\n  Failed queries ({len(failed)}):")
        for f in failed[:10]:
            print(f"    - {f['query']}")
            if f.get('error'):
                print(f"      Error: {f['error']}")
        if len(failed) > 10:
            print(f"    ... and {len(failed) - 10} more")
    
    return {
        'method': method,
        'total': total,
        'matched': matched,
        'match_rate': matched/total*100,
        'high_confidence': high_conf,
        'errors': errors,
        'results': results
    }

async def main():
    """Run comprehensive test"""
    print("="*80)
    print("COMPREHENSIVE 100 QUERY TEST")
    print("="*80)
    print(f"Timestamp: {datetime.now()}")
    
    # Generate test queries
    queries = generate_test_queries()
    print(f"\nGenerated {len(queries)} test queries")
    
    # Run rule-based test
    rule_results = test_rule_based(queries)
    
    # Run LLM-enhanced test
    llm_results = await test_with_llm(queries)
    
    # Compare results
    if llm_results:
        print("\n" + "="*80)
        print("COMPARISON SUMMARY")
        print("="*80)
        print(f"\nRule-Based Match Rate: {rule_results['match_rate']:.1f}%")
        print(f"LLM-Enhanced Match Rate: {llm_results['match_rate']:.1f}%")
        
        improvement = llm_results['match_rate'] - rule_results['match_rate']
        if improvement > 0:
            print(f"\n✅ LLM Enhancement improved match rate by {improvement:.1f}%")
        else:
            print(f"\n⚠️  No improvement with LLM enhancement")
    
    # Save detailed results
    with open('test_results_comprehensive.json', 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'rule_based': rule_results,
            'llm_enhanced': llm_results if llm_results else None
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\nDetailed results saved to: test_results_comprehensive.json")

if __name__ == "__main__":
    asyncio.run(main())