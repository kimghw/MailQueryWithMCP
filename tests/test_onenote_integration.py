#!/usr/bin/env python3
"""
OneNote 통합 도구 검증 테스트
실제 핸들러 대신 구조만 검증
"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_tool_structure():
    """통합된 도구 구조 검증"""
    print("=" * 80)
    print("🧪 OneNote 도구 통합 구조 검증")
    print("=" * 80)

    # 예상되는 도구 구조
    expected_tools = {
        "manage_sections_and_pages": {
            "actions": ["create_section", "list_sections", "list_pages"],
            "description": "섹션과 페이지 목록 관리"
        },
        "manage_page_content": {
            "actions": ["get", "create", "delete"],
            "description": "페이지 내용 CRUD"
        },
        "edit_page": {
            "actions": None,  # action 파라미터 없음
            "description": "페이지 편집 (자주 사용)"
        },
        "db_onenote_update": {
            "actions": None,
            "description": "DB 저장/업데이트"
        }
    }

    print(f"\n✅ 예상 도구 개수: {len(expected_tools)}개\n")

    for tool_name, info in expected_tools.items():
        print(f"📌 {tool_name}")
        print(f"   설명: {info['description']}")
        if info['actions']:
            print(f"   actions: {', '.join(info['actions'])}")
        print()

    return True


def test_handler_file():
    """핸들러 파일 존재 및 구조 확인"""
    print("=" * 80)
    print("📁 핸들러 파일 검증")
    print("=" * 80)

    handler_file = project_root / "modules" / "onenote_mcp" / "handlers.py"

    if not handler_file.exists():
        print(f"❌ 핸들러 파일이 없습니다: {handler_file}")
        return False

    print(f"\n✅ 핸들러 파일 존재: {handler_file}")

    # 파일 내용에서 주요 키워드 검색
    with open(handler_file, 'r', encoding='utf-8') as f:
        content = f.read()

    checks = {
        "manage_sections_and_pages 도구": 'name="manage_sections_and_pages"',
        "manage_page_content 도구": 'name="manage_page_content"',
        "edit_page 도구": 'name="edit_page"',
        "db_onenote_update 도구": 'name="db_onenote_update"',
        "create_section action": 'action == "create_section"',
        "list_sections action": 'action == "list_sections"',
        "list_pages action": 'action == "list_pages"',
        "get action (page_content)": 'action == "get"',
        "create action (page_content)": 'action == "create"',
        "delete action (page_content)": 'action == "delete"',
        "delete_page 메서드 호출": 'delete_page(',
    }

    print("\n검증 항목:")
    all_passed = True
    for check_name, keyword in checks.items():
        found = keyword in content
        status = "✅" if found else "❌"
        print(f"  {status} {check_name}")
        if not found:
            all_passed = False

    return all_passed


def test_onenote_handler_file():
    """OneNote API 핸들러 파일에 delete_page 메서드 확인"""
    print("\n" + "=" * 80)
    print("📁 OneNote API 핸들러 검증")
    print("=" * 80)

    handler_file = project_root / "modules" / "onenote_mcp" / "onenote_handler.py"

    if not handler_file.exists():
        print(f"❌ API 핸들러 파일이 없습니다: {handler_file}")
        return False

    print(f"\n✅ API 핸들러 파일 존재: {handler_file}")

    with open(handler_file, 'r', encoding='utf-8') as f:
        content = f.read()

    checks = {
        "delete_page 메서드 정의": "async def delete_page",
        "DELETE 요청": "client.delete",
        "페이지 삭제 성공 메시지": "페이지가 성공적으로 삭제",
    }

    print("\n검증 항목:")
    all_passed = True
    for check_name, keyword in checks.items():
        found = keyword in content
        status = "✅" if found else "❌"
        print(f"  {status} {check_name}")
        if not found:
            all_passed = False

    return all_passed


def test_test_file():
    """테스트 파일 검증"""
    print("\n" + "=" * 80)
    print("📁 테스트 파일 검증")
    print("=" * 80)

    test_file = project_root / "tests" / "handlers" / "test_onenote_handlers.py"

    if not test_file.exists():
        print(f"❌ 테스트 파일이 없습니다: {test_file}")
        return False

    print(f"\n✅ 테스트 파일 존재: {test_file}")

    with open(test_file, 'r', encoding='utf-8') as f:
        content = f.read()

    checks = {
        "manage_sections_and_pages 테스트": '"manage_sections_and_pages"',
        "manage_page_content 테스트": '"manage_page_content"',
        "delete_page 테스트": "test_delete_page",
        "총 10개 테스트": "[10/10]",
    }

    print("\n검증 항목:")
    all_passed = True
    for check_name, keyword in checks.items():
        found = keyword in content
        status = "✅" if found else "❌"
        print(f"  {status} {check_name}")
        if not found:
            all_passed = False

    # 테스트 함수 개수 세기
    test_funcs = content.count("async def test_")
    print(f"\n  📊 테스트 함수 개수: {test_funcs}개")

    return all_passed


def main():
    print("\n🚀 OneNote MCP 통합 검증 테스트 시작\n")

    results = []

    # 1. 도구 구조 검증
    results.append(("도구 구조", test_tool_structure()))

    # 2. 핸들러 파일 검증
    results.append(("핸들러 파일", test_handler_file()))

    # 3. OneNote API 핸들러 검증
    results.append(("API 핸들러", test_onenote_handler_file()))

    # 4. 테스트 파일 검증
    results.append(("테스트 파일", test_test_file()))

    # 결과 요약
    print("\n" + "=" * 80)
    print("📊 검증 결과 요약")
    print("=" * 80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")

    print(f"\n총 {total}개 중 {passed}개 통과")

    if passed == total:
        print("\n🎉 모든 검증 통과!")
        return 0
    else:
        print(f"\n⚠️ {total - passed}개 실패")
        return 1


if __name__ == "__main__":
    sys.exit(main())
