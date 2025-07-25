#!/usr/bin/env python3
"""
Test 100 queries with LLM enhancement using OpenRouter
"""
import os
import json
import asyncio
from typing import List, Dict, Any
from mock_claude_desktop import MockClaudeDesktop
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from modules.query_assistant.services.query_matcher import QueryMatcher

def generate_test_queries() -> List[Dict[str, Any]]:
    """Generate 100 diverse test queries"""
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
        
        # 메일 관련 (15개) - 첫 10개만
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
    ]
    
    return queries[:30]  # Test with 30 queries first to avoid rate limits

async def test_with_llm():
    """Test queries with LLM enhancement"""
    mock = MockClaudeDesktop()
    query_matcher = QueryMatcher()
    test_queries = generate_test_queries()
    
    print("="*80)
    print("100 Query Test with LLM Enhancement (OpenRouter)")
    print("="*80)
    print(f"\nTesting {len(test_queries)} queries...")
    
    results = []
    
    for i, test_case in enumerate(test_queries, 1):
        query = test_case['query']
        expected_category = test_case['expected_category']
        
        print(f"\n[{i}/{len(test_queries)}] {query}")
        
        try:
            # Analyze with LLM
            analysis = await mock.analyze_query(query)
            keywords = analysis.get('keywords', [])
            parameters = analysis.get('parameters', {})
            
            print(f"  LLM Keywords: {keywords[:5]}")
            print(f"  LLM Parameters: {parameters}")
            
            # Override parameter extractor with LLM results
            original_extract = query_matcher.parameter_extractor.extract_parameters
            query_matcher.parameter_extractor.extract_parameters = lambda q: {
                "keywords": keywords,
                **parameters
            }
            
            # Find matches
            matches = query_matcher.find_best_matches(
                query=query,
                top_k=3,
                return_similar=False
            )
            
            # Restore original
            query_matcher.parameter_extractor.extract_parameters = original_extract
            
            if matches:
                best_match = matches[0]
                result = {
                    'query': query,
                    'expected_category': expected_category,
                    'matched': True,
                    'confidence': best_match.get('similarity', 0),
                    'template_id': best_match.get('template_id'),
                    'llm_keywords': keywords,
                    'llm_parameters': parameters
                }
                print(f"  ✓ Match: {best_match.get('template_id')} ({best_match.get('similarity', 0):.3f})")
            else:
                result = {
                    'query': query,
                    'expected_category': expected_category,
                    'matched': False,
                    'confidence': 0,
                    'llm_keywords': keywords,
                    'llm_parameters': parameters
                }
                print(f"  ✗ No match found")
                
            results.append(result)
            
            # Rate limiting for OpenRouter
            await asyncio.sleep(0.5)
            
        except Exception as e:
            print(f"  Error: {e}")
            results.append({
                'query': query,
                'expected_category': expected_category,
                'matched': False,
                'error': str(e)
            })
    
    # Summary
    print("\n" + "="*80)
    print("RESULTS SUMMARY")
    print("="*80)
    
    total = len(results)
    matched = sum(1 for r in results if r.get('matched', False))
    high_conf = sum(1 for r in results if r.get('matched') and r.get('confidence', 0) > 0.7)
    
    print(f"\nTotal queries: {total}")
    print(f"Matched: {matched} ({matched/total*100:.1f}%)")
    print(f"High confidence (>0.7): {high_conf}")
    
    # Compare with/without LLM
    print("\n" + "="*80)
    print("LLM IMPACT ANALYSIS")
    print("="*80)
    
    with_keywords = sum(1 for r in results if r.get('llm_keywords'))
    with_params = sum(1 for r in results if r.get('llm_parameters'))
    
    print(f"\nQueries with LLM keywords: {with_keywords}/{total}")
    print(f"Queries with LLM parameters: {with_params}/{total}")
    
    # Save results
    with open('test_results_with_llm.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\nDetailed results saved to: test_results_with_llm.json")

if __name__ == "__main__":
    if not os.getenv("OPENROUTER_API_KEY"):
        print("Please add OPENROUTER_API_KEY to your .env file")
        print("Get your API key from: https://openrouter.ai/keys")
        print("\nExample .env file:")
        print("OPENROUTER_API_KEY=sk-or-v1-xxxxx")
        exit(1)
    
    asyncio.run(test_with_llm())