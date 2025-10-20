#!/usr/bin/env python3
"""
JSON-RPC 형식으로 핸들러 직접 테스트

사용법:
    python tests/handlers/test_with_jsonrpc.py <module> <tool_name> <json_args>

예시:
    # Enrollment 테스트
    python tests/handlers/test_with_jsonrpc.py enrollment register_account '{"use_env_vars":true}'
    python tests/handlers/test_with_jsonrpc.py enrollment list_active_accounts '{}'
    python tests/handlers/test_with_jsonrpc.py enrollment get_account_status '{"user_id":"kimghw"}'

    # Mail Query 테스트
    python tests/handlers/test_with_jsonrpc.py mail-query help '{}'
    python tests/handlers/test_with_jsonrpc.py mail-query query_email '{"user_id":"kimghw","days_back":3,"include_body":false}'

    # OneNote 테스트
    python tests/handlers/test_with_jsonrpc.py onenote list_notebooks '{"user_id":"kimghw"}'
"""

import sys
import json
import asyncio
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from modules.enrollment.mcp_server.handlers import AuthAccountHandlers
from modules.mail_query_MCP.mcp_server.handlers import MCPHandlers
from modules.onenote_mcp.handlers import OneNoteHandlers


async def test_handler_with_jsonrpc(module: str, tool_name: str, arguments: dict):
    """JSON-RPC 형식으로 핸들러 테스트"""

    print("=" * 80)
    print(f"🧪 JSON-RPC 핸들러 테스트")
    print("=" * 80)
    print(f"📦 모듈: {module}")
    print(f"🔧 툴: {tool_name}")
    print(f"📝 인자: {json.dumps(arguments, indent=2, ensure_ascii=False)}")
    print("=" * 80)
    print()

    try:
        # 핸들러 선택
        if module == "enrollment":
            handler = AuthAccountHandlers()
        elif module == "mail-query":
            handler = MCPHandlers()
        elif module == "onenote":
            handler = OneNoteHandlers()
        else:
            print(f"❌ 알 수 없는 모듈: {module}")
            print("사용 가능한 모듈: enrollment, mail-query, onenote")
            return 1

        # JSON-RPC 요청 생성
        jsonrpc_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }

        print("📤 JSON-RPC 요청:")
        print(json.dumps(jsonrpc_request, indent=2, ensure_ascii=False))
        print()
        print("⏳ 실행 중...")
        print()

        # 핸들러 호출
        result = await handler.handle_call_tool(tool_name, arguments)

        # 결과를 JSON-RPC 응답 형식으로 변환
        result_content = []
        if result:
            for item in result:
                result_content.append({
                    "type": item.type,
                    "text": item.text
                })

        jsonrpc_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "content": result_content
            }
        }

        print("=" * 80)
        print("📥 JSON-RPC 응답:")
        print("=" * 80)
        print(json.dumps(jsonrpc_response, indent=2, ensure_ascii=False))
        print()

        print("=" * 80)
        print("📄 결과 텍스트:")
        print("=" * 80)
        if result_content:
            print(result_content[0]["text"])
        else:
            print("(결과 없음)")

        print()
        print("✅ 테스트 완료")
        return 0

    except Exception as e:
        print("=" * 80)
        print("❌ 에러 발생:")
        print("=" * 80)
        print(f"{type(e).__name__}: {e}")

        # JSON-RPC 에러 응답 형식
        jsonrpc_error = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {
                "code": -32603,
                "message": "Internal error",
                "data": {
                    "type": type(e).__name__,
                    "message": str(e)
                }
            }
        }

        print()
        print("📥 JSON-RPC 에러 응답:")
        print(json.dumps(jsonrpc_error, indent=2, ensure_ascii=False))

        import traceback
        print()
        print("상세 스택:")
        traceback.print_exc()

        return 1


def main():
    """메인 함수"""
    if len(sys.argv) < 3:
        print("사용법: python test_with_jsonrpc.py <module> <tool_name> <json_args>")
        print()
        print("모듈:")
        print("  enrollment  - Enrollment MCP (계정 관리)")
        print("  mail-query  - Mail Query MCP (이메일 조회)")
        print("  onenote     - OneNote MCP (OneNote 관리)")
        print()
        print("예시:")
        print('  python test_with_jsonrpc.py enrollment register_account \'{"use_env_vars":true}\'')
        print('  python test_with_jsonrpc.py enrollment list_active_accounts \'{}\'')
        print('  python test_with_jsonrpc.py mail-query help \'{}\'')
        print('  python test_with_jsonrpc.py mail-query query_email \'{"user_id":"kimghw","days_back":3}\'')
        print('  python test_with_jsonrpc.py onenote list_notebooks \'{"user_id":"kimghw"}\'')
        return 1

    module = sys.argv[1]
    tool_name = sys.argv[2]

    # JSON 인자 파싱
    if len(sys.argv) >= 4:
        try:
            arguments = json.loads(sys.argv[3])
        except json.JSONDecodeError as e:
            print(f"❌ JSON 파싱 실패: {e}")
            print(f"입력된 값: {sys.argv[3]}")
            return 1
    else:
        arguments = {}

    # 비동기 테스트 실행
    exit_code = asyncio.run(test_handler_with_jsonrpc(module, tool_name, arguments))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
