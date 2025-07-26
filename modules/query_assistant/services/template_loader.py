"""Template loader service using database and VectorDB"""

from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from ..database.template_manager import TemplateManager
from ..services.vector_store_unified import VectorStoreUnified
from ..schema import VectorSearchResult

logger = logging.getLogger(__name__)


class TemplateLoader:
    """Load and search templates from Database and VectorDB"""
    
    def __init__(self, db_url: str = "sqlite:///templates.db", vector_store: Optional[VectorStoreUnified] = None):
        self.template_manager = TemplateManager(db_url=db_url, vector_store=vector_store)
        self.vector_store = vector_store or VectorStoreUnified()
        self._cache = {}  # Simple in-memory cache
        
    def search_templates(
        self, 
        query: str, 
        keywords: List[str],
        limit: int = 5,
        category: Optional[str] = None,
        score_threshold: float = 0.5
    ) -> List[VectorSearchResult]:
        """Search templates using vector similarity"""
        try:
            # Use VectorStore's search method
            results = self.vector_store.search(
                query=query,
                keywords=keywords,
                limit=limit,
                category=category,
                score_threshold=score_threshold
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching templates: {e}")
            return []
    
    def get_template_by_id(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get specific template by ID from database"""
        # Check cache first
        if template_id in self._cache:
            return self._cache[template_id]
        
        try:
            # Get from database
            db_template = self.template_manager.get_template(template_id)
            
            if db_template:
                template_dict = db_template.to_dict()
                self._cache[template_id] = template_dict
                return template_dict
                
            return None
            
        except Exception as e:
            logger.error(f"Error getting template by ID: {e}")
            return None
    
    def get_templates_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get all active templates in a category from database"""
        try:
            db_templates = self.template_manager.list_templates(
                category=category,
                active_only=True
            )
            
            templates = [template.to_dict() for template in db_templates]
            return templates
            
        except Exception as e:
            logger.error(f"Error getting templates by category: {e}")
            return []
    
    def find_best_template(
        self, 
        query: str,
        keywords: List[str],
        extracted_params: Dict[str, Any] = None
    ) -> Optional[Dict[str, Any]]:
        """Find the best matching template for a query"""
        # Search for templates
        search_results = self.search_templates(query, keywords, limit=10)
        
        if not search_results:
            return None
        
        # If we have extracted parameters, filter by required params
        if extracted_params:
            param_keys = set(extracted_params.keys())
            
            # Find templates where all required params are satisfied
            valid_results = []
            for result in search_results:
                template = result.template
                required_params = set(template.required_params)
                if required_params.issubset(param_keys):
                    valid_results.append(result)
            
            if valid_results:
                # Return the highest scoring valid template
                return valid_results[0].template.dict()
        
        # Return highest scoring template
        return search_results[0].template.dict()
    
    def update_usage_stats(self, template_id: str) -> bool:
        """Update usage statistics for a template"""
        try:
            # Update in VectorDB - check if method exists first
            if hasattr(self.vector_store, 'update_usage_stats'):
                success = self.vector_store.update_usage_stats(template_id)
            else:
                # Skip vector store update if method doesn't exist
                success = True
            
            if success:
                # Update in database
                db_template = self.template_manager.get_template(template_id)
                if db_template:
                    self.template_manager.update_template(
                        template_id,
                        {
                            'usage_count': db_template.usage_count + 1,
                            'last_used_at': datetime.utcnow()
                        }
                    )
                    
                # Clear cache entry
                if template_id in self._cache:
                    del self._cache[template_id]
                    
            return success
            
        except Exception as e:
            logger.error(f"Error updating usage stats: {e}")
            return False
    
    def refresh_cache(self):
        """Clear the template cache"""
        self._cache.clear()
        logger.info("Template cache cleared")
    
    async def ensure_templates_synced(self):
        """Ensure templates are synced between DB and VectorDB"""
        try:
            stats = self.template_manager.get_statistics()
            if stats['active_templates'] > stats['indexed_templates']:
                logger.info("Syncing templates to VectorDB...")
                result = await self.template_manager.full_sync()
                logger.info(f"Sync complete: {result['newly_indexed']} templates indexed")
                return result
            return {'sync_complete': True, 'newly_indexed': 0}
        except Exception as e:
            logger.error(f"Error syncing templates: {e}")
            return {'sync_complete': False, 'error': str(e)}


# Singleton instance
_template_loader_instance = None


def get_template_loader(db_url: str = "sqlite:///templates.db", vector_store: Optional[VectorStoreUnified] = None) -> TemplateLoader:
    """Get singleton instance of TemplateLoader"""
    global _template_loader_instance
    if _template_loader_instance is None:
        _template_loader_instance = TemplateLoader(db_url=db_url, vector_store=vector_store)
    return _template_loader_instance