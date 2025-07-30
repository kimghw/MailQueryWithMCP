#!/usr/bin/env python3
"""
Simple test script for query similarity matching
"""
import os
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from modules.query_assistant.services.query_matcher import QueryMatcher

def test_simple_queries():
    """Test simple queries against the vector database"""
    query_matcher = QueryMatcher()
    
    test_queries = [
        "최근 아젠다 목록 보여줘",
        "한국선급 응답 현황",
        "어제 받은 이메일들", 
        "IMO 관련 문서",
        "지난주 등록된 아젠다들"
    ]
    
    print("=" * 80)
    print("Simple Query Test")
    print("=" * 80)
    
    for query in test_queries:
        print(f"\n쿼리: {query}")
        print("-" * 40)
        
        try:
            # Suppress debug output
            os.environ['SUPPRESS_DEBUG'] = '1'
            
            # Find matches
            matches = query_matcher.find_best_matches(
                query=query,
                top_k=3,
                return_similar=False
            )
            
            if matches:
                print(f"매칭된 템플릿 수: {len(matches)}")
                for i, match in enumerate(matches, 1):
                    print(f"\n  {i}. {match['template_id']}")
                    print(f"     유사도: {match['similarity']:.3f}")
                    if match.get('matched_question'):
                        print(f"     매칭된 질문: {match['matched_question']}")
            else:
                print("매칭된 템플릿이 없습니다.")
                
        except Exception as e:
            print(f"오류 발생: {e}")
            import traceback
            traceback.print_exc()
            
        finally:
            # Restore debug output
            os.environ.pop('SUPPRESS_DEBUG', None)

if __name__ == "__main__":
    test_simple_queries()