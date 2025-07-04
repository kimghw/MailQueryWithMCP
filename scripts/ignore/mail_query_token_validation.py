#!/usr/bin/env python3
"""
Mail Query 모듈 통합 테스트
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

# 프로젝트 루트 경로 추가
sys.path.append(str(Path(__file__).parent.parent.parent))

from modules.mail_query import (
    MailQueryOrchestrator,
    MailQueryRequest,
    MailQueryFilters,
    PaginationOptions,
)
from infra.core.logger import get_logger

logger = get_logger(__name__)


async def test_basic_mail_query(orchestrator: MailQueryOrchestrator):
    """기본 메일 조회 테스트"""
    print("\n" + "=" * 60)
    print("기본 메일 조회 테스트")
    print("=" * 60)

    try:
        request = MailQueryRequest(
            user_id="kimghw",
            pagination=PaginationOptions(top=10, skip=0, max_pages=1),
            select_fields=["id", "subject", "from", "receivedDateTime", "bodyPreview"],
        )

        response = await orchestrator.mail_query_user_emails(request)

        print(f"✅ 조회 성공!")
        print(f"- 총 메일 수: {response.total_fetched}")
        print(f"- 실행 시간: {response.execution_time_ms}ms")
        print(f"- 추가 데이터 여부: {response.has_more}")

        if response.messages:
            print("\n최근 메일 3개:")
            for i, msg in enumerate(response.messages[:3], 1):
                print(f"\n{i}. {msg.subject}")
                print(
                    f"   발신자: {msg.from_address.get('emailAddress', {}).get('address') if msg.from_address else 'Unknown'}"
                )
                print(f"   수신 시간: {msg.received_date_time}")
                print(
                    f"   미리보기: {msg.body_preview[:100] if msg.body_preview else 'No preview'}..."
                )

            # 상위 3개 메일을 JSON으로 저장
            # await test_save_mail_originals_to_json(orchestrator, response.messages[:3])

    except Exception as e:
        print(f"❌ 메일 조회 실패: {e}")


async def test_filtered_mail_query(orchestrator: MailQueryOrchestrator):
    """필터링된 메일 조회 테스트"""
    print("\n" + "=" * 60)
    print("필터링된 메일 조회 테스트 (최근 7일, 읽지 않은 메일)")
    print("=" * 60)

    try:
        filters = MailQueryFilters(
            date_from=datetime.now() - timedelta(days=7), is_read=False
        )

        request = MailQueryRequest(
            user_id="kimghw",
            filters=filters,
            pagination=PaginationOptions(top=20, skip=0, max_pages=2),
            select_fields=["id", "subject", "from", "receivedDateTime", "isRead"],
        )

        response = await orchestrator.mail_query_user_emails(request)

        print(f"✅ 필터링 조회 성공!")
        print(f"- 읽지 않은 메일 수: {response.total_fetched}")
        print(f"- 실행 시간: {response.execution_time_ms}ms")
        print(
            f"- 성능 예상: {response.query_info.get('performance_estimate', 'Unknown')}"
        )

    except Exception as e:
        print(f"❌ 필터링 조회 실패: {e}")


async def test_search_messages(orchestrator: MailQueryOrchestrator):
    """메시지 검색 테스트"""
    print("\n" + "=" * 60)
    print("메시지 검색 테스트")
    print("=" * 60)

    try:
        search_term = "meeting"

        response = await orchestrator.mail_query_search_messages(
            user_id="kimghw",
            search_term=search_term,
            select_fields=["id", "subject", "from", "receivedDateTime"],
            top=10,
        )

        print(f"✅ 검색 성공!")
        print(f"- 검색어: '{search_term}'")
        print(f"- 검색 결과 수: {response.total_fetched}")
        print(f"- 실행 시간: {response.execution_time_ms}ms")

        if response.messages:
            print(f"\n검색 결과 상위 3개:")
            for i, msg in enumerate(response.messages[:3], 1):
                print(f"{i}. {msg.subject}")

    except Exception as e:
        print(f"❌ 검색 실패: {e}")


async def test_mailbox_info(orchestrator: MailQueryOrchestrator):
    """메일박스 정보 조회 테스트"""
    print("\n" + "=" * 60)
    print("메일박스 정보 조회 테스트")
    print("=" * 60)

    try:
        mailbox_info = await orchestrator.mail_query_get_mailbox_info("kimghw")

        print(f"✅ 메일박스 정보 조회 성공!")
        print(f"- 표시 이름: {mailbox_info.display_name}")
        print(f"- 시간대: {mailbox_info.time_zone}")
        print(f"- 언어: {mailbox_info.language}")

    except Exception as e:
        print(f"❌ 메일박스 정보 조회 실패: {e}")


async def test_token_validation_during_query(orchestrator: MailQueryOrchestrator):
    """쿼리 중 토큰 검증 테스트"""
    print("\n" + "=" * 60)
    print("쿼리 중 토큰 자동 검증/갱신 테스트")
    print("=" * 60)

    try:
        # 토큰 검증이 자동으로 수행되는 일반 조회
        request = MailQueryRequest(
            user_id="kimghw", pagination=PaginationOptions(top=5, skip=0, max_pages=1)
        )

        print("토큰 자동 검증을 포함한 메일 조회 시작...")
        response = await orchestrator.mail_query_user_emails(request)

        print(f"✅ 토큰 자동 검증 및 조회 성공!")
        print(f"- 조회된 메일 수: {response.total_fetched}")
        print(f"- 실행 시간: {response.execution_time_ms}ms")

    except Exception as e:
        print(f"❌ 토큰 검증 실패: {e}")


async def test_complex_filters(orchestrator: MailQueryOrchestrator):
    """복잡한 필터 조건 테스트"""
    print("\n" + "=" * 60)
    print("복잡한 필터 조건 테스트")
    print("=" * 60)

    try:
        filters = MailQueryFilters(
            date_from=datetime.now() - timedelta(days=30),
            date_to=datetime.now() - timedelta(days=1),
            has_attachments=True,
            importance="high",
        )

        request = MailQueryRequest(
            user_id="kimghw",
            filters=filters,
            pagination=PaginationOptions(top=10, skip=0, max_pages=1),
            select_fields=[
                "id",
                "subject",
                "importance",
                "hasAttachments",
                "receivedDateTime",
            ],
        )

        response = await orchestrator.mail_query_user_emails(request)

        print(f"✅ 복잡한 필터 조회 성공!")
        print(f"- 조회된 중요 메일(첨부파일 포함) 수: {response.total_fetched}")
        print(f"- OData 필터: {response.query_info.get('odata_filter', 'None')}")
        print(
            f"- 성능 예상: {response.query_info.get('performance_estimate', 'Unknown')}"
        )

    except Exception as e:
        print(f"❌ 복잡한 필터 조회 실패: {e}")


async def test_pagination(orchestrator: MailQueryOrchestrator):
    """페이징 처리 테스트"""
    print("\n" + "=" * 60)
    print("페이징 처리 테스트")
    print("=" * 60)

    try:
        # 첫 페이지
        request1 = MailQueryRequest(
            user_id="kimghw", pagination=PaginationOptions(top=5, skip=0, max_pages=1)
        )

        response1 = await orchestrator.mail_query_user_emails(request1)
        print(f"✅ 첫 페이지 조회 성공! (메일 수: {response1.total_fetched})")

        # 두 번째 페이지
        request2 = MailQueryRequest(
            user_id="kimghw", pagination=PaginationOptions(top=5, skip=5, max_pages=1)
        )

        response2 = await orchestrator.mail_query_user_emails(request2)
        print(f"✅ 두 번째 페이지 조회 성공! (메일 수: {response2.total_fetched})")

        print(
            f"- 전체 페이지에서 조회된 메일: {response1.total_fetched + response2.total_fetched}"
        )

    except Exception as e:
        print(f"❌ 페이징 테스트 실패: {e}")


async def test_save_mail_originals_to_json(
    orchestrator: MailQueryOrchestrator, messages: list
):
    """메일 원본을 JSON 파일로 저장하는 테스트"""
    print("\n" + "=" * 60)
    print("메일 원본 JSON 저장 테스트")
    print("=" * 60)

    try:
        saved_files = []

        # 각 메시지의 원본 데이터를 가져와서 저장
        for i, msg in enumerate(messages, 1):
            print(f"\n{i}. 메시지 저장 중: {msg.subject}")

            # 메시지 ID로 원본 데이터 조회 및 저장
            filepath = await orchestrator.save_message_to_json(
                user_id="kimghw", message_id=msg.id, save_dir="./data/mail_samples"
            )

            saved_files.append(filepath)
            print(f"   ✅ 저장 완료: {filepath}")

        print(f"\n총 {len(saved_files)}개의 메일이 JSON으로 저장되었습니다.")
        print("저장 위치: ./data/mail_samples/")

    except Exception as e:
        print(f"❌ 메일 JSON 저장 실패: {e}")


async def main():
    """메인 테스트 실행"""
    print("\n" + "=" * 60)
    print("Mail Query 모듈 통합 테스트 시작")
    print("=" * 60)

    # 컨텍스트 매니저를 사용하여 자동 리소스 정리
    async with MailQueryOrchestrator() as orchestrator:
        # 기본 테스트들
        await test_basic_mail_query(orchestrator)
        await test_filtered_mail_query(orchestrator)
        await test_search_messages(orchestrator)

        # 토큰 검증 테스트
        await test_token_validation_during_query(orchestrator)

        # 고급 테스트들
        await test_complex_filters(orchestrator)
        await test_pagination(orchestrator)

        # 메일박스 정보 테스트 (권한 문제가 있을 수 있음)
        # await test_mailbox_info(orchestrator)

    print("\n" + "=" * 60)
    print("모든 테스트 완료!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
