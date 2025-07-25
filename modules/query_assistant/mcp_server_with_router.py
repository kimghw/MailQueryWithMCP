"""Enhanced MCP Server with Query Router for SQL Templates and VectorDB"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, date
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
import mcp.types as types
from pydantic import BaseModel, Field

from .query_assistant import QueryAssistant
from .schema import QueryResult
from .services.query_router import QueryRouter, QueryType, QueryRoute
from .services.enhanced_date_handler import EnhancedDateHandler
from .services.query_scope_handler import QueryScopeHandler

logger = logging.getLogger(__name__)


class EnhancedQueryRequest(BaseModel):
    """Enhanced request model with LLM-extracted parameters"""
    query: str = Field(..., description="Natural language query")
    
    # LLM이 추출한 파라미터들
    extracted_dates: Optional[Dict[str, str]] = Field(
        None, 
        description="LLM-extracted date parameters"
    )
    extracted_keywords: Optional[List[str]] = Field(
        None,
        description="LLM-extracted keywords from the query"
    )
    query_scope: Optional[str] = Field(
        None,
        description="Query scope: 'all' (모든 패널/기관), 'one' (단일), 'more' (2개 이상)"
    )
    
    # 라우팅 힌트
    force_route: Optional[str] = Field(
        None,
        description="Force specific route: 'sql', 'vectordb', 'hybrid'"
    )
    
    # 기존 파라미터
    category: Optional[str] = Field(None, description="Query category filter")
    execute: bool = Field(True, description="Whether to execute the SQL")
    limit: Optional[int] = Field(None, description="Result limit")
    use_defaults: bool = Field(False, description="Use default values for missing parameters")


class QueryResponse(BaseModel):
    """Unified response model for all query types"""
    status: str
    query_type: str  # 'sql_template', 'vectordb', 'hybrid'
    results: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    sql_query: Optional[str] = None
    matched_template: Optional[Dict[str, Any]] = None
    vectordb_results: Optional[List[Dict[str, Any]]] = None
    routing_info: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class EnhancedIacsGraphQueryServer:
    """Enhanced MCP Server with Query Router"""
    
    def __init__(self, db_config: Optional[Dict[str, Any]] = None, db_path: Optional[str] = None, 
                 qdrant_url: str = "localhost", qdrant_port: int = 6333,
                 openai_api_key: Optional[str] = None,
                 vectordb_config: Optional[Dict[str, Any]] = None):
        self.server = Server("iacsgraph-query-assistant-with-router")
        
        # Handle backward compatibility
        if db_config is None and db_path is not None:
            db_config = {"type": "sqlite", "path": db_path}
        
        # Initialize components
        self.query_assistant = QueryAssistant(
            db_config=db_config,
            qdrant_url=qdrant_url,
            qdrant_port=qdrant_port,
            openai_api_key=openai_api_key
        )
        
        self.query_router = QueryRouter()
        self.date_handler = EnhancedDateHandler()
        self.scope_handler = QueryScopeHandler()
        
        # VectorDB client (placeholder for actual implementation)
        self.vectordb_client = self._init_vectordb_client(vectordb_config)
        
        # Register handlers
        self._register_handlers()
    
    def _init_vectordb_client(self, config: Optional[Dict[str, Any]]) -> Optional[Any]:
        """Initialize VectorDB client if configured"""
        # TODO: Implement actual VectorDB client initialization
        if config:
            logger.info("VectorDB client configuration received")
        return None
        
    def _register_handlers(self):
        """Register MCP protocol handlers"""
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """List available tools"""
            return [
                Tool(
                    name="query_with_routing",
                    description="""Execute query with automatic routing to SQL templates or VectorDB.
                    
The system will automatically determine whether to use:
- SQL templates for structured data queries (의제, 응답, 통계 등)
- VectorDB for document/content search (규정, 가이드라인, 문서 등)
- Hybrid mode for queries requiring both

Claude should extract:
1. Dates from the query
2. Important keywords
3. Query scope ('all', 'one', 'more')
4. Optional: force_route to override automatic routing

The query will be automatically routed based on its content.""",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Natural language query"
                            },
                            "extracted_dates": {
                                "type": "object",
                                "description": "LLM-extracted dates",
                                "properties": {
                                    "start": {"type": "string"},
                                    "end": {"type": "string"},
                                    "days": {"type": "string"},
                                    "date": {"type": "string"}
                                }
                            },
                            "extracted_keywords": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Keywords extracted by LLM"
                            },
                            "query_scope": {
                                "type": "string",
                                "enum": ["all", "one", "more"],
                                "description": "Query scope"
                            },
                            "force_route": {
                                "type": "string",
                                "enum": ["sql", "vectordb", "hybrid"],
                                "description": "Force specific routing"
                            },
                            "category": {"type": "string"},
                            "execute": {"type": "boolean", "default": True},
                            "limit": {"type": "integer"},
                            "use_defaults": {"type": "boolean", "default": False}
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="check_query_route",
                    description="Check how a query would be routed without executing it",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Query to check routing for"
                            }
                        },
                        "required": ["query"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Optional[Dict[str, Any]] = None) -> List[TextContent]:
            """Handle tool calls"""
            try:
                if name == "query_with_routing":
                    request = EnhancedQueryRequest(**arguments)
                    response = await self.query_with_routing(request)
                    
                    return [TextContent(
                        type="text",
                        text=self._format_response(response)
                    )]
                
                elif name == "check_query_route":
                    query = arguments.get("query", "")
                    route = self.query_router.route_query(query)
                    
                    return [TextContent(
                        type="text",
                        text=f"Query routing analysis:\\n"
                             f"Route: {route.query_type.value}\\n"
                             f"Confidence: {route.confidence:.2f}\\n"
                             f"Reason: {route.reason}\\n"
                             f"Metadata: {route.metadata}"
                    )]
                
                else:
                    return [TextContent(
                        type="text",
                        text=f"Unknown tool: {name}"
                    )]
                    
            except Exception as e:
                logger.error(f"Error in tool {name}: {str(e)}")
                return [TextContent(
                    type="text",
                    text=f"Error: {str(e)}"
                )]
    
    async def query_with_routing(self, request: EnhancedQueryRequest) -> QueryResponse:
        """Execute query with automatic routing"""
        try:
            # Determine route
            if request.force_route:
                route_type = {
                    "sql": QueryType.SQL_TEMPLATE,
                    "vectordb": QueryType.VECTORDB,
                    "hybrid": QueryType.HYBRID
                }.get(request.force_route, QueryType.SQL_TEMPLATE)
                
                route = QueryRoute(
                    query_type=route_type,
                    confidence=1.0,
                    reason="Forced routing",
                    metadata={"forced": True}
                )
            else:
                # Automatic routing
                context = {
                    "keywords": request.extracted_keywords,
                    "scope": request.query_scope
                }
                route = self.query_router.route_query(request.query, context)
            
            # Execute based on route
            if route.query_type == QueryType.SQL_TEMPLATE:
                return await self._handle_sql_query(request, route)
            elif route.query_type == QueryType.VECTORDB:
                return await self._handle_vectordb_query(request, route)
            else:  # HYBRID
                return await self._handle_hybrid_query(request, route)
                
        except Exception as e:
            logger.error(f"Query routing error: {str(e)}")
            return QueryResponse(
                status="error",
                query_type="unknown",
                results=[],
                metadata={},
                error=str(e)
            )
    
    async def _handle_sql_query(self, request: EnhancedQueryRequest, route: QueryRoute) -> QueryResponse:
        """Handle SQL template query"""
        # Process date parameters
        date_params = None
        if request.extracted_dates:
            date_params = self.date_handler.process_extracted_dates(request.extracted_dates)
        
        # Process scope
        scope_info = None
        if request.query_scope:
            scope_info = self.scope_handler.process_scope(request.query_scope, [])
        
        # Execute query
        result = await self.query_assistant.query(
            request.query,
            category=request.category,
            execute=request.execute,
            limit=request.limit,
            use_defaults=request.use_defaults,
            llm_params={
                "extracted_dates": date_params,
                "extracted_keywords": request.extracted_keywords,
                "query_scope": scope_info
            }
        )
        
        return QueryResponse(
            status=result.status,
            query_type="sql_template",
            results=result.data or [],
            metadata=result.metadata or {},
            sql_query=result.sql_query,
            matched_template=result.matched_template,
            routing_info={
                "route": route.query_type.value,
                "confidence": route.confidence,
                "reason": route.reason
            }
        )
    
    async def _handle_vectordb_query(self, request: EnhancedQueryRequest, route: QueryRoute) -> QueryResponse:
        """Handle VectorDB query"""
        if not self.vectordb_client:
            return QueryResponse(
                status="error",
                query_type="vectordb",
                results=[],
                metadata={},
                error="VectorDB client not configured",
                routing_info={
                    "route": route.query_type.value,
                    "confidence": route.confidence,
                    "reason": route.reason
                }
            )
        
        # TODO: Implement actual VectorDB search
        # This is a placeholder implementation
        return QueryResponse(
            status="success",
            query_type="vectordb",
            results=[],
            metadata={
                "message": "VectorDB search not yet implemented",
                "query": request.query,
                "keywords": request.extracted_keywords
            },
            routing_info={
                "route": route.query_type.value,
                "confidence": route.confidence,
                "reason": route.reason
            }
        )
    
    async def _handle_hybrid_query(self, request: EnhancedQueryRequest, route: QueryRoute) -> QueryResponse:
        """Handle hybrid query (SQL + VectorDB)"""
        # Execute both queries in parallel
        sql_task = self._handle_sql_query(request, route)
        vectordb_task = self._handle_vectordb_query(request, route)
        
        sql_response, vectordb_response = await asyncio.gather(sql_task, vectordb_task)
        
        # Merge results
        return QueryResponse(
            status="success" if sql_response.status == "success" else sql_response.status,
            query_type="hybrid",
            results=sql_response.results,
            metadata={
                "sql_metadata": sql_response.metadata,
                "vectordb_metadata": vectordb_response.metadata
            },
            sql_query=sql_response.sql_query,
            matched_template=sql_response.matched_template,
            vectordb_results=vectordb_response.results,
            routing_info={
                "route": route.query_type.value,
                "confidence": route.confidence,
                "reason": route.reason
            }
        )
    
    def _format_response(self, response: QueryResponse) -> str:
        """Format response for display"""
        lines = []
        lines.append(f"Query Type: {response.query_type}")
        lines.append(f"Status: {response.status}")
        
        if response.routing_info:
            lines.append(f"Routing: {response.routing_info}")
        
        if response.error:
            lines.append(f"Error: {response.error}")
            return "\\n".join(lines)
        
        if response.sql_query:
            lines.append(f"\\nSQL Query:\\n{response.sql_query}")
        
        if response.matched_template:
            lines.append(f"\\nMatched Template: {response.matched_template.get('template_id', 'unknown')}")
        
        if response.results:
            lines.append(f"\\nResults ({len(response.results)} rows):")
            for i, row in enumerate(response.results[:5]):
                lines.append(f"  {i+1}. {row}")
            if len(response.results) > 5:
                lines.append(f"  ... and {len(response.results) - 5} more rows")
        
        if response.vectordb_results:
            lines.append(f"\\nVectorDB Results ({len(response.vectordb_results)} documents):")
            for i, doc in enumerate(response.vectordb_results[:3]):
                lines.append(f"  {i+1}. {doc}")
        
        return "\\n".join(lines)
    
    async def run(self):
        """Run the MCP server"""
        async with stdio_server() as (read_stream, write_stream):
            init_options = InitializationOptions(
                server_name="iacsgraph-query-assistant-with-router",
                server_version="1.1.0",
                capabilities=self.server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                )
            )
            
            await self.server.run(
                read_stream,
                write_stream,
                init_options
            )


def main():
    """Main entry point"""
    import sys
    import os
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Create server
    server = EnhancedIacsGraphQueryServer(
        db_path=os.environ.get("IACSGRAPH_DB_PATH", "iacsgraph.db"),
        qdrant_url=os.environ.get("QDRANT_URL", "localhost"),
        qdrant_port=int(os.environ.get("QDRANT_PORT", "6333")),
        openai_api_key=os.environ.get("OPENAI_API_KEY")
    )
    
    # Run server
    asyncio.run(server.run())


if __name__ == "__main__":
    main()