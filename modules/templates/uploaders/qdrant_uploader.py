"""Qdrant vector database uploader for templates"""

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

load_dotenv()
logger = logging.getLogger(__name__)


class QdrantTemplateUploader:
    """Upload templates to Qdrant vector database"""
    
    def __init__(
        self,
        qdrant_url: str = None,
        qdrant_port: int = None,
        collection_name: str = "query_templates_unified",
        embedding_model: str = "text-embedding-3-large",
        vector_size: int = 3072
    ):
        self.qdrant_url = qdrant_url or os.getenv('QDRANT_URL', 'localhost')
        self.qdrant_port = qdrant_port or int(os.getenv('QDRANT_PORT', 6333))
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        self.vector_size = vector_size
        self.api_key = os.getenv('OPENAI_API_KEY')
        
        # Initialize Qdrant client
        self.client = QdrantClient(url=self.qdrant_url, port=self.qdrant_port)
        
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
            return
        except:
            pass
            
        # Create new collection
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE)
        )
        logger.info(f"Created collection: {self.collection_name}")
        
    def get_embedding(self, text: str) -> List[float]:
        """Get embedding for text using OpenAI API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "input": text,
            "model": self.embedding_model
        }
        
        response = requests.post(
            "https://api.openai.com/v1/embeddings",
            headers=headers,
            json=data
        )
        response.raise_for_status()
        
        return response.json()['data'][0]['embedding']
        
    def prepare_template_text(self, template: Dict[str, Any]) -> str:
        """Prepare template content for embedding"""
        parts = []
        
        # Add template ID and category
        parts.append(f"Template ID: {template.get('template_id', '')}")
        parts.append(f"Category: {template.get('template_category', '')}")
        
        # Add natural questions
        query_info = template.get('query_info', {})
        questions = query_info.get('natural_questions', [])
        if questions:
            parts.append(f"Questions: {' | '.join(questions)}")
            
        # Add keywords
        keywords = query_info.get('keywords', [])
        if keywords:
            parts.append(f"Keywords: {', '.join(keywords)}")
            
        # Add SQL description
        sql_template = template.get('sql_template', {})
        if sql_template.get('system'):
            parts.append(f"Description: {sql_template['system']}")
            
        return " ".join(parts)
        
    def upload_templates(self, templates: List[Dict[str, Any]], batch_size: int = 10) -> int:
        """Upload templates to Qdrant
        
        Args:
            templates: List of template dictionaries
            batch_size: Number of templates to upload in each batch
            
        Returns:
            Number of templates uploaded
        """
        points = []
        uploaded = 0
        
        for i, template in enumerate(templates):
            try:
                # Skip config templates
                template_id = template.get('template_id', '')
                if template_id.startswith('_config'):
                    logger.debug(f"Skipping config template: {template_id}")
                    continue
                    
                # Prepare text and get embedding
                text = self.prepare_template_text(template)
                logger.debug(f"Getting embedding for template {i+1}/{len(templates)}: {template_id}")
                embedding = self.get_embedding(text)
                
                # Create point
                point = PointStruct(
                    id=str(uuid.uuid4()),
                    vector=embedding,
                    payload={
                        "template_id": template_id,
                        "template_category": template.get('template_category', ''),
                        "template_version": template.get('template_version', ''),
                        "natural_questions": template.get('query_info', {}).get('natural_questions', []),
                        "keywords": template.get('query_info', {}).get('keywords', []),
                        "sql_query": template.get('sql_template', {}).get('query', ''),
                        "sql_system": template.get('sql_template', {}).get('system', ''),
                        "sql_user": template.get('sql_template', {}).get('user', ''),
                        "target_scope": template.get('target_scope', {}),
                        "parameters": template.get('parameters', []),
                        "uploaded_at": datetime.now().isoformat()
                    }
                )
                points.append(point)
                
                # Upload in batches
                if len(points) >= batch_size:
                    self.client.upsert(
                        collection_name=self.collection_name,
                        points=points
                    )
                    uploaded += len(points)
                    logger.info(f"Uploaded batch of {len(points)} templates")
                    points = []
                    
            except Exception as e:
                logger.error(f"Error processing template {template_id}: {e}")
                continue
                
        # Upload remaining points
        if points:
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            uploaded += len(points)
            logger.info(f"Uploaded final batch of {len(points)} templates")
            
        logger.info(f"Successfully uploaded {uploaded} templates to Qdrant")
        return uploaded
        
    def get_template_count(self) -> int:
        """Get count of templates in collection"""
        info = self.client.get_collection(self.collection_name)
        return info.points_count
        
    def search_templates(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for templates using semantic search"""
        embedding = self.get_embedding(query)
        
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=embedding,
            limit=limit
        )
        
        return [{
            'template_id': r.payload.get('template_id'),
            'category': r.payload.get('template_category'),
            'score': r.score,
            'questions': r.payload.get('natural_questions', [])
        } for r in results]