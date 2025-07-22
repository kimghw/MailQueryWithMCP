"""Template loader service for VectorDB"""

from typing import List, Dict, Any, Optional
import asyncio
from datetime import datetime

from modules.query_assistant.services.vector_store_http import VectorStoreService
from modules.core.utils.embeddings import EmbeddingsManager
from modules.query_assistant.template_vectordb_schema import QueryTemplate


class TemplateLoader:
    """Load and search templates from VectorDB"""
    
    def __init__(self):
        self.vector_store = VectorStoreService()
        self.embeddings_manager = EmbeddingsManager()
        self.collection_name = "query_templates"
        self._cache = {}  # Simple in-memory cache
        
    async def search_templates(
        self, 
        query: str, 
        limit: int = 5,
        category: Optional[str] = None,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """Search templates by natural language query"""
        try:
            # Generate embedding for query
            query_embedding = await self.embeddings_manager.get_embedding(query)
            
            # Build filter
            filter_conditions = []
            if active_only:
                filter_conditions.append({
                    "key": "active",
                    "match": {"value": True}
                })
            if category:
                filter_conditions.append({
                    "key": "category", 
                    "match": {"value": category}
                })
            
            # Search in VectorDB
            results = await self.vector_store.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=limit,
                filter={"must": filter_conditions} if filter_conditions else None
            )
            
            # Format results
            templates = []
            for result in results:
                template_data = result['payload']
                template_data['score'] = result['score']
                templates.append(template_data)
            
            return templates
            
        except Exception as e:
            print(f"Error searching templates: {e}")
            return []
    
    async def get_template_by_id(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get specific template by ID"""
        # Check cache first
        if template_id in self._cache:
            return self._cache[template_id]
        
        try:
            # Search by template_id
            filter_condition = {
                "must": [{
                    "key": "template_id",
                    "match": {"value": template_id}
                }]
            }
            
            results = await self.vector_store.search(
                collection_name=self.collection_name,
                query_vector=[0] * 768,  # Dummy vector for filter-only search
                limit=1,
                filter=filter_condition
            )
            
            if results:
                template = results[0]['payload']
                self._cache[template_id] = template
                return template
                
            return None
            
        except Exception as e:
            print(f"Error getting template by ID: {e}")
            return None
    
    async def get_templates_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get all templates in a category"""
        try:
            filter_condition = {
                "must": [
                    {
                        "key": "category",
                        "match": {"value": category}
                    },
                    {
                        "key": "active",
                        "match": {"value": True}
                    }
                ]
            }
            
            # Get all templates in category (up to 100)
            results = await self.vector_store.search(
                collection_name=self.collection_name,
                query_vector=[0] * 768,  # Dummy vector
                limit=100,
                filter=filter_condition
            )
            
            templates = [result['payload'] for result in results]
            return templates
            
        except Exception as e:
            print(f"Error getting templates by category: {e}")
            return []
    
    async def find_best_template(
        self, 
        query: str,
        extracted_params: Dict[str, Any] = None
    ) -> Optional[Dict[str, Any]]:
        """Find the best matching template for a query"""
        # Search for templates
        templates = await self.search_templates(query, limit=10)
        
        if not templates:
            return None
        
        # If we have extracted parameters, filter by required params
        if extracted_params:
            param_keys = set(extracted_params.keys())
            
            # Find templates where all required params are satisfied
            valid_templates = []
            for template in templates:
                required_params = set(template.get('required_params', []))
                if required_params.issubset(param_keys):
                    valid_templates.append(template)
            
            if valid_templates:
                # Return the highest scoring valid template
                return valid_templates[0]
        
        # Return highest scoring template
        return templates[0]
    
    async def refresh_cache(self):
        """Clear the template cache"""
        self._cache.clear()
        print("Template cache cleared")


# Singleton instance
_template_loader_instance = None


def get_template_loader() -> TemplateLoader:
    """Get singleton instance of TemplateLoader"""
    global _template_loader_instance
    if _template_loader_instance is None:
        _template_loader_instance = TemplateLoader()
    return _template_loader_instance


# Example usage
async def example_usage():
    """Example of how to use the template loader"""
    loader = get_template_loader()
    
    # Search templates
    query = "최근 30일 아젠다 보여줘"
    templates = await loader.search_templates(query)
    
    print(f"Found {len(templates)} templates for query: {query}")
    for template in templates:
        print(f"  - {template['template_id']}: {template['natural_questions']} (score: {template['score']:.3f})")
    
    # Get specific template
    template = await loader.get_template_by_id("recent_agendas_by_period")
    if template:
        print(f"\nTemplate details:")
        print(f"  - ID: {template['template_id']}")
        print(f"  - Question: {template['natural_questions']}")
        print(f"  - Required params: {template['required_params']}")
    
    # Find best template with parameters
    best_template = await loader.find_best_template(
        query="최근 30일 아젠다", 
        extracted_params={"period": "30일", "days": 30}
    )
    if best_template:
        print(f"\nBest matching template: {best_template['template_id']}")


if __name__ == "__main__":
    asyncio.run(example_usage())