"""Enhanced MCP Server for Query Assistant with LLM Parameter Support

Claude가 먼저 dates/keywords를 추출하고, 이를 MCP 서버에 전달하는 구조
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, date
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent
import mcp.types as types
from pydantic import BaseModel, Field

from .query_assistant import QueryAssistant
from .schema import QueryResult

logger = logging.getLogger(__name__)


class EnhancedQueryRequest(BaseModel):
    """Enhanced request model with LLM-extracted parameters"""
    query: str = Field(..., description="Natural language query")
    
    # LLM이 추출한 파라미터들
    extracted_dates: Optional[Dict[str, str]] = Field(
        None, 
        description="LLM-extracted date parameters (e.g., {'start': '2024-01-01', 'end': '2024-01-31'})"
    )
    extracted_keywords: Optional[List[str]] = Field(
        None,
        description="LLM-extracted keywords from the query"
    )
    
    # 기존 파라미터
    category: Optional[str] = Field(None, description="Query category filter")
    execute: bool = Field(True, description="Whether to execute the SQL")
    limit: Optional[int] = Field(None, description="Result limit")
    use_defaults: bool = Field(False, description="Use default values for missing parameters")


class ParameterExtractionRequest(BaseModel):
    """Request for parameter extraction only"""
    query: str = Field(..., description="Natural language query")
    extract_dates: bool = Field(True, description="Extract date parameters")
    extract_keywords: bool = Field(True, description="Extract keywords")
    extract_entities: bool = Field(True, description="Extract named entities")


class EnhancedIacsGraphQueryServer:
    """Enhanced MCP Server with LLM parameter support"""
    
    def __init__(self, db_config: Optional[Dict[str, Any]] = None, db_path: Optional[str] = None, 
                 qdrant_url: str = "localhost", qdrant_port: int = 6333,
                 openai_api_key: Optional[str] = None):
        self.server = Server("iacsgraph-query-assistant-enhanced")
        
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
                    name="query_with_llm_params",
                    description="""Execute natural language query with LLM-extracted parameters.
                    
The MCP server will automatically extract rule-based parameters:
- organization, organization_code (e.g., "한국선급" → "KR")
- agenda_base, agenda_base_version (e.g., "PL25016a" → base: "PL25016", version: "a")
- status, limit, etc.

Claude should additionally extract:
1. Dates from the query (e.g., "last week" → actual dates)
2. Important keywords for better template matching

Example:
Query: "Show me PL25016a Korean Register responses from last week"
Claude extracts:
- dates: {"start": "2024-01-15", "end": "2024-01-22"}
- keywords: ["Korean Register", "KR", "response", "recent", "approval"]

MCP server will extract:
- agenda_base: "PL25016"
- agenda_base_version: "a"
- organization_code: "KR"
- organization: "Korean Register"
""",
                    inputSchema=EnhancedQueryRequest.model_json_schema()
                ),
                Tool(
                    name="extract_parameters_only",
                    description="Extract parameters from query without executing (for testing)",
                    inputSchema=ParameterExtractionRequest.model_json_schema()
                ),
                Tool(
                    name="query",
                    description="Execute natural language query (legacy, without LLM params)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "category": {"type": "string"},
                            "execute": {"type": "boolean"},
                            "limit": {"type": "integer"}
                        },
                        "required": ["query"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Handle tool calls"""
            
            if name == "query_with_llm_params":
                request = EnhancedQueryRequest(**arguments)
                result = await self._handle_enhanced_query(request)
                return [TextContent(type="text", text=self._format_enhanced_result(result))]
                
            elif name == "extract_parameters_only":
                request = ParameterExtractionRequest(**arguments)
                params = await self._handle_parameter_extraction(request)
                return [TextContent(type="text", text=self._format_parameters(params))]
                
            elif name == "query":
                # Legacy handler
                result = await self._handle_legacy_query(arguments)
                return [TextContent(type="text", text=self._format_query_result(result))]
                
            else:
                raise ValueError(f"Unknown tool: {name}")
    
    async def _handle_enhanced_query(self, request: EnhancedQueryRequest) -> Dict[str, Any]:
        """Handle query with LLM-extracted parameters"""
        try:
            # 1. 규칙 기반 파라미터 추출
            from ..common.parsers import QueryParameterExtractor
            extractor = QueryParameterExtractor()
            rule_based_params = extractor.extract_parameters(request.query)
            
            # 2. LLM 파라미터 병합
            enhanced_params = rule_based_params.copy()
            
            # dates 파라미터 처리
            if request.extracted_dates:
                if 'start' in request.extracted_dates and 'end' in request.extracted_dates:
                    enhanced_params['date_range'] = {
                        'start': datetime.fromisoformat(request.extracted_dates['start']),
                        'end': datetime.fromisoformat(request.extracted_dates['end'])
                    }
                    # 날짜 차이로 days 계산
                    delta = (enhanced_params['date_range']['end'] - enhanced_params['date_range']['start']).days
                    enhanced_params['days'] = delta + 1
            
            # keywords 파라미터 처리
            if request.extracted_keywords:
                enhanced_params['llm_keywords'] = request.extracted_keywords
            
            # 3. 템플릿 검색을 위한 키워드 준비
            search_keywords = rule_based_params.get('expanded_keywords', [])
            if request.extracted_keywords:
                search_keywords.extend(request.extracted_keywords)
            
            # 4. 쿼리 실행을 위한 파라미터 준비
            # QueryAssistant에 전달할 파라미터 구성
            execution_params = {
                'agenda_base': enhanced_params.get('agenda_base'),
                'agenda_base_version': enhanced_params.get('agenda_base_version'),
                'organization_code': enhanced_params.get('organization_code'),
                'organization': enhanced_params.get('organization'),
                'date_range': enhanced_params.get('date_range'),
                'days': enhanced_params.get('days'),
                'status': enhanced_params.get('status'),
                'llm_keywords': enhanced_params.get('llm_keywords'),
                'expanded_keywords': list(set(search_keywords))  # 중복 제거
            }
            
            # 5. 쿼리 실행
            result = self.query_assistant.process_query(
                user_query=request.query,
                category=request.category,
                execute=request.execute,
                use_defaults=request.use_defaults,
                additional_params=execution_params  # 추가 파라미터 전달
            )
            
            # 결과에 파라미터 정보 추가
            return {
                'result': result,
                'extracted_params': enhanced_params,
                'rule_based_params': {
                    'agenda_base': rule_based_params.get('agenda_base'),
                    'agenda_base_version': rule_based_params.get('agenda_base_version'),
                    'organization_code': rule_based_params.get('organization_code'),
                    'organization': rule_based_params.get('organization')
                },
                'llm_contribution': {
                    'dates': request.extracted_dates,
                    'keywords': request.extracted_keywords
                }
            }
            
        except Exception as e:
            logger.error(f"Error handling enhanced query: {e}")
            return {
                'error': str(e),
                'extracted_params': {},
                'rule_based_params': {},
                'llm_contribution': {}
            }
    
    async def _handle_parameter_extraction(self, request: ParameterExtractionRequest) -> Dict[str, Any]:
        """파라미터 추출만 수행 (테스트용)"""
        try:
            from ..common.parsers import QueryParameterExtractor
            extractor = QueryParameterExtractor()
            
            # 규칙 기반 추출
            params = extractor.extract_parameters(request.query)
            
            # 분석 정보 추가
            analysis = self.query_assistant.analyze_query(request.query)
            
            return {
                'rule_based_params': {
                    'agenda_base': params.get('agenda_base'),
                    'agenda_base_version': params.get('agenda_base_version'),
                    'organization_code': params.get('organization_code'),
                    'organization': params.get('organization')
                },
                'needs_llm_extraction': {
                    'dates': request.extract_dates and not params.get('date_range'),
                    'keywords': request.extract_keywords
                },
                'analysis': analysis
            }
            
        except Exception as e:
            logger.error(f"Error extracting parameters: {e}")
            return {'error': str(e)}
    
    async def _handle_legacy_query(self, arguments: Dict[str, Any]) -> QueryResult:
        """Legacy query handler"""
        try:
            result = self.query_assistant.process_query(
                user_query=arguments['query'],
                category=arguments.get('category'),
                execute=arguments.get('execute', True)
            )
            
            if arguments.get('limit') and result.results:
                result.results = result.results[:arguments['limit']]
            
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
    
    def _format_enhanced_result(self, result: Dict[str, Any]) -> str:
        """Format enhanced query result"""
        if 'error' in result:
            return f"❌ Error: {result['error']}"
        
        lines = []
        
        # 규칙 기반 파라미터
        if any(result['rule_based_params'].values()):
            lines.append("🔧 Rule-based Parameters (MCP Extracted):")
            for key, value in result['rule_based_params'].items():
                if value:
                    lines.append(f"  • {key}: {value}")
            lines.append("")
        
        # LLM 기여도
        if result['llm_contribution']['dates'] or result['llm_contribution']['keywords']:
            lines.append("🤖 LLM Extracted Parameters:")
            if result['llm_contribution']['dates']:
                lines.append(f"  📅 Dates: {result['llm_contribution']['dates']}")
            if result['llm_contribution']['keywords']:
                lines.append(f"  🔑 Keywords: {', '.join(result['llm_contribution']['keywords'])}")
            lines.append("")
        
        # 병합된 전체 파라미터
        lines.append("📋 Final Merged Parameters:")
        important_params = ['agenda_base', 'agenda_base_version', 'organization_code', 'organization', 
                           'date_range', 'days', 'status', 'llm_keywords']
        for key in important_params:
            if key in result['extracted_params'] and result['extracted_params'][key]:
                value = result['extracted_params'][key]
                if key == 'date_range' and isinstance(value, dict):
                    lines.append(f"  • {key}: {value['start'].date()} to {value['end'].date()}")
                else:
                    lines.append(f"  • {key}: {value}")
        lines.append("")
        
        # 쿼리 결과
        query_result = result['result']
        if query_result.error:
            lines.append(f"❌ Query Error: {query_result.error}")
        else:
            lines.append(f"✅ Query executed successfully")
            lines.append(f"⏱️  Execution time: {query_result.execution_time:.2f}s")
            lines.append(f"📊 Results: {len(query_result.results)} rows")
            
            if query_result.results:
                lines.append("\n📈 Sample Results:")
                # Show first 3 results
                for i, row in enumerate(query_result.results[:3]):
                    lines.append(f"\nRow {i+1}:")
                    for key, value in row.items():
                        lines.append(f"  {key}: {value}")
                        
                if len(query_result.results) > 3:
                    lines.append(f"\n... and {len(query_result.results) - 3} more rows")
        
        return "\n".join(lines)
    
    def _format_parameters(self, params: Dict[str, Any]) -> str:
        """Format parameter extraction result"""
        if 'error' in params:
            return f"❌ Error: {params['error']}"
        
        lines = []
        lines.append("📋 Parameter Extraction Results:")
        lines.append("\n🔧 Rule-based Parameters:")
        for key, value in params['rule_based_params'].items():
            status = "✓" if value else "✗"
            lines.append(f"  {status} {key}: {value}")
        
        lines.append("\n🤖 Needs LLM Extraction:")
        for key, needs in params['needs_llm_extraction'].items():
            status = "⚠️" if needs else "✅"
            lines.append(f"  {status} {key}: {'Yes' if needs else 'No'}")
        
        return "\n".join(lines)
    
    def _format_query_result(self, result: QueryResult) -> str:
        """Format query result for display"""
        if result.error:
            return f"❌ Error: {result.error}"
        
        lines = []
        lines.append(f"✅ Query executed successfully")
        lines.append(f"⏱️  Execution time: {result.execution_time:.2f}s")
        lines.append(f"📊 Results: {len(result.results)} rows")
        
        if result.results:
            lines.append("\n📈 Results:")
            for i, row in enumerate(result.results[:10]):
                lines.append(f"\nRow {i+1}:")
                for key, value in row.items():
                    lines.append(f"  {key}: {value}")
                    
            if len(result.results) > 10:
                lines.append(f"\n... and {len(result.results) - 10} more rows")
        
        return "\n".join(lines)
    
    async def run(self):
        """Run the MCP server"""
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="iacsgraph-query-assistant-enhanced",
                    server_version="2.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={}
                    ),
                ),
            )


async def main():
    """Main entry point"""
    import os
    import sys
    
    # Get configuration from environment or use defaults
    db_config = {
        "type": os.getenv("DB_TYPE", "sqlite"),
        "path": os.getenv("DB_PATH", "data/email_dashboard.db")
    }
    
    server = EnhancedIacsGraphQueryServer(
        db_config=db_config,
        qdrant_url=os.getenv("QDRANT_URL", "localhost"),
        qdrant_port=int(os.getenv("QDRANT_PORT", "6333")),
        openai_api_key=os.getenv("OPENAI_API_KEY")
    )
    
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())