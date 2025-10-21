#!/usr/bin/env python3
"""
OneNote 모듈 핸들러 직접 테스트

사용법:
    python tests/handlers/test_onenote_handlers.py
"""

import sys
import asyncio
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from modules.onenote_mcp.handlers import OneNoteHandlers


def print_test_result(test_name: str, passed: bool, details: str = ""):
    """테스트 결과 출력"""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} - {test_name}")
    if details:
        print(f"  {details}")


async def test_list_sections():
    """manage_sections_and_pages (list_sections) 핸들러 테스트"""
    print("\n📁 [1/10] manage_sections_and_pages (list_sections) 핸들러 테스트...")

    try:
        handler = OneNoteHandlers()
        result = await handler.handle_call_tool(
            "manage_sections_and_pages",
            {"action": "list_sections", "user_id": "kimghw"}
        )
        result_text = result[0].text if result else ""

        # 결과 검증
        success = "sections" in result_text.lower() or "액세스 토큰이 없습니다" in result_text
        print_test_result("list_sections", success, result_text[:200])

        return success

    except Exception as e:
        print_test_result("list_sections", False, f"Exception: {e}")
        return False


async def test_list_sections_with_filter():
    """manage_sections_and_pages (list_sections 필터링) 핸들러 테스트"""
    print("\n📁 [2/10] manage_sections_and_pages (list_sections 필터) 핸들러 테스트...")

    try:
        handler = OneNoteHandlers()
        result = await handler.handle_call_tool(
            "manage_sections_and_pages",
            {"action": "list_sections", "user_id": "kimghw", "section_name": "테스트"}
        )
        result_text = result[0].text if result else ""

        # 결과 검증
        success = "sections" in result_text.lower() or "액세스 토큰이 없습니다" in result_text
        print_test_result("list_sections (필터)", success, result_text[:200])

        return success

    except Exception as e:
        print_test_result("list_sections (필터)", False, f"Exception: {e}")
        return False


async def test_list_pages():
    """manage_sections_and_pages (list_pages) 핸들러 테스트"""
    print("\n📄 [3/10] manage_sections_and_pages (list_pages) 핸들러 테스트...")

    try:
        handler = OneNoteHandlers()
        result = await handler.handle_call_tool(
            "manage_sections_and_pages",
            {"action": "list_pages", "user_id": "kimghw"}
        )
        result_text = result[0].text if result else ""

        # 결과 검증
        success = "pages" in result_text.lower() or "액세스 토큰이 없습니다" in result_text
        print_test_result("list_pages (전체)", success, result_text[:200])

        return success

    except Exception as e:
        print_test_result("list_pages (전체)", False, f"Exception: {e}")
        return False


async def test_list_pages_by_section():
    """manage_sections_and_pages (list_pages 섹션 필터) 핸들러 테스트"""
    print("\n📄 [4/10] manage_sections_and_pages (list_pages 섹션 필터) 핸들러 테스트...")

    try:
        handler = OneNoteHandlers()
        result = await handler.handle_call_tool(
            "manage_sections_and_pages",
            {"action": "list_pages", "user_id": "kimghw", "section_id": "1-test-section"}
        )
        result_text = result[0].text if result else ""

        # 결과 검증
        success = "pages" in result_text.lower() or "액세스 토큰이 없습니다" in result_text
        print_test_result("list_pages (섹션별)", success, result_text[:200])

        return success

    except Exception as e:
        print_test_result("list_pages (섹션별)", False, f"Exception: {e}")
        return False


async def test_create_section():
    """manage_sections_and_pages (create_section) 핸들러 테스트"""
    print("\n📁 [5/10] manage_sections_and_pages (create_section) 핸들러 테스트...")

    try:
        handler = OneNoteHandlers()
        result = await handler.handle_call_tool(
            "manage_sections_and_pages",
            {
                "action": "create_section",
                "user_id": "kimghw",
                "notebook_id": "1-test-notebook",
                "section_name": "Test Section"
            }
        )
        result_text = result[0].text if result else ""

        # 결과 검증
        success = "success" in result_text.lower() or "액세스 토큰이 없습니다" in result_text
        print_test_result("create_section", success, result_text[:200])

        return success

    except Exception as e:
        print_test_result("create_section", False, f"Exception: {e}")
        return False


async def test_get_page_content():
    """manage_page_content (get) 핸들러 테스트"""
    print("\n📄 [6/10] manage_page_content (get) 핸들러 테스트...")

    try:
        handler = OneNoteHandlers()
        result = await handler.handle_call_tool(
            "manage_page_content",
            {"action": "get", "user_id": "kimghw", "page_id": "1-test-page"}
        )
        result_text = result[0].text if result else ""

        # 결과 검증
        success = "content" in result_text.lower() or "액세스 토큰이 없습니다" in result_text or "error" in result_text.lower()
        print_test_result("get_page_content", success, result_text[:200])

        return success

    except Exception as e:
        print_test_result("get_page_content", False, f"Exception: {e}")
        return False


async def test_create_page():
    """manage_page_content (create) 핸들러 테스트"""
    print("\n📝 [7/10] manage_page_content (create) 핸들러 테스트...")

    try:
        handler = OneNoteHandlers()
        result = await handler.handle_call_tool(
            "manage_page_content",
            {
                "action": "create",
                "user_id": "kimghw",
                "section_id": "1-test-section",
                "title": "Test Page",
                "content": "<html><body><p>Test content</p></body></html>"
            }
        )
        result_text = result[0].text if result else ""

        # 결과 검증
        success = "success" in result_text.lower() or "액세스 토큰이 없습니다" in result_text
        print_test_result("create_page", success, result_text[:200])

        return success

    except Exception as e:
        print_test_result("create_page", False, f"Exception: {e}")
        return False


async def test_delete_page():
    """manage_page_content (delete) 핸들러 테스트"""
    print("\n🗑️ [8/10] manage_page_content (delete) 핸들러 테스트...")

    try:
        handler = OneNoteHandlers()
        result = await handler.handle_call_tool(
            "manage_page_content",
            {"action": "delete", "user_id": "kimghw", "page_id": "1-test-page"}
        )
        result_text = result[0].text if result else ""

        # 결과 검증
        success = "success" in result_text.lower() or "액세스 토큰이 없습니다" in result_text or "error" in result_text.lower()
        print_test_result("delete_page", success, result_text[:200])

        return success

    except Exception as e:
        print_test_result("delete_page", False, f"Exception: {e}")
        return False


async def test_edit_page():
    """edit_page 핸들러 테스트 (기존 update_page)"""
    print("\n✏️ [9/10] edit_page 핸들러 테스트...")

    try:
        handler = OneNoteHandlers()
        result = await handler.handle_call_tool(
            "edit_page",
            {
                "user_id": "kimghw",
                "page_id": "1-test-page",
                "content": "<html><body><p>Updated content</p></body></html>"
            }
        )
        result_text = result[0].text if result else ""

        # 결과 검증
        success = "success" in result_text.lower() or "액세스 토큰이 없습니다" in result_text
        print_test_result("edit_page", success, result_text[:200])

        return success

    except Exception as e:
        print_test_result("edit_page", False, f"Exception: {e}")
        return False


async def test_db_onenote_update():
    """db_onenote_update 핸들러 테스트"""
    print("\n💾 [10/10] db_onenote_update 핸들러 테스트...")

    try:
        handler = OneNoteHandlers()
        result = await handler.handle_call_tool(
            "db_onenote_update",
            {
                "user_id": "kimghw",
                "section_id": "1-test-section",
                "section_name": "Test Section",
                "notebook_id": "1-test-notebook",
                "notebook_name": "Test Notebook"
            }
        )
        result_text = result[0].text if result else ""

        # 결과 검증
        success = "success" in result_text.lower()
        print_test_result("db_onenote_update", success, result_text[:200])

        return success

    except Exception as e:
        print_test_result("db_onenote_update", False, f"Exception: {e}")
        return False


async def run_tests():
    """비동기 테스트 실행"""
    results = []

    # 테스트 실행
    results.append(await test_list_sections())
    results.append(await test_list_sections_with_filter())
    results.append(await test_list_pages())
    results.append(await test_list_pages_by_section())
    results.append(await test_create_section())
    results.append(await test_get_page_content())
    results.append(await test_create_page())
    results.append(await test_delete_page())
    results.append(await test_edit_page())
    results.append(await test_db_onenote_update())

    return results


def main():
    """메인 테스트 실행"""
    print("=" * 80)
    print("🧪 OneNote 핸들러 직접 테스트")
    print("=" * 80)

    # 비동기 테스트 실행
    results = asyncio.run(run_tests())

    # 결과 요약
    print("\n" + "=" * 80)
    print("📊 테스트 결과 요약")
    print("=" * 80)

    total = len(results)
    passed = sum(results)
    failed = total - passed

    print(f"총 테스트: {total}개")
    print(f"✅ 성공: {passed}개")
    print(f"❌ 실패: {failed}개")

    if failed == 0:
        print("\n✅ 모든 테스트 통과!")
        return 0
    else:
        print(f"\n❌ {failed}개의 테스트 실패")
        return 1


if __name__ == "__main__":
    sys.exit(main())
