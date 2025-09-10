"""Query Tools for MCP Server"""

import logging
from typing import Any, Dict, List, Optional

from mcp.types import Tool
from pydantic import BaseModel, Field

from infra.core.logger import get_logger
from ..query_assistant import QueryAssistant
from ..mail_data_refresher import MailDataRefresher
from ..utils.logger_config import get_query_logger

logger = get_query_logger()


class EnhancedQueryRequest(BaseModel):
    """Enhanced request model with LLM-extracted parameters"""
    query: str = Field(..., description="Natural language query")
    
    # LLM이 추출한 파라미터들
    extracted_period: Optional[Dict[str, str]] = Field(
        None, 
        description="LLM-extracted period with start and end dates in YYYY-MM-DD format"
    )
    extracted_keywords: Optional[List[str]] = Field(
        None,
        description="LLM-extracted keywords from the query"
    )
    extracted_organization: Optional[str] = Field(
        None,
        description="Organization code extracted from query"
    )
    query_scope: str = Field(
        "all",
        description="Query scope: 'all' (모든 패널/기관), 'one' (단일), 'more' (2개 이상)"
    )
    intent: str = Field(
        "search",
        description="Query intent: 'search' (검색), 'list' (목록), 'analyze' (분석), 'count' (개수)"
    )
    
    # 기존 파라미터
    category: Optional[str] = Field(None, description="Query category filter")
    execute: bool = Field(True, description="Whether to execute the SQL")
    limit: int = Field(10, description="Result limit")
    use_defaults: bool = Field(True, description="Use default values for missing parameters")


class QueryTools:
    """Query tools for MCP Server"""
    
    def __init__(self, query_assistant: QueryAssistant, mail_refresher: MailDataRefresher):
        self.query_assistant = query_assistant
        self.mail_refresher = mail_refresher
        
        logger.info("🛠️ QueryTools initialized")
    
    def get_tools(self) -> List[Tool]:
        """Get available tools"""
        return [
            Tool(
                name="simple_query",
                title="🔍 Simple Query",
                description="Execute a simple database query",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The query to execute"
                        }
                    },
                    "required": ["query"]
                }
            ),
            Tool(
                name="query",
                title="📊 Query Database",
                description="Execute natural language query with options",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Natural language query"
                        },
                        "category": {
                            "type": "string",
                            "description": "Query category filter"
                        },
                        "execute": {
                            "type": "boolean",
                            "description": "Whether to execute the SQL"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Result limit"
                        }
                    },
                    "required": ["query"]
                }
            ),
            Tool(
                name="query_with_llm_params",
                title="🤖 Query with LLM Parameters",
                description="Retrieve the emails discussing IACS GPG, panels, and working groups.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Natural language query"
                        },
                        "extracted_period": {
                            "type": "object",
                            "description": "Period with start and end dates",
                            "properties": {
                                "start": {
                                    "type": "string",
                                    "description": "Start date (YYYY-MM-DD)"
                                },
                                "end": {
                                    "type": "string",
                                    "description": "End date (YYYY-MM-DD)"
                                }
                            },
                            "required": ["start", "end"]
                        },
                        "extracted_keywords": {
                            "type": "array",
                            "description": "Keywords from the query (required)",
                            "items": {
                                "type": "string"
                            }
                        },
                        "extracted_organization": {
                            "type": "string",
                            "description": "Organization code (KR, NK, etc.) - defaults to KR if not provided",
                            "default": "KR"
                        },
                        "query_scope": {
                            "type": "string",
                            "description": "Query scope: all, one, or more",
                            "enum": ["all", "one", "more"]
                        },
                        "intent": {
                            "type": "string",
                            "description": "Query intent: search, list, analyze, or count (required)",
                            "enum": ["search", "list", "analyze", "count"]
                        }
                    },
                    "required": ["query", "extracted_keywords", "extracted_organization", "intent"]
                }
            )
        ]
    
    async def execute_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a tool by name"""
        if name == "simple_query":
            return await self._handle_legacy_query(arguments)
            
        elif name == "query_with_llm_params":
            # Set default values for required fields if not provided
            if 'extracted_organization' not in arguments or not arguments.get('extracted_organization'):
                arguments['extracted_organization'] = 'KR'
            
            logger.info(f"🤖 [QueryTools] Processing query_with_llm_params")
            logger.info(f"  • Query: {arguments.get('query')}")
            logger.info(f"  • Keywords: {arguments.get('extracted_keywords')}")
            logger.info(f"  • Organization: {arguments.get('extracted_organization')}")
            logger.info(f"  • Period: {arguments.get('extracted_period')}")
            logger.info(f"  • Intent: {arguments.get('intent')}")
            
            request = EnhancedQueryRequest(**arguments)
            return await self._handle_enhanced_query(request)
            
        elif name == "query":
            return await self._handle_legacy_query(arguments)
            
        else:
            raise ValueError(f"Unknown tool: {name}")
    
    async def _handle_legacy_query(self, arguments: Dict[str, Any]) -> Any:
        """Handle legacy query request"""
        logger.info("🔍 [QueryTools] Processing legacy query")
        
        query_text = arguments.get("query", "")
        category = arguments.get("category", None)
        execute = arguments.get("execute", True)
        limit = arguments.get("limit", 10)
        
        # Note: process_query is not async, so we don't need await
        result = self.query_assistant.process_query(
            user_query=query_text,
            category=category,
            execute=execute,
            use_defaults=True
        )
        
        # Apply limit if provided
        if limit and hasattr(result, 'results') and result.results:
            result.results = result.results[:limit]
        
        return result
    
    async def _handle_enhanced_query(self, request: EnhancedQueryRequest) -> Dict[str, Any]:
        """Handle enhanced query request"""
        logger.info("🤖 [QueryTools] Processing enhanced query")
        try:
            # Simple approach - pass parameters directly to query assistant
            # The query assistant should handle the parameter extraction and processing
            
            # Prepare execution parameters
            search_keywords = request.extracted_keywords.copy() if request.extracted_keywords else []
            
            execution_params = {
                'organization_code': request.extracted_organization or 'KR',
                'organization': request.extracted_organization or 'KR',
                'keywords': search_keywords,
                'llm_keywords': request.extracted_keywords,
                'expanded_keywords': list(set(search_keywords)),
                'intent': request.intent,
                'extracted_period': request.extracted_period,
                'extracted_keywords': request.extracted_keywords,
                'extracted_organization': request.extracted_organization,
                'extracted_intent': request.intent
            }
            
            # Add period if provided
            if request.extracted_period:
                execution_params['date_range'] = {
                    'type': 'range',
                    'from': request.extracted_period['start'],
                    'to': request.extracted_period['end']
                }
                try:
                    from datetime import datetime
                    start = datetime.fromisoformat(request.extracted_period['start'])
                    end = datetime.fromisoformat(request.extracted_period['end'])
                    execution_params['days'] = (end - start).days + 1
                except:
                    execution_params['days'] = 30
            
            # Execute query
            logger.info(f"🚀 [QueryTools] Executing query with params:")
            logger.info(f"  • Keywords for search: {search_keywords}")
            logger.info(f"  • Organization: {execution_params.get('organization_code')}")
            logger.info(f"  • Date range: {execution_params.get('date_range')}")
            logger.info(f"  • Intent: {execution_params.get('intent')}")
            
            result = self.query_assistant.process_query(
                user_query=request.query,
                category=request.category,
                execute=request.execute,
                use_defaults=request.use_defaults,
                additional_params=execution_params
            )
            
            logger.info(f"✅ [QueryTools] Query executed successfully")
            logger.info(f"  • SQL executed: {getattr(result, 'executed_sql', 'N/A')[:200]}...")
            logger.info(f"  • Results count: {len(getattr(result, 'results', []))}")
            logger.info(f"  • Execution time: {getattr(result, 'execution_time', 0):.2f}s")
            
            return {
                'result': result,
                'extracted_params': execution_params,
                'rule_based_params': {},  # Simplified - no rule-based extraction
                'llm_contribution': {
                    'period': request.extracted_period,
                    'keywords': request.extracted_keywords,
                    'organization': request.extracted_organization,
                    'intent': request.intent
                }
            }
            
        except Exception as e:
            logger.error(f"Error handling enhanced query: {e}")
            return {
                'error': str(e),
                'extracted_params': {},
                'rule_based_params': {},
                'llm_contribution': {
                    'period': request.extracted_period,
                    'keywords': request.extracted_keywords,
                    'organization': request.extracted_organization,
                    'intent': request.intent
                }
            }