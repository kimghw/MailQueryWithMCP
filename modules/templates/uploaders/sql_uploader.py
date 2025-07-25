"""SQL database uploader for templates"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class SQLTemplateUploader:
    """Upload templates to SQL database"""
    
    def __init__(self, db_path: str = "data/iacsgraph.db"):
        self.db_path = db_path
        self.connection = None
        
    def connect(self):
        """Connect to database"""
        self.connection = sqlite3.connect(self.db_path)
        return self.connection
        
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            
    def upload_templates(self, templates: List[Dict[str, Any]], version: str = "unified") -> int:
        """Upload templates to SQL database
        
        Args:
            templates: List of template dictionaries
            version: Template version
            
        Returns:
            Number of templates uploaded
        """
        if not self.connection:
            self.connect()
            
        cursor = self.connection.cursor()
        uploaded = 0
        
        # Delete existing templates of the same version
        cursor.execute("DELETE FROM query_templates WHERE template_version = ?", (version,))
        logger.info(f"Deleted {cursor.rowcount} existing templates with version {version}")
        
        for template in templates:
            try:
                # Skip config templates
                template_id = template.get('template_id', '')
                if template_id.startswith('_config'):
                    logger.debug(f"Skipping config template: {template_id}")
                    continue
                    
                # Extract data
                query_info = template.get('query_info', {})
                sql_template = template.get('sql_template', {})
                parameters = template.get('parameters', [])
                
                # Prepare values
                natural_questions = ' | '.join(query_info.get('natural_questions', []))
                keywords = query_info.get('keywords', [])
                sql_query = sql_template.get('query', '')
                category = template.get('template_category', '')
                
                # Extract parameter info
                required_params = [p['name'] for p in parameters if p.get('required', True)]
                optional_params = [p['name'] for p in parameters if not p.get('required', True)]
                default_params = {p['name']: p.get('default', '') for p in parameters if 'default' in p}
                
                # Insert into database
                cursor.execute("""
                    INSERT INTO query_templates (
                        template_id, natural_questions, sql_query_with_parameters, keywords,
                        category, required_params, optional_params, default_params,
                        template_version, embedding_model, embedding_dimension,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    template_id,
                    natural_questions,
                    sql_query,
                    json.dumps(keywords, ensure_ascii=False),
                    category,
                    json.dumps(required_params),
                    json.dumps(optional_params),
                    json.dumps(default_params),
                    version,
                    'text-embedding-3-large',
                    3072,
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))
                
                uploaded += 1
                logger.debug(f"Uploaded template: {template_id}")
                
            except Exception as e:
                logger.error(f"Failed to upload template {template.get('template_id', 'unknown')}: {e}")
                
        self.connection.commit()
        logger.info(f"Successfully uploaded {uploaded} templates to SQL database")
        
        return uploaded
        
    def get_template_count(self, version: str = "unified") -> int:
        """Get count of templates in database"""
        if not self.connection:
            self.connect()
            
        cursor = self.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM query_templates WHERE template_version = ?", (version,))
        return cursor.fetchone()[0]
        
    def __enter__(self):
        self.connect()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()