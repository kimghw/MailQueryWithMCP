#!/usr/bin/env python3
"""
Test 3% tolerance for similar templates
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from services.query_matcher_v3 import QueryMatcherV3

def test_tolerance():
    """Test 3% tolerance feature"""
    print("="*60)
    print("3% 유사도 허용 범위 테스트")
    print("="*60)
    
    matcher = QueryMatcherV3()
    
    # Test cases where we expect multiple results
    test_queries = [
        "Korea 응답 시간 평균",
        "KR 평균 응답 시간",
        "한국 응답 속도",
        "우리나라 답변 시간 통계",
    ]
    
    for query in test_queries:
        print(f"\n🔍 쿼리: '{query}'")
        
        primary_matches, similar_matches = matcher.find_best_matches(query, top_k=5)
        
        if primary_matches:
            top_match = primary_matches[0]
            print(f"\n📌 최고 매칭:")
            print(f"   템플릿: {top_match['template_id']}")
            print(f"   점수: {top_match['similarity']:.4f}")
            print(f"   매칭된 질문: {top_match['matched_question']}")
            
            if similar_matches:
                print(f"\n📊 3% 이내 유사 매칭 ({len(similar_matches)}개):")
                for i, match in enumerate(similar_matches):
                    score_diff = ((top_match['similarity'] - match['similarity']) / top_match['similarity']) * 100
                    print(f"\n   {i+1}. {match['template_id']}")
                    print(f"      점수: {match['similarity']:.4f} (차이: {score_diff:.1f}%)")
                    print(f"      매칭된 질문: {match['matched_question']}")
            else:
                print("\n   ℹ️ 3% 이내 유사 매칭 없음")
        else:
            print("   ❌ 매칭 결과 없음")
    
    # Test edge case with very different scores
    print("\n\n📝 극단적 케이스 테스트:")
    edge_cases = [
        "진행중인 의제 보여줘",
        "날씨 정보",
    ]
    
    for query in edge_cases:
        print(f"\n쿼리: '{query}'")
        primary_matches, similar_matches = matcher.find_best_matches(query)
        
        if primary_matches:
            print(f"최고 점수: {primary_matches[0]['similarity']:.4f}")
            print(f"3% 이내 추가 매칭: {len(similar_matches)}개")

def main():
    """Run tolerance test"""
    test_tolerance()

if __name__ == "__main__":
    main()