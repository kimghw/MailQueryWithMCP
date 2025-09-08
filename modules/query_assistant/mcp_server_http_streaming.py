"""HTTP Streaming-based MCP Server using Starlette framework

This server uses HTTP streaming (chunked transfer encoding) for communication.
SSE support is being deprecated, so this implementation uses pure HTTP streaming.
"""

import asyncio
import json
import logging
import os
import secrets
from typing import Any, Dict, List, Optional, AsyncIterator
from datetime import datetime
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent, Prompt, PromptMessage, PromptArgument
from pydantic import BaseModel, Field
from starlette.applications import Starlette
from starlette.responses import StreamingResponse, JSONResponse, Response
from starlette.routing import Route
from starlette.requests import Request
import uvicorn
from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from infra.core.database import get_database_manager
from infra.core.auth_logger import get_auth_logger
from .query_assistant import QueryAssistant
from .schema import QueryResult
from .mail_data_refresher import MailDataRefresher

logger = logging.getLogger(__name__)
auth_logger = get_auth_logger()


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


class HTTPStreamingMCPServer:
    """HTTP Streaming-based MCP Server"""
    
    def __init__(self, db_config: Optional[Dict[str, Any]] = None, db_path: Optional[str] = None, 
                 qdrant_url: str = "localhost", qdrant_port: int = 6333,
                 openai_api_key: Optional[str] = None, 
                 host: str = "0.0.0.0", port: int = 8765):
        self.host = host
        self.port = port
        
        # MCP Server
        self.mcp_server = Server("iacsgraph-query-assistant-http")
        
        # Handle backward compatibility
        if db_config is None and db_path is not None:
            db_config = {"type": "sqlite", "path": db_path}
        
        self.query_assistant = QueryAssistant(
            db_config=db_config,
            qdrant_url=qdrant_url,
            qdrant_port=qdrant_port,
            openai_api_key=openai_api_key
        )
        
        # Initialize database connection and check authentication
        self._initialize_and_check_auth()
        
        # Initialize mail data refresher
        self.mail_refresher = MailDataRefresher()
        self._mail_refresh_done = False
        
        # Load system prompt
        self.system_prompt = self._load_system_prompt()
        
        # Active sessions
        self.sessions: Dict[str, Dict[str, Any]] = {}
        
        # Store handlers for direct access
        self._handlers = {}
        
        # Register handlers
        self._register_handlers()
        
        # Create Starlette app
        self.app = self._create_app()
    
    def _initialize_and_check_auth(self):
        """Initialize database connection and check authentication status"""
        logger.info("🔍 Initializing database and checking authentication...")
        
        try:
            # Get database manager directly from query assistant
            db = get_database_manager()
            
            # Force database connection initialization
            query = "SELECT COUNT(*) FROM accounts WHERE is_active = 1"
            result = db.fetch_one(query)
            active_accounts = result[0] if result else 0
            
            logger.info(f"✅ Database connection successful")
            logger.info(f"📊 Active accounts found: {active_accounts}")
            
            # Check authentication status for all active accounts
            if active_accounts > 0:
                auth_query = """
                SELECT user_id, 
                       CASE 
                           WHEN access_token IS NOT NULL AND token_expiry > datetime('now') THEN 'VALID'
                           WHEN refresh_token IS NOT NULL THEN 'REFRESH_NEEDED'
                           ELSE 'EXPIRED'
                       END as auth_status
                FROM accounts 
                WHERE is_active = 1
                ORDER BY user_id
                """
                auth_results = db.fetch_all(auth_query)
                
                logger.info("🔐 Authentication status:")
                
                # Count by status
                valid_count = sum(1 for row in auth_results if row[1] == "VALID")
                refresh_count = sum(1 for row in auth_results if row[1] == "REFRESH_NEEDED") 
                expired_count = sum(1 for row in auth_results if row[1] == "EXPIRED")
                
                for row in auth_results:
                    user_id, status = row
                    status_emoji = "✅" if status == "VALID" else "⚠️" if status == "REFRESH_NEEDED" else "❌"
                    logger.info(f"   {status_emoji} {user_id}: {status}")
                    auth_logger.log_authentication(user_id, status, "server startup check")
                
                # Log batch check summary
                auth_logger.log_batch_auth_check(active_accounts, valid_count, refresh_count, expired_count)
            else:
                logger.warning("⚠️ No active accounts found in database")
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize database or check auth: {str(e)}")
            raise
    
    def _register_handlers(self):
        """Register MCP protocol handlers"""
        
        @self.mcp_server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """List available tools"""
            logger.info("🔧 [MCP Handler] list_tools() called")
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
        
        # Store handler for direct access
        self._handlers['list_tools'] = handle_list_tools
        
        @self.mcp_server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Handle tool calls"""
            logger.info(f"🛠️ [MCP Handler] call_tool() called with tool: {name}")
            logger.info(f"📝 [MCP Handler] Raw arguments: {json.dumps(arguments, indent=2, ensure_ascii=False)}")
            
            # Mail data refresh for krsdtp account before first query
            if not self._mail_refresh_done:
                logger.info("📧 [MCP Handler] Refreshing mail data for krsdtp account...")
                try:
                    refresh_result = await self.mail_refresher.refresh_mail_data_for_user(
                        user_id="krsdtp",
                        max_mails=1000,
                        use_last_date=True
                    )
                    
                    if refresh_result['status'] == 'success':
                        logger.info(f"✅ Mail refresh completed: {refresh_result['mail_count']} mails queried, "
                                   f"{refresh_result.get('processed_count', 0)} processed, "
                                   f"{refresh_result.get('events_processed', 0)} events saved to agenda_chair")
                    else:
                        logger.warning(f"⚠️ Mail refresh failed: {refresh_result.get('error', 'Unknown error')}")
                    
                    self._mail_refresh_done = True
                except Exception as e:
                    logger.error(f"❌ Error during mail refresh: {e}")
            
            # Preprocess arguments
            arguments = self._preprocess_arguments(arguments)
            logger.info(f"🔄 [MCP Handler] Preprocessed arguments: {json.dumps(arguments, indent=2, ensure_ascii=False)}")
            
            if name == "simple_query":
                # Simple query handler
                result = await self._handle_legacy_query(arguments)
                return [TextContent(type="text", text=self._format_query_result(result))]
                
            elif name == "query_with_llm_params":
                # Set default values for required fields if not provided
                if 'extracted_organization' not in arguments or not arguments.get('extracted_organization'):
                    arguments['extracted_organization'] = 'KR'
                
                logger.info(f"🤖 [MCP Handler] Processing query_with_llm_params")
                logger.info(f"  • Query: {arguments.get('query')}")
                logger.info(f"  • Keywords: {arguments.get('extracted_keywords')}")
                logger.info(f"  • Organization: {arguments.get('extracted_organization')}")
                logger.info(f"  • Period: {arguments.get('extracted_period')}")
                logger.info(f"  • Intent: {arguments.get('intent')}")
                
                request = EnhancedQueryRequest(**arguments)
                result = await self._handle_enhanced_query(request)
                formatted_text = self._format_enhanced_result(result)
                return [TextContent(type="text", text=formatted_text)]
                
            elif name == "query":
                # Legacy handler
                result = await self._handle_legacy_query(arguments)
                return [TextContent(type="text", text=self._format_query_result(result))]
                
            else:
                raise ValueError(f"Unknown tool: {name}")
        
        # Store handler for direct access
        self._handlers['call_tool'] = handle_call_tool
        
        @self.mcp_server.list_prompts()
        async def handle_list_prompts() -> List[Prompt]:
            """List available prompts"""
            logger.info("📋 [MCP Handler] list_prompts() called")
            return [
                Prompt(
                    name="iacsgraph_query",
                    description="IACS 업무 활동 중 송수신한 메일 시스템을 관리 합니다.",
                    arguments=[
                        PromptArgument(
                            name="user_query",
                            description="사용자의 자연어 질의",
                            required=True
                        )
                    ]
                )
            ]
        
        # Store handler for direct access
        self._handlers['list_prompts'] = handle_list_prompts
        
        @self.mcp_server.get_prompt()
        async def handle_get_prompt(name: str, arguments: Dict[str, Any]) -> PromptMessage:
            """Get specific prompt"""
            logger.info(f"📝 [MCP Handler] get_prompt() called with prompt: {name}")
            if name == "iacsgraph_query":
                user_query = arguments.get("user_query", "")
                prompt_content = self.system_prompt
                if user_query:
                    prompt_content = prompt_content.replace("원본 질의", user_query)
                
                return PromptMessage(
                    role="assistant",  # Spec: "user" | "assistant" only
                    content=TextContent(type="text", text=prompt_content)
                )
            else:
                raise ValueError(f"Unknown prompt: {name}")
        
        # Store handler for direct access
        self._handlers['get_prompt'] = handle_get_prompt
    
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
        """Preprocess arguments from Claude Desktop"""
        import json
        
        # Clean backslashes from all string values
        def clean_backslashes(obj):
            if isinstance(obj, str):
                return obj.replace('\\', '')
            elif isinstance(obj, dict):
                return {k: clean_backslashes(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [clean_backslashes(item) for item in obj]
            return obj
        
        arguments = clean_backslashes(arguments)
        
        # Special handling for limit field
        if 'limit' in arguments and isinstance(arguments['limit'], str):
            cleaned_limit = arguments['limit'].strip().strip("'").strip('"')
            try:
                arguments['limit'] = int(cleaned_limit)
            except ValueError:
                pass
        
        # Handle string-wrapped JSON
        if 'extracted_period' in arguments and isinstance(arguments['extracted_period'], str):
            try:
                arguments['extracted_period'] = json.loads(arguments['extracted_period'])
            except:
                pass
        
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
        
        return arguments
    
    async def _handle_enhanced_query(self, request: EnhancedQueryRequest) -> Dict[str, Any]:
        """Handle query with LLM-extracted parameters"""
        logger.info(f"📊 [Enhanced Query] Starting processing for: {request.query}")
        try:
            from ..common.parsers import QueryParameterExtractor
            extractor = QueryParameterExtractor()
            rule_based_params = extractor.extract_parameters(request.query)
            
            from .services.keyword_expander import KeywordExpander
            keyword_expander = KeywordExpander()
            expansion = keyword_expander.expand_query(request.query)
            rule_based_params['keywords'] = expansion.expanded_keywords
            
            enhanced_params = rule_based_params.copy()
            
            # Process organization
            if request.extracted_organization:
                enhanced_params['organization'] = request.extracted_organization
                enhanced_params['organization_code'] = request.extracted_organization
            elif enhanced_params.get('organization'):
                normalized_org = extractor.synonym_service.normalize_organization(enhanced_params['organization'])
                enhanced_params['organization'] = normalized_org
                enhanced_params['organization_code'] = normalized_org
            
            # Process period
            from .services.enhanced_date_handler import EnhancedDateHandler
            date_handler = EnhancedDateHandler()
            
            if request.extracted_period:
                enhanced_params['date_range'] = {
                    'type': 'range',
                    'from': request.extracted_period['start'],
                    'to': request.extracted_period['end']
                }
                try:
                    from datetime import datetime
                    start = datetime.fromisoformat(request.extracted_period['start'])
                    end = datetime.fromisoformat(request.extracted_period['end'])
                    enhanced_params['days'] = (end - start).days + 1
                except:
                    enhanced_params['days'] = 30
            
            # Process keywords
            if request.extracted_keywords:
                enhanced_params['llm_keywords'] = request.extracted_keywords
                enhanced_params['keywords'] = request.extracted_keywords
            
            # Process intent
            if request.intent:
                enhanced_params['intent'] = request.intent
            
            # Process scope
            from .services.query_scope_handler import QueryScopeHandler
            scope_handler = QueryScopeHandler()
            
            scope_info = scope_handler.process_scope_parameter(
                request.query_scope,
                request.query,
                [enhanced_params.get('organization_code')] if enhanced_params.get('organization_code') else None
            )
            enhanced_params['scope_info'] = scope_info
            
            # Prepare execution parameters
            search_keywords = request.extracted_keywords.copy() if request.extracted_keywords else []
            rule_keywords = rule_based_params.get('keywords', [])
            for kw in rule_keywords:
                if kw not in search_keywords:
                    search_keywords.append(kw)
            
            execution_params = {
                'agenda_base': enhanced_params.get('agenda_base'),
                'agenda_base_version': enhanced_params.get('agenda_base_version'),
                'organization_code': enhanced_params.get('organization_code'),
                'organization': enhanced_params.get('organization'),
                'date_range': enhanced_params.get('date_range'),
                'days': enhanced_params.get('days'),
                'status': enhanced_params.get('status'),
                'keywords': search_keywords,
                'llm_keywords': enhanced_params.get('llm_keywords'),
                'expanded_keywords': list(set(search_keywords)),
                'intent': enhanced_params.get('intent'),
                'extracted_period': request.extracted_period,
                'extracted_keywords': request.extracted_keywords,
                'extracted_organization': request.extracted_organization,
                'extracted_intent': request.intent
            }
            
            # Execute query
            logger.info(f"🚀 [Enhanced Query] Executing query with params:")
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
            
            logger.info(f"✅ [Enhanced Query] Query executed successfully")
            logger.info(f"  • SQL executed: {getattr(result, 'executed_sql', 'N/A')[:200]}...")
            logger.info(f"  • Results count: {len(getattr(result, 'results', []))}")
            logger.info(f"  • Execution time: {getattr(result, 'execution_time', 0):.2f}s")
            
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
        
        # Rule-based parameters
        if any(result['rule_based_params'].values()):
            lines.append("🔧 Rule-based Parameters (MCP Extracted):")
            for key, value in result['rule_based_params'].items():
                if value:
                    lines.append(f"  • {key}: {value}")
            lines.append("")
        
        # LLM contribution
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
        
        # Query results
        query_result = result['result']
        if query_result.error:
            lines.append(f"❌ Query Error: {query_result.error}")
        else:
            lines.append(f"✅ Query executed successfully")
            lines.append(f"⏱️  Execution time: {query_result.execution_time:.2f}s")
            lines.append(f"📊 Results: {len(query_result.results)} rows")
            
            if query_result.results:
                lines.append("\n📈 Sample Results:")
                for i, row in enumerate(query_result.results[:3]):
                    lines.append(f"\nRow {i+1}:")
                    for key, value in row.items():
                        lines.append(f"  {key}: {value}")
                        
                if len(query_result.results) > 3:
                    lines.append(f"\n... and {len(query_result.results) - 3} more rows")
        
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
    
    async def _error_stream(self, error_message: str) -> AsyncIterator[str]:
        """Generate error stream"""
        yield json.dumps({"error": error_message}) + "\n"
    
    async def _send_list_changed_notifications(self, request: Request):
        """Send list changed notifications after initialization"""
        # Wait a bit to ensure client is ready
        await asyncio.sleep(0.1)
        
        # Note: In a real implementation, we would need to track the client's SSE connection
        # For now, we'll just log that we would send these
        logger.info("📤 Would send notifications/tools/list_changed")
        logger.info("📤 Would send notifications/prompts/list_changed")
        logger.info("📤 Would send notifications/resources/list_changed")
    
    async def _handle_streaming_request(self, request: Request):
        """Handle MCP request - returns single JSON response"""
        # Common headers
        base_headers = {
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS, DELETE",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, Mcp-Session-Id, MCP-Protocol-Version",
            "Access-Control-Expose-Headers": "Mcp-Session-Id",
        }
        
        # Read and parse request
        try:
            body = await request.body()
            if not body:
                return JSONResponse(
                    {"jsonrpc": "2.0", "error": {"code": -32700, "message": "Empty request body"}},
                    status_code=400,
                    headers=base_headers
                )
            
            try:
                rpc_request = json.loads(body)
            except json.JSONDecodeError as e:
                return JSONResponse(
                    {"jsonrpc": "2.0", "error": {"code": -32700, "message": f"Parse error: {str(e)}"}},
                    status_code=400,
                    headers=base_headers
                )
        except Exception as e:
            return JSONResponse(
                {"jsonrpc": "2.0", "error": {"code": -32603, "message": f"Internal error: {str(e)}"}},
                status_code=500,
                headers=base_headers
            )
        
        # Extract request details
        method = rpc_request.get('method')
        params = rpc_request.get('params', {}) or {}
        request_id = rpc_request.get('id')
        
        logger.info(f"📨 Received RPC request: {method} with id: {request_id}")
        
        # Handle notification (no id) - return 202 with no body
        if request_id is None:
            logger.info(f"📤 Handling notification: {method}")
            
            # If this is the initialized notification, send list changed notifications
            if method == 'notifications/initialized':
                # Send tools list changed notification after a short delay
                asyncio.create_task(self._send_list_changed_notifications(request))
            
            return Response(status_code=202, headers=base_headers)
        
        # Process based on method
        logger.info(f"📤 Processing method: {method} with params: {params}")
        
        if method == 'initialize':
            # Initialize session with standard Mcp-Session-Id
            session_id = secrets.token_urlsafe(24)
            caps = self.mcp_server.get_capabilities(
                notification_options=NotificationOptions(),
                experimental_capabilities={}
            )
            
            # Fix null fields to empty objects/lists for spec compliance
            caps_dict = caps.model_dump()
            if caps_dict.get('logging') is None:
                caps_dict['logging'] = {}
            if caps_dict.get('resources') is None:
                caps_dict['resources'] = {
                    "listChanged": False
                }
            # Remove completions field if it's null (not supported by this server)
            if caps_dict.get('completions') is None:
                caps_dict.pop('completions', None)
            
            self.sessions[session_id] = {
                'initialized': True,
                'capabilities': caps_dict
            }
            
            # Use the protocol version requested by the client
            requested_version = params.get('protocolVersion', '2025-06-18')
            
            # Add session header and ensure it's exposed
            headers = base_headers.copy()
            headers["Mcp-Session-Id"] = session_id
            headers["MCP-Protocol-Version"] = requested_version
            headers["Access-Control-Expose-Headers"] = "Mcp-Session-Id, MCP-Protocol-Version"
            
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": requested_version,
                    # Use fixed capabilities (with logging as empty object)
                    "capabilities": caps_dict,
                    "serverInfo": {
                        "name": "iacsgraph-query-assistant-http",
                        "title": "🌊 IACSGRAPH Query Assistant",
                        "version": "2.0.0"
                    },
                    "instructions": "IACSGRAPH 해양 데이터베이스 쿼리 시스템입니다. 'query' 도구를 사용하여 자연어로 데이터베이스를 조회할 수 있습니다."
                }
            }
            logger.info(f"📤 Sending initialize response: {json.dumps(response, indent=2)}")
            return JSONResponse(response, headers=headers)
        
        elif method == 'tools/list':
            # List tools
            if 'list_tools' in self._handlers:
                tools = await self._handlers['list_tools']()
            else:
                tools = []
            
            # Clean up tool data - remove null fields
            tools_data = []
            for tool in tools:
                tool_dict = tool.model_dump()
                # Remove null fields as per spec
                cleaned_tool = {}
                for key, value in tool_dict.items():
                    if value is not None:
                        cleaned_tool[key] = value
                tools_data.append(cleaned_tool)
            
            # Debug: Log the actual tool data being sent
            logger.info(f"📤 Tool data details: {json.dumps(tools_data, indent=2)}")
            
            logger.info(f"📤 Returning {len(tools_data)} tools: {[t['name'] for t in tools_data]}")
            
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "tools": tools_data
                }
            }
            return JSONResponse(response, headers=base_headers)
        
        elif method == 'tools/call':
            # Call tool
            tool_name = params.get('name')
            tool_args = params.get('arguments', {})
            
            logger.info(f"🔧 [MCP Server] Received tools/call request")
            logger.info(f"  • Tool: {tool_name}")
            logger.info(f"  • Arguments: {json.dumps(tool_args, indent=2, ensure_ascii=False)}")
            
            try:
                if 'call_tool' in self._handlers:
                    results = await self._handlers['call_tool'](tool_name, tool_args)
                else:
                    raise ValueError("Tool handler not available")
                    
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [content.model_dump() for content in results]
                    }
                }
            except Exception as e:
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32603,
                        "message": str(e)
                    }
                }
            
            return JSONResponse(response, headers=base_headers)
        
        elif method == 'prompts/list':
            # List prompts
            if 'list_prompts' in self._handlers:
                prompts = await self._handlers['list_prompts']()
            else:
                prompts = []
                
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "prompts": [prompt.model_dump() for prompt in prompts]
                }
            }
            return JSONResponse(response, headers=base_headers)
        
        elif method == 'resources/list':
            # Resources not supported, return empty list
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "resources": []
                }
            }
            return JSONResponse(response, headers=base_headers)
        
        elif method == 'prompts/get':
            # Get prompt
            prompt_name = params.get('name')
            prompt_args = params.get('arguments', {})
            
            try:
                if 'get_prompt' in self._handlers:
                    prompt_msg = await self._handlers['get_prompt'](prompt_name, prompt_args)
                else:
                    raise ValueError("Prompt handler not available")
                    
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "messages": [prompt_msg.model_dump()]
                    }
                }
            except Exception as e:
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32603,
                        "message": str(e)
                    }
                }
            
            return JSONResponse(response, headers=base_headers)
        
        else:
            # Unknown method
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }
            return JSONResponse(response, status_code=404, headers=base_headers)
    
    def _create_app(self):
        """Create Starlette application"""
        async def health_check(request):
            """Health check endpoint"""
            return JSONResponse({
                "status": "healthy",
                "server": "iacsgraph-query-assistant-http",
                "version": "2.0.0",
                "transport": "http-streaming"
            }, headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Mcp-Session-Id, MCP-Protocol-Version",
                "Access-Control-Expose-Headers": "Mcp-Session-Id"
            })
        
        async def server_info(request):
            """Server information endpoint"""
            return JSONResponse({
                "name": "iacsgraph-query-assistant-http",
                "version": "2.0.0",
                "protocol": "mcp",
                "transport": "http-streaming",
                "endpoints": {
                    "streaming": "/stream",
                    "health": "/health",
                    "info": "/info"
                }
            })
        
        # OPTIONS handler for CORS preflight
        async def options_handler(request):
            return Response(
                "",
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS, DELETE",
                    "Access-Control-Allow-Headers": "Content-Type, Mcp-Session-Id, Authorization, MCP-Protocol-Version",
                    "Access-Control-Expose-Headers": "Mcp-Session-Id",
                    "Access-Control-Max-Age": "3600"
                }
            )
        
        # Root endpoint handler
        async def root_handler(request):
            """Handle root endpoint requests"""
            if request.method == "POST":
                # For POST requests, handle as MCP request
                return await self._handle_streaming_request(request)
            else:
                # For GET/HEAD requests, return server info
                return JSONResponse({
                    "name": "iacsgraph-query-assistant-http",
                    "version": "2.0.0",
                    "protocol": "mcp",
                    "transport": "http",
                    "endpoints": {
                        "mcp": "/",
                        "health": "/health",
                        "info": "/info"
                    }
                }, headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS, HEAD, DELETE",
                    "Access-Control-Allow-Headers": "Content-Type, Mcp-Session-Id, Authorization, MCP-Protocol-Version",
                    "Access-Control-Expose-Headers": "Mcp-Session-Id"
                })
        
        # Register endpoint - for client registration
        async def register_handler(request):
            """Handle client registration"""
            return JSONResponse({
                "success": True,
                "message": "No registration required - this is an open server",
                "endpoint": "/stream"
            }, headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type"
            })
        
        # OAuth discovery endpoints - indicate no auth required
        async def oauth_authorization_server(request):
            """OAuth authorization server metadata - returns empty to indicate no auth"""
            # Return 404 to indicate OAuth is not supported
            return JSONResponse(
                {"error": "OAuth not supported - this server does not require authentication"},
                status_code=404,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Content-Type": "application/json"
                }
            )
        
        async def oauth_protected_resource(request):
            """OAuth protected resource metadata - returns empty to indicate no auth"""
            # Return 404 to indicate this resource is not OAuth protected
            return JSONResponse(
                {"error": "This resource does not require authentication"},
                status_code=404,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Content-Type": "application/json"
                }
            )
        
        # Create routes
        routes = [
            # Root endpoint
            Route("/", endpoint=root_handler, methods=["GET", "POST", "HEAD"]),
            Route("/", endpoint=options_handler, methods=["OPTIONS"]),
            # MCP endpoint (alias for root)
            Route("/mcp", endpoint=self._handle_streaming_request, methods=["POST"]),
            Route("/mcp", endpoint=options_handler, methods=["OPTIONS"]),
            # Register endpoint
            Route("/register", endpoint=register_handler, methods=["POST"]),
            Route("/register", endpoint=options_handler, methods=["OPTIONS"]),
            # Health and info endpoints
            Route("/health", endpoint=health_check, methods=["GET"]),
            Route("/info", endpoint=server_info, methods=["GET"]),
            # Streaming endpoints (both /stream and /steam for compatibility)
            Route("/stream", endpoint=self._handle_streaming_request, methods=["POST"]),
            Route("/steam", endpoint=self._handle_streaming_request, methods=["POST", "GET", "HEAD"]),
            Route("/stream", endpoint=options_handler, methods=["OPTIONS"]),
            Route("/steam", endpoint=options_handler, methods=["OPTIONS"]),
            Route("/health", endpoint=options_handler, methods=["OPTIONS"]),
            Route("/info", endpoint=options_handler, methods=["OPTIONS"]),
            # OAuth discovery endpoints
            Route("/.well-known/oauth-authorization-server", endpoint=oauth_authorization_server, methods=["GET"]),
            Route("/.well-known/oauth-protected-resource", endpoint=oauth_protected_resource, methods=["GET"]),
            Route("/.well-known/oauth-authorization-server/stream", endpoint=oauth_authorization_server, methods=["GET"]),
            Route("/.well-known/oauth-protected-resource/stream", endpoint=oauth_protected_resource, methods=["GET"]),
            Route("/.well-known/oauth-authorization-server/steam", endpoint=oauth_authorization_server, methods=["GET"]),
            Route("/.well-known/oauth-protected-resource/steam", endpoint=oauth_protected_resource, methods=["GET"]),
        ]
        
        return Starlette(routes=routes)
    
    def run(self):
        """Run the HTTP streaming MCP server"""
        logger.info(f"Starting HTTP Streaming MCP Server on http://{self.host}:{self.port}")
        logger.info(f"Streaming endpoint: http://{self.host}:{self.port}/stream")
        logger.info(f"Health check: http://{self.host}:{self.port}/health")
        logger.info(f"Server info: http://{self.host}:{self.port}/info")
        
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
            logging.FileHandler('/home/kimghw/IACSGRAPH/mcp_server_latest.log')
        ]
    )
    
    # Get configuration from environment or use defaults
    db_config = {
        "type": os.getenv("DB_TYPE", "sqlite"),
        "path": os.getenv("DB_PATH", "data/iacsgraph.db")
    }
    
    server = HTTPStreamingMCPServer(
        db_config=db_config,
        qdrant_url=os.getenv("QDRANT_URL", "localhost"),
        qdrant_port=int(os.getenv("QDRANT_PORT", "6333")),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        host=os.getenv("MCP_HOST", "0.0.0.0"),
        port=int(os.getenv("MCP_PORT", "8766"))  # Different port from SSE server
    )
    
    # Run the server
    server.run()


if __name__ == "__main__":
    main()