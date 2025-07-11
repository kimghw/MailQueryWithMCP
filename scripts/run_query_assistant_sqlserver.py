#!/usr/bin/env python3
"""Script to run Query Assistant MCP Server with SQL Server"""

import os
import sys
import subprocess
import json
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

def get_sqlserver_config():
    """Get SQL Server configuration from user"""
    print("\n📊 SQL Server Configuration")
    print("-" * 30)
    
    # Check environment variables first
    db_config_json = os.getenv("IACSGRAPH_DB_CONFIG")
    if db_config_json:
        try:
            config = json.loads(db_config_json)
            print("Using configuration from environment variable")
            return config
        except:
            pass
    
    print("\nChoose authentication method:")
    print("1. Windows Authentication (Trusted Connection)")
    print("2. SQL Server Authentication")
    print("3. Azure SQL Database")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    config = {"type": "sqlserver"}
    
    if choice == "1":
        # Windows Authentication
        server = input("Server name [localhost\\SQLEXPRESS]: ").strip() or "localhost\\SQLEXPRESS"
        database = input("Database name [IACSGraph]: ").strip() or "IACSGraph"
        
        config.update({
            "server": server,
            "database": database,
            "trusted_connection": True,
            "driver": "{ODBC Driver 17 for SQL Server}"
        })
        
    elif choice == "2":
        # SQL Server Authentication
        server = input("Server name [localhost]: ").strip() or "localhost"
        database = input("Database name [IACSGraph]: ").strip() or "IACSGraph"
        username = input("Username: ").strip()
        password = input("Password: ").strip()
        
        config.update({
            "server": server,
            "database": database,
            "username": username,
            "password": password,
            "trusted_connection": False,
            "driver": "{ODBC Driver 17 for SQL Server}"
        })
        
    elif choice == "3":
        # Azure SQL Database
        server = input("Server name (e.g., myserver.database.windows.net): ").strip()
        database = input("Database name: ").strip()
        username = input("Username: ").strip()
        password = input("Password: ").strip()
        
        config.update({
            "server": server,
            "database": database,
            "username": username,
            "password": password,
            "driver": "{ODBC Driver 17 for SQL Server}"
        })
        
    else:
        print("Invalid choice. Exiting.")
        sys.exit(1)
    
    return config

def main():
    """Run Query Assistant MCP Server with SQL Server"""
    
    # Check if Qdrant is running
    if not check_qdrant():
        sys.exit(1)
    
    # Get SQL Server configuration
    db_config = get_sqlserver_config()
    
    # Set environment variables
    os.environ["IACSGRAPH_DB_CONFIG"] = json.dumps(db_config)
    os.environ["QDRANT_URL"] = "localhost"
    os.environ["QDRANT_PORT"] = "6333"
    
    print(f"\n📊 Using SQL Server: {db_config['server']}/{db_config['database']}")
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
        
        if "pyodbc" in str(e):
            print("\n💡 To use SQL Server, install pyodbc:")
            print("   pip install pyodbc")
            print("\n   On Ubuntu/Debian:")
            print("   sudo apt-get install unixodbc-dev")
            
        if "ODBC Driver" in str(e):
            print("\n💡 Install Microsoft ODBC Driver for SQL Server:")
            print("   https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server")
        
        sys.exit(1)

if __name__ == "__main__":
    main()