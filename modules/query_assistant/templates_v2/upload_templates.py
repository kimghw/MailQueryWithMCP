#!/usr/bin/env python3
import json
import sqlite3
from pathlib import Path
from datetime import datetime

def upload_templates():
    """Upload v2 templates to IACSGRAPH database"""
    
    # Load templates
    template_file = Path("modules/query_assistant/templates_v2/query_templates.json")
    with open(template_file, 'r', encoding='utf-8') as f:
        templates = json.load(f)
    
    # Connect to database
    db_path = Path("data/iacsgraph.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Use existing table schema
    # Clear existing v2 templates
    cursor.execute("DELETE FROM query_templates WHERE template_id LIKE '%_v2'")
    
    # Insert templates
    inserted = 0
    errors = 0
    
    for template in templates:
        try:
            # Extract data from nested structure
            query_info = template.get('query_info', {})
            target_scope = template.get('target_scope', {})
            sql_template = template.get('sql_template', {})
            parameters = template.get('parameters', {})
            embedding_config = template.get('embedding_config', {})
            
            # Combine natural questions into a single string
            natural_questions = ' | '.join(query_info.get('natural_questions', []))
            
            cursor.execute("""
                INSERT INTO query_templates (
                    template_id, natural_questions, sql_query_with_parameters,
                    keywords, category, required_params, optional_params,
                    default_params, template_version, embedding_model,
                    embedding_dimension
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                template['template_id'],
                natural_questions,
                sql_template.get('query', ''),
                json.dumps(query_info.get('keywords', []), ensure_ascii=False),
                template.get('template_category', ''),
                json.dumps(parameters.get('required_params', []), ensure_ascii=False),
                json.dumps(parameters.get('optional_params', []), ensure_ascii=False),
                json.dumps(parameters.get('default_params', {}), ensure_ascii=False),
                template.get('template_version', '2.0'),
                embedding_config.get('model', 'text-embedding-3-large'),
                embedding_config.get('dimension', 1536)
            ))
            inserted += 1
            
        except Exception as e:
            print(f"Error inserting template {template.get('template_id', 'unknown')}: {str(e)}")
            errors += 1
            continue
    
    conn.commit()
    
    # Verify upload
    cursor.execute("SELECT COUNT(*) FROM query_templates")
    total_count = cursor.fetchone()[0]
    
    print(f"\nTemplate upload completed!")
    print(f"- Total templates: {len(templates)}")
    print(f"- Successfully inserted: {inserted}")
    print(f"- Errors: {errors}")
    print(f"- Total in database: {total_count}")
    
    # Show sample templates
    print("\nSample templates in database:")
    cursor.execute("""
        SELECT template_id, category, 
               substr(natural_questions, 1, 50) as first_question
        FROM query_templates 
        WHERE template_id LIKE '%_v2'
        LIMIT 10
    """)
    
    for row in cursor.fetchall():
        print(f"- {row[0]} ({row[1]}): {row[2]}...")
    
    # Category statistics
    print("\nTemplates by category:")
    cursor.execute("""
        SELECT category, COUNT(*) as count 
        FROM query_templates 
        WHERE template_id LIKE '%_v2'
        GROUP BY category 
        ORDER BY count DESC
    """)
    
    for row in cursor.fetchall():
        print(f"- {row[0]}: {row[1]}")
    
    conn.close()

if __name__ == "__main__":
    upload_templates()