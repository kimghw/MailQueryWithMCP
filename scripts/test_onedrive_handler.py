#!/usr/bin/env python3
"""
OneDrive Handler 직접 테스트
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from modules.onedrive_mcp.onedrive_handler import OneDriveHandler
from infra.core.logger import get_logger

logger = get_logger(__name__)


async def test_list_files():
    """OneDrive 파일 목록 조회 테스트"""

    print("=" * 80)
    print("📁 OneDrive Handler 테스트")
    print("=" * 80)
    print()

    # OneDrive 핸들러 초기화
    handler = OneDriveHandler()

    # 테스트할 user_id (실제 등록된 사용자 ID 필요)
    user_id = input("사용자 ID를 입력하세요 (예: user@example.com): ").strip()

    if not user_id:
        print("❌ 사용자 ID가 필요합니다.")
        return

    print()
    print("=" * 80)
    print("1. 루트 폴더 파일 목록 조회")
    print("=" * 80)

    result = await handler.list_files(user_id)

    if result.get("success"):
        files = result.get("files", [])
        print(f"✅ 파일 {len(files)}개 조회 성공\n")

        for file_item in files[:10]:  # 처음 10개만 출력
            name = file_item.get("name", "Unknown")
            is_folder = "folder" in file_item
            size = file_item.get("size", 0)
            file_id = file_item.get("id", "")

            icon = "📁" if is_folder else "📄"
            print(f"{icon} {name}")
            if not is_folder:
                print(f"   크기: {size:,} bytes")
            print(f"   ID: {file_id}")
            print()

        if len(files) > 10:
            print(f"... 외 {len(files) - 10}개 파일")
    else:
        print(f"❌ 실패: {result.get('message')}")

    print()

    # Documents 폴더 조회
    print("=" * 80)
    print("2. Documents 폴더 파일 목록 조회")
    print("=" * 80)

    result = await handler.list_files(user_id, folder_path="Documents")

    if result.get("success"):
        files = result.get("files", [])
        print(f"✅ Documents 폴더에 {len(files)}개 파일\n")

        for file_item in files[:5]:
            name = file_item.get("name", "Unknown")
            is_folder = "folder" in file_item
            print(f"  {'📁' if is_folder else '📄'} {name}")
    else:
        print(f"❌ 실패: {result.get('message')}")

    print()

    # 파일 검색
    print("=" * 80)
    print("3. 파일 검색 (검색어 입력)")
    print("=" * 80)

    search_query = input("검색어를 입력하세요 (Enter로 건너뛰기): ").strip()

    if search_query:
        result = await handler.list_files(user_id, search=search_query)

        if result.get("success"):
            files = result.get("files", [])
            print(f"✅ 검색 결과: {len(files)}개 파일\n")

            for file_item in files[:5]:
                name = file_item.get("name", "Unknown")
                is_folder = "folder" in file_item
                print(f"  {'📁' if is_folder else '📄'} {name}")
        else:
            print(f"❌ 실패: {result.get('message')}")

    print()
    print("=" * 80)
    print("✅ 테스트 완료")
    print("=" * 80)


async def test_create_and_read():
    """OneDrive 파일 생성 및 읽기 테스트"""

    print("=" * 80)
    print("📝 OneDrive 파일 생성/읽기 테스트")
    print("=" * 80)
    print()

    handler = OneDriveHandler()

    user_id = input("사용자 ID를 입력하세요: ").strip()

    if not user_id:
        print("❌ 사용자 ID가 필요합니다.")
        return

    # 1. 폴더 생성
    print("\n1. 테스트 폴더 생성")
    result = await handler.create_folder(user_id, "MCPTest")

    if result.get("success"):
        print(f"✅ 폴더 생성 성공: {result.get('folder_name')}")
    else:
        print(f"⚠️  폴더 생성 실패 (이미 존재할 수 있음): {result.get('message')}")

    # 2. 파일 쓰기
    print("\n2. 테스트 파일 생성")
    test_content = f"Hello from OneDrive MCP!\nCreated by handler test.\n테스트 파일입니다."

    result = await handler.write_file(user_id, "MCPTest/test.txt", test_content)

    if result.get("success"):
        print(f"✅ 파일 생성 성공: {result.get('file_name')}")
        file_id = result.get('file_id')

        # 3. 파일 읽기
        print("\n3. 파일 내용 읽기")
        result = await handler.read_file(user_id, "MCPTest/test.txt")

        if result.get("success"):
            print(f"✅ 파일 읽기 성공")
            print(f"   파일명: {result.get('file_name')}")
            print(f"   크기: {result.get('file_size')} bytes")
            print(f"   MIME: {result.get('mime_type')}")
            print(f"\n내용:\n{'-' * 40}")
            print(result.get('content'))
            print('-' * 40)
        else:
            print(f"❌ 파일 읽기 실패: {result.get('message')}")
    else:
        print(f"❌ 파일 생성 실패: {result.get('message')}")

    print("\n" + "=" * 80)
    print("✅ 테스트 완료")
    print("=" * 80)


async def main():
    """메인 함수"""
    print("\n🔧 OneDrive Handler 테스트 메뉴")
    print("1. 파일 목록 조회 테스트")
    print("2. 파일 생성/읽기 테스트")
    print("3. 종료")

    choice = input("\n선택하세요 (1-3): ").strip()

    if choice == "1":
        await test_list_files()
    elif choice == "2":
        await test_create_and_read()
    elif choice == "3":
        print("👋 종료합니다.")
        return
    else:
        print("❌ 잘못된 선택입니다.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 사용자가 중단했습니다.")
    except Exception as e:
        logger.error(f"❌ 오류 발생: {e}", exc_info=True)
        print(f"\n❌ 오류 발생: {e}")
