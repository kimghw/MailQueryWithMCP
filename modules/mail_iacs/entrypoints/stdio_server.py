"""
IACS MCP stdio 서버
Claude Desktop과 통합 - MCP 표준 구조
"""

import asyncio
from mcp.server.models import InitializationOptions
from mcp.server import Server, NotificationOptions
from mcp.server.stdio import stdio_server

from infra.core.logger import get_logger
from modules.mail_iacs.handlers import IACSHandlers

logger = get_logger(__name__)

# MCP 서버 및 핸들러 인스턴스 생성
app = Server("iacs-mail-server")
handlers = IACSHandlers()


@app.list_tools()
async def handle_list_tools():
    """사용 가능한 도구 목록 반환 - Handler 위임"""
    return await handlers.handle_list_tools()


@app.call_tool()
async def handle_call_tool(name: str, arguments: dict):
    """도구 호출 처리 - Handler 위임"""
    return await handlers.handle_call_tool(name, arguments)


@app.list_prompts()
async def handle_list_prompts():
    """사용 가능한 프롬프트 목록 반환 - Handler 위임"""
    return await handlers.handle_list_prompts()


@app.get_prompt()
async def handle_get_prompt(name: str, arguments: dict):
    """프롬프트 내용 반환 - Handler 위임"""
    return await handlers.handle_get_prompt(name, arguments)


async def main():
    """메인 함수"""
    logger.info("IACS MCP stdio 서버 시작")

    try:
        async with stdio_server() as (read_stream, write_stream):
            await app.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="iacs-mail-server",
                    server_version="1.0.0",
                    capabilities=app.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )
    except Exception as e:
        logger.error(f"서버 실행 오류: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
