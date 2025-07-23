"""Template Database Schema for Query Assistant"""

from sqlalchemy import (
    Column, String, Text, JSON, DateTime, Boolean, Integer,
    create_engine, Index, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from typing import Dict, Any, List, Optional

Base = declarative_base()


class QueryTemplateDB(Base):
    """Query Template Database Model"""
    __tablename__ = 'query_templates'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Template identification
    template_id = Column(String(100), unique=True, nullable=False, index=True)
    version = Column(String(20), default="1.0.0")
    
    # Content fields
    natural_questions = Column(Text, nullable=False)
    sql_query = Column(Text, nullable=False)
    sql_query_with_parameters = Column(Text)
    
    # Metadata
    keywords = Column(JSON, default=list)
    category = Column(String(50), nullable=False, index=True)
    required_params = Column(JSON, default=list)
    optional_params = Column(JSON, default=list)
    default_params = Column(JSON, default=dict)
    
    # Examples and documentation
    examples = Column(JSON, default=list)
    description = Column(Text)
    to_agent_prompt = Column(Text)
    
    # Vector DB sync
    vector_indexed = Column(Boolean, default=False)
    vector_id = Column(String(100))
    embedding_model = Column(String(50), default="text-embedding-3-large")
    embedding_dimension = Column(Integer, default=3072)
    
    # Statistics
    usage_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    avg_execution_time_ms = Column(Integer)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_used_at = Column(DateTime)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Indexes
    __table_args__ = (
        Index('idx_category_active', 'category', 'is_active'),
        Index('idx_vector_sync', 'vector_indexed', 'is_active'),
        UniqueConstraint('template_id', 'version', name='uq_template_version'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'template_id': self.template_id,
            'version': self.version,
            'natural_questions': self.natural_questions,
            'sql_query': self.sql_query,
            'sql_query_with_parameters': self.sql_query_with_parameters,
            'keywords': self.keywords or [],
            'category': self.category,
            'required_params': self.required_params or [],
            'optional_params': self.optional_params or [],
            'default_params': self.default_params or {},
            'examples': self.examples or [],
            'description': self.description,
            'to_agent_prompt': self.to_agent_prompt,
            'usage_count': self.usage_count,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def to_vector_payload(self) -> Dict[str, Any]:
        """Convert to VectorDB payload format"""
        return {
            'template_id': self.template_id,
            'natural_questions': self.natural_questions,
            'sql_query': self.sql_query,
            'sql_query_with_parameters': self.sql_query_with_parameters,
            'keywords': self.keywords or [],
            'category': self.category,
            'required_params': self.required_params or [],
            'optional_params': self.optional_params or [],
            'default_params': self.default_params or {},
            'examples': self.examples or [],
            'to_agent_prompt': self.to_agent_prompt,
            'version': self.version,
            'usage_count': self.usage_count,
            'embedding_model': self.embedding_model,
            'embedding_dimension': self.embedding_dimension,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None
        }


# Database setup
def create_tables(engine):
    """Create all tables"""
    Base.metadata.create_all(engine)


def get_session(db_url: str = "sqlite:///templates.db"):
    """Get database session"""
    engine = create_engine(db_url)
    create_tables(engine)
    Session = sessionmaker(bind=engine)
    return Session()