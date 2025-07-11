#!/usr/bin/env python3
"""Debug vector search and template matching"""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

def debug_vector_search():
    """Debug why vector search is not matching"""
    
    print("🔍 Debugging Vector Search")
    print("=" * 50)
    
    from modules.query_assistant import QueryAssistant
    from sentence_transformers import SentenceTransformer
    import numpy as np
    
    # Initialize components
    db_path = os.getenv("DATABASE_PATH", "./data/iacsgraph.db")
    if not Path(db_path).is_absolute():
        db_path = str(project_root / db_path)
    
    qa = QueryAssistant(
        db_path=db_path,
        qdrant_url="localhost",
        qdrant_port=6333
    )
    
    # Test queries
    test_queries = [
        "KR 기관의 응답률은 어떻게 되나요?",
        "KR 응답률",
        "최근 7일 주요 아젠다는 무엇인가?",
        "미결정 아젠다는 무엇인가요?",
        "아젠다 목록"
    ]
    
    # Get the encoder
    encoder = qa.vector_store.encoder
    
    print("\n📝 Templates in Qdrant:")
    # Get all templates
    from modules.query_assistant.templates import get_templates
    templates = get_templates()
    
    for i, template in enumerate(templates[:5]):
        print(f"\n{i+1}. Template ID: {template.id}")
        print(f"   Natural Query: {template.natural_query}")
        print(f"   Keywords: {template.keywords}")
        
    print("\n\n🧪 Testing Vector Matching:")
    
    for query in test_queries:
        print(f"\n Query: '{query}'")
        
        # Get query expansion
        expansion = qa.keyword_expander.expand_query(query)
        print(f"   Original keywords: {expansion.original_keywords}")
        print(f"   Expanded keywords: {expansion.expanded_keywords[:10]}")
        
        # Search
        results = qa.vector_store.search(
            query=query,
            keywords=expansion.expanded_keywords,
            limit=3,
            score_threshold=0.0  # Lower threshold to see all results
        )
        
        if results:
            print(f"   Found {len(results)} matches:")
            for j, result in enumerate(results):
                print(f"     {j+1}. {result.template.natural_query} (score: {result.score:.3f})")
                print(f"        Keywords matched: {result.keyword_matches}")
        else:
            print("   ❌ No matches found!")
            
            # Manual vector similarity check
            print("   Manual similarity check:")
            query_text = f"{query} {' '.join(expansion.expanded_keywords)}"
            query_vec = encoder.encode(query_text)
            
            for template in templates[:3]:
                template_text = f"{template.natural_query} {' '.join(template.keywords)}"
                template_vec = encoder.encode(template_text)
                
                # Cosine similarity
                similarity = np.dot(query_vec, template_vec) / (np.linalg.norm(query_vec) * np.linalg.norm(template_vec))
                print(f"     - {template.natural_query[:50]}... : {similarity:.3f}")

def check_qdrant_data():
    """Check what's actually in Qdrant"""
    
    print("\n\n🔍 Checking Qdrant Collection Data")
    print("=" * 50)
    
    import requests
    
    # Get collection info
    response = requests.get("http://localhost:6333/collections/iacsgraph_queries")
    data = response.json()
    
    if 'result' in data:
        print(f"Collection: {data['result']['config']['params']}")
        print(f"Vectors count: {data['result']['vectors_count']}")
        print(f"Points count: {data['result']['points_count']}")
    
    # Scroll through points
    response = requests.post(
        "http://localhost:6333/collections/iacsgraph_queries/points/scroll",
        json={"limit": 5, "with_payload": True, "with_vector": False}
    )
    
    if response.status_code == 200:
        points_data = response.json()
        if 'result' in points_data and 'points' in points_data['result']:
            print(f"\nStored points: {len(points_data['result']['points'])}")
            for point in points_data['result']['points'][:3]:
                print(f"\nPoint ID: {point['id']}")
                payload = point.get('payload', {})
                print(f"  Natural query: {payload.get('natural_query', 'N/A')}")
                print(f"  Keywords: {payload.get('keywords', [])[:5]}")

if __name__ == "__main__":
    try:
        debug_vector_search()
        check_qdrant_data()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()