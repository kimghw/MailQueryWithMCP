"""Test SharePoint uploader with Playwright"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from modules.mail_process.sharepoint_uploader import SharePointUploader


async def test_sharepoint_upload():
    """SharePoint 업로드 테스트"""

    # Load .env file if exists
    from dotenv import load_dotenv
    load_dotenv()

    # SharePoint 폴더 URL (환경변수에서 읽기)
    sharepoint_url = os.getenv('SHAREPOINT_FOLDER_URL')

    if not sharepoint_url:
        print("❌ SHAREPOINT_FOLDER_URL 환경변수가 설정되지 않았습니다.")
        print("💡 .env 파일에 SHAREPOINT_FOLDER_URL을 설정하세요.")
        return

    print(f"🔗 SharePoint URL: {sharepoint_url}")

    # 테스트 파일 찾기 (다운로드 폴더에서 최신 파일 5개)
    download_dir = Path.home() / 'Downloads'

    if not download_dir.exists():
        print(f"❌ 다운로드 폴더를 찾을 수 없습니다: {download_dir}")
        return

    print(f"📁 다운로드 폴더 확인 중: {download_dir}")

    # 파일 목록 가져오기
    files = []
    try:
        for file_path in download_dir.iterdir():
            if file_path.is_file():
                files.append({
                    'path': file_path,
                    'name': file_path.name,
                    'mtime': file_path.stat().st_mtime
                })
    except Exception as e:
        print(f"❌ 파일 목록 읽기 실패: {str(e)}")
        return

    # 최신 순으로 정렬
    files.sort(key=lambda x: x['mtime'], reverse=True)

    # 최신 파일 5개 선택
    test_files = [f['path'] for f in files[:5]]

    if not test_files:
        print("❌ 업로드할 파일이 없습니다.")
        return

    print(f"\n📤 업로드할 파일 ({len(test_files)}개):")
    for i, file_path in enumerate(test_files, 1):
        size_mb = file_path.stat().st_size / (1024 * 1024)
        print(f"  {i}. {file_path.name} ({size_mb:.2f} MB)")

    # 자동으로 진행 (테스트용)
    print(f"\n✅ 자동으로 업로드를 시작합니다...")

    # SharePoint uploader 초기화
    print(f"\n🌐 브라우저 시작 중...")
    uploader = SharePointUploader(
        folder_url=sharepoint_url,
        headless=False  # UI를 보기 위해 headless=False
    )

    try:
        # 단일 파일 업로드 테스트
        print(f"\n📤 테스트 1: 단일 파일 업로드")
        result = await uploader.upload_file(test_files[0])

        if result['success']:
            print(f"✅ 업로드 성공: {result['message']}")
        else:
            print(f"❌ 업로드 실패: {result.get('error', 'Unknown error')}")

        # 다중 파일 업로드 테스트 (나머지 파일들)
        if len(test_files) > 1:
            print(f"\n📤 테스트 2: 다중 파일 업로드 ({len(test_files[1:])}개 파일)")
            result = await uploader.upload_files(test_files[1:])

            if result['success']:
                print(f"✅ 업로드 성공: {result['message']}")
                print(f"   업로드된 파일: {', '.join(result['file_names'])}")
            else:
                print(f"❌ 업로드 실패: {result.get('error', 'Unknown error')}")

        print(f"\n⏸️  브라우저를 5초 후 닫습니다...")
        await asyncio.sleep(5)

    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()

    finally:
        await uploader.close()
        print("✅ 테스트 완료")


if __name__ == "__main__":
    asyncio.run(test_sharepoint_upload())
