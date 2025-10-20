#!/usr/bin/env python3
"""
OneNote 모듈 핸들러 직접 테스트

사용법:
    python tests/handlers/test_onenote_handlers.py
"""

import sys
import os
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


def test_save_section_info():
    """save_section_info 핸들러 테스트"""
    print("\n📁 [1/5] save_section_info 핸들러 테스트...")

    try:
        handler = OneNoteHandlers()

        result = handler.save_section_info(
            user_id="kimghw",
            notebook_id="1-test-notebook",
            section_id="1-test-section",
            section_name="Test Section"
        )

        # 결과 검증
        success = "success" in result.lower() and "true" in result.lower()
        print_test_result("save_section_info", success, result[:200])

        return success

    except Exception as e:
        print_test_result("save_section_info", False, f"Exception: {e}")
        return False


def test_save_page_info():
    """save_page_info 핸들러 테스트"""
    print("\n📄 [2/5] save_page_info 핸들러 테스트...")

    try:
        handler = OneNoteHandlers()

        result = handler.save_page_info(
            user_id="kimghw",
            section_id="1-test-section",
            page_id="1-test-page",
            page_title="Test Page"
        )

        # 결과 검증
        success = "success" in result.lower() and "true" in result.lower()
        print_test_result("save_page_info", success, result[:200])

        return success

    except Exception as e:
        print_test_result("save_page_info", False, f"Exception: {e}")
        return False


def test_list_notebooks():
    """list_notebooks 핸들러 테스트"""
    print("\n📚 [3/5] list_notebooks 핸들러 테스트...")

    try:
        handler = OneNoteHandlers()
        result = handler.list_notebooks(user_id="kimghw")

        # 결과 검증 (노트북 목록 또는 인증 필요)
        success = "notebooks" in result.lower() or "액세스 토큰이 없습니다" in result
        print_test_result("list_notebooks", success, result[:200])

        return success

    except Exception as e:
        print_test_result("list_notebooks", False, f"Exception: {e}")
        return False


def test_list_sections():
    """list_sections 핸들러 테스트"""
    print("\n📁 [4/5] list_sections 핸들러 테스트...")

    try:
        handler = OneNoteHandlers()
        result = handler.list_sections(
            user_id="kimghw",
            notebook_id="1-test-notebook"
        )

        # 결과 검증
        success = "sections" in result.lower() or "액세스 토큰이 없습니다" in result
        print_test_result("list_sections", success, result[:200])

        return success

    except Exception as e:
        print_test_result("list_sections", False, f"Exception: {e}")
        return False


def test_list_pages():
    """list_pages 핸들러 테스트"""
    print("\n📄 [5/5] list_pages 핸들러 테스트...")

    try:
        handler = OneNoteHandlers()
        result = handler.list_pages(
            user_id="kimghw",
            section_id="1-test-section"
        )

        # 결과 검증
        success = "pages" in result.lower() or "액세스 토큰이 없습니다" in result
        print_test_result("list_pages", success, result[:200])

        return success

    except Exception as e:
        print_test_result("list_pages", False, f"Exception: {e}")
        return False


def main():
    """메인 테스트 실행"""
    print("=" * 80)
    print("🧪 OneNote 핸들러 직접 테스트")
    print("=" * 80)

    results = []

    # 테스트 실행
    results.append(test_save_section_info())
    results.append(test_save_page_info())
    results.append(test_list_notebooks())
    results.append(test_list_sections())
    results.append(test_list_pages())

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
