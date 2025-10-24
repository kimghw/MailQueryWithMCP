#!/usr/bin/env python3
"""
메일 첨부파일 → OneDrive 자동 업로드 테스트
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from modules.mail_process.attachment_downloader import AttachmentDownloader
from infra.core.logger import get_logger

logger = get_logger(__name__)


async def test_text_file_upload():
    """텍스트 파일 업로드 테스트"""

    print("=" * 80)
    print("📝 텍스트 파일 → OneDrive 업로드 테스트")
    print("=" * 80)
    print()

    # AttachmentDownloader 초기화 (OneDrive 모드)
    downloader = AttachmentDownloader(
        output_dir="./test_attachments",
        storage_mode="onedrive"
    )

    # 테스트 파일 내용
    test_content = """Hello from Email Attachment!

This is a test text file from email.
Mail attachment test (Korean: 메일 첨부파일 테스트입니다)

Created: 2025-10-24
""".encode('utf-8')

    # 가상 메일 정보
    email_date = datetime(2025, 10, 24, 13, 30, 0)
    sender_email = "test@example.com"
    email_subject = "Test Email with Attachment"

    # 파일 저장 및 OneDrive 업로드
    result = await downloader.download_and_save(
        graph_client=None,  # 이미 다운로드된 content 사용
        message_id="test_message_id",
        attachment={
            "id": "test_attachment_id",
            "name": "test_document.txt",
            "contentBytes": None  # content를 직접 전달
        },
        user_id="kimghw",
        email_date=email_date,
        sender_email=sender_email,
        email_subject=email_subject,
        upload_to_onedrive=True
    )

    # 수동으로 content 처리 (download_and_save의 로직 우회)
    if hasattr(downloader, 'onedrive_handler'):
        # 직접 OneDrive 업로드 테스트
        file_path = f"EmailAttachments/kimghw/Test_Email_20251024_test@example.com/test_document.txt"

        upload_result = await downloader.onedrive_handler.write_file(
            user_id="kimghw",
            file_path=file_path,
            content=test_content.decode('utf-8'),
            overwrite=True,
            is_binary=False
        )

        if upload_result and upload_result.get("success"):
            print("✅ 텍스트 파일 업로드 성공!")
            print(f"   파일명: {upload_result.get('file_name')}")
            print(f"   파일 ID: {upload_result.get('file_id')}")
            print(f"   크기: {upload_result.get('size')} bytes")
            print(f"   URL: {upload_result.get('web_url')}")
        else:
            print(f"❌ 업로드 실패: {upload_result.get('message')}")
    else:
        print("❌ OneDrive handler가 초기화되지 않았습니다.")

    print()


async def test_binary_file_upload():
    """바이너리 파일 업로드 테스트"""

    print("=" * 80)
    print("📷 바이너리 파일 → OneDrive 업로드 테스트")
    print("=" * 80)
    print()

    # AttachmentDownloader 초기화
    downloader = AttachmentDownloader(
        output_dir="./test_attachments",
        storage_mode="onedrive"
    )

    # 작은 PNG 이미지 (1x1 픽셀 투명)
    test_binary = bytes.fromhex(
        '89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000a49444154789c6300010000050001'
    )

    if hasattr(downloader, 'onedrive_handler'):
        import base64

        file_path = "EmailAttachments/kimghw/Test_Binary_20251024_test@example.com/test_image.png"
        file_content_base64 = base64.b64encode(test_binary).decode('utf-8')

        upload_result = await downloader.onedrive_handler.write_file(
            user_id="kimghw",
            file_path=file_path,
            content=file_content_base64,
            overwrite=True,
            is_binary=True,
            content_type="image/png"
        )

        if upload_result and upload_result.get("success"):
            print("✅ 바이너리 파일 업로드 성공!")
            print(f"   파일명: {upload_result.get('file_name')}")
            print(f"   파일 ID: {upload_result.get('file_id')}")
            print(f"   크기: {upload_result.get('size')} bytes")
            print(f"   URL: {upload_result.get('web_url')}")
        else:
            print(f"❌ 업로드 실패: {upload_result.get('message')}")
    else:
        print("❌ OneDrive handler가 초기화되지 않았습니다.")

    print()


async def test_list_uploaded_files():
    """업로드된 파일 목록 확인"""

    print("=" * 80)
    print("📁 업로드된 파일 목록 확인")
    print("=" * 80)
    print()

    downloader = AttachmentDownloader(
        output_dir="./test_attachments",
        storage_mode="onedrive"
    )

    if hasattr(downloader, 'onedrive_handler'):
        result = await downloader.onedrive_handler.list_files(
            user_id="kimghw",
            folder_path="EmailAttachments/kimghw"
        )

        if result.get("success"):
            files = result.get("files", [])
            print(f"✅ {len(files)}개 폴더 발견\n")

            for folder in files[:10]:
                name = folder.get("name", "Unknown")
                is_folder = "folder" in folder
                modified = folder.get("lastModifiedDateTime", "")[:19].replace("T", " ")

                print(f"{'📁' if is_folder else '📄'} {name}")
                print(f"   수정: {modified}")
                print()
        else:
            print(f"❌ 목록 조회 실패: {result.get('message')}")
    else:
        print("❌ OneDrive handler가 초기화되지 않았습니다.")


async def main():
    """메인 함수"""
    print("\n🧪 메일 첨부파일 → OneDrive 업로드 테스트\n")

    try:
        # 1. 텍스트 파일 업로드
        await test_text_file_upload()

        # 2. 바이너리 파일 업로드
        await test_binary_file_upload()

        # 3. 업로드된 파일 목록 확인
        await test_list_uploaded_files()

        print("=" * 80)
        print("✅ 모든 테스트 완료!")
        print("=" * 80)

    except Exception as e:
        logger.error(f"❌ 테스트 실패: {e}", exc_info=True)
        print(f"\n❌ 테스트 실패: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 사용자가 중단했습니다.")
