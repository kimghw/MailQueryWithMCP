#!/usr/bin/env python3
"""
OneNote MCP JSON-RPC 간단 테스트
의존성 없이 도구 스키마만 확인
"""

import json

# 통합된 도구 정의
onenote_tools = [
    {
        "name": "manage_sections_and_pages",
        "description": "OneNote 섹션과 페이지를 관리합니다. action 파라미터로 동작을 지정",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["create_section", "list_sections", "list_pages"],
                    "description": "수행할 작업"
                },
                "user_id": {"type": "string", "description": "사용자 ID"},
                "notebook_id": {"type": "string", "description": "노트북 ID (create_section 시 필수)"},
                "section_name": {"type": "string", "description": "섹션 이름"},
                "section_id": {"type": "string", "description": "섹션 ID"},
                "page_title": {"type": "string", "description": "페이지 제목"}
            },
            "required": ["action", "user_id"]
        }
    },
    {
        "name": "manage_page_content",
        "description": "OneNote 페이지 내용을 관리합니다. action 파라미터로 동작을 지정",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["get", "create", "delete"],
                    "description": "수행할 작업: get(내용 조회), create(페이지 생성), delete(페이지 삭제)"
                },
                "user_id": {"type": "string", "description": "사용자 ID"},
                "page_id": {"type": "string", "description": "페이지 ID (get, delete 시 필수)"},
                "section_id": {"type": "string", "description": "섹션 ID (create 시 필수)"},
                "title": {"type": "string", "description": "페이지 제목 (create 시 필수)"},
                "content": {"type": "string", "description": "페이지 내용 HTML (create 시 필수)"}
            },
            "required": ["action", "user_id"]
        }
    },
    {
        "name": "edit_page",
        "description": "OneNote 페이지 내용을 편집합니다 (내용 추가/append).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "사용자 ID"},
                "page_id": {"type": "string", "description": "OneNote 페이지 ID"},
                "content": {"type": "string", "description": "추가할 내용 (HTML)"}
            },
            "required": ["user_id", "page_id", "content"]
        }
    },
    {
        "name": "db_onenote_update",
        "description": "OneNote 섹션 또는 페이지 정보를 데이터베이스에 저장/업데이트합니다.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "사용자 ID"},
                "section_id": {"type": "string", "description": "섹션 ID"},
                "section_name": {"type": "string", "description": "섹션 이름"},
                "notebook_id": {"type": "string", "description": "노트북 ID"},
                "notebook_name": {"type": "string", "description": "노트북 이름"},
                "page_id": {"type": "string", "description": "페이지 ID"},
                "page_title": {"type": "string", "description": "페이지 제목"}
            },
            "required": ["user_id"]
        }
    }
]


def print_header(title):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def test_tool_schemas():
    """도구 스키마 검증"""
    print_header("🔧 OneNote MCP 도구 스키마")

    print(f"\n총 {len(onenote_tools)}개의 도구가 정의되어 있습니다.\n")

    for i, tool in enumerate(onenote_tools, 1):
        print(f"{i}. {tool['name']}")
        print(f"   설명: {tool['description']}")
        print(f"   필수 파라미터: {tool['inputSchema']['required']}")

        # action이 있는 경우 enum 표시
        props = tool['inputSchema']['properties']
        if 'action' in props:
            actions = props['action'].get('enum', [])
            print(f"   ✓ actions: {', '.join(actions)}")

        print()


def test_jsonrpc_requests():
    """JSON-RPC 요청 예시"""
    print_header("📤 JSON-RPC 요청 예시")

    test_cases = [
        {
            "name": "1. list_sections - 섹션 목록 조회",
            "method": "tools/call",
            "params": {
                "name": "manage_sections_and_pages",
                "arguments": {
                    "action": "list_sections",
                    "user_id": "kimghw"
                }
            }
        },
        {
            "name": "2. list_pages - 페이지 목록 조회",
            "method": "tools/call",
            "params": {
                "name": "manage_sections_and_pages",
                "arguments": {
                    "action": "list_pages",
                    "user_id": "kimghw"
                }
            }
        },
        {
            "name": "3. create_section - 섹션 생성",
            "method": "tools/call",
            "params": {
                "name": "manage_sections_and_pages",
                "arguments": {
                    "action": "create_section",
                    "user_id": "kimghw",
                    "notebook_id": "1-notebook-123",
                    "section_name": "새 섹션"
                }
            }
        },
        {
            "name": "4. get page content - 페이지 내용 조회",
            "method": "tools/call",
            "params": {
                "name": "manage_page_content",
                "arguments": {
                    "action": "get",
                    "user_id": "kimghw",
                    "page_id": "1-page-456"
                }
            }
        },
        {
            "name": "5. create page - 페이지 생성",
            "method": "tools/call",
            "params": {
                "name": "manage_page_content",
                "arguments": {
                    "action": "create",
                    "user_id": "kimghw",
                    "section_id": "1-section-789",
                    "title": "테스트 페이지",
                    "content": "<html><body><p>내용</p></body></html>"
                }
            }
        },
        {
            "name": "6. delete page - 페이지 삭제",
            "method": "tools/call",
            "params": {
                "name": "manage_page_content",
                "arguments": {
                    "action": "delete",
                    "user_id": "kimghw",
                    "page_id": "1-page-456"
                }
            }
        },
        {
            "name": "7. edit_page - 페이지 편집 (내용 추가)",
            "method": "tools/call",
            "params": {
                "name": "edit_page",
                "arguments": {
                    "user_id": "kimghw",
                    "page_id": "1-page-456",
                    "content": "<html><body><p>추가 내용</p></body></html>"
                }
            }
        }
    ]

    for test_case in test_cases:
        print(f"\n{test_case['name']}")
        print("-" * 80)

        jsonrpc_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": test_case['method'],
            "params": test_case['params']
        }

        print(json.dumps(jsonrpc_request, indent=2, ensure_ascii=False))


def main():
    print("=" * 80)
    print("  🚀 OneNote MCP JSON-RPC 스키마 테스트")
    print("=" * 80)

    # 1. 도구 스키마 확인
    test_tool_schemas()

    # 2. JSON-RPC 요청 예시
    test_jsonrpc_requests()

    print("\n" + "=" * 80)
    print("  ✅ 테스트 완료")
    print("=" * 80)
    print("\n💡 실제 테스트는 서버를 실행한 후 HTTP 요청으로 진행하세요.")
    print("   python entrypoints/production/unified_http_server.py\n")


if __name__ == "__main__":
    main()
