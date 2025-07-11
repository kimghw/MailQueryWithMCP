#!/usr/bin/env python3
"""Run Query Assistant Web API Server"""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

def check_qdrant():
    """Check if Qdrant is running"""
    import requests
    try:
        response = requests.get("http://localhost:6333/health")
        if response.status_code == 200:
            print("✅ Qdrant is running")
            return True
    except:
        pass
    
    print("❌ Qdrant is not running")
    print("Please start Qdrant with:")
    print("docker run -p 6333:6333 -v $(pwd)/qdrant_storage:/qdrant/storage:z qdrant/qdrant")
    return False

def main():
    """Run Query Assistant Web API Server"""
    
    # Check if Qdrant is running
    if not check_qdrant():
        print("\n💡 You can still run the web server, but queries will fail without Qdrant.")
        response = input("Continue anyway? (y/N): ").strip().lower()
        if response != 'y':
            sys.exit(1)
    
    # Set environment variables
    db_path = os.getenv("DATABASE_PATH", "./data/iacsgraph.db")
    if not Path(db_path).is_absolute():
        db_path = str(project_root / db_path)
    
    os.environ["DATABASE_PATH"] = db_path
    
    print(f"📊 Using database: {db_path}")
    print("🚀 Starting Query Assistant Web API...")
    print("🌐 Open http://localhost:8000 in your browser")
    print("\n📝 API Documentation: http://localhost:8000/docs")
    print("🔄 Interactive API: http://localhost:8000/redoc")
    print("\nPress Ctrl+C to stop the server")
    
    # Run web server
    try:
        from modules.query_assistant.web_api import run_server
        run_server(host="0.0.0.0", port=8000)
    except KeyboardInterrupt:
        print("\n👋 Server stopped")
    except ImportError as e:
        print(f"\n❌ Missing dependency: {e}")
        print("Please install FastAPI and Uvicorn:")
        print("  pip install fastapi uvicorn")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()