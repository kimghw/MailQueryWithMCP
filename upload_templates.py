#!/usr/bin/env python3
import json
import sqlite3
from pathlib import Path
from datetime import datetime

def upload_templates():
    # Load templates
    template_file = Path("agenda_query_templates_final.json")
    with open(template_file) as f:
        templates = json.load(f)
    
    # Connect to database
    db_path = Path("data/iacsgraph.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create query_templates table if not exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS query_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            template_id TEXT UNIQUE NOT NULL,
            natural_questions TEXT NOT NULL,
            sql_query_with_parameters TEXT NOT NULL,
            keywords TEXT,
            category TEXT,
            required_params TEXT,
            optional_params TEXT,
            default_params TEXT,
            template_version TEXT,
            embedding_model TEXT,
            embedding_dimension INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Insert templates
    inserted = 0
    updated = 0
    
    for template in templates:
        try:
            cursor.execute("""
                INSERT INTO query_templates (
                    template_id, natural_questions, sql_query_with_parameters,
                    keywords, category, required_params, optional_params,
                    default_params, template_version, embedding_model,
                    embedding_dimension
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                template['template_id'],
                template['natural_questions'],
                template['sql_query_with_parameters'],
                json.dumps(template.get('keywords', []), ensure_ascii=False),
                template.get('category', ''),
                json.dumps(template.get('required_params', []), ensure_ascii=False),
                json.dumps(template.get('optional_params', []), ensure_ascii=False),
                json.dumps(template.get('default_params', {}), ensure_ascii=False),
                template.get('template_version', '1.0'),
                template.get('embedding_model', 'text-embedding-3-large'),
                template.get('embedding_dimension', 1536)
            ))
            inserted += 1
        except sqlite3.IntegrityError:
            # Update existing template
            cursor.execute("""
                UPDATE query_templates SET
                    natural_questions = ?,
                    sql_query_with_parameters = ?,
                    keywords = ?,
                    category = ?,
                    required_params = ?,
                    optional_params = ?,
                    default_params = ?,
                    template_version = ?,
                    embedding_model = ?,
                    embedding_dimension = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE template_id = ?
            """, (
                template['natural_questions'],
                template['sql_query_with_parameters'],
                json.dumps(template.get('keywords', []), ensure_ascii=False),
                template.get('category', ''),
                json.dumps(template.get('required_params', []), ensure_ascii=False),
                json.dumps(template.get('optional_params', []), ensure_ascii=False),
                json.dumps(template.get('default_params', {}), ensure_ascii=False),
                template.get('template_version', '1.0'),
                template.get('embedding_model', 'text-embedding-3-large'),
                template.get('embedding_dimension', 1536),
                template['template_id']
            ))
            updated += 1
    
    conn.commit()
    
    # Verify upload
    cursor.execute("SELECT COUNT(*) FROM query_templates")
    total_count = cursor.fetchone()[0]
    
    print(f"Template upload completed!")
    print(f"- Inserted: {inserted} templates")
    print(f"- Updated: {updated} templates")
    print(f"- Total templates in database: {total_count}")
    
    # Show all templates
    print("\nTemplates in database:")
    cursor.execute("SELECT template_id, natural_questions FROM query_templates")
    for row in cursor.fetchall():
        print(f"- {row[0]}: {row[1]}")
    
    conn.close()

if __name__ == "__main__":
    upload_templates()