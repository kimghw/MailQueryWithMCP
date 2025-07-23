#!/usr/bin/env python3
"""
하이브리드 검색 개념 설명
"""

def explain_hybrid_search():
    """Vector DB 하이브리드 검색 방법 설명"""
    
    print("=" * 80)
    print("Vector DB 하이브리드 검색 방법")
    print("=" * 80)
    
    print("\n1. 검색 쿼리 준비:")
    print("-" * 60)
    
    # 예시 쿼리
    user_query = "한국선급의 PL25016a 승인 현황"
    
    # 추출된 파라미터 (실제로는 QueryParameterExtractor 사용)
    extracted_params = {
        'organization': '한국선급',
        'organization_code': 'KR',
        'agenda_base': 'PL25016',
        'agenda_base_version': 'a'
    }
    
    # 확장된 키워드 (실제로는 KeywordExpander 사용)
    expanded_keywords = [
        'KR', '한국선급', 'Korean Register',
        'agenda', '아젠다', '안건',
        'approved', '승인', '허가',
        'status', '현황', '상태'
    ]
    
    # 벡터 검색용 텍스트 구성
    search_text = f"{user_query} {extracted_params['organization']} {extracted_params['agenda_base']}"
    print(f"원본 쿼리: {user_query}")
    print(f"벡터 검색용 텍스트: {search_text}")
    print(f"키워드 목록: {expanded_keywords[:5]}...")
    
    print("\n2. Qdrant 검색 요청 구성:")
    print("-" * 60)
    
    # 실제 Qdrant 검색 파라미터
    search_params = {
        # 1. 벡터 검색
        "query_vector": "embedding_of(search_text)",  # 실제로는 임베딩 벡터
        
        # 2. 필터 조건 (정확한 매칭)
        "filter": {
            "must": [
                {"key": "keywords", "match": {"any": expanded_keywords}},
                # 선택적 필터
                # {"key": "organization_code", "match": {"value": "KR"}},
                # {"key": "category", "match": {"value": "response"}}
            ]
        },
        
        # 3. 검색 옵션
        "limit": 10,  # 상위 10개
        "with_payload": True,  # 메타데이터 포함
        "score_threshold": 0.3  # 최소 점수
    }
    
    print("Qdrant 검색 파라미터:")
    print(f"  - 벡터 검색: {search_text} → embedding")
    print(f"  - 키워드 필터: {expanded_keywords[:3]}...")
    print(f"  - 조직 필터: organization_code = {extracted_params['organization_code']}")
    
    print("\n3. 점수 계산 방법:")
    print("-" * 60)
    
    # 예시 검색 결과
    mock_results = [
        {
            "template_id": "T001",
            "vector_score": 0.85,
            "keywords": ["agenda", "response", "approved", "KR"],
            "matched_keywords": ["agenda", "approved", "KR"]
        },
        {
            "template_id": "T002", 
            "vector_score": 0.72,
            "keywords": ["agenda", "status", "organization"],
            "matched_keywords": ["agenda", "status"]
        },
        {
            "template_id": "T003",
            "vector_score": 0.65,
            "keywords": ["PL25016", "response", "decision", "KR"],
            "matched_keywords": ["response", "KR"]
        }
    ]
    
    print("템플릿 | 벡터점수 | 키워드매칭 | 키워드점수 | 최종점수")
    print("-" * 60)
    
    for result in mock_results:
        # 키워드 점수 계산
        keyword_score = len(result['matched_keywords']) / len(expanded_keywords[:5])
        
        # 하이브리드 점수 (벡터 60% + 키워드 40%)
        hybrid_score = (result['vector_score'] * 0.6) + (keyword_score * 0.4)
        
        print(f"{result['template_id']}    | {result['vector_score']:.2f}    | "
              f"{len(result['matched_keywords'])}/5        | {keyword_score:.2f}       | "
              f"{hybrid_score:.2f}")
    
    print("\n4. 실제 Vector DB 호출 코드:")
    print("-" * 60)
    print("""
# Qdrant 사용 예시
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchAny

client = QdrantClient(url="localhost", port=6333)

# 1. 임베딩 생성
query_embedding = get_embedding(search_text)

# 2. 하이브리드 검색
results = client.search(
    collection_name="query_templates",
    query_vector=query_embedding,
    query_filter=Filter(
        must=[
            FieldCondition(
                key="keywords",
                match=MatchAny(any=expanded_keywords)
            )
        ]
    ),
    limit=10,
    with_payload=True
)

# 3. 점수 재계산 및 정렬
final_results = []
for result in results:
    keyword_matches = set(result.payload['keywords']) & set(expanded_keywords)
    keyword_score = len(keyword_matches) / len(expanded_keywords)
    hybrid_score = (result.score * 0.6) + (keyword_score * 0.4)
    
    final_results.append({
        'template': result.payload,
        'score': hybrid_score,
        'matched_keywords': list(keyword_matches)
    })

# 최종 정렬
final_results.sort(key=lambda x: x['score'], reverse=True)
    """)
    
    print("\n5. 최적화 팁:")
    print("-" * 60)
    print("• 임베딩 생성 시 중요 키워드 반복: 'PL25016a KR PL25016a approved'")
    print("• 동의어 확장으로 매칭 확률 증가")
    print("• 필터로 불필요한 벡터 연산 감소")
    print("• 벡터/키워드 가중치는 데이터 특성에 따라 조정")
    print("• Qdrant의 payload 인덱싱으로 키워드 검색 속도 향상")


if __name__ == "__main__":
    explain_hybrid_search()