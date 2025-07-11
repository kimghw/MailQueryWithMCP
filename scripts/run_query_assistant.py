#!/usr/bin/env python3
"""Script to run Query Assistant MCP Server"""

import os
import sys
import subprocess
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
    """Run Query Assistant MCP Server"""
    
    # Check if Qdrant is running
    if not check_qdrant():
        sys.exit(1)
    
    # Set environment variables
    db_path = os.getenv("DATABASE_PATH", "./data/iacsgraph.db")
    if not Path(db_path).exists():
        print(f"❌ Database not found: {db_path}")
        sys.exit(1)
    
    # Convert relative path to absolute
    if not Path(db_path).is_absolute():
        db_path = str(project_root / db_path)
    
    os.environ["IACSGRAPH_DB_PATH"] = db_path
    os.environ["QDRANT_URL"] = "localhost"
    os.environ["QDRANT_PORT"] = "6333"
    
    print(f"📊 Using database: {db_path}")
    print("🚀 Starting Query Assistant MCP Server...")
    
    # Run MCP server
    try:
        subprocess.run([
            sys.executable, 
            "-m", 
            "modules.query_assistant.mcp_server"
        ], cwd=project_root)
    except KeyboardInterrupt:
        print("\n👋 Server stopped")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()