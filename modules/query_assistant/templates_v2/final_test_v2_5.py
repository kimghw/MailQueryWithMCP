#!/usr/bin/env python3
"""
Final comprehensive test for v2.5 templates with synonyms
"""
import os
import json
import requests
from qdrant_client import QdrantClient
from collections import defaultdict
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from services.synonym_processor import synonym_processor

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SIMILARITY_THRESHOLD = 0.5

class FinalTestV25:
    def __init__(self):
        self.client = QdrantClient("localhost", port=6333, check_compatibility=False)
        self.collection_name = "query_templates_v2_5"
        
        # Comprehensive test queries
        self.test_queries = [
            # Korean organization variations
            ("우리가 회신해야 할 아젠다", "kr_response_required_v2"),
            ("우리나라가 응답해야 하는 의제", "kr_response_required_v2"),
            ("한국이 답변해야 할 안건", "kr_response_required_v2"),
            ("대한민국 미응답 의제", "kr_no_response_ongoing_v2"),
            ("Korea 응답 시간 평균", "kr_avg_response_time_v2"),
            
            # Time-based queries
            ("어제 온 메일", "flexible_time_range_activities_v2"),
            ("오늘 받은 이메일", "flexible_time_range_activities_v2"),
            ("금일 마감인 아젠다", "flexible_ongoing_deadline_agendas_v2"),
            ("마감일 임박한 안건", "flexible_ongoing_deadline_agendas_v2"),
            ("긴급 마감 의제", "flexible_ongoing_deadline_agendas_v2"),
            
            # Status queries
            ("진행중인 의제 보여줘", "flexible_ongoing_deadline_agendas_v2"),
            ("ongoing 상태 아젠다", "flexible_ongoing_deadline_agendas_v2"),
            ("미완료 안건들", "all_panels_incomplete_agendas_v2"),
            
            # Keyword searches
            ("IMO 관련 의제", "imo_related_agendas_v2"),
            ("cyber 키워드 아젠다", "cyber_keyword_agendas_v2"),
            ("디지털 전환 관련 논의", "digital_transformation_agendas_v2"),
            
            # Statistics
            ("보류중인 메일 개수", "pending_agenda_count_v2"),
            ("기관별 메일 발송 통계", "org_mail_count_v2"),
            ("올해 들어온 의제 수", "yearly_agenda_count_v2"),
            
            # Complex queries
            ("최근 3개월간 논의된 의제", "all_panels_recent_3months_v2"),
            ("KR 응답 필요 의제의 타기관 의견", "kr_agenda_issues_summary_v2"),
            
            # Negative tests (should be filtered)
            ("날씨 정보", None),
            ("주식 시세", None),
            ("오늘 점심 메뉴", None),
            ("축구 경기 결과", None),
        ]
    
    def get_embedding(self, text):
        """Get embedding from OpenAI"""
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "text-embedding-3-large",
            "input": text
        }
        
        response = requests.post(
            "https://api.openai.com/v1/embeddings",
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        
        return response.json()['data'][0]['embedding']
    
    def search_query(self, query):
        """Search with synonym normalization"""
        # Normalize query
        normalized_query = synonym_processor.normalize_query(query)
        
        # Try both original and normalized
        best_result = None
        best_score = 0
        best_top3 = []
        used_query = query
        
        for test_query in [query, normalized_query] if normalized_query != query else [query]:
            query_embedding = self.get_embedding(test_query)
            
            search_results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=3,
                with_payload=True
            )
            
            if search_results and search_results[0].score > best_score:
                best_result = search_results[0]
                best_score = search_results[0].score
                best_top3 = [(r.payload.get("template_id"), r.score) for r in search_results[:3]]
                used_query = test_query
        
        if best_score < SIMILARITY_THRESHOLD:
            return None, best_score, best_top3, normalized_query
        
        template_id = best_result.payload.get("template_id") if best_result else None
        return template_id, best_score, best_top3, normalized_query
    
    def run_test(self):
        """Run comprehensive test"""
        print("\n" + "="*80)
        print("v2.5 최종 종합 테스트")
        print("="*80)
        print(f"총 테스트 케이스: {len(self.test_queries)}개")
        print(f"임계값: {SIMILARITY_THRESHOLD}")
        
        results = defaultdict(list)
        correct = 0
        
        for i, (query, expected) in enumerate(self.test_queries):
            template_id, score, top_3, normalized = self.search_query(query)
            
            success = template_id == expected
            if success:
                correct += 1
                results['correct'].append({
                    'query': query,
                    'expected': expected,
                    'score': score,
                    'normalized': normalized if normalized != query else None
                })
            elif expected is None and template_id is None:
                correct += 1
                results['correctly_filtered'].append({
                    'query': query,
                    'best_score': score,
                    'reason': 'Below threshold'
                })
            elif expected is None and template_id is not None:
                results['false_positive'].append({
                    'query': query,
                    'actual': template_id,
                    'score': score
                })
            else:
                results['wrong'].append({
                    'query': query,
                    'expected': expected,
                    'actual': template_id,
                    'score': score,
                    'normalized': normalized if normalized != query else None,
                    'top_3': top_3
                })
            
            # Progress indicator
            if (i + 1) % 5 == 0:
                print(f"진행중: {i+1}/{len(self.test_queries)}")
        
        # Calculate statistics
        accuracy = correct / len(self.test_queries)
        
        # Print results
        print(f"\n📊 최종 결과:")
        print(f"- 전체 정확도: {accuracy:.1%} ({correct}/{len(self.test_queries)})")
        print(f"- 정확한 매칭: {len(results['correct'])}개")
        print(f"- 올바른 필터링: {len(results['correctly_filtered'])}개")
        print(f"- 잘못된 매칭: {len(results['wrong'])}개")
        print(f"- 오탐지: {len(results['false_positive'])}개")
        
        # Category breakdown
        print("\n📂 카테고리별 성공률:")
        categories = {
            "조직 관련": ["우리", "한국", "대한민국", "Korea", "KR"],
            "시간 관련": ["어제", "오늘", "금일", "마감"],
            "상태 관련": ["진행중", "ongoing", "미완료"],
            "키워드 검색": ["IMO", "cyber", "디지털"],
            "통계": ["개수", "통계", "평균"],
        }
        
        for cat_name, keywords in categories.items():
            cat_results = [r for r in results['correct'] if any(kw in r['query'] for kw in keywords)]
            print(f"- {cat_name}: {len(cat_results)}개 성공")
        
        # Show failures if any
        if results['wrong']:
            print("\n❌ 실패한 케이스:")
            for r in results['wrong']:
                print(f"- '{r['query']}' → {r['actual']} (기대: {r['expected']})")
        
        if results['false_positive']:
            print("\n⚠️ 오탐지 케이스:")
            for r in results['false_positive']:
                print(f"- '{r['query']}' → {r['actual']} (점수: {r['score']:.3f})")
        
        # Save results
        with open('final_test_results_v2_5.json', 'w', encoding='utf-8') as f:
            json.dump({
                'accuracy': accuracy,
                'total_tests': len(self.test_queries),
                'correct': correct,
                'threshold': SIMILARITY_THRESHOLD,
                'results': dict(results)
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 결과가 final_test_results_v2_5.json에 저장되었습니다.")
        
        return accuracy

if __name__ == "__main__":
    if not OPENAI_API_KEY:
        print("ERROR: OPENAI_API_KEY not set")
        exit(1)
    
    tester = FinalTestV25()
    accuracy = tester.run_test()