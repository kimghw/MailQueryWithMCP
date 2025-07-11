"""MCP Server for Query Assistant

Provides natural language query interface through MCP protocol.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent
import mcp.types as types
from pydantic import BaseModel, Field

from .query_assistant import QueryAssistant
from .schema import QueryResult

logger = logging.getLogger(__name__)


class QueryRequest(BaseModel):
    """Request model for natural language query"""
    query: str = Field(..., description="Natural language query")
    category: Optional[str] = Field(None, description="Query category filter")
    execute: bool = Field(True, description="Whether to execute the SQL")
    limit: Optional[int] = Field(None, description="Result limit")


class AnalyzeRequest(BaseModel):
    """Request model for query analysis"""
    query: str = Field(..., description="Natural language query to analyze")


class SuggestRequest(BaseModel):
    """Request model for query suggestions"""
    partial_query: str = Field(..., description="Partial query for suggestions")
    limit: int = Field(5, description="Number of suggestions")


class IacsGraphQueryServer:
    """MCP Server for IACSGraph Query Assistant"""
    
    def __init__(self, db_config: Optional[Dict[str, Any]] = None, db_path: Optional[str] = None, 
                 qdrant_url: str = "localhost", qdrant_port: int = 6333,
                 openai_api_key: Optional[str] = None):
        self.server = Server("iacsgraph-query-assistant")
        
        # Handle backward compatibility
        if db_config is None and db_path is not None:
            db_config = {"type": "sqlite", "path": db_path}
        
        self.query_assistant = QueryAssistant(
            db_config=db_config,
            qdrant_url=qdrant_url,
            qdrant_port=qdrant_port,
            openai_api_key=openai_api_key
        )
        
        # Register handlers
        self._register_handlers()
        
    def _register_handlers(self):
        """Register MCP protocol handlers"""
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """List available tools"""
            return [
                Tool(
                    name="query",
                    description="Execute natural language query on Email Dashboard data",
                    inputSchema=QueryRequest.model_json_schema()
                ),
                Tool(
                    name="analyze_query",
                    description="Analyze natural language query without executing",
                    inputSchema=AnalyzeRequest.model_json_schema()
                ),
                Tool(
                    name="suggest_queries",
                    description="Get query suggestions based on partial input",
                    inputSchema=SuggestRequest.model_json_schema()
                ),
                Tool(
                    name="popular_queries",
                    description="Get most frequently used queries",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "description": "Number of queries to return",
                                "default": 10
                            }
                        }
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Handle tool calls"""
            
            if name == "query":
                request = QueryRequest(**arguments)
                result = await self._handle_query(request)
                return [TextContent(type="text", text=self._format_query_result(result))]
                
            elif name == "analyze_query":
                request = AnalyzeRequest(**arguments)
                analysis = await self._handle_analyze(request)
                return [TextContent(type="text", text=self._format_analysis(analysis))]
                
            elif name == "suggest_queries":
                request = SuggestRequest(**arguments)
                suggestions = await self._handle_suggest(request)
                return [TextContent(type="text", text=self._format_suggestions(suggestions))]
                
            elif name == "popular_queries":
                limit = arguments.get("limit", 10)
                queries = await self._handle_popular_queries(limit)
                return [TextContent(type="text", text=self._format_popular_queries(queries))]
                
            else:
                raise ValueError(f"Unknown tool: {name}")
    
    async def _handle_query(self, request: QueryRequest) -> QueryResult:
        """Handle natural language query"""
        try:
            # Process query
            result = self.query_assistant.process_query(
                user_query=request.query,
                category=request.category,
                execute=request.execute
            )
            
            # Apply limit if specified
            if request.limit and result.results:
                result.results = result.results[:request.limit]
            
            return result
            
        except Exception as e:
            logger.error(f"Error handling query: {e}")
            return QueryResult(
                query_id="",
                executed_sql="",
                parameters={},
                results=[],
                execution_time=0.0,
                error=str(e)
            )
    
    async def _handle_analyze(self, request: AnalyzeRequest) -> Dict[str, Any]:
        """Handle query analysis"""
        try:
            return self.query_assistant.analyze_query(request.query)
        except Exception as e:
            logger.error(f"Error analyzing query: {e}")
            return {"error": str(e)}
    
    async def _handle_suggest(self, request: SuggestRequest) -> List[tuple]:
        """Handle query suggestions"""
        try:
            return self.query_assistant.get_suggestions(
                partial_query=request.partial_query
            )[:request.limit]
        except Exception as e:
            logger.error(f"Error getting suggestions: {e}")
            return []
    
    async def _handle_popular_queries(self, limit: int) -> List[Dict[str, Any]]:
        """Handle popular queries request"""
        try:
            templates = self.query_assistant.get_popular_queries(limit)
            return [
                {
                    "query": template.natural_query,
                    "category": template.category,
                    "usage_count": template.usage_count,
                    "last_used": template.last_used.isoformat() if template.last_used else None
                }
                for template in templates
            ]
        except Exception as e:
            logger.error(f"Error getting popular queries: {e}")
            return []
    
    def _format_query_result(self, result: QueryResult) -> str:
        """Format query result for display"""
        if result.error:
            return f"❌ Error: {result.error}"
        
        lines = []
        lines.append(f"✅ Query executed successfully")
        lines.append(f"⏱️  Execution time: {result.execution_time:.2f}s")
        lines.append(f"📊 Results: {len(result.results)} rows")
        
        if result.results:
            lines.append("\n📋 Data:")
            # Format as table
            if result.results:
                headers = list(result.results[0].keys())
                lines.append("| " + " | ".join(headers) + " |")
                lines.append("|-" + "-|-".join(["-" * len(h) for h in headers]) + "-|")
                
                for row in result.results[:20]:  # Limit display
                    values = [str(row.get(h, "")) for h in headers]
                    lines.append("| " + " | ".join(values) + " |")
                
                if len(result.results) > 20:
                    lines.append(f"\n... and {len(result.results) - 20} more rows")
        
        return "\n".join(lines)
    
    def _format_analysis(self, analysis: Dict[str, Any]) -> str:
        """Format query analysis for display"""
        if "error" in analysis:
            return f"❌ Error: {analysis['error']}"
        
        lines = []
        lines.append("🔍 Query Analysis")
        lines.append(f"📝 Original: {analysis['original_query']}")
        lines.append(f"🔑 Keywords: {', '.join(analysis['extracted_keywords'])}")
        lines.append(f"🔄 Expanded: {', '.join(analysis['expanded_keywords'][:10])}")
        lines.append(f"📊 Confidence: {analysis['confidence']:.0%}")
        
        if analysis['missing_info']:
            lines.append(f"⚠️  Missing: {', '.join(analysis['missing_info'])}")
        
        if analysis['suggestions']:
            lines.append("\n💡 Suggestions:")
            for suggestion in analysis['suggestions']:
                lines.append(f"  • {suggestion}")
        
        if analysis['matching_templates']:
            lines.append("\n🎯 Matching Templates:")
            for template in analysis['matching_templates']:
                lines.append(f"  • [{template['match_score']:.0%}] {template['natural_query']}")
        
        return "\n".join(lines)
    
    def _format_suggestions(self, suggestions: List[tuple]) -> str:
        """Format query suggestions for display"""
        if not suggestions:
            return "No suggestions available"
        
        lines = ["💡 Query Suggestions:"]
        for query, score in suggestions:
            lines.append(f"  • [{score:.0%}] {query}")
        
        return "\n".join(lines)
    
    def _format_popular_queries(self, queries: List[Dict[str, Any]]) -> str:
        """Format popular queries for display"""
        if not queries:
            return "No popular queries found"
        
        lines = ["🔥 Popular Queries:"]
        for i, query in enumerate(queries, 1):
            lines.append(
                f"{i}. {query['query']} "
                f"[{query['category']}] "
                f"(used {query['usage_count']} times)"
            )
        
        return "\n".join(lines)
    
    async def run(self):
        """Run the MCP server"""
        async with self.server:
            # Initialize with options
            init_options = InitializationOptions(
                server_name="iacsgraph-query-assistant",
                server_version="1.0.0"
            )
            
            logger.info("IACSGraph Query Assistant MCP Server started")
            
            # Keep server running
            await asyncio.Event().wait()


async def main():
    """Main entry point"""
    import sys
    import os
    import json
    
    # Load database configuration from environment
    db_config_json = os.environ.get("IACSGRAPH_DB_CONFIG")
    
    if db_config_json:
        # Use JSON configuration if provided
        try:
            db_config = json.loads(db_config_json)
            logger.info(f"Using database type: {db_config.get('type', 'unknown')}")
        except json.JSONDecodeError:
            logger.error("Invalid IACSGRAPH_DB_CONFIG JSON")
            sys.exit(1)
    else:
        # Fallback to SQLite configuration
        db_path = os.environ.get("IACSGRAPH_DB_PATH", "/home/kimghw/IACSGRAPH/data/iacsgraph.db")
        db_config = {"type": "sqlite", "path": db_path}
    
    qdrant_url = os.environ.get("QDRANT_URL", "localhost")
    qdrant_port = int(os.environ.get("QDRANT_PORT", "6333"))
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Create and run server
    server = IacsGraphQueryServer(
        db_config=db_config,
        qdrant_url=qdrant_url,
        qdrant_port=qdrant_port
    )
    
    try:
        await server.run()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())