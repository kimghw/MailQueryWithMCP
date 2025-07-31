#!/usr/bin/env python3
import sqlite3
import json
from datetime import datetime, timedelta

# Read a template and test it properly
def test_template_query():
    # Load template
    with open('modules/templates/data/query_templates_split/query_templates_group_001.json', 'r') as f:
        data = json.load(f)
    
    # Get first template
    template = data['templates'][0]
    print(f"Testing template: {template['template_id']}")
    if 'natural_questions' in template:
        print(f"Natural question: {template['natural_questions'][0]}")
    
    # Get SQL query
    sql_query = template['sql_template']['query']
    print(f"\nOriginal SQL:\n{sql_query}")
    
    # Get parameters
    params = template['parameters']
    print(f"\nParameters: {params}")
    
    # Connect to database
    conn = sqlite3.connect('data/iacsgraph.db')
    cursor = conn.cursor()
    
    # Build parameter dictionary
    param_dict = {}
    for param in params:
        param_name = param['name']
        default_value = param['default']
        
        # Handle datetime parameters
        if param['type'] == 'datetime':
            # Convert SQL function to actual datetime
            if default_value == "datetime('now', '-90 days')":
                param_dict[param_name] = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d %H:%M:%S')
            elif default_value == "datetime('now', '-30 days')":
                param_dict[param_name] = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
            elif default_value == "datetime('now', '-1 days')":
                param_dict[param_name] = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
            else:
                param_dict[param_name] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        else:
            param_dict[param_name] = default_value
    
    print(f"\nParameter values: {param_dict}")
    
    # Execute query with parameters
    try:
        cursor.execute(sql_query + " LIMIT 5", param_dict)
        results = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        
        print(f"\nQuery executed successfully! Found {len(results)} results")
        print(f"Columns: {columns}")
        
        if results:
            print(f"\nFirst result:")
            for col, val in zip(columns, results[0]):
                if col == 'content' or col == 'body':
                    print(f"  {col}: {str(val)[:100]}...")
                else:
                    print(f"  {col}: {val}")
        
    except Exception as e:
        print(f"\nError: {e}")
    
    conn.close()

# Test KR organization query
def test_kr_query():
    conn = sqlite3.connect('data/iacsgraph.db')
    cursor = conn.cursor()
    
    query = """
    SELECT c.agenda_code, c.subject, c.sent_time, c.deadline, r.KR as kr_response
    FROM agenda_chair c
    LEFT JOIN agenda_responses_content r ON c.agenda_base_version = r.agenda_base_version
    WHERE c.deadline IS NOT NULL 
      AND c.deadline > datetime('now')
      AND r.KR IS NULL
      AND c.sent_time >= :period_start
    ORDER BY c.sent_time DESC
    LIMIT 5
    """
    
    params = {
        'period_start': (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d %H:%M:%S')
    }
    
    try:
        cursor.execute(query, params)
        results = cursor.fetchall()
        print(f"\nKR query test: Found {len(results)} results")
        for row in results[:2]:
            print(f"  - {row[1][:50]}... (deadline: {row[3]})")
    except Exception as e:
        print(f"KR query error: {e}")
    
    conn.close()

if __name__ == "__main__":
    print("=== Testing Query Template with Proper Parameter Binding ===\n")
    test_template_query()
    print("\n=== Testing KR Organization Query ===")
    test_kr_query()