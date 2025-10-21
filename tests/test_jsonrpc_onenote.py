#!/usr/bin/env python3
"""
OneNote MCP JSON-RPC 스타일 테스트
핸들러를 직접 호출하여 JSON-RPC 형식으로 테스트
"""

import sys
import asyncio
import json
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from modules.onenote_mcp.handlers import OneNoteHandlers


def print_test_header(test_name: str):
    """테스트 헤더 출력"""
    print("\n" + "=" * 80)
    print(f"🧪 {test_name}")
    print("=" * 80)


def print_result(result):
    """결과를 JSON 형식으로 예쁘게 출력"""
    if isinstance(result, list):
        for item in result:
            if hasattr(item, 'text'):
                try:
                    data = json.loads(item.text)
                    print(json.dumps(data, indent=2, ensure_ascii=False))
                except:
                    print(item.text)
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))


async def test_list_tools():
    """tools/list 테스트"""
    print_test_header("1. tools/list - 도구 목록 조회")

    handler = OneNoteHandlers()
    tools = await handler.handle_list_tools()

    print(f"\n✅ 총 {len(tools)}개의 도구가 등록되어 있습니다.\n")

    for i, tool in enumerate(tools, 1):
        print(f"{i}. {tool.name}")
        print(f"   설명: {tool.description}")
        print(f"   필수 파라미터: {tool.inputSchema.get('required', [])}")

        # action이 있는 경우 enum 표시
        if 'action' in tool.inputSchema.get('properties', {}):
            actions = tool.inputSchema['properties']['action'].get('enum', [])
            print(f"   actions: {actions}")
        print()


async def test_manage_sections_and_pages():
    """manage_sections_and_pages 도구 테스트"""

    # 1. list_sections
    print_test_header("2. manage_sections_and_pages - list_sections")
    handler = OneNoteHandlers()

    request = {
        "action": "list_sections",
        "user_id": "kimghw"
    }
    print(f"📤 Request: {json.dumps(request, indent=2)}")

    result = await handler.handle_call_tool("manage_sections_and_pages", request)
    print("\n📥 Response:")
    print_result(result)

    # 2. list_pages
    print_test_header("3. manage_sections_and_pages - list_pages")

    request = {
        "action": "list_pages",
        "user_id": "kimghw"
    }
    print(f"📤 Request: {json.dumps(request, indent=2)}")

    result = await handler.handle_call_tool("manage_sections_and_pages", request)
    print("\n📥 Response:")
    print_result(result)


async def test_manage_page_content():
    """manage_page_content 도구 테스트"""

    # 1. get
    print_test_header("4. manage_page_content - get (페이지 조회)")
    handler = OneNoteHandlers()

    request = {
        "action": "get",
        "user_id": "kimghw",
        "page_id": "test-page-id"
    }
    print(f"📤 Request: {json.dumps(request, indent=2)}")

    result = await handler.handle_call_tool("manage_page_content", request)
    print("\n📥 Response:")
    print_result(result)

    # 2. create (실제 생성하지 않고 파라미터만 확인)
    print_test_header("5. manage_page_content - create (페이지 생성)")

    request = {
        "action": "create",
        "user_id": "kimghw",
        "section_id": "test-section-id",
        "title": "Test Page from JSON-RPC",
        "content": "<html><body><p>Test content</p></body></html>"
    }
    print(f"📤 Request: {json.dumps(request, indent=2)}")
    print("\n⚠️ 실제 생성은 액세스 토큰이 필요하므로 스킵")


async def test_edit_page():
    """edit_page 도구 테스트"""
    print_test_header("6. edit_page - 페이지 편집")

    handler = OneNoteHandlers()

    request = {
        "user_id": "kimghw",
        "page_id": "test-page-id",
        "content": "<html><body><p>Appended content</p></body></html>"
    }
    print(f"📤 Request: {json.dumps(request, indent=2)}")

    result = await handler.handle_call_tool("edit_page", request)
    print("\n📥 Response:")
    print_result(result)


async def test_db_onenote_update():
    """db_onenote_update 도구 테스트"""
    print_test_header("7. db_onenote_update - DB 저장")

    handler = OneNoteHandlers()

    request = {
        "user_id": "kimghw",
        "section_id": "1-test-section",
        "section_name": "Test Section",
        "notebook_id": "1-test-notebook",
        "notebook_name": "Test Notebook"
    }
    print(f"📤 Request: {json.dumps(request, indent=2)}")

    result = await handler.handle_call_tool("db_onenote_update", request)
    print("\n📥 Response:")
    print_result(result)


async def main():
    """메인 테스트 실행"""
    print("=" * 80)
    print("🚀 OneNote MCP JSON-RPC 테스트 시작")
    print("=" * 80)

    try:
        # 1. 도구 목록 조회
        await test_list_tools()

        # 2. manage_sections_and_pages 테스트
        await test_manage_sections_and_pages()

        # 3. manage_page_content 테스트
        await test_manage_page_content()

        # 4. edit_page 테스트
        await test_edit_page()

        # 5. db_onenote_update 테스트
        await test_db_onenote_update()

        print("\n" + "=" * 80)
        print("✅ 모든 테스트 완료")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ 테스트 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
