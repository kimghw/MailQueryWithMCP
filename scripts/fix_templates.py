#!/usr/bin/env python3
"""Fix SQL templates to match actual database schema"""

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
    """Create fixed SQL template for organization response rate"""
    
    print("🔧 Creating fixed SQL template")
    print("=" * 50)
    
    # Test the fixed SQL directly
    import sqlite3
    
    db_path = os.getenv("DATABASE_PATH", "./data/iacsgraph.db")
    if not Path(db_path).is_absolute():
        db_path = str(project_root / db_path)
    
    # Fixed SQL for KR organization
    fixed_sql = """
        WITH org_responses AS (
            SELECT 
                COUNT(CASE WHEN arc.KR IS NOT NULL AND arc.KR != '' THEN 1 END) as responded,
                COUNT(*) as total
            FROM agenda_chair ac
            JOIN agenda_responses_content arc ON ac.agenda_base_version = arc.agenda_base_version
            WHERE ac.sent_time >= datetime('now', '-30 days')
        )
        SELECT 
            'KR' as organization,
            responded,
            total,
            ROUND(CAST(responded AS FLOAT) / total * 100, 2) as response_rate
        FROM org_responses
    """
    
    print("📊 Testing fixed SQL query:")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(fixed_sql)
        result = cursor.fetchone()
        
        if result:
            print(f"✅ Query successful!")
            print(f"   Organization: {result[0]}")
            print(f"   Responded: {result[1]}")
            print(f"   Total: {result[2]}")
            print(f"   Response Rate: {result[3]}%")
        
        conn.close()
        
        # Now let's create a simpler template that works
        print("\n📝 Creating simplified templates...")
        
        # Write a new simplified templates file
        simplified_templates = '''"""Simplified SQL templates that work with actual schema"""

SIMPLE_TEMPLATES = [
    {
        "id": "all_agendas",
        "natural_query": "모든 아젠다 보여줘",
        "sql_template": """
            SELECT 
                agenda_code,
                subject,
                sent_time,
                decision_status
            FROM agenda_chair
            ORDER BY sent_time DESC
            LIMIT {limit}
        """,
        "keywords": ["아젠다", "모든", "전체", "목록", "all", "agenda"],
        "required_params": [],
        "optional_params": ["limit"],
        "category": "list"
    },
    {
        "id": "recent_agendas_simple",
        "natural_query": "최근 아젠다",
        "sql_template": """
            SELECT 
                agenda_code,
                subject,
                sent_time,
                decision_status
            FROM agenda_chair
            WHERE sent_time >= datetime('now', '-{days} days')
            ORDER BY sent_time DESC
            LIMIT {limit}
        """,
        "keywords": ["최근", "recent", "아젠다", "agenda"],
        "required_params": [],
        "optional_params": ["days", "limit"],
        "category": "recent"
    },
    {
        "id": "kr_response_rate_fixed",
        "natural_query": "KR 응답률",
        "sql_template": """
            WITH org_responses AS (
                SELECT 
                    COUNT(CASE WHEN arc.KR IS NOT NULL AND arc.KR != '' THEN 1 END) as responded,
                    COUNT(*) as total
                FROM agenda_chair ac
                JOIN agenda_responses_content arc ON ac.agenda_base_version = arc.agenda_base_version
                WHERE ac.sent_time >= datetime('now', '-{days} days')
            )
            SELECT 
                'KR' as organization,
                responded,
                total,
                ROUND(CAST(responded AS FLOAT) / total * 100, 2) as response_rate
            FROM org_responses
        """,
        "keywords": ["KR", "응답률", "response", "rate"],
        "required_params": [],
        "optional_params": ["days"],
        "category": "statistics"
    }
]
'''
        
        with open(project_root / "modules/query_assistant/templates/simple_templates.py", "w") as f:
            f.write(simplified_templates)
        
        print("✅ Created simple_templates.py")
        
        # Re-initialize Query Assistant to reload templates
        print("\n🚀 Re-initializing Query Assistant with fixed templates...")
        
        try:
            # Delete the collection to start fresh
            import requests
            response = requests.delete("http://localhost:6333/collections/iacsgraph_queries")
            print("   Deleted old collection")
            
            # Re-initialize
            from modules.query_assistant import QueryAssistant
            qa = QueryAssistant(
                db_path=db_path,
                qdrant_url="localhost",
                qdrant_port=6333
            )
            print("✅ Query Assistant re-initialized!")
            
            # Test the query
            print("\n🧪 Testing 'KR 응답률' query...")
            result = qa.process_query("KR 응답률", execute=True)
            
            if result.error:
                print(f"❌ Error: {result.error}")
            else:
                print("✅ Query successful!")
                if result.results:
                    data = result.results[0]
                    print(f"   KR Response Rate: {data.get('response_rate', 'N/A')}%")
                    
        except Exception as e:
            print(f"❌ Error re-initializing: {e}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()