"""Vector database uploader for templates with individual embeddings"""

import json
import os
import uuid
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import requests
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()
logger = logging.getLogger(__name__)


class VectorUploader:
    """Upload templates to vector database with individual embeddings per question/component"""
    
    def __init__(
        self,
        qdrant_url: str = None,
        qdrant_port: int = None,
        collection_name: str = None,
        embedding_model: str = "text-embedding-3-large",
        vector_size: int = 3072
    ):
        self.qdrant_url = qdrant_url or os.getenv('QDRANT_URL', 'localhost')
        self.qdrant_port = qdrant_port or int(os.getenv('QDRANT_PORT', 6333))
        self.collection_name = collection_name or os.getenv('QDRANT_COLLECTION_NAME', 'query_templates_unified')
        self.embedding_model = embedding_model
        self.vector_size = vector_size
        self.api_key = os.getenv('OPENAI_API_KEY')
        
        if not self.api_key:
            raise ValueError("OpenAI API key is required for embeddings")
        
        # Initialize Qdrant client
        self.client = QdrantClient(
            url=self.qdrant_url, 
            port=self.qdrant_port,
            check_compatibility=False
        )
        
    def create_collection(self, recreate: bool = False):
        """Create or recreate the collection"""
        try:
            if recreate:
                self.client.delete_collection(self.collection_name)
                logger.info(f"Deleted existing collection: {self.collection_name}")
        except:
            pass
            
        # Check if collection exists
        try:
            self.client.get_collection(self.collection_name)
            logger.info(f"Collection {self.collection_name} already exists")
        except:
            # Create new collection
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE
                )
            )
            logger.info(f"Created collection: {self.collection_name}")
        
    def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for multiple texts in one API call"""
        if not texts:
            return []
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "input": texts,
            "model": self.embedding_model
        }
        
        response = requests.post(
            "https://api.openai.com/v1/embeddings",
            headers=headers,
            json=data
        )
        response.raise_for_status()
        
        # Extract embeddings in order
        embeddings = []
        for item in response.json()['data']:
            embeddings.append(item['embedding'])
        
        return embeddings
        
    def upload_templates(self, templates: List[Dict[str, Any]], batch_size: int = 50) -> int:
        """Upload templates to Qdrant with individual embeddings for each natural question"""
        
        total_uploaded = 0
        all_embedding_requests = []
        
        # First, collect all texts that need embedding
        for template in templates:
            # Skip config templates
            if template.get('template_id', '').startswith('_config'):
                continue
                
            query_info = template.get('query_info', {})
            sql_template = template.get('sql_template', {})
            
            # Get texts to embed
            texts_to_embed = []
            
            # 1. system description separately
            system_desc = sql_template.get('system', '')
            if system_desc and system_desc.strip():
                texts_to_embed.append({
                    'text': system_desc,
                    'type': 'system',
                    'template': template
                })
            
            # 2. sql user separately
            sql_user = sql_template.get('user', '')
            if sql_user and sql_user.strip():
                texts_to_embed.append({
                    'text': sql_user,
                    'type': 'sql_user',
                    'template': template
                })
            
            # 3. query_info user separately
            user_query = query_info.get('user', '')
            if user_query and user_query.strip():
                texts_to_embed.append({
                    'text': user_query,
                    'type': 'user',
                    'template': template
                })
            
            # 4. Each natural question individually
            natural_questions = query_info.get('natural_questions', [])
            for question in natural_questions:
                if question.strip():
                    texts_to_embed.append({
                        'text': question,
                        'type': 'natural_question',
                        'template': template,
                        'question': question
                    })
            
            all_embedding_requests.extend(texts_to_embed)
        
        # Process embeddings in batches
        points = []
        
        for batch_start in range(0, len(all_embedding_requests), batch_size):
            batch_end = min(batch_start + batch_size, len(all_embedding_requests))
            batch_requests = all_embedding_requests[batch_start:batch_end]
            
            try:
                # Get texts for batch
                texts = [req['text'] for req in batch_requests]
                
                # Get embeddings
                logger.info(f"Getting embeddings for batch {batch_start//batch_size + 1} ({len(texts)} texts)")
                embeddings = self.get_embeddings_batch(texts)
                
                # Create points for each embedding
                for req, embedding in zip(batch_requests, embeddings):
                    template = req['template']
                    query_info = template.get('query_info', {})
                    sql_template = template.get('sql_template', {})
                    
                    # Create payload with embedding type info
                    payload = {
                        "template_id": template.get('template_id', ''),
                        "template_category": template.get('template_category', ''),
                        "template_version": template.get('template_version', ''),
                        "description": query_info.get('description', ''),
                        "user": query_info.get('user', ''),
                        "natural_questions": query_info.get('natural_questions', []),
                        "keywords": query_info.get('keywords', []),
                        "sql_query": sql_template.get('query', ''),
                        "sql_system": sql_template.get('system', ''),
                        "sql_user": sql_template.get('user', ''),
                        "target_scope": template.get('target_scope', {}),
                        "parameters": template.get('parameters', []),
                        "related_tables": template.get('related_tables', []),
                        "uploaded_at": datetime.now().isoformat(),
                        "embedding_type": req['type'],
                        "embedded_text": req['text']
                    }
                    
                    # Add specific question if it's a natural question embedding
                    if req['type'] == 'natural_question':
                        payload['embedded_question'] = req['question']
                    
                    point = PointStruct(
                        id=str(uuid.uuid4()),
                        vector=embedding,
                        payload=payload
                    )
                    points.append(point)
                
            except Exception as e:
                logger.error(f"Error processing batch starting at {batch_start}: {e}")
                continue
        
        # Upload all points in batches
        for batch_start in range(0, len(points), 100):
            batch_end = min(batch_start + 100, len(points))
            batch_points = points[batch_start:batch_end]
            
            try:
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=batch_points
                )
                total_uploaded += len(batch_points)
                logger.info(f"Uploaded batch of {len(batch_points)} points")
                    
            except Exception as e:
                logger.error(f"Error uploading batch: {e}")
                continue
                
        logger.info(f"Successfully uploaded {total_uploaded} points to Qdrant")
        return total_uploaded
        
    def get_template_count(self) -> int:
        """Get count of templates in collection"""
        info = self.client.get_collection(self.collection_name)
        return info.points_count
    
    def upload_from_file(self, template_file: str = None) -> int:
        """Load templates from file and upload to vector database"""
        if template_file is None:
            # Default template file path
            template_file = Path(__file__).parent.parent / "data" / "unified" / "query_templates_unified.json"
        
        with open(template_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        templates = data.get('templates', [])
        logger.info(f"Found {len(templates)} templates in {template_file}")
        
        # Create/recreate collection
        self.create_collection(recreate=True)
        
        # Upload templates
        return self.upload_templates(templates)


def main():
    """Main function to upload templates"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Upload templates to vector database')
    parser.add_argument('--file', type=str, help='Template file path')
    parser.add_argument('--recreate', action='store_true', help='Recreate collection')
    args = parser.parse_args()
    
    # Initialize uploader
    uploader = VectorUploader()
    
    # Upload from file
    if args.file:
        count = uploader.upload_from_file(args.file)
    else:
        count = uploader.upload_from_file()
    
    print(f"Upload complete! Total vectors: {count}")
    print(f"Templates in collection: {uploader.get_template_count()}")


if __name__ == "__main__":
    main()