#!/usr/bin/env python3
"""Migrate from sentence-transformers to OpenAI embeddings"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from qdrant_client import QdrantClient

# Load environment variables from .env file
load_dotenv()

def migrate_to_openai():
    """Check and prepare for OpenAI migration"""
    print("🔄 Preparing for OpenAI Embeddings Migration")
    print("=" * 60)
    
    # Check OpenAI API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("\n❌ OPENAI_API_KEY not found!")
        print("\nTo use OpenAI embeddings, you need to:")
        print("1. Get an API key from https://platform.openai.com/api-keys")
        print("2. Edit your .env file and uncomment/update the OPENAI_API_KEY line:")
        print("   # Current: # OPENAI_API_KEY=your-openai-api-key-here")
        print("   # Change to: OPENAI_API_KEY=sk-proj-your-actual-key-here")
        print("\n📝 The .env file is located at: /home/kimghw/IACSGRAPH/.env")
        print("\nAlternatively, set it as an environment variable:")
        print("   export OPENAI_API_KEY='your-api-key-here'")
        return False
    
    print("✅ OpenAI API key found")
    
    # Check Qdrant collections
    print("\n🔍 Checking Qdrant collections...")
    try:
        client = QdrantClient(host="localhost", port=6333, check_compatibility=False)
        collections = client.get_collections().collections
        
        print(f"\nExisting collections:")
        for collection in collections:
            try:
                info = client.get_collection(collection.name)
                # Handle different response formats
                if hasattr(info, 'vectors_count'):
                    vectors_count = info.vectors_count
                elif hasattr(info, 'points_count'):
                    vectors_count = info.points_count
                else:
                    vectors_count = "unknown"
                
                # Get vector size
                if hasattr(info.config.params.vectors, 'size'):
                    vector_size = info.config.params.vectors.size
                elif isinstance(info.config.params.vectors, dict) and 'size' in info.config.params.vectors:
                    vector_size = info.config.params.vectors['size']
                else:
                    vector_size = "unknown"
                    
                print(f"  - {collection.name}: {vectors_count} vectors, dimension={vector_size}")
            except Exception as e:
                print(f"  - {collection.name}: (error getting details: {e})")
        
        # Check if old collection exists
        old_collection = "iacsgraph_queries"
        
        # Get model from env
        model_name = os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-large")
        new_collection = f"iacsgraph_queries_{model_name.replace('-', '_')}"
        
        # Get vector size
        if "text-embedding-3-large" in model_name:
            vector_size = 3072
        elif "text-embedding-3-small" in model_name:
            vector_size = 1536
        else:
            vector_size = 1536
        
        if any(c.name == old_collection for c in collections):
            print(f"\n⚠️  Found old collection: {old_collection}")
            print("   This uses sentence-transformers (384 dimensions)")
        
        if any(c.name == new_collection for c in collections):
            print(f"\n✅ OpenAI collection already exists: {new_collection}")
            print(f"   This uses {model_name} ({vector_size} dimensions)")
        else:
            print(f"\n📝 New collection will be created: {new_collection}")
            print(f"   Using {model_name} ({vector_size} dimensions)")
        
        print("\n✅ Ready to use OpenAI embeddings!")
        print("\nTo start the Query Assistant with OpenAI:")
        print("  python -m modules.query_assistant.web_api")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error checking Qdrant: {e}")
        print("Make sure Qdrant is running on localhost:6333")
        return False

if __name__ == "__main__":
    success = migrate_to_openai()
    sys.exit(0 if success else 1)