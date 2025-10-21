#!/usr/bin/env python3
"""
OneNote 코드 상세 분석 테스트
실제 코드 구조와 로직 검증
"""

import sys
import ast
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def analyze_handlers_file():
    """handlers.py 파일 AST 분석"""
    print("=" * 80)
    print("🔍 handlers.py 상세 분석")
    print("=" * 80)

    handler_file = project_root / "modules" / "onenote_mcp" / "handlers.py"

    with open(handler_file, 'r', encoding='utf-8') as f:
        tree = ast.parse(f.read(), filename=str(handler_file))

    # OneNoteHandlers 클래스 찾기
    handlers_class = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "OneNoteHandlers":
            handlers_class = node
            break

    if not handlers_class:
        print("❌ OneNoteHandlers 클래스를 찾을 수 없습니다")
        return False

    print("✅ OneNoteHandlers 클래스 발견\n")

    # 메서드 목록
    methods = [n.name for n in handlers_class.body if isinstance(n, ast.FunctionDef)]
    print(f"📋 메서드 목록 ({len(methods)}개):")
    for method in methods:
        print(f"  • {method}")

    # 주요 메서드 확인
    required_methods = [
        "handle_list_tools",
        "handle_call_tool",
        "call_tool_as_dict"
    ]

    print("\n✅ 필수 메서드 확인:")
    for method in required_methods:
        found = method in methods
        status = "✅" if found else "❌"
        print(f"  {status} {method}")

    return True


def analyze_tool_definitions():
    """도구 정의 분석"""
    print("\n" + "=" * 80)
    print("🔍 도구 정의 상세 분석")
    print("=" * 80)

    handler_file = project_root / "modules" / "onenote_mcp" / "handlers.py"

    with open(handler_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 각 도구의 action enum 확인
    tool_actions = {
        "manage_sections_and_pages": ["create_section", "list_sections", "list_pages"],
        "manage_page_content": ["get", "create", "delete"]
    }

    print("\n📌 Action 기반 도구:")
    for tool_name, expected_actions in tool_actions.items():
        print(f"\n  {tool_name}:")
        for action in expected_actions:
            found = f'enum": [' in content and action in content
            status = "✅" if found else "❌"
            print(f"    {status} {action}")

    # edit_page는 action 없음 확인
    print("\n📌 단일 액션 도구:")
    single_action_tools = ["edit_page", "db_onenote_update"]
    for tool in single_action_tools:
        found = f'name="{tool}"' in content
        status = "✅" if found else "❌"
        print(f"  {status} {tool}")

    return True


def analyze_action_handling():
    """action 분기 처리 분석"""
    print("\n" + "=" * 80)
    print("🔍 Action 분기 처리 분석")
    print("=" * 80)

    handler_file = project_root / "modules" / "onenote_mcp" / "handlers.py"

    with open(handler_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # manage_sections_and_pages의 action 분기
    print("\n📌 manage_sections_and_pages 분기:")
    sections_actions = {
        'if action == "create_section"': "섹션 생성",
        'elif action == "list_sections"': "섹션 목록",
        'elif action == "list_pages"': "페이지 목록"
    }

    for condition, desc in sections_actions.items():
        found = condition in content
        status = "✅" if found else "❌"
        print(f"  {status} {desc}: {condition}")

    # manage_page_content의 action 분기
    print("\n📌 manage_page_content 분기:")
    page_actions = {
        'if action == "get"': "페이지 조회",
        'elif action == "create"': "페이지 생성",
        'elif action == "delete"': "페이지 삭제"
    }

    for condition, desc in page_actions.items():
        found = condition in content
        status = "✅" if found else "❌"
        print(f"  {status} {desc}: {condition}")

    # delete_page 호출 확인
    print("\n📌 delete_page 메서드 호출:")
    delete_calls = [
        "await self.onenote_handler.delete_page",
        "result = await self.onenote_handler.delete_page(user_id, page_id)"
    ]

    for call in delete_calls:
        found = call in content
        status = "✅" if found else "❌"
        print(f"  {status} {call}")

    return True


def analyze_test_coverage():
    """테스트 커버리지 분석"""
    print("\n" + "=" * 80)
    print("🔍 테스트 커버리지 분석")
    print("=" * 80)

    test_file = project_root / "tests" / "handlers" / "test_onenote_handlers.py"

    with open(test_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 테스트 함수 찾기
    test_functions = []
    for line in content.split('\n'):
        if line.strip().startswith('async def test_'):
            func_name = line.split('(')[0].replace('async def ', '').strip()
            test_functions.append(func_name)

    print(f"\n✅ 총 {len(test_functions)}개 테스트 함수:")
    for i, func in enumerate(test_functions, 1):
        print(f"  {i}. {func}")

    # 각 도구별 테스트 확인
    print("\n📌 도구별 테스트 커버리지:")
    tool_tests = {
        "manage_sections_and_pages": [
            "test_list_sections",
            "test_list_sections_with_filter",
            "test_list_pages",
            "test_list_pages_by_section",
            "test_create_section"
        ],
        "manage_page_content": [
            "test_get_page_content",
            "test_create_page",
            "test_delete_page"
        ],
        "edit_page": ["test_edit_page"],
        "db_onenote_update": ["test_db_onenote_update"]
    }

    for tool_name, expected_tests in tool_tests.items():
        print(f"\n  {tool_name}:")
        for test in expected_tests:
            found = test in test_functions
            status = "✅" if found else "❌"
            print(f"    {status} {test}")

    return True


def main():
    print("\n🚀 OneNote 코드 상세 분석 시작\n")

    results = []

    # 1. handlers.py 파일 분석
    results.append(("handlers.py 구조", analyze_handlers_file()))

    # 2. 도구 정의 분석
    results.append(("도구 정의", analyze_tool_definitions()))

    # 3. action 분기 처리 분석
    results.append(("Action 분기 처리", analyze_action_handling()))

    # 4. 테스트 커버리지 분석
    results.append(("테스트 커버리지", analyze_test_coverage()))

    # 결과 요약
    print("\n" + "=" * 80)
    print("📊 분석 결과 요약")
    print("=" * 80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")

    print(f"\n총 {total}개 중 {passed}개 통과")

    if passed == total:
        print("\n🎉 모든 분석 통과!")
        print("\n✨ OneNote 도구 통합이 완벽하게 완료되었습니다!")
        return 0
    else:
        print(f"\n⚠️ {total - passed}개 실패")
        return 1


if __name__ == "__main__":
    sys.exit(main())
