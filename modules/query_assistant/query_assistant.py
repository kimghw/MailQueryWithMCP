"""Main Query Assistant implementation"""

import re
import logging
import sqlite3
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
from .repositories.preprocessing_repository import PreprocessingRepository
from .templates import get_templates

logger = logging.getLogger(__name__)


class QueryAssistant:
    """Natural language to SQL query assistant"""
    
    def __init__(
        self,
        db_config: Optional[Dict[str, Any]] = None,
        db_path: Optional[str] = None,  # For backward compatibility
        qdrant_url: str = "localhost",
        qdrant_port: int = 6333,
        openai_api_key: Optional[str] = None
    ):
        """Initialize Query Assistant
        
        Args:
            db_config: Database configuration dict with keys:
                - type: "sqlite", "sqlserver", "postgresql"
                - For SQLite: path
                - For SQL Server: server, database, username, password, driver, trusted_connection
                - For PostgreSQL: host, port, database, user, password
            db_path: SQLite database path (deprecated, use db_config)
            qdrant_url: Qdrant server URL
            qdrant_port: Qdrant server port
            openai_api_key: OpenAI API key (optional, uses env var if not provided)
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
        
        # Initialize vector store with HTTP embeddings
        self.vector_store = VectorStoreHTTP(
            qdrant_url=qdrant_url,
            qdrant_port=qdrant_port,
            api_key=openai_api_key
        )
        
        # Initialize keyword expander
        self.keyword_expander = KeywordExpander()
        
        # Initialize parameter validator
        self.parameter_validator = ParameterValidator(self.db_connector)
        
        # Initialize NER with preprocessing repository
        try:
            preprocessing_repo = PreprocessingRepository()
            self.ner = DomainNER(preprocessing_repo)
            logger.info("Initialized NER with preprocessing dataset")
        except Exception as e:
            logger.warning(f"Failed to initialize NER with preprocessing: {e}")
            self.ner = DomainNER()
        
        # Index templates on initialization
        self._index_templates()
        
    def _index_templates(self):
        """Index all templates into vector store"""
        templates = get_templates()
        success = self.vector_store.index_templates(templates)
        if success:
            logger.info(f"Successfully indexed {len(templates)} templates")
        else:
            logger.error("Failed to index templates")
    
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
            
            # Search for matching templates with lower threshold
            search_results = self.vector_store.search(
                query=user_query,
                keywords=expansion.expanded_keywords,
                category=category,
                limit=5,
                score_threshold=0.3  # Lower threshold for better matching
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
                    # Apply template-specific defaults first
                    template_defaults = template.default_params
                    
                    # Apply defaults for missing required parameters
                    for param in validation_result["missing_params"]:
                        # First check template-specific defaults
                        if param in template_defaults:
                            parameters[param] = template_defaults[param]
                            logger.info(f"Applied template default for {param}: {template_defaults[param]}")
                        # Then check global defaults
                        elif param in DEFAULT_PARAMS:
                            parameters[param] = DEFAULT_PARAMS[param]
                            logger.info(f"Applied global default for {param}: {DEFAULT_PARAMS[param]}")
                        # Finally use suggestions
                        elif param in validation_result["suggestions"] and validation_result["suggestions"][param]:
                            parameters[param] = validation_result["suggestions"][param][0]
                            logger.info(f"Applied suggested value for {param}: {validation_result['suggestions'][param][0]}")
                    
                    # Apply all template defaults for optional params too
                    for param, value in template_defaults.items():
                        if param not in parameters:
                            parameters[param] = value
                            logger.info(f"Applied template default for optional {param}: {value}")
                else:
                    # Return validation result with suggestions
                    return QueryResult(
                        query_id=template.id,
                        executed_sql="",
                        parameters=parameters,
                        results=[],
                        execution_time=0.0,
                        error=validation_result["clarification_message"],
                        validation_info=validation_result  # Add validation info to response
                    )
            
            # Apply default values for optional parameters
            for param in template.optional_params:
                if param not in parameters:
                    parameters[param] = DEFAULT_PARAMS.get(param, "")
            
            # Generate SQL
            sql = self._generate_sql(template.sql_template, parameters)
            
            # Execute if requested
            if execute:
                start_time = datetime.now()
                results = self._execute_sql(sql)
                execution_time = (datetime.now() - start_time).total_seconds()
                
                # Update usage statistics
                self.vector_store.update_usage_stats(template.id)
                
                return QueryResult(
                    query_id=template.id,
                    executed_sql=sql,
                    parameters=parameters,
                    results=results,
                    execution_time=execution_time,
                    error=None
                )
            else:
                return QueryResult(
                    query_id=template.id,
                    executed_sql=sql,
                    parameters=parameters,
                    results=[],
                    execution_time=0.0,
                    error=None
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
        query: str, 
        template: QueryTemplate,
        expansion: QueryExpansion,
        entities: List = None
    ) -> Dict[str, Any]:
        """Extract parameters from user query using NER results"""
        parameters = {}
        
        # NER 기반 파라미터 추출 (우선순위 높음)
        if entities:
            for entity in entities:
                # Organization 파라미터
                if (entity.entity_type == EntityType.ORGANIZATION and 
                    "organization" in template.required_params + template.optional_params):
                    parameters["organization"] = entity.normalized_value
                    logger.info(f"NER extracted organization: {entity.normalized_value}")
                
                # Time period 파라미터
                elif (entity.entity_type == EntityType.TIME_PERIOD and 
                      any(p in ["period", "days", "weeks", "months", "years"] 
                          for p in template.required_params + template.optional_params)):
                    if isinstance(entity.normalized_value, dict):
                        if "days" in entity.normalized_value:
                            parameters["days"] = entity.normalized_value["days"]
                            parameters["period"] = entity.text
                            logger.info(f"NER extracted time period: {entity.normalized_value['days']} days")
                
                # Status 파라미터
                elif (entity.entity_type == EntityType.STATUS and 
                      "status" in template.required_params + template.optional_params):
                    parameters["status"] = entity.normalized_value
                    logger.info(f"NER extracted status: {entity.normalized_value}")
                
                # Quantity 파라미터
                elif (entity.entity_type == EntityType.QUANTITY and 
                      "limit" in template.optional_params):
                    if isinstance(entity.normalized_value, dict) and "value" in entity.normalized_value:
                        if isinstance(entity.normalized_value["value"], int):
                            parameters["limit"] = entity.normalized_value["value"]
                            logger.info(f"NER extracted limit: {entity.normalized_value['value']}")
                
                # Agenda ID 파라미터
                elif (entity.entity_type == EntityType.AGENDA_ID and 
                      "agenda_id" in template.required_params + template.optional_params):
                    parameters["agenda_id"] = entity.normalized_value
                    logger.info(f"NER extracted agenda_id: {entity.normalized_value}")
                
                # Keyword 파라미터
                elif (entity.entity_type == EntityType.KEYWORD and 
                      "keyword" in template.required_params + template.optional_params):
                    parameters["keyword"] = entity.normalized_value
                    logger.info(f"NER extracted keyword: {entity.normalized_value}")
        
        # Extract period parameter
        if "period" in template.required_params or "period" in template.optional_params:
            period_match = re.search(r'(\d+)\s*(일|주|개월|년|days?|weeks?|months?|years?)', query)
            if period_match:
                value = int(period_match.group(1))
                unit = period_match.group(2)
                
                # Convert to days
                if unit in ["주", "weeks", "week"]:
                    parameters["days"] = value * 7
                elif unit in ["개월", "months", "month"]:
                    parameters["days"] = value * 30
                elif unit in ["년", "years", "year"]:
                    parameters["days"] = value * 365
                else:
                    parameters["days"] = value
                
                parameters["period"] = period_match.group(0)
        
        # Extract time period for specific summary templates
        if "weeks" in template.optional_params:
            weeks_match = re.search(r'(\d+)\s*(주|weeks?)', query)
            if weeks_match:
                parameters["weeks"] = int(weeks_match.group(1))
                
        if "months" in template.optional_params:
            months_match = re.search(r'(\d+)\s*(개월|달|months?)', query)
            if months_match:
                parameters["months"] = int(months_match.group(1))
                
        if "quarters" in template.optional_params:
            quarters_match = re.search(r'(\d+)\s*(분기|quarters?)', query)
            if quarters_match:
                parameters["quarters"] = int(quarters_match.group(1)) * 3  # Convert quarters to months
                
        if "years" in template.optional_params:
            years_match = re.search(r'(\d+)\s*(년|년간|years?)', query)
            if years_match:
                parameters["years"] = int(years_match.group(1))
        
        # Extract organization parameter
        if "organization" in template.required_params:
            # Look for known organization names (including short codes)
            orgs = ["KRSDTP", "KOMDTP", "KMDTP", "GMDTP", "BMDTP", "PLDTP", 
                    "KR", "BV", "CCS", "CRS", "DNV", "IRS", "NK", "PRS", "RINA", "LR", "ABS"]
            for org in orgs:
                if org.lower() in query.lower():
                    parameters["organization"] = org
                    break
        
        # Extract status parameter
        if "status" in template.required_params:
            status_map = {
                "승인": "approved",
                "반려": "rejected", 
                "미결정": "pending",
                "approved": "approved",
                "rejected": "rejected",
                "pending": "pending"
            }
            for korean, english in status_map.items():
                if korean in query:
                    parameters["status"] = english
                    break
        
        # Extract keyword parameter for search
        if "keyword" in template.required_params:
            # Extract quoted text
            quoted = re.findall(r'"([^"]*)"', query)
            if quoted:
                parameters["keyword"] = quoted[0]
            else:
                # Use the most relevant expanded keyword
                if expansion.expanded_keywords:
                    parameters["keyword"] = expansion.expanded_keywords[0]
        
        # Extract limit if mentioned
        limit_match = re.search(r'(\d+)\s*개', query)
        if limit_match:
            parameters["limit"] = int(limit_match.group(1))
        
        # Period format for summary reports
        if "period_format" in template.optional_params:
            if "주간" in query or "weekly" in query.lower():
                parameters["period_format"] = "%Y-%W"
                parameters["days"] = parameters.get("days", 30)
            elif "월간" in query or "monthly" in query.lower():
                parameters["period_format"] = "%Y-%m"
                parameters["days"] = parameters.get("days", 90)
        
        return parameters
    
    def _generate_sql(self, template: str, parameters: Dict[str, Any]) -> str:
        """Generate SQL from template and parameters"""
        sql = template
        
        # Replace placeholders
        for param, value in parameters.items():
            placeholder = "{" + param + "}"
            if placeholder in sql:
                # Handle different value types
                if isinstance(value, str):
                    sql = sql.replace(placeholder, str(value))
                elif isinstance(value, (int, float)):
                    sql = sql.replace(placeholder, str(value))
                else:
                    sql = sql.replace(placeholder, str(value))
        
        return sql.strip()
    
    def _execute_sql(self, sql: str) -> List[Dict[str, Any]]:
        """Execute SQL query and return results"""
        try:
            return self.db_connector.execute_query(sql)
        except Exception as e:
            logger.error(f"Error executing SQL: {e}")
            raise
    
    def get_suggestions(
        self, 
        partial_query: str
    ) -> List[Tuple[str, float]]:
        """Get query suggestions based on partial input"""
        try:
            # Extract keywords from partial query
            expansion = self.keyword_expander.expand_query(partial_query)
            
            # Search for matching templates
            search_results = self.vector_store.search(
                query=partial_query,
                keywords=expansion.expanded_keywords,
                limit=10,
                score_threshold=0.3  # Lower threshold for suggestions
            )
            
            # Format suggestions
            suggestions = []
            for result in search_results:
                suggestion = (result.template.natural_query, result.score)
                suggestions.append(suggestion)
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Error getting suggestions: {e}")
            return []
    
    def get_popular_queries(self, limit: int = 10) -> List[QueryTemplate]:
        """Get most frequently used query templates"""
        return self.vector_store.get_popular_templates(limit)
    
    def analyze_query(self, user_query: str) -> Dict[str, Any]:
        """Analyze user query without executing"""
        # Extract named entities
        entities = self.ner.extract_entities(user_query)
        entity_summary = self.ner.get_entity_summary(entities)
        
        # Get query expansion
        expansion = self.keyword_expander.expand_query(user_query)
        
        # Search for matching templates
        search_results = self.vector_store.search(
            query=user_query,
            keywords=expansion.expanded_keywords,
            limit=3
        )
        
        # Prepare analysis
        analysis = {
            "original_query": user_query,
            "named_entities": [
                {
                    "text": e.text,
                    "type": e.entity_type.value,
                    "normalized": e.normalized_value,
                    "confidence": e.confidence,
                    "position": [e.start_pos, e.end_pos]
                }
                for e in entities
            ],
            "entity_summary": entity_summary,
            "extracted_keywords": expansion.original_keywords,
            "expanded_keywords": expansion.expanded_keywords,
            "missing_info": expansion.missing_params,
            "suggestions": expansion.suggestions,
            "confidence": expansion.confidence_score,
            "matching_templates": []
        }
        
        for result in search_results:
            template_info = {
                "id": result.template.id,
                "natural_query": result.template.natural_query,
                "category": result.template.category,
                "match_score": result.score,
                "keyword_matches": result.keyword_matches,
                "required_params": result.template.required_params
            }
            analysis["matching_templates"].append(template_info)
        
        return analysis