#!/usr/bin/env python3
"""Comprehensive test for all 174 templates"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple
import random
from datetime import datetime
import sqlite3

sys.path.insert(0, str(Path(__file__).parent))

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
import requests
from dotenv import load_dotenv

load_dotenv()

class TemplateTestSuite:
    def __init__(self):
        self.qdrant_client = QdrantClient(url='localhost', port=6333)
        self.collection_name = "query_templates_unified"
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.embedding_url = "https://api.openai.com/v1/embeddings"
        self.embedding_model = "text-embedding-3-large"
        
        # Load templates from file
        template_path = Path("modules/query_assistant/templates_v2/query_templates_unified.json")
        with open(template_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.templates = data.get('templates', [])
        
        # Group templates by category
        self.templates_by_category = {}
        for template in self.templates:
            if template.get('template_id', '').startswith('_config'):
                continue
            category = template.get('template_category', 'unknown')
            if category not in self.templates_by_category:
                self.templates_by_category[category] = []
            self.templates_by_category[category].append(template)
    
    def get_embedding(self, text: str) -> List[float]:
        """Get embedding for text"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "input": text,
            "model": self.embedding_model
        }
        response = requests.post(self.embedding_url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()['data'][0]['embedding']
    
    def search_templates(self, query: str, limit: int = 3) -> List[Dict]:
        """Search templates using Qdrant"""
        embedding = self.get_embedding(query)
        results = self.qdrant_client.search(
            collection_name=self.collection_name,
            query_vector=embedding,
            limit=limit
        )
        return results
    
    def test_category(self, category: str, test_queries: List[str]) -> Dict:
        """Test a specific category with given queries"""
        results = {
            'category': category,
            'template_count': len(self.templates_by_category.get(category, [])),
            'test_count': len(test_queries),
            'success_count': 0,
            'details': []
        }
        
        for query in test_queries:
            search_results = self.search_templates(query)
            
            # Check if top result is from expected category
            top_result = search_results[0] if search_results else None
            if top_result:
                matched_category = top_result.payload.get('template_category', '')
                matched_id = top_result.payload.get('template_id', '')
                score = top_result.score
                
                # Success if category matches or score is very high
                is_success = matched_category == category or score > 0.85
                if is_success:
                    results['success_count'] += 1
                
                results['details'].append({
                    'query': query,
                    'expected_category': category,
                    'matched_template': matched_id,
                    'matched_category': matched_category,
                    'score': score,
                    'success': is_success
                })
            else:
                results['details'].append({
                    'query': query,
                    'expected_category': category,
                    'matched_template': 'None',
                    'matched_category': 'None',
                    'score': 0,
                    'success': False
                })
        
        results['success_rate'] = results['success_count'] / results['test_count'] if results['test_count'] > 0 else 0
        return results

def main():
    print("=" * 80)
    print("🧪 174개 템플릿 포괄적 테스트")
    print("=" * 80)
    
    tester = TemplateTestSuite()
    
    # Define test cases for each major category
    test_cases = {
        'agenda_status': [
            "진행중인 의제 목록 보여줘",
            "완료되지 않은 의제들",
            "ongoing 상태의 아젠다",
            "오늘 마감인 의제",
            "마감일 임박한 의제들"
        ],
        'organization_response': [
            "한국선급이 응답하지 않은 의제",
            "KR이 응답해야 하는 의제 목록",
            "Bureau Veritas 미응답 의제",
            "중국선급 응답 현황",
            "ABS가 아직 답변 안한 의제"
        ],
        'agenda_statistics': [
            "조직별 평균 응답 시간",
            "KR 평균 응답 소요일",
            "월별 의제 통계",
            "연간 의제 발행 수",
            "패널별 의제 수"
        ],
        'time_based_query': [
            "최근 3개월 논의 의제",
            "이번달 발행된 의제",
            "어제 들어온 메일",
            "지난주 업데이트된 응답",
            "올해 논의된 의제들"
        ],
        'keyword_analysis': [
            "사이버 보안 관련 의제",
            "autonomous ship 키워드 분석",
            "디지털 전환 관련 논의",
            "IMO 관련 의제들",
            "최근 3개월 주요 키워드"
        ],
        'panel_specific': [
            "SDTP 패널 의제 목록",
            "EG 패널 진행 상황",
            "PL 패널 최근 논의",
            "UR 개정 관련 의제",
            "PR 개정 진행 상황"
        ],
        'agenda_search': [
            "PL25016a 의제 내용",
            "특정 의제 검색",
            "키워드로 의제 찾기",
            "제목에 'safety' 포함된 의제",
            "2025년 발행 의제 검색"
        ],
        'project_team': [
            "진행중인 PT 리스트",
            "완료된 프로젝트 팀",
            "PT 참여 멤버 조회",
            "프로젝트 팀 현황",
            "PT 관련 문서"
        ],
        'meeting_info': [
            "다음 미팅 일정",
            "회의 참석자 명단",
            "미팅 공지 메일",
            "회의 안건 확인",
            "참석 예정 회의"
        ],
        'data_quality': [
            "이메일 주소 불일치 확인",
            "데이터 오류 검증",
            "sender 정보 확인",
            "중복 데이터 체크",
            "데이터 품질 현황"
        ]
    }
    
    # Run tests
    all_results = []
    total_tests = 0
    total_success = 0
    
    print(f"\n📋 테스트할 카테고리: {len(test_cases)}개")
    print(f"📋 전체 템플릿 수: {len(tester.templates)}개")
    print(f"📋 카테고리별 분포:")
    for category, templates in sorted(tester.templates_by_category.items()):
        print(f"   - {category}: {len(templates)}개")
    
    print("\n" + "=" * 80)
    print("테스트 시작...")
    print("=" * 80)
    
    for category, queries in test_cases.items():
        print(f"\n🔍 Testing category: {category}")
        result = tester.test_category(category, queries)
        all_results.append(result)
        
        total_tests += result['test_count']
        total_success += result['success_count']
        
        print(f"   ✅ Success rate: {result['success_rate']:.1%} ({result['success_count']}/{result['test_count']})")
        
        # Show failed cases
        failed = [d for d in result['details'] if not d['success']]
        if failed:
            print("   ❌ Failed cases:")
            for f in failed[:2]:  # Show first 2 failures
                print(f"      - Query: '{f['query']}'")
                print(f"        Expected: {f['expected_category']}, Got: {f['matched_category']} ({f['score']:.3f})")
    
    # Summary report
    print("\n" + "=" * 80)
    print("📊 테스트 결과 요약")
    print("=" * 80)
    
    print(f"\n전체 성공률: {total_success/total_tests:.1%} ({total_success}/{total_tests})")
    
    print("\n카테고리별 성공률:")
    for result in sorted(all_results, key=lambda x: x['success_rate'], reverse=True):
        status = "🟢" if result['success_rate'] >= 0.8 else "🟡" if result['success_rate'] >= 0.6 else "🔴"
        print(f"{status} {result['category']:25s}: {result['success_rate']:6.1%} ({result['success_count']}/{result['test_count']})")
    
    # Random template test
    print("\n" + "=" * 80)
    print("🎲 무작위 템플릿 테스트 (10개)")
    print("=" * 80)
    
    random_templates = random.sample([t for t in tester.templates if not t.get('template_id', '').startswith('_config')], 10)
    
    for template in random_templates:
        template_id = template.get('template_id', '')
        questions = template.get('query_info', {}).get('natural_questions', [])
        
        if questions:
            test_query = questions[0]
            results = tester.search_templates(test_query)
            
            if results and results[0].payload.get('template_id') == template_id:
                print(f"✅ {template_id}: 정확히 매칭됨 (score: {results[0].score:.3f})")
            else:
                matched_id = results[0].payload.get('template_id') if results else 'None'
                print(f"❌ {template_id}: 다른 템플릿 매칭됨 ({matched_id})")
                print(f"   Query: {test_query}")

if __name__ == "__main__":
    main()