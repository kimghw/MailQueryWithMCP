"""Compare direct similarity calculation vs vector DB search"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from modules.query_assistant.similarity_calculator import SimilarityCalculator
from modules.query_assistant.services.vector_store_http import VectorStoreHTTP

def compare_methods():
    print("="*80)
    print("직접 유사도 계산 vs 벡터 DB 검색 비교")
    print("="*80)
    
    # Test queries
    test_queries = [
        "최근 Hull Panel 에서 논의 되고 있는 의제 목록",
        "최근 SDTP 패널에서 한국선급 응답율",
        "PL25016의 응답현황"
    ]
    
    print("\n1️⃣ 직접 유사도 계산 (OpenAI Embeddings)")
    print("-" * 60)
    
    # Initialize calculator
    calc = SimilarityCalculator()
    
    # Compare with template-like sentences
    template_sentences = [
        "최근 {panel} 에서 논의 되고 있는 의제 목록",
        "최근 {period} 발행한 의제 중 {panel} 패널에서 {organization} 응답율",
        "{agenda_code}의 응답현황"
    ]
    
    for query in test_queries:
        print(f"\n🔍 Query: '{query}'")
        for template in template_sentences:
            similarity = calc.calculate_similarity(query, template)
            if similarity > 0.5:  # Only show relevant matches
                print(f"   ✓ '{template}' → {similarity:.2%}")
    
    print("\n\n2️⃣ 벡터 DB 검색 (Qdrant에 저장된 템플릿)")
    print("-" * 60)
    
    # Initialize vector store
    vector_store = VectorStoreHTTP(
        qdrant_url="localhost",
        qdrant_port=6333
    )
    
    for query in test_queries:
        print(f"\n🔍 Query: '{query}'")
        
        # Simple keywords extraction
        keywords = query.split()
        
        try:
            # Search in vector DB
            results = vector_store.search(
                query=query,
                keywords=keywords,
                limit=2,
                score_threshold=0.3
            )
            
            if results:
                for result in results:
                    print(f"   ✓ Template ID: {result.template.template_id}")
                    print(f"     Score: {result.score:.2%}")
                    print(f"     Natural Questions: {result.template.natural_questions[:60]}...")
            else:
                print("   ❌ No matching templates in vector DB")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print("\n\n📊 요약:")
    print("-" * 60)
    print("• 직접 계산: 두 문장 간의 실시간 유사도 계산")
    print("• 벡터 DB: 사전에 저장된 템플릿과의 유사도 검색")
    print("• 직접 계산은 모든 문장 비교 가능, 벡터 DB는 저장된 템플릿만 검색 가능")

if __name__ == "__main__":
    compare_methods()