"""Unified template uploader for both SQL and Qdrant"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

from .sql_uploader import SQLTemplateUploader
from .vector_uploader import VectorUploader

logger = logging.getLogger(__name__)


class TemplateUploader:
    """Unified uploader for templates to both SQL and Qdrant databases"""
    
    def __init__(
        self,
        db_path: str = "data/iacsgraph.db",
        qdrant_url: str = "localhost",
        qdrant_port: int = 6333,
        collection_name: str = "query_templates_unified"
    ):
        self.sql_uploader = SQLTemplateUploader(db_path)
        self.vector_uploader = VectorUploader(
            qdrant_url=qdrant_url,
            qdrant_port=qdrant_port,
            collection_name=collection_name
        )
        
    def load_templates_from_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Load templates from JSON file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        if isinstance(data, list):
            # Old format - list of templates
            return data
        elif isinstance(data, dict) and 'templates' in data:
            # New unified format
            return data['templates']
        else:
            raise ValueError(f"Unknown template file format in {file_path}")
            
    def upload_to_sql(self, templates: List[Dict[str, Any]], version: str = "unified") -> int:
        """Upload templates to SQL database"""
        logger.info("Uploading templates to SQL database...")
        with self.sql_uploader as uploader:
            count = uploader.upload_templates(templates, version)
            
        logger.info(f"Uploaded {count} templates to SQL database")
        return count
        
    def upload_to_vector_db(self, templates: List[Dict[str, Any]], recreate: bool = False) -> int:
        """Upload templates to vector database"""
        logger.info("Uploading templates to vector database...")
        
        # Create/recreate collection
        self.vector_uploader.create_collection(recreate=recreate)
        
        # Upload templates
        count = self.vector_uploader.upload_templates(templates)
        
        logger.info(f"Uploaded {count} vectors to vector database")
        return count
        
    def upload_all(
        self,
        file_path: Path,
        version: str = "unified",
        recreate_qdrant: bool = False
    ) -> Dict[str, int]:
        """Upload templates to both SQL and Qdrant
        
        Args:
            file_path: Path to template JSON file
            version: Template version for SQL
            recreate_qdrant: Whether to recreate Qdrant collection
            
        Returns:
            Dictionary with upload counts for each database
        """
        # Load templates
        templates = self.load_templates_from_file(file_path)
        logger.info(f"Loaded {len(templates)} templates from {file_path}")
        
        # Upload to both databases
        results = {
            'sql': self.upload_to_sql(templates, version),
            'vector_db': self.upload_to_vector_db(templates, recreate_qdrant)
        }
        
        # Verify counts
        sql_count = self.sql_uploader.get_template_count(version)
        vector_count = self.vector_uploader.get_template_count()
        
        results['sql_total'] = sql_count
        results['vector_db_total'] = vector_count
        
        logger.info(f"Upload complete - SQL: {sql_count}, Vector DB: {vector_count}")
        
        return results
        
    def verify_sync(self, version: str = "unified") -> Dict[str, Any]:
        """Verify that SQL and vector DB are in sync"""
        sql_count = self.sql_uploader.get_template_count(version)
        vector_count = self.vector_uploader.get_template_count()
        
        # Note: vector_count will be higher due to individual embeddings
        return {
            'sql_count': sql_count,
            'vector_count': vector_count,
            'avg_vectors_per_template': vector_count / sql_count if sql_count > 0 else 0
        }