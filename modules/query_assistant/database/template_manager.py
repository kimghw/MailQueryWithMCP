"""Template Manager for Query Assistant

Manages template creation, storage, and synchronization with VectorDB
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import asyncio

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from .template_db_schema import QueryTemplateDB, get_session
from ..services.vector_store_unified import VectorStoreUnified
from ..schema import QueryTemplate

logger = logging.getLogger(__name__)


class TemplateManager:
    """Manages templates in database and VectorDB"""
    
    def __init__(
        self, 
        db_url: str = "sqlite:///templates.db",
        vector_store: Optional[VectorStoreUnified] = None
    ):
        self.db_url = db_url
        self.vector_store = vector_store or VectorStoreUnified()
        
    def get_db_session(self) -> Session:
        """Get database session"""
        return get_session(self.db_url)
    
    # ================ Template CRUD Operations ================
    
    def create_template(self, template_data: Dict[str, Any]) -> QueryTemplateDB:
        """Create new template in database"""
        session = self.get_db_session()
        try:
            # Validate template data
            errors = self._validate_template_data(template_data)
            if errors:
                raise ValueError(f"Template validation failed: {', '.join(errors)}")
            
            # Check for duplicates
            existing = session.query(QueryTemplateDB).filter_by(
                template_id=template_data['template_id']
            ).first()
            
            if existing:
                raise ValueError(f"Template with ID '{template_data['template_id']}' already exists")
            
            # Create template
            template = QueryTemplateDB(**template_data)
            session.add(template)
            session.commit()
            
            logger.info(f"Created template: {template.template_id}")
            return template
            
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    def update_template(self, template_id: str, updates: Dict[str, Any]) -> QueryTemplateDB:
        """Update existing template"""
        session = self.get_db_session()
        try:
            template = session.query(QueryTemplateDB).filter_by(
                template_id=template_id
            ).first()
            
            if not template:
                raise ValueError(f"Template '{template_id}' not found")
            
            # Update fields
            for key, value in updates.items():
                if hasattr(template, key):
                    setattr(template, key, value)
            
            template.updated_at = datetime.utcnow()
            template.vector_indexed = False  # Need re-indexing
            
            session.commit()
            logger.info(f"Updated template: {template_id}")
            return template
            
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    def get_template(self, template_id: str) -> Optional[QueryTemplateDB]:
        """Get template by ID"""
        session = self.get_db_session()
        try:
            return session.query(QueryTemplateDB).filter_by(
                template_id=template_id,
                is_active=True
            ).first()
        finally:
            session.close()
    
    def list_templates(
        self, 
        category: Optional[str] = None,
        active_only: bool = True,
        limit: int = 100
    ) -> List[QueryTemplateDB]:
        """List templates with filters"""
        session = self.get_db_session()
        try:
            query = session.query(QueryTemplateDB)
            
            if active_only:
                query = query.filter_by(is_active=True)
                
            if category:
                query = query.filter_by(category=category)
            
            return query.limit(limit).all()
            
        finally:
            session.close()
    
    def delete_template(self, template_id: str, hard_delete: bool = False):
        """Delete or deactivate template"""
        session = self.get_db_session()
        try:
            template = session.query(QueryTemplateDB).filter_by(
                template_id=template_id
            ).first()
            
            if not template:
                raise ValueError(f"Template '{template_id}' not found")
            
            if hard_delete:
                session.delete(template)
            else:
                template.is_active = False
                template.updated_at = datetime.utcnow()
            
            session.commit()
            logger.info(f"{'Deleted' if hard_delete else 'Deactivated'} template: {template_id}")
            
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    # ================ Bulk Operations ================
    
    def bulk_create_templates(self, templates_data: List[Dict[str, Any]]) -> Tuple[int, List[str]]:
        """Bulk create templates from list"""
        session = self.get_db_session()
        success_count = 0
        errors = []
        
        try:
            for idx, template_data in enumerate(templates_data):
                try:
                    # Validate
                    validation_errors = self._validate_template_data(template_data)
                    if validation_errors:
                        errors.append(f"Template {idx}: {', '.join(validation_errors)}")
                        continue
                    
                    # Check duplicate
                    existing = session.query(QueryTemplateDB).filter_by(
                        template_id=template_data['template_id']
                    ).first()
                    
                    if existing:
                        errors.append(f"Template {template_data['template_id']} already exists")
                        continue
                    
                    # Create
                    template = QueryTemplateDB(**template_data)
                    session.add(template)
                    success_count += 1
                    
                except Exception as e:
                    errors.append(f"Template {idx}: {str(e)}")
            
            session.commit()
            logger.info(f"Bulk created {success_count} templates")
            
            return success_count, errors
            
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    def load_from_json_files(self, data_folder: str) -> Tuple[int, List[str]]:
        """Load templates from JSON files in data folder"""
        data_path = Path(data_folder)
        if not data_path.exists():
            raise ValueError(f"Data folder not found: {data_folder}")
        
        all_templates = []
        errors = []
        
        # Read all JSON files
        json_files = list(data_path.glob("*.json"))
        logger.info(f"Found {len(json_files)} JSON files")
        
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # Handle both single template and list of templates
                    if isinstance(data, list):
                        all_templates.extend(data)
                    else:
                        all_templates.append(data)
                        
            except Exception as e:
                errors.append(f"Error reading {json_file.name}: {str(e)}")
        
        # Bulk create templates
        if all_templates:
            success_count, create_errors = self.bulk_create_templates(all_templates)
            errors.extend(create_errors)
            return success_count, errors
        
        return 0, errors
    
    # ================ VectorDB Synchronization ================
    
    async def sync_to_vectordb(self, batch_size: int = 50) -> Tuple[int, List[str]]:
        """Synchronize unindexed templates to VectorDB"""
        session = self.get_db_session()
        success_count = 0
        errors = []
        
        try:
            # Get unindexed templates
            unindexed = session.query(QueryTemplateDB).filter_by(
                vector_indexed=False,
                is_active=True
            ).all()
            
            logger.info(f"Found {len(unindexed)} templates to index")
            
            # Process in batches
            for i in range(0, len(unindexed), batch_size):
                batch = unindexed[i:i+batch_size]
                
                try:
                    # Convert to QueryTemplate objects
                    templates = []
                    for db_template in batch:
                        template = QueryTemplate(
                            template_id=db_template.template_id,
                            natural_questions=db_template.natural_questions,
                            sql_query=db_template.sql_query,
                            sql_query_with_parameters=db_template.sql_query_with_parameters or db_template.sql_query,
                            keywords=db_template.keywords or [],
                            category=db_template.category,
                            required_params=db_template.required_params or [],
                            query_filter=db_template.optional_params or [],
                            default_params=db_template.default_params or {},
                            usage_count=db_template.usage_count,
                            related_tables=[],  # Extract from SQL if needed
                            to_agent_prompt=db_template.to_agent_prompt,
                            template_version=db_template.version,
                            embedding_model=db_template.embedding_model,
                            embedding_dimension=db_template.embedding_dimension,
                            created_at=db_template.created_at,
                            last_used=db_template.last_used_at
                        )
                        templates.append(template)
                    
                    # Index in VectorDB
                    if self.vector_store.index_templates(templates):
                        # Mark as indexed
                        for db_template in batch:
                            db_template.vector_indexed = True
                            db_template.updated_at = datetime.utcnow()
                        
                        session.commit()
                        success_count += len(batch)
                        logger.info(f"Indexed batch {i//batch_size + 1}: {len(batch)} templates")
                    else:
                        errors.append(f"Failed to index batch {i//batch_size + 1}")
                        
                except Exception as e:
                    errors.append(f"Error in batch {i//batch_size + 1}: {str(e)}")
                    session.rollback()
            
            return success_count, errors
            
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    async def full_sync(self) -> Dict[str, Any]:
        """Full synchronization: DB → VectorDB"""
        session = self.get_db_session()
        
        try:
            # Get statistics
            total_templates = session.query(QueryTemplateDB).filter_by(is_active=True).count()
            indexed_templates = session.query(QueryTemplateDB).filter_by(
                is_active=True, 
                vector_indexed=True
            ).count()
            
            # Sync unindexed
            success_count, errors = await self.sync_to_vectordb()
            
            return {
                'total_templates': total_templates,
                'previously_indexed': indexed_templates,
                'newly_indexed': success_count,
                'errors': errors,
                'sync_complete': len(errors) == 0
            }
            
        finally:
            session.close()
    
    # ================ Validation ================
    
    def _validate_template_data(self, template_data: Dict[str, Any]) -> List[str]:
        """Validate template data"""
        errors = []
        
        # Required fields
        required_fields = ['template_id', 'natural_questions', 'sql_query', 'category']
        for field in required_fields:
            if field not in template_data or not template_data[field]:
                errors.append(f"Missing required field: {field}")
        
        # Template ID format
        if 'template_id' in template_data:
            template_id = template_data['template_id']
            if not template_id or not template_id.replace('_', '').isalnum():
                errors.append("Invalid template_id format")
        
        # SQL validation (basic)
        if 'sql_query' in template_data:
            sql = template_data['sql_query'].strip().upper()
            if not sql.startswith('SELECT'):
                errors.append("SQL query must start with SELECT")
        
        # Parameter consistency
        if 'sql_query_with_parameters' in template_data:
            sql_params = self._extract_parameters(template_data['sql_query_with_parameters'])
            declared_params = set(
                template_data.get('required_params', []) + 
                template_data.get('optional_params', [])
            )
            
            if sql_params != declared_params:
                errors.append(f"Parameter mismatch: SQL has {sql_params}, declared {declared_params}")
        
        return errors
    
    def _extract_parameters(self, sql: str) -> set:
        """Extract parameter placeholders from SQL"""
        import re
        # Find {param} style placeholders
        params = re.findall(r'\{(\w+)\}', sql)
        return set(params)
    
    # ================ Statistics ================
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get template statistics"""
        session = self.get_db_session()
        
        try:
            from sqlalchemy import func
            
            stats = {
                'total_templates': session.query(QueryTemplateDB).count(),
                'active_templates': session.query(QueryTemplateDB).filter_by(is_active=True).count(),
                'indexed_templates': session.query(QueryTemplateDB).filter_by(
                    is_active=True,
                    vector_indexed=True
                ).count(),
                'categories': session.query(
                    QueryTemplateDB.category,
                    func.count(QueryTemplateDB.id)
                ).group_by(QueryTemplateDB.category).all(),
                'most_used': session.query(QueryTemplateDB).filter_by(
                    is_active=True
                ).order_by(QueryTemplateDB.usage_count.desc()).limit(10).all()
            }
            
            return stats
            
        finally:
            session.close()


# ================ CLI Interface ================

async def main():
    """CLI for template management"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Template Manager CLI")
    parser.add_argument('action', choices=['load', 'sync', 'stats', 'list'])
    parser.add_argument('--data-folder', default='./data', help='Folder containing JSON files')
    parser.add_argument('--db-url', default='sqlite:///templates.db', help='Database URL')
    parser.add_argument('--category', help='Filter by category')
    
    args = parser.parse_args()
    
    manager = TemplateManager(db_url=args.db_url)
    
    if args.action == 'load':
        # Load templates from JSON files
        success, errors = manager.load_from_json_files(args.data_folder)
        print(f"✓ Loaded {success} templates")
        if errors:
            print(f"✗ Errors: {len(errors)}")
            for error in errors[:5]:
                print(f"  - {error}")
                
    elif args.action == 'sync':
        # Sync to VectorDB
        result = await manager.full_sync()
        print(f"✓ Sync complete: {result['newly_indexed']} templates indexed")
        if result['errors']:
            print(f"✗ Errors: {len(result['errors'])}")
            
    elif args.action == 'stats':
        # Show statistics
        stats = manager.get_statistics()
        print(f"Total templates: {stats['total_templates']}")
        print(f"Active templates: {stats['active_templates']}")
        print(f"Indexed templates: {stats['indexed_templates']}")
        print("\nCategories:")
        for category, count in stats['categories']:
            print(f"  - {category}: {count}")
            
    elif args.action == 'list':
        # List templates
        templates = manager.list_templates(category=args.category)
        for template in templates[:20]:
            print(f"- {template.template_id}: {template.natural_questions[:50]}...")


if __name__ == "__main__":
    asyncio.run(main())