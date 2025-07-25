#!/usr/bin/env python3
"""Test with real-world queries"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from qdrant_client import QdrantClient
import requests
from dotenv import load_dotenv
import sqlite3

load_dotenv()

class RealQueryTester:
    def __init__(self):
        self.qdrant_client = QdrantClient(url='localhost', port=6333)
        self.collection_name = "query_templates_unified"
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.db_path = 'data/iacsgraph.db'
        
    def get_embedding(self, text: str) -> List[float]:
        """Get embedding for text"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        response = requests.post(
            "https://api.openai.com/v1/embeddings",
            headers=headers,
            json={"input": text, "model": "text-embedding-3-large"}
        )
        response.raise_for_status()
        return response.json()['data'][0]['embedding']
    
    def search_and_execute(self, query: str) -> Dict:
        """Search template and simulate SQL execution"""
        # Search in Qdrant
        embedding = self.get_embedding(query)
        results = self.qdrant_client.search(
            collection_name=self.collection_name,
            query_vector=embedding,
            limit=3
        )
        
        if not results:
            return {'query': query, 'success': False, 'error': 'No matching template found'}
        
        top_result = results[0]
        template_id = top_result.payload.get('template_id', '')
        category = top_result.payload.get('template_category', '')
        score = top_result.score
        sql_query = top_result.payload.get('sql_query', '')
        
        # Get template details from SQL DB
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM query_templates WHERE template_id = ? AND template_version = 'unified'",
            (template_id,)
        )
        template_data = cursor.fetchone()
        conn.close()
        
        return {
            'query': query,
            'matched_template': template_id,
            'category': category,
            'score': score,
            'sql_template': sql_query[:200] + '...' if len(sql_query) > 200 else sql_query,
            'success': score > 0.4  # Threshold for success
        }

def main():
    print("=" * 80)
    print("🌐 실제 사용 시나리오 테스트")
    print("=" * 80)
    
    tester = RealQueryTester()
    
    # Real-world test queries
    real_queries = [
        # 조직 관련 질의
        "한국선급이 아직 응답하지 않은 진행중인 의제 보여줘",
        "Bureau Veritas의 평균 응답 시간은 얼마나 되나요?",
        "중국선급이 최근 한달간 응답한 의제 목록",
        "ABS가 응답해야 하는 긴급 의제",
        
        # 시간 기반 질의
        "지난 3개월 동안 논의된 모든 의제",
        "이번달에 발행된 SDTP 패널 의제",
        "어제 업데이트된 응답 내용",
        "올해 완료된 의제 통계",
        
        # 의제 상태 관련
        "현재 진행중인 모든 의제 리스트",
        "마감일이 3일 이내인 긴급 의제",
        "완료되지 않은 의제들 중 마감일이 지난 것",
        "오늘까지 응답해야 하는 의제",
        
        # 키워드 검색
        "사이버 보안 관련 최근 논의",
        "autonomous ship에 대한 의제 검색",
        "IMO 규정 관련 진행중인 논의",
        "디지털 전환 키워드가 포함된 의제",
        
        # 패널별 조회
        "SDTP 패널에서 한국선급이 응답해야 하는 의제",
        "EG 패널의 현재 진행 상황",
        "PL 패널에서 최근 발행된 의제",
        "UR 개정과 관련된 모든 의제",
        
        # 통계 및 분석
        "각 조직별 응답률 통계",
        "패널별 의제 발행 현황",
        "최근 3개월간 가장 많이 논의된 키워드",
        "월별 의제 처리 현황",
        
        # 특정 의제 조회
        "PL25016a 의제의 현재 상태",
        "UR A1 개정안 진행 상황",
        "PR123 의제에 대한 각 기관 응답",
        
        # 프로젝트 팀
        "현재 활동중인 프로젝트 팀 목록",
        "완료된 PT의 결과 보고서",
        "PT 멤버 구성 현황",
        
        # 회의 관련
        "다음 주 예정된 회의 일정",
        "최근 회의 공지 메일",
        "회의 참석 예정자 명단"
    ]
    
    # Execute tests
    results = []
    success_count = 0
    
    for i, query in enumerate(real_queries):
        print(f"\n[{i+1}/{len(real_queries)}] 질의: '{query}'")
        result = tester.search_and_execute(query)
        results.append(result)
        
        if result['success']:
            success_count += 1
            print(f"✅ 매칭: {result['matched_template']} (score: {result['score']:.3f})")
            print(f"   카테고리: {result['category']}")
            print(f"   SQL: {result['sql_template']}")
        else:
            print(f"❌ 매칭 실패 또는 낮은 점수")
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 테스트 결과 요약")
    print("=" * 80)
    
    print(f"\n전체 성공률: {success_count/len(real_queries):.1%} ({success_count}/{len(real_queries)})")
    
    # Category analysis
    category_stats = {}
    for result in results:
        if result['success']:
            cat = result['category']
            category_stats[cat] = category_stats.get(cat, 0) + 1
    
    print("\n매칭된 카테고리 분포:")
    for cat, count in sorted(category_stats.items(), key=lambda x: x[1], reverse=True):
        print(f"  - {cat}: {count}회")
    
    # Failed queries
    failed = [r for r in results if not r['success']]
    if failed:
        print(f"\n실패한 질의 ({len(failed)}개):")
        for f in failed[:5]:  # Show first 5
            print(f"  - '{f['query']}'")

if __name__ == "__main__":
    main()