#!/usr/bin/env python3
"""Initialize Query Assistant with existing Qdrant instance"""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

def main():
    """Initialize Query Assistant and create necessary collections"""
    
    print("🚀 Initializing Query Assistant")
    print("=" * 50)
    
    # Check Qdrant
    import requests
    try:
        response = requests.get("http://localhost:6333/")
        if response.status_code == 200:
            qdrant_info = response.json()
            print(f"✅ Qdrant is running (version: {qdrant_info.get('version', 'unknown')})")
            
            # Check collections
            collections_response = requests.get("http://localhost:6333/collections")
            collections_data = collections_response.json()
            existing_collections = [c['name'] for c in collections_data['result']['collections']]
            print(f"📦 Existing collections: {', '.join(existing_collections)}")
        else:
            print(f"❌ Qdrant check failed (status: {response.status_code})")
            return
    except Exception as e:
        print(f"❌ Cannot connect to Qdrant: {e}")
        return
    
    # Initialize Query Assistant
    print("\n📚 Initializing Query Assistant...")
    
    try:
        from modules.query_assistant import QueryAssistant
        
        # Get database path
        db_path = os.getenv("DATABASE_PATH", "./data/iacsgraph.db")
        if not Path(db_path).is_absolute():
            db_path = str(project_root / db_path)
        
        print(f"📊 Using database: {db_path}")
        
        # Create Query Assistant instance
        qa = QueryAssistant(
            db_path=db_path,
            qdrant_url="localhost",
            qdrant_port=6333
        )
        
        print("✅ Query Assistant initialized successfully!")
        print("✅ Templates indexed in Qdrant")
        
        # Verify collection was created
        collections_response = requests.get("http://localhost:6333/collections")
        collections_data = collections_response.json()
        new_collections = [c['name'] for c in collections_data['result']['collections']]
        
        if 'iacsgraph_queries' in new_collections:
            print("✅ Collection 'iacsgraph_queries' created successfully!")
            
            # Get collection info
            collection_info = requests.get("http://localhost:6333/collections/iacsgraph_queries")
            info_data = collection_info.json()
            if 'result' in info_data:
                vectors_count = info_data['result'].get('vectors_count', 0)
                print(f"📊 Indexed templates: {vectors_count}")
        
        # Test a query
        print("\n🧪 Testing a sample query...")
        result = qa.process_query("최근 7일 주요 아젠다는?", execute=False)
        
        if result.error:
            print(f"❌ Query test failed: {result.error}")
        else:
            print("✅ Query test passed!")
            print(f"   Template ID: {result.query_id}")
            print(f"   SQL generated: {result.executed_sql[:100]}...")
        
        print("\n✅ Query Assistant is ready to use!")
        print("\n📝 Next steps:")
        print("1. Run web interface: python scripts/run_query_assistant_web.py")
        print("2. Or use MCP server: python scripts/run_query_assistant.py")
        
    except Exception as e:
        print(f"❌ Error initializing Query Assistant: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()