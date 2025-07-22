"""JSONL Template Loader for VectorDB"""

import json
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import sys

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from modules.query_assistant.services.vector_store_http import VectorStoreService
from modules.core.utils.embeddings import EmbeddingsManager
from modules.query_assistant.template_vectordb_schema import QueryTemplate


class JSONLTemplateLoader:
    """Load templates from JSONL files and store in VectorDB"""
    
    def __init__(self):
        self.vector_store = VectorStoreService()
        self.embeddings_manager = EmbeddingsManager()
        self.collection_name = "query_templates"
        self.data_dir = Path(__file__).parent / "data"
        
    async def ensure_collection_exists(self):
        """Ensure the templates collection exists in VectorDB"""
        try:
            # Check if collection exists
            collections = await self.vector_store.get_collections()
            
            if self.collection_name not in collections:
                # Create collection with proper configuration
                collection_config = {
                    "vectors": {
                        "size": 768,  # Adjust based on your embedding model
                        "distance": "Cosine"
                    }
                }
                
                await self.vector_store.create_collection(
                    collection_name=self.collection_name,
                    config=collection_config
                )
                print(f"✓ Collection '{self.collection_name}' created")
            else:
                print(f"✓ Collection '{self.collection_name}' already exists")
                
        except Exception as e:
            print(f"✗ Error ensuring collection: {e}")
            raise
    
    def load_jsonl_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Load templates from a JSONL file"""
        templates = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:  # Skip empty lines
                        continue
                        
                    try:
                        template_data = json.loads(line)
                        templates.append(template_data)
                    except json.JSONDecodeError as e:
                        print(f"✗ Error parsing line {line_num} in {file_path.name}: {e}")
                        
            print(f"✓ Loaded {len(templates)} templates from {file_path.name}")
            return templates
            
        except FileNotFoundError:
            print(f"✗ File not found: {file_path}")
            return []
        except Exception as e:
            print(f"✗ Error loading file {file_path}: {e}")
            return []
    
    async def store_template(self, template_data: Dict[str, Any], index: int) -> bool:
        """Store a single template in VectorDB"""
        try:
            # Create QueryTemplate instance
            template = QueryTemplate(
                template_id=template_data['template_id'],
                natural_questions=template_data['natural_questions'],
                sql_query=template_data['sql_query'],
                sql_query_with_parameters=template_data.get('sql_query_with_parameters'),
                keywords=template_data.get('keywords', []),
                category=template_data.get('category', 'general'),
                required_params=template_data.get('required_params', []),
                optional_params=template_data.get('optional_params', []),
                examples=template_data.get('examples', [])
            )
            
            # Generate embedding text
            embedding_text = template.generate_embedding_text()
            template.embedding_text = embedding_text
            
            # Generate embedding
            embedding = await self.embeddings_manager.get_embedding(embedding_text)
            
            # Prepare point for VectorDB
            point = {
                "id": index,  # VectorDB requires numeric IDs
                "vector": embedding,
                "payload": {
                    "template_id": template.template_id,
                    "natural_questions": template.natural_questions,
                    "sql_query": template.sql_query,
                    "sql_query_with_parameters": template.sql_query_with_parameters,
                    "keywords": template.keywords,
                    "category": template.category,
                    "required_params": template.required_params,
                    "optional_params": template.optional_params,
                    "examples": template.examples,
                    "embedding_text": template.embedding_text,
                    "version": template.version,
                    "created_at": template.created_at.isoformat(),
                    "updated_at": template.updated_at.isoformat(),
                    "active": template.active
                }
            }
            
            # Insert into VectorDB
            await self.vector_store.upsert_points(
                collection_name=self.collection_name,
                points=[point]
            )
            
            return True
            
        except Exception as e:
            print(f"✗ Error storing template {template_data.get('template_id', 'unknown')}: {e}")
            return False
    
    async def load_all_templates(self, clear_existing: bool = False):
        """Load all templates from JSONL files in the data directory"""
        print(f"\n{'='*60}")
        print(f"Loading templates from {self.data_dir}")
        print(f"{'='*60}\n")
        
        # Ensure collection exists
        await self.ensure_collection_exists()
        
        # Clear existing templates if requested
        if clear_existing:
            try:
                await self.vector_store.delete_collection(self.collection_name)
                await self.ensure_collection_exists()
                print("✓ Cleared existing templates\n")
            except Exception as e:
                print(f"✗ Error clearing collection: {e}\n")
        
        # Find all JSONL files
        jsonl_files = list(self.data_dir.glob("*.jsonl"))
        
        if not jsonl_files:
            print(f"⚠ No JSONL files found in {self.data_dir}")
            return
        
        print(f"Found {len(jsonl_files)} JSONL files\n")
        
        # Process each file
        total_templates = 0
        success_count = 0
        failed_count = 0
        
        for file_path in jsonl_files:
            print(f"\nProcessing {file_path.name}...")
            templates = self.load_jsonl_file(file_path)
            
            for template_data in templates:
                total_templates += 1
                success = await self.store_template(template_data, total_templates)
                
                if success:
                    success_count += 1
                    print(f"  ✓ {template_data['template_id']}")
                else:
                    failed_count += 1
        
        # Print summary
        print(f"\n{'='*60}")
        print(f"Loading completed:")
        print(f"  - Total templates: {total_templates}")
        print(f"  - Successfully loaded: {success_count}")
        print(f"  - Failed: {failed_count}")
        print(f"{'='*60}\n")
        
        # Verify collection
        await self.verify_collection()
    
    async def verify_collection(self):
        """Verify the templates collection"""
        try:
            info = await self.vector_store.get_collection_info(self.collection_name)
            print(f"Collection verification:")
            print(f"  - Points count: {info.get('points_count', 0)}")
            print(f"  - Vectors count: {info.get('vectors_count', 0)}")
            
        except Exception as e:
            print(f"✗ Error verifying collection: {e}")


async def main():
    """Main function to load templates"""
    loader = JSONLTemplateLoader()
    
    # Load all templates (set clear_existing=True to clear existing templates)
    await loader.load_all_templates(clear_existing=False)


if __name__ == "__main__":
    # Run the loader
    asyncio.run(main())