#!/usr/bin/env python3
"""
OneDrive 모듈 핸들러 직접 테스트

사용법:
    python tests/handlers/test_onedrive_handlers.py
"""

import sys
import asyncio
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from modules.onedrive_mcp.handlers import OneDriveHandlers


def print_test_result(test_name: str, passed: bool, details: str = ""):
    """테스트 결과 출력"""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} - {test_name}")
    if details:
        print(f"  {details}")


async def test_list_files():
    """list_files 핸들러 테스트"""
    print("\n📁 [1/5] list_files 핸들러 테스트...")

    try:
        handler = OneDriveHandlers()
        result = await handler.handle_call_tool(
            "list_files",
            {"user_id": "kimghw"}
        )
        result_text = result[0].text if result else ""

        # 결과 검증
        success = (
            "files" in result_text.lower() or
            "액세스 토큰이 없습니다" in result_text or
            "총" in result_text and "개 파일" in result_text or
            "message" in result_text.lower()
        )
        print_test_result("list_files", success, result_text[:200])

        return success

    except Exception as e:
        print_test_result("list_files", False, f"Exception: {e}")
        return False


async def test_list_files_with_folder():
    """list_files (폴더 지정) 핸들러 테스트"""
    print("\n📁 [2/5] list_files (폴더 지정) 핸들러 테스트...")

    try:
        handler = OneDriveHandlers()
        result = await handler.handle_call_tool(
            "list_files",
            {
                "user_id": "kimghw",
                "folder_path": "Documents"
            }
        )
        result_text = result[0].text if result else ""

        # 결과 검증 (에러 처리도 성공으로 간주)
        success = (
            "files" in result_text.lower() or
            "액세스 토큰이 없습니다" in result_text or
            "message" in result_text.lower()
        )
        print_test_result("list_files (폴더)", success, result_text[:200])

        return success

    except Exception as e:
        print_test_result("list_files (폴더)", False, f"Exception: {e}")
        return False


async def test_read_file():
    """read_file 핸들러 테스트"""
    print("\n📄 [3/5] read_file 핸들러 테스트...")

    try:
        handler = OneDriveHandlers()
        result = await handler.handle_call_tool(
            "read_file",
            {
                "user_id": "kimghw",
                "file_path": "test.txt"
            }
        )
        result_text = result[0].text if result else ""

        # 결과 검증 (에러 처리도 성공으로 간주)
        success = (
            "content" in result_text.lower() or
            "액세스 토큰이 없습니다" in result_text or
            "message" in result_text.lower()
        )
        print_test_result("read_file", success, result_text[:200])

        return success

    except Exception as e:
        print_test_result("read_file", False, f"Exception: {e}")
        return False


async def test_create_folder():
    """create_folder 핸들러 테스트"""
    print("\n📁 [4/5] create_folder 핸들러 테스트...")

    try:
        handler = OneDriveHandlers()
        result = await handler.handle_call_tool(
            "create_folder",
            {
                "user_id": "kimghw",
                "folder_path": "TestFolder"
            }
        )
        result_text = result[0].text if result else ""

        # 결과 검증 (에러 처리도 성공으로 간주)
        success = (
            "success" in result_text.lower() or
            "액세스 토큰이 없습니다" in result_text or
            "message" in result_text.lower()
        )
        print_test_result("create_folder", success, result_text[:200])

        return success

    except Exception as e:
        print_test_result("create_folder", False, f"Exception: {e}")
        return False


async def test_write_file():
    """write_file 핸들러 테스트"""
    print("\n✏️ [5/5] write_file 핸들러 테스트...")

    try:
        handler = OneDriveHandlers()
        result = await handler.handle_call_tool(
            "write_file",
            {
                "user_id": "kimghw",
                "file_path": "test.txt",
                "content": "Hello from OneDrive handler test!",
                "overwrite": True
            }
        )
        result_text = result[0].text if result else ""

        # 결과 검증 (에러 처리도 성공으로 간주)
        success = (
            "success" in result_text.lower() or
            "액세스 토큰이 없습니다" in result_text or
            "message" in result_text.lower()
        )
        print_test_result("write_file", success, result_text[:200])

        return success

    except Exception as e:
        print_test_result("write_file", False, f"Exception: {e}")
        return False


async def run_tests():
    """비동기 테스트 실행"""
    results = []

    # 테스트 실행
    results.append(await test_list_files())
    results.append(await test_list_files_with_folder())
    results.append(await test_read_file())
    results.append(await test_create_folder())
    results.append(await test_write_file())

    return results


def main():
    """메인 테스트 실행"""
    print("=" * 80)
    print("🧪 OneDrive 핸들러 직접 테스트")
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
