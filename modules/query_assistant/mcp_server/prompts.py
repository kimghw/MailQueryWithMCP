"""Query Prompts for MCP Server"""

import logging
from typing import Any, Dict, List
from pathlib import Path

from mcp.types import Prompt, PromptMessage, PromptArgument, TextContent

from infra.core.logger import get_logger

logger = get_logger(__name__)


class QueryPrompts:
    """Query prompts for MCP Server"""
    
    def __init__(self):
        self.system_prompt = self._load_system_prompt()
        logger.info("📋 QueryPrompts initialized")
    
    def get_prompts(self) -> List[Prompt]:
        """Get available prompts"""
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
    
    async def get_prompt(self, name: str, arguments: Dict[str, Any]) -> PromptMessage:
        """Get specific prompt"""
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
    
    def _load_system_prompt(self) -> str:
        """Load system prompt from file"""
        prompt_file = Path(__file__).parent.parent / "prompts" / "mcp_system_prompt.txt"
        try:
            with open(prompt_file, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logger.warning(f"System prompt file not found: {prompt_file}")
            return "IACSGRAPH 해양 데이터베이스 쿼리 처리 시스템입니다."
        except Exception as e:
            logger.error(f"Error loading system prompt: {e}")
            return "IACSGRAPH 해양 데이터베이스 쿼리 처리 시스템입니다."