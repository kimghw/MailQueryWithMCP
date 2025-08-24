"""SSE-based MCP Server using Starlette framework

This server uses Server-Sent Events (SSE) for communication, enabling SSH remote connections.
Based on the official MCP SSE transport implementation.
"""

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional
from datetime import datetime
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent, Prompt, PromptMessage, PromptArgument
from pydantic import BaseModel, Field
from starlette.applications import Starlette
from starlette.responses import Response
from starlette.routing import Route, Mount
import uvicorn
from pathlib import Path

from .query_assistant import QueryAssistant
from .schema import QueryResult

logger = logging.getLogger(__name__)


class EnhancedQueryRequest(BaseModel):
    """Enhanced request model with LLM-extracted parameters"""
    query: str = Field(..., description="Natural language query")
    
    # LLM이 추출한 파라미터들
    extracted_period: Dict[str, str] = Field(
        ..., 
        description="LLM-extracted period with start and end dates in YYYY-MM-DD format (e.g., {'start': 'YYYY-MM-DD', 'end': 'YYYY-MM-DD'}). If no end date is specified in the query, use the current date as 'end'. If dates cannot be determined from the query, use the current date as 'end' and 30 days before as 'start'."
    )
    extracted_keywords: List[str] = Field(
        ...,
        description="LLM-extracted keywords from the query"
    )
    extracted_organization: Optional[str] = Field(
        None,
        description="Organization code extracted from query. Must be one of: KR, NK, CCS, ABS, DNV, BV, LR, RINA, RS, IRS, PRS, CRS, TL, IMO, IACS. If organization is not clearly identifiable or not in this list, use the string \"null\" (not JSON null)."
    )
    query_scope: str = Field(
        ...,
        description="Query scope: 'all' (모든 패널/기관), 'one' (단일), 'more' (2개 이상)"
    )
    intent: str = Field(
        ...,
        description="Query intent: 'search' (검색), 'list' (목록), 'analyze' (분석), 'count' (개수)"
    )
    
    # 기존 파라미터
    category: str = Field(..., description="Query category filter")
    execute: bool = Field(True, description="Whether to execute the SQL (default: true)")
    limit: int = Field(10, description="Result limit (default: 10)")
    use_defaults: bool = Field(True, description="Use default values for missing parameters (default: true)")


class ParameterExtractionRequest(BaseModel):
    """Request for parameter extraction only"""
    query: str = Field(..., description="Natural language query")
    extract_dates: bool = Field(True, description="Extract date parameters")
    extract_keywords: bool = Field(True, description="Extract keywords")
    extract_entities: bool = Field(True, description="Extract named entities")


class StarletteSSEServer:
    """Starlette-based SSE MCP Server"""
    
    def __init__(self, db_config: Optional[Dict[str, Any]] = None, db_path: Optional[str] = None, 
                 qdrant_url: str = "localhost", qdrant_port: int = 6333,
                 openai_api_key: Optional[str] = None, 
                 host: str = "0.0.0.0", port: int = 8765):
        self.host = host
        self.port = port
        
        # MCP Server
        self.mcp_server = Server("iacsgraph-query-assistant-sse")
        
        # SSE Transport
        self.sse_transport = SseServerTransport("/messages/")
        
        # Handle backward compatibility
        if db_config is None and db_path is not None:
            db_config = {"type": "sqlite", "path": db_path}
        
        self.query_assistant = QueryAssistant(
            db_config=db_config,
            qdrant_url=qdrant_url,
            qdrant_port=qdrant_port,
            openai_api_key=openai_api_key
        )
        
        # Load system prompt
        self.system_prompt = self._load_system_prompt()
        
        # Register handlers
        self._register_handlers()
        
        # Create Starlette app
        self.app = self._create_app()
    
    def _register_handlers(self):
        """Register MCP protocol handlers"""
        
        @self.mcp_server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """List available tools"""
            logger.info("🔧 [MCP Handler] list_tools() called")
            return [
                Tool(
                    name="query_with_llm_params",
                    description="""Execute natural language query with LLM-extracted parameters.
                    
The MCP server will automatically extract rule-based parameters:
- organization, organization_code (e.g., "한국선급" → "KR")
- agenda_base, agenda_base_version (e.g., "PL25016a" → base: "PL25016", version: "a")
- status, limit, etc.

Claude should additionally extract:
1. Period from the query with start/end dates (e.g., "last week" → {"start": "2024-02-26", "end": "2024-03-04"})
2. Important keywords for better template matching
3. Query scope:
   - 'all': 모든 패널/기관에 관한 질의 (e.g., "모든 기관의 응답", "전체 패널 현황")
   - 'one': 단일 패널/기관 질의 (e.g., "KR 응답", "PL 패널 의제")
   - 'more': 2개 이상 패널/기관 질의 (e.g., "KR과 BV의 응답", "여러 기관")
4. Organization code (if not identifiable, set to null)

Example:
Query: "Show me all organizations' responses from last week"
Claude extracts:
- period: {"start": "2024-01-15", "end": "2024-01-22"}
- keywords: ["response", "recent", "all", "organizations"]
- organization: null
- scope: "all"

Optional parameters (with defaults):
- execute: true
- limit: 10
- use_defaults: true

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
        
        @self.mcp_server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Handle tool calls"""
            logger.info(f"🛠️ [MCP Handler] call_tool() called with tool: {name}")
            
            # Preprocess arguments
            arguments = self._preprocess_arguments(arguments)
            
            if name == "query_with_llm_params":
                request = EnhancedQueryRequest(**arguments)
                result = await self._handle_enhanced_query(request)
                formatted_text = self._format_enhanced_result(result)
                logger.info("📤 MCP Response to Claude Desktop:")
                logger.info("=" * 80)
                for line in formatted_text.split('\n'):
                    logger.info(line)
                logger.info("=" * 80)
                return [TextContent(type="text", text=formatted_text)]
                
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
        
        @self.mcp_server.list_prompts()
        async def handle_list_prompts() -> List[Prompt]:
            """List available prompts"""
            logger.info("📋 [MCP Handler] list_prompts() called")
            return [
                Prompt(
                    name="iacsgraph_query",
                    description="IACSGRAPH 해양 데이터베이스 쿼리 처리를 위한 시스템 프롬프트",
                    arguments=[
                        PromptArgument(
                            name="user_query",
                            description="사용자의 자연어 질의",
                            required=True
                        )
                    ]
                )
            ]
        
        @self.mcp_server.get_prompt()
        async def handle_get_prompt(name: str, arguments: Dict[str, Any]) -> PromptMessage:
            """Get specific prompt"""
            logger.info(f"📝 [MCP Handler] get_prompt() called with prompt: {name}")
            logger.info(f"   Arguments: {arguments}")
            if name == "iacsgraph_query":
                user_query = arguments.get("user_query", "")
                
                # Replace the placeholder in system prompt
                prompt_content = self.system_prompt
                if user_query:
                    prompt_content = prompt_content.replace("원본 질의", user_query)
                
                return PromptMessage(
                    role="system",
                    content=TextContent(type="text", text=prompt_content)
                )
            else:
                raise ValueError(f"Unknown prompt: {name}")
    
    def _load_system_prompt(self) -> str:
        """Load system prompt from file"""
        prompt_file = Path(__file__).parent / "prompts" / "mcp_system_prompt.txt"
        try:
            with open(prompt_file, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logger.warning(f"System prompt file not found: {prompt_file}")
            return "IACSGRAPH 해양 데이터베이스 쿼리 처리 시스템입니다."
        except Exception as e:
            logger.error(f"Error loading system prompt: {e}")
            return "IACSGRAPH 해양 데이터베이스 쿼리 처리 시스템입니다."
    
    def _preprocess_arguments(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Preprocess arguments from Claude Desktop
        
        Claude Desktop에서 전달받은 arguments를 정제하는 전처리 함수
        - 백슬래시 제거
        - 타입 변환 (string → int, JSON 파싱)
        - "null" 문자열을 None으로 변환
        """
        import json
        
        # Clean backslashes from all string values in arguments
        def clean_backslashes(obj):
            if isinstance(obj, str):
                return obj.replace('\\', '')
            elif isinstance(obj, dict):
                return {k: clean_backslashes(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [clean_backslashes(item) for item in obj]
            return obj
        
        # Apply cleaning to all arguments
        arguments = clean_backslashes(arguments)
        
        # Log incoming arguments
        logger.info(f"=== Incoming arguments ===")
        logger.info(f"Raw arguments: {arguments}")
        logger.info(f"Arguments type: {type(arguments)}")
        for key, value in arguments.items():
            logger.info(f"  {key}: {value} (type: {type(value).__name__})")
        
        # Special handling for limit field - convert string to int
        if 'limit' in arguments and isinstance(arguments['limit'], str):
            # Remove surrounding quotes and try to convert to int
            cleaned_limit = arguments['limit'].strip().strip("'").strip('"')
            try:
                arguments['limit'] = int(cleaned_limit)
            except ValueError:
                # If conversion fails, keep original value
                pass
        
        # Handle string-wrapped JSON for period
        if 'extracted_period' in arguments and isinstance(arguments['extracted_period'], str):
            try:
                arguments['extracted_period'] = json.loads(arguments['extracted_period'])
            except:
                pass
        
        # Handle string-wrapped JSON for keywords
        if 'extracted_keywords' in arguments and isinstance(arguments['extracted_keywords'], str):
            try:
                arguments['extracted_keywords'] = json.loads(arguments['extracted_keywords'])
            except:
                pass
        
        # Handle string "null" to actual null
        null_fields = ['extracted_organization', 'category', 'query_scope', 'intent']
        for key in null_fields:
            if key in arguments and arguments[key] == 'null':
                arguments[key] = None
        
        # Log after conversion
        logger.info(f"=== After preprocessing ===")
        for key, value in arguments.items():
            logger.info(f"  {key}: {value} (type: {type(value).__name__})")
        
        return arguments
    
    async def _handle_enhanced_query(self, request: EnhancedQueryRequest) -> Dict[str, Any]:
        """Handle query with LLM-extracted parameters"""
        try:
            # 1. 규칙 기반 파라미터 추출
            from ..common.parsers import QueryParameterExtractor
            extractor = QueryParameterExtractor()
            rule_based_params = extractor.extract_parameters(request.query)
            
            # Extract keywords using keyword expander
            from .services.keyword_expander import KeywordExpander
            keyword_expander = KeywordExpander()
            expansion = keyword_expander.expand_query(request.query)
            rule_based_params['keywords'] = expansion.expanded_keywords
            
            # 2. LLM 파라미터 병합 - LLM 우선
            enhanced_params = rule_based_params.copy()
            
            # organization 파라미터 처리 - LLM 우선, 동의어 처리
            if request.extracted_organization:
                # LLM이 추출한 조직 사용 (이미 정규화된 코드)
                enhanced_params['organization'] = request.extracted_organization
                enhanced_params['organization_code'] = request.extracted_organization
                logger.info(f"Using LLM-extracted organization: {request.extracted_organization}")
            elif enhanced_params.get('organization'):
                # 규칙 기반 추출된 조직이 있으면 동의어 처리
                # Use the synonym service from the extractor which has preprocessing_repo
                normalized_org = extractor.synonym_service.normalize_organization(enhanced_params['organization'])
                enhanced_params['organization'] = normalized_org
                enhanced_params['organization_code'] = normalized_org
                logger.info(f"Normalized organization: {enhanced_params.get('organization_text')} → {normalized_org}")
            
            # Import enhanced date handler
            from .services.enhanced_date_handler import EnhancedDateHandler
            date_handler = EnhancedDateHandler()
            
            # period 파라미터 처리 - LLM 우선
            if request.extracted_period:
                # LLM이 추출한 기간 우선 사용
                enhanced_params['date_range'] = {
                    'type': 'range',
                    'from': request.extracted_period['start'],
                    'to': request.extracted_period['end']
                }
                # Calculate days for backward compatibility
                try:
                    from datetime import datetime
                    start = datetime.fromisoformat(request.extracted_period['start'])
                    end = datetime.fromisoformat(request.extracted_period['end'])
                    enhanced_params['days'] = (end - start).days + 1
                except:
                    enhanced_params['days'] = 30
                logger.info(f"Using LLM-extracted period: {request.extracted_period}")
            else:
                # 기존 로직: 규칙 기반 날짜 추출 또는 기본값
                template_params = [
                    {
                        "name": "date_range",
                        "type": "date_range",
                        "required": False,
                        "default": {"type": "relative", "days": 30}  # 기본값 30일
                    }
                ]
                
                # Process dates with enhanced handler
                processed_params = date_handler.process_date_parameters(
                    template_params,
                    None,  # No LLM dates
                    enhanced_params
                )
                enhanced_params.update(processed_params)
            
            # Calculate days for backward compatibility
            if 'date_range' in enhanced_params:
                date_range = enhanced_params['date_range']
                if date_range.get('type') == 'relative':
                    enhanced_params['days'] = date_range.get('days', 30)
                elif date_range.get('type') == 'range' and 'from' in date_range and 'to' in date_range:
                    try:
                        start = datetime.fromisoformat(date_range['from'])
                        end = datetime.fromisoformat(date_range['to'])
                        enhanced_params['days'] = (end - start).days + 1
                    except:
                        enhanced_params['days'] = 30  # 기본값
            
            # keywords 파라미터 처리 - LLM 키워드 우선
            if request.extracted_keywords:
                enhanced_params['llm_keywords'] = request.extracted_keywords
                # LLM 키워드를 메인 키워드로 사용
                enhanced_params['keywords'] = request.extracted_keywords
                logger.info(f"Using LLM-extracted keywords: {request.extracted_keywords}")
            
            # intent 파라미터 처리
            if request.intent:
                enhanced_params['intent'] = request.intent
                logger.info(f"Using LLM-extracted intent: {request.intent}")
            
            # Import scope handler
            from .services.query_scope_handler import QueryScopeHandler
            scope_handler = QueryScopeHandler()
            
            # Process query scope
            scope_info = scope_handler.process_scope_parameter(
                request.query_scope,
                request.query,
                [enhanced_params.get('organization_code')] if enhanced_params.get('organization_code') else None
            )
            enhanced_params['scope_info'] = scope_info
            logger.info(f"Query scope: {scope_info['scope']} - SQL: {scope_info['sql_condition']}")
            
            # 3. 템플릿 검색을 위한 키워드 준비
            # LLM 키워드를 우선으로 사용
            if request.extracted_keywords:
                search_keywords = request.extracted_keywords.copy()
                # 규칙 기반 키워드 추가 (중복 제거)
                rule_keywords = rule_based_params.get('keywords', [])
                for kw in rule_keywords:
                    if kw not in search_keywords:
                        search_keywords.append(kw)
            else:
                search_keywords = rule_based_params.get('keywords', [])
            
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
                'keywords': search_keywords,  # 템플릿 매칭용 키워드
                'llm_keywords': enhanced_params.get('llm_keywords'),
                'expanded_keywords': list(set(search_keywords)),  # 중복 제거
                'intent': enhanced_params.get('intent'),  # intent 추가
                # MCP parameters for SQL generation
                'extracted_period': request.extracted_period,
                'extracted_keywords': request.extracted_keywords,
                'extracted_organization': request.extracted_organization,
                'extracted_intent': request.intent  # MCP intent 추가
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
        if any(result['llm_contribution'].values()):
            lines.append("🤖 LLM Extracted Parameters:")
            if result['llm_contribution'].get('period'):
                lines.append(f"  📅 Period: {result['llm_contribution']['period']}")
            if result['llm_contribution'].get('keywords'):
                lines.append(f"  🔑 Keywords: {', '.join(result['llm_contribution']['keywords'])}")
            if result['llm_contribution'].get('organization'):
                lines.append(f"  🏢 Organization: {result['llm_contribution']['organization']}")
            if result['llm_contribution'].get('intent'):
                lines.append(f"  🎯 Intent: {result['llm_contribution']['intent']}")
            lines.append("")
        
        # 병합된 전체 파라미터
        lines.append("📋 Final Merged Parameters:")
        important_params = ['agenda_base', 'agenda_base_version', 'organization_code', 'organization', 
                           'date_range', 'days', 'status', 'llm_keywords', 'intent']
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
    
    def _create_app(self):
        """Create Starlette application"""
        async def handle_sse(request):
            """Handle SSE connections"""
            logger.info("🌐 [MCP Server] SSE connection established")
            logger.info(f"   Remote: {request.client.host}:{request.client.port}")
            async with self.sse_transport.connect_sse(
                request.scope, request.receive, request._send
            ) as streams:
                await self.mcp_server.run(
                    streams[0], 
                    streams[1], 
                    InitializationOptions(
                        server_name="iacsgraph-query-assistant-sse",
                        server_version="2.0.0",
                        capabilities=self.mcp_server.get_capabilities(
                            notification_options=NotificationOptions(),
                            experimental_capabilities={}
                        ),
                    )
                )
            # Return empty response to avoid NoneType error
            return Response()
        
        async def health_check(request):
            """Health check endpoint"""
            return Response(
                content='{"status": "healthy", "server": "iacsgraph-query-assistant-sse", "version": "2.0.0"}',
                media_type="application/json"
            )
        
        # Create routes
        routes = [
            Route("/health", endpoint=health_check),
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=self.sse_transport.handle_post_message),
        ]
        
        return Starlette(routes=routes)
    
    def run(self):
        """Run the SSE MCP server"""
        logger.info(f"Starting SSE MCP Server on http://{self.host}:{self.port}")
        logger.info(f"SSE endpoint: http://{self.host}:{self.port}/sse")
        logger.info(f"Message endpoint: http://{self.host}:{self.port}/messages/")
        
        # Run uvicorn
        uvicorn.run(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info"
        )


def main():
    """Main entry point"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('/home/kimghw/IACSGRAPH/mcp_server_detail.log')
        ]
    )
    
    # Get configuration from environment or use defaults
    db_config = {
        "type": os.getenv("DB_TYPE", "sqlite"),
        "path": os.getenv("DB_PATH", "data/email_dashboard.db")
    }
    
    server = StarletteSSEServer(
        db_config=db_config,
        qdrant_url=os.getenv("QDRANT_URL", "localhost"),
        qdrant_port=int(os.getenv("QDRANT_PORT", "6333")),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        host=os.getenv("MCP_HOST", "0.0.0.0"),
        port=int(os.getenv("MCP_PORT", "8765"))
    )
    
    # Run the server
    server.run()


if __name__ == "__main__":
    main()