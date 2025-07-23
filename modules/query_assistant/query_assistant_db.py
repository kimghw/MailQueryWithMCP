"""Enhanced Query Assistant with database-backed templates"""

import re
import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import os

from .schema import (
    QueryTemplate, QueryExpansion, QueryResult, 
    VectorSearchResult, DEFAULT_PARAMS
)
from .services.vector_store_http import VectorStoreHTTP
from .services.keyword_expander import KeywordExpander
from .services.db_connector import create_db_connector, DBConnector
from .services.parameter_validator import ParameterValidator
from .services.domain_ner import DomainNER, EntityType
from .services.template_loader import TemplateLoader, get_template_loader
from .repositories.preprocessing_repository import PreprocessingRepository
from .database.template_manager import TemplateManager

logger = logging.getLogger(__name__)


class QueryAssistantWithDB:
    """Enhanced Query Assistant with database-backed templates"""
    
    def __init__(
        self,
        db_config: Optional[Dict[str, Any]] = None,
        db_path: Optional[str] = None,  # For backward compatibility
        template_db_url: str = "sqlite:///templates.db",
        qdrant_url: str = "localhost",
        qdrant_port: int = 6333,
        openai_api_key: Optional[str] = None,
        use_dimension_reduction: bool = False,
        vector_size: Optional[int] = None
    ):
        """Initialize Enhanced Query Assistant
        
        Args:
            db_config: Database configuration dict
            db_path: SQLite database path (deprecated)
            template_db_url: Template database URL
            qdrant_url: Qdrant server URL
            qdrant_port: Qdrant server port
            openai_api_key: OpenAI API key
            use_dimension_reduction: Enable cost-saving dimension reduction
            vector_size: Target vector dimension for reduction
        """
        # Handle backward compatibility
        if db_config is None and db_path is not None:
            db_config = {"type": "sqlite", "path": db_path}
        elif db_config is None:
            raise ValueError("Either db_config or db_path must be provided")
        
        self.db_config = db_config
        self.db_connector = create_db_connector(db_config)
        
        # Test database connection
        if not self.db_connector.test_connection():
            raise ConnectionError("Failed to connect to database")
        
        # Initialize vector store with dimension reduction support
        self.vector_store = VectorStoreHTTP(
            qdrant_url=qdrant_url,
            qdrant_port=qdrant_port,
            api_key=openai_api_key,
            use_dimension_reduction=use_dimension_reduction,
            vector_size=vector_size
        )
        
        # Initialize template manager
        self.template_manager = TemplateManager(
            db_url=template_db_url,
            vector_store=self.vector_store
        )
        
        # Initialize template loader
        self.template_loader = get_template_loader(
            db_url=template_db_url,
            vector_store=self.vector_store
        )
        
        # Initialize other services
        self.keyword_expander = KeywordExpander()
        self.parameter_validator = ParameterValidator(self.db_connector)
        
        # Initialize NER
        try:
            preprocessing_repo = PreprocessingRepository()
            self.ner = DomainNER(preprocessing_repo)
            logger.info("Initialized NER with preprocessing dataset")
        except Exception as e:
            logger.warning(f"Failed to initialize NER with preprocessing: {e}")
            self.ner = DomainNER()
        
        # Auto-sync templates on initialization
        self._ensure_templates_synced()
    
    def _ensure_templates_synced(self):
        """Ensure templates are synced to VectorDB"""
        try:
            # Run async sync in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.template_loader.ensure_templates_synced())
            loop.close()
            
            if result.get('newly_indexed', 0) > 0:
                logger.info(f"Synced {result['newly_indexed']} templates to VectorDB")
        except Exception as e:
            logger.error(f"Error syncing templates: {e}")
    
    def reload_templates(self):
        """Reload templates from database and sync to VectorDB"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.template_manager.full_sync())
            loop.close()
            
            logger.info(f"Templates reloaded: {result}")
            self.template_loader.refresh_cache()
        except Exception as e:
            logger.error(f"Error reloading templates: {e}")
    
    def process_query(
        self, 
        user_query: str,
        category: Optional[str] = None,
        execute: bool = True,
        use_defaults: bool = False
    ) -> QueryResult:
        """Process natural language query and optionally execute SQL"""
        try:
            # Extract named entities
            entities = self.ner.extract_entities(user_query)
            entity_summary = self.ner.get_entity_summary(entities)
            
            # Extract and expand keywords
            expansion = self.keyword_expander.expand_query(user_query)
            
            # Search for matching templates
            search_results = self.template_loader.search_templates(
                query=user_query,
                keywords=expansion.expanded_keywords,
                category=category,
                limit=5,
                score_threshold=0.3
            )
            
            if not search_results:
                return QueryResult(
                    query_id="",
                    executed_sql="",
                    parameters={},
                    results=[],
                    execution_time=0.0,
                    error="No matching query template found"
                )
            
            # Use the best matching template
            best_match = search_results[0]
            template = best_match.template
            
            # Update usage statistics
            self.template_loader.update_usage_stats(template.template_id)
            
            # Extract parameters from user query with NER results
            parameters = self._extract_parameters(
                user_query, 
                template,
                expansion,
                entities
            )
            
            # Validate parameters and get suggestions
            validation_result = self.parameter_validator.validate_and_suggest(
                template=template,
                extracted_params=parameters,
                user_query=user_query
            )
            
            if not validation_result["is_valid"]:
                if use_defaults:
                    # Apply defaults logic (same as original)
                    template_defaults = template.default_params
                    
                    for param in validation_result["missing_params"]:
                        if param in template_defaults:
                            parameters[param] = template_defaults[param]
                            logger.info(f"Applied template default for {param}: {template_defaults[param]}")
                        elif param in DEFAULT_PARAMS:
                            parameters[param] = DEFAULT_PARAMS[param]
                            logger.info(f"Applied global default for {param}: {DEFAULT_PARAMS[param]}")
                        elif param in validation_result["suggestions"] and validation_result["suggestions"][param]:
                            parameters[param] = validation_result["suggestions"][param][0]
                            logger.info(f"Applied suggested value for {param}: {validation_result['suggestions'][param][0]}")
                    
                    for param, value in template_defaults.items():
                        if param not in parameters:
                            parameters[param] = value
                            logger.info(f"Applied template default for optional {param}: {value}")
                else:
                    return QueryResult(
                        query_id=template.template_id,
                        executed_sql="",
                        parameters=parameters,
                        results=[],
                        execution_time=0.0,
                        error=validation_result["clarification_message"],
                        validation_info=validation_result
                    )
            
            # Generate SQL query
            executed_sql = self._generate_sql(template, parameters)
            
            if execute:
                # Execute SQL query
                start_time = datetime.now()
                try:
                    results = self.db_connector.execute_query(executed_sql)
                    # Convert results to list of dicts if needed
                    if results and isinstance(results[0], (tuple, list)):
                        # Get column names
                        column_names = self._get_column_names(executed_sql)
                        results = [dict(zip(column_names, row)) for row in results]
                except Exception as e:
                    logger.error(f"SQL execution error: {e}")
                    return QueryResult(
                        query_id=template.template_id,
                        executed_sql=executed_sql,
                        parameters=parameters,
                        results=[],
                        execution_time=0.0,
                        error=str(e)
                    )
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                return QueryResult(
                    query_id=template.template_id,
                    executed_sql=executed_sql,
                    parameters=parameters,
                    results=results,
                    execution_time=execution_time,
                    matched_templates=[
                        {
                            "template_id": result.template.template_id,
                            "score": result.score,
                            "keyword_matches": result.keyword_matches
                        } for result in search_results[:3]
                    ],
                    keyword_expansion=expansion,
                    entity_summary=entity_summary
                )
            else:
                return QueryResult(
                    query_id=template.template_id,
                    executed_sql=executed_sql,
                    parameters=parameters,
                    results=[],
                    execution_time=0.0
                )
                
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return QueryResult(
                query_id="",
                executed_sql="",
                parameters={},
                results=[],
                execution_time=0.0,
                error=str(e)
            )
    
    def _extract_parameters(
        self, 
        user_query: str, 
        template: QueryTemplate,
        expansion: QueryExpansion,
        entities: List[Any]
    ) -> Dict[str, Any]:
        """Extract parameters from user query"""
        parameters = {}
        
        # Extract parameters using patterns
        patterns = {
            'period': r'최근\s*(\d+)\s*(일|주|개월|달|년)',
            'days': r'(\d+)\s*일',
            'weeks': r'(\d+)\s*주',
            'months': r'(\d+)\s*(개월|달)',
            'years': r'(\d+)\s*년',
            'limit': r'(\d+)\s*개',
            'organization': r'(KR|JA|US|MX|BR|전체)',
            'issue_type': r'(안건|지시사항|실행항목|전체)',
            'date': r'(\d{4}[-/]\d{2}[-/]\d{2})',
            'start_date': r'(\d{4}[-/]\d{2}[-/]\d{2})\s*부터',
            'end_date': r'(\d{4}[-/]\d{2}[-/]\d{2})\s*까지',
        }
        
        for param, pattern in patterns.items():
            match = re.search(pattern, user_query)
            if match:
                value = match.group(1)
                if param in ['days', 'weeks', 'months', 'years', 'limit']:
                    parameters[param] = int(value)
                else:
                    parameters[param] = value
        
        # Extract from NER entities
        for entity in entities:
            if entity.entity_type == EntityType.ORGANIZATION and 'organization' not in parameters:
                parameters['organization'] = entity.value
            elif entity.entity_type == EntityType.DATE:
                if 'date' not in parameters:
                    parameters['date'] = entity.value
            elif entity.entity_type == EntityType.PERIOD:
                if 'period' not in parameters:
                    parameters['period'] = entity.value
        
        # Convert period to days if needed
        if 'period' in parameters and 'days' not in parameters:
            period_value = parameters['period']
            if '일' in period_value:
                parameters['days'] = int(re.search(r'(\d+)', period_value).group(1))
            elif '주' in period_value:
                weeks = int(re.search(r'(\d+)', period_value).group(1))
                parameters['days'] = weeks * 7
            elif '개월' in period_value or '달' in period_value:
                months = int(re.search(r'(\d+)', period_value).group(1))
                parameters['days'] = months * 30
            elif '년' in period_value:
                years = int(re.search(r'(\d+)', period_value).group(1))
                parameters['days'] = years * 365
        
        return parameters
    
    def _generate_sql(self, template: QueryTemplate, parameters: Dict[str, Any]) -> str:
        """Generate SQL query from template and parameters"""
        sql_template = template.sql_query_with_parameters or template.sql_query
        
        # Replace parameters in SQL template
        for param, value in parameters.items():
            placeholder = f"{{{param}}}"
            if placeholder in sql_template:
                # Handle different value types
                if isinstance(value, str):
                    sql_template = sql_template.replace(placeholder, f"'{value}'")
                else:
                    sql_template = sql_template.replace(placeholder, str(value))
        
        return sql_template
    
    def _get_column_names(self, sql: str) -> List[str]:
        """Extract column names from SQL query"""
        # Simple extraction - can be improved
        select_match = re.search(r'SELECT\s+(.*?)\s+FROM', sql, re.IGNORECASE | re.DOTALL)
        if select_match:
            columns_str = select_match.group(1)
            # Handle simple column lists
            columns = [col.strip() for col in columns_str.split(',')]
            # Extract aliases
            column_names = []
            for col in columns:
                if ' AS ' in col.upper():
                    column_names.append(col.split()[-1])
                elif ' ' in col:
                    column_names.append(col.split()[-1])
                else:
                    column_names.append(col)
            return column_names
        return []
    
    def get_template_stats(self) -> Dict[str, Any]:
        """Get template statistics"""
        return self.template_manager.get_statistics()
    
    def create_template(self, template_data: Dict[str, Any]) -> bool:
        """Create a new template"""
        try:
            template = self.template_manager.create_template(template_data)
            # Trigger sync
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.template_manager.sync_to_vectordb())
            loop.close()
            return True
        except Exception as e:
            logger.error(f"Error creating template: {e}")
            return False