"""
IACS Tools 테스트 스크립트
"""

import asyncio
import sys
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from modules.mail_iacs import (
    IACSTools,
    InsertInfoRequest,
    SearchAgendaRequest,
    SearchResponsesRequest,
    InsertDefaultValueRequest,
)


async def test_insert_info():
    """패널 정보 삽입 테스트"""
    print("\n" + "=" * 60)
    print("1. 패널 정보 삽입 테스트")
    print("=" * 60)

    tools = IACSTools()

    request = InsertInfoRequest(
        chair_address="chair@example.com",
        panel_name="sdtp",
        kr_panel_member="member@example.com",
    )

    response = await tools.insert_info(request)

    print(f"\n성공: {response.success}")
    print(f"메시지: {response.message}")
    print(f"패널: {response.panel_name}")
    print(f"의장: {response.chair_address}")
    print(f"멤버: {response.kr_panel_member}")


async def test_insert_default_value():
    """기본 패널 설정 테스트"""
    print("\n" + "=" * 60)
    print("2. 기본 패널 설정 테스트")
    print("=" * 60)

    tools = IACSTools()

    request = InsertDefaultValueRequest(panel_name="sdtp")

    response = await tools.insert_default_value(request)

    print(f"\n성공: {response.success}")
    print(f"메시지: {response.message}")
    print(f"패널: {response.panel_name}")


async def test_search_agenda():
    """아젠다 검색 테스트"""
    print("\n" + "=" * 60)
    print("3. 아젠다 검색 테스트")
    print("=" * 60)

    tools = IACSTools()

    request = SearchAgendaRequest(
        panel_name="sdtp",
        content_field=["id", "subject", "from", "receivedDateTime"],
    )

    response = await tools.search_agenda(request)

    print(f"\n성공: {response.success}")
    print(f"메시지: {response.message}")
    print(f"결과 수: {response.total_count}")
    print(f"패널: {response.panel_name}")
    print(f"의장: {response.chair_address}")
    print(f"멤버: {response.kr_panel_member}")

    if response.mails:
        print(f"\n상위 3개 메일:")
        for i, mail in enumerate(response.mails[:3], 1):
            print(f"\n{i}. {mail.get('subject')}")
            print(f"   발신자: {mail.get('from_address', {}).get('emailAddress', {}).get('address')}")
            print(f"   수신: {mail.get('received_date_time')}")


async def test_search_responses():
    """응답 검색 테스트"""
    print("\n" + "=" * 60)
    print("4. 응답 검색 테스트")
    print("=" * 60)

    tools = IACSTools()

    request = SearchResponsesRequest(
        agenda_code="SDTP-24",  # 예시 아젠다 코드
        content_field=["id", "subject", "from", "receivedDateTime"],
    )

    response = await tools.search_responses(request)

    print(f"\n성공: {response.success}")
    print(f"메시지: {response.message}")
    print(f"결과 수: {response.total_count}")
    print(f"아젠다 코드: {response.agenda_code}")

    if response.mails:
        print(f"\n상위 3개 응답:")
        for i, mail in enumerate(response.mails[:3], 1):
            print(f"\n{i}. {mail.get('subject')}")
            print(f"   발신자: {mail.get('from_address', {}).get('emailAddress', {}).get('address')}")


async def main():
    """메인 테스트 함수"""
    print("IACS Tools 테스트 시작")
    print("=" * 60)

    try:
        # 1. 패널 정보 삽입
        await test_insert_info()

        # 2. 기본 패널 설정
        await test_insert_default_value()

        # 3. 아젠다 검색 (실제 메일 조회 - 인증 필요)
        # await test_search_agenda()

        # 4. 응답 검색 (실제 메일 조회 - 인증 필요)
        # await test_search_responses()

        print("\n" + "=" * 60)
        print("✅ 테스트 완료")
        print("=" * 60)
        print("\n참고: 메일 검색 테스트는 주석 처리되어 있습니다.")
        print("실제 테스트를 위해서는 인증이 필요합니다.")

    except Exception as e:
        print(f"\n❌ 테스트 실패: {str(e)}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
