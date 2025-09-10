"""MCP Protocol Handlers for Query Assistant"""

import json
import logging
from typing import Any, Dict, List
from pathlib import Path

from mcp.types import Tool, TextContent, Prompt, PromptMessage, PromptArgument

from infra.core.logger import get_logger
from ..query_assistant import QueryAssistant
from ..mail_data_refresher import MailDataRefresher
from .tools import QueryTools
from .prompts import QueryPrompts
from .utils import preprocess_arguments, format_query_result, format_enhanced_result
from ..utils.logger_config import get_query_logger

logger = get_query_logger()


class MCPHandlers:
    """MCP Protocol Handlers for Query Assistant"""
    
    def __init__(self, query_assistant: QueryAssistant, mail_refresher: MailDataRefresher):
        self.query_assistant = query_assistant
        self.mail_refresher = mail_refresher
        self.tools = QueryTools(query_assistant, mail_refresher)
        self.prompts = QueryPrompts()
        
        # Track mail refresh status
        self._mail_refresh_done = False
        
        logger.info("🔧 MCPHandlers initialized")
    
    async def handle_list_tools(self) -> List[Tool]:
        """List available tools"""
        logger.info("🔧 [MCPHandlers] handle_list_tools() called")
        return self.tools.get_tools()
    
    async def handle_call_tool(self, name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle tool calls"""
        logger.info(f"🛠️ [MCPHandlers] handle_call_tool() called with tool: {name}")
        logger.info(f"📝 [MCPHandlers] Raw arguments: {json.dumps(arguments, indent=2, ensure_ascii=False)}")
        
        # Mail data refresh for krsdtp account before first query
        if not self._mail_refresh_done:
            await self._refresh_mail_data()
        
        # Preprocess arguments
        arguments = preprocess_arguments(arguments)
        logger.info(f"🔄 [MCPHandlers] Preprocessed arguments: {json.dumps(arguments, indent=2, ensure_ascii=False)}")
        
        # Delegate to tools
        result = await self.tools.execute_tool(name, arguments)
        
        # Format result based on tool type
        if name == "query_with_llm_params":
            formatted_text = format_enhanced_result(result)
        else:
            formatted_text = format_query_result(result)
        
        return [TextContent(type="text", text=formatted_text)]
    
    async def handle_list_prompts(self) -> List[Prompt]:
        """List available prompts"""
        logger.info("📋 [MCPHandlers] handle_list_prompts() called")
        return self.prompts.get_prompts()
    
    async def handle_get_prompt(self, name: str, arguments: Dict[str, Any]) -> PromptMessage:
        """Get specific prompt"""
        logger.info(f"📝 [MCPHandlers] handle_get_prompt() called with prompt: {name}")
        return await self.prompts.get_prompt(name, arguments)
    
    async def _refresh_mail_data(self):
        """Refresh mail data for krsdtp account"""
        logger.info("📧 [MCPHandlers] Refreshing mail data for krsdtp account...")
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