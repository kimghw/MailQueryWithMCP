#!/usr/bin/env python3
"""
메일 큐 저장 테스트 - 더 많은 메일 조회
"""

import asyncio
from datetime import datetime, timedelta
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.mail_process.mail_processor_orchestrator import MailProcessorOrchestrator
from modules.mail_query.mail_query_orchestrator import MailQueryOrchestrator
from modules.mail_query.mail_query_schema import (
    MailQueryFilters,
    PaginationOptions,
    MailQueryRequest,
)
from infra.core.logger import get_logger
from infra.core.database import get_database_manager

logger = get_logger(__name__)


async def test_with_more_mails(user_id: str):
    """더 많은 메일을 조회하는 테스트"""

    print(f"\n🧪 확장된 메일 큐 저장 테스트: {user_id}")
    print("=" * 80)

    orchestrator = MailProcessorOrchestrator()
    db = get_database_manager()

    try:
        # 백그라운드 프로세서 시작
        await orchestrator.start_background_processor()

        # 기존 메일 히스토리 확인
        existing_count = db.fetch_one(
            """
            SELECT COUNT(*) as count 
            FROM mail_history mh
            JOIN accounts a ON mh.account_id = a.id
            WHERE a.user_id = ?
            """,
            (user_id,),
        )

        print(
            f"\n📊 기존 저장된 메일: {existing_count['count'] if existing_count else 0}개"
        )

        # 더 긴 기간과 더 많은 페이지로 설정
        filters = MailQueryFilters(
            date_from=datetime.now() - timedelta(days=90)  # 90일로 확장
        )

        # 페이지네이션 설정 - 더 많은 메일 조회
        pagination = PaginationOptions(
            top=100, max_pages=10  # 페이지당 100개로 증가  # 최대 10페이지 (1000개)
        )

        print(f"\n📧 메일 조회 설정:")
        print(f"  - 조회 기간: 최근 90일")
        print(f"  - 페이지당 메일 수: 100개")
        print(f"  - 최대 페이지: 10개")
        print(f"  - 최대 조회 가능: 1000개")

        # 메일 조회 및 큐 저장
        print(f"\n⏳ 메일 조회 중...")
        start_time = datetime.now()

        # 메일 조회
        mail_query_orchestrator = MailQueryOrchestrator()
        try:
            query_request = MailQueryRequest(
                user_id=user_id, filters=filters, pagination=pagination
            )

            query_response = await mail_query_orchestrator.mail_query_user_emails(
                query_request
            )

            print(f"📧 메일 조회 완료: {query_response.total_fetched}개")

            # 큐에 저장
            if query_response.messages:
                # account_id 조회 (user_id로부터)
                account_record = db.fetch_one(
                    "SELECT id FROM accounts WHERE user_id = ?", (user_id,)
                )
                if not account_record:
                    raise ValueError(f"계정을 찾을 수 없습니다: {user_id}")

                account_id = account_record["id"]

                result = await orchestrator.enqueue_mail_batch(
                    account_id=account_id, mails=query_response.messages
                )
            else:
                result = {
                    "account_id": user_id,
                    "total": 0,
                    "enqueued": 0,
                    "filtered": 0,
                    "duplicates": 0,
                    "errors": 0,
                    "queue_size": 0,
                    "success": True,
                }

        finally:
            await mail_query_orchestrator.close()

        elapsed_time = (datetime.now() - start_time).total_seconds()

        print(f"\n✅ 큐 저장 완료!")
        print(f"  - 큐에 저장된 메일: {result.get('enqueued', 0)}개")
        print(f"  - 중복 메일: {result.get('duplicates', 0)}개")
        print(f"  - 현재 큐 크기: {result.get('queue_size', 0)}개")
        print(f"  - 소요 시간: {elapsed_time:.1f}초")

        # 큐 배치 크기 확인
        queue_status = await orchestrator.queue_service.get_queue_status()
        print(f"\n📦 큐 설정:")
        print(f"  - 배치 크기: {queue_status['batch_size']}개")
        print(f"  - 큐 비어있음: {queue_status['is_empty']}")

        # 큐 처리 진행 모니터링
        if not queue_status["is_empty"]:
            print(f"\n⏳ 큐 처리 진행 모니터링 (30초)...")

            for i in range(6):  # 5초마다 6번 = 30초
                await asyncio.sleep(5)

                current_status = await orchestrator.get_processing_stats()
                queue_size = current_status["queue"]["queue_size"]

                print(f"  [{(i+1)*5}초] 남은 큐: {queue_size}개")

                if queue_size == 0:
                    print("  ✅ 큐 처리 완료!")
                    break

        # 최종 통계
        final_stats = await orchestrator.get_processing_stats()
        print(f"\n📊 최종 통계:")
        print(f"  - DB 저장된 전체 메일: {final_stats['database']['total_mails']}개")
        print(f"  - 오늘 처리된 메일: {final_stats['database']['today_mails']}개")
        print(f"  - 이번 주 처리된 메일: {final_stats['database']['week_mails']}개")

    except Exception as e:
        logger.error(f"테스트 중 오류 발생: {str(e)}", exc_info=True)
        print(f"❌ 오류 발생: {str(e)}")

    finally:
        await orchestrator.cleanup()
        print("\n✅ 리소스 정리 완료")


async def check_mail_history_duplicates(user_id: str):
    """메일 히스토리 중복 체크"""

    print(f"\n🔍 메일 히스토리 중복 분석: {user_id}")
    print("=" * 80)

    db = get_database_manager()

    # 전체 메일 수
    total_query = """
        SELECT COUNT(*) as total_count
        FROM mail_history mh
        JOIN accounts a ON mh.account_id = a.id
        WHERE a.user_id = ?
    """

    # 고유 메시지 ID 수
    unique_query = """
        SELECT COUNT(DISTINCT message_id) as unique_count
        FROM mail_history mh
        JOIN accounts a ON mh.account_id = a.id
        WHERE a.user_id = ?
    """

    # 최근 메일 정보
    recent_query = """
        SELECT 
            message_id,
            subject,
            received_time,
            processed_at
        FROM mail_history mh
        JOIN accounts a ON mh.account_id = a.id
        WHERE a.user_id = ?
        ORDER BY processed_at DESC
        LIMIT 10
    """

    total_result = db.fetch_one(total_query, (user_id,))
    unique_result = db.fetch_one(unique_query, (user_id,))
    recent_mails = db.fetch_all(recent_query, (user_id,))

    total_count = total_result["total_count"] if total_result else 0
    unique_count = unique_result["unique_count"] if unique_result else 0

    print(f"📊 메일 히스토리 통계:")
    print(f"  - 전체 레코드: {total_count}개")
    print(f"  - 고유 메시지: {unique_count}개")
    print(f"  - 중복 레코드: {total_count - unique_count}개")

    if recent_mails:
        print(f"\n📧 최근 처리된 메일 (10개):")
        for mail in recent_mails:
            print(f"  - {mail['subject'][:50]}...")
            print(f"    수신: {mail['received_time']}")
            print(f"    처리: {mail['processed_at']}")
            print()


async def check_queue_status_and_process():
    """큐 상태 확인 및 처리"""

    print(f"\n📊 큐 상태 확인 및 처리")
    print("=" * 80)

    orchestrator = MailProcessorOrchestrator()

    try:
        # 현재 큐 상태 확인
        initial_status = await orchestrator.get_processing_stats()
        queue_size = initial_status["queue"]["queue_size"]

        print(f"\n현재 큐 상태:")
        print(f"  - 큐 크기: {queue_size}개")
        print(f"  - 배치 크기: {initial_status['queue']['batch_size']}개")
        print(f"  - 큐 비어있음: {initial_status['queue']['is_empty']}")

        if queue_size == 0:
            print("\n✅ 큐가 비어있습니다. 처리할 메일이 없습니다.")

            # DB 통계 표시
            print(f"\n📊 DB 통계:")
            print(
                f"  - 전체 저장된 메일: {initial_status['database']['total_mails']}개"
            )
            print(
                f"  - 오늘 처리된 메일: {initial_status['database']['today_mails']}개"
            )
            return

        # 큐에 메일이 있으면 처리 시작
        process_choice = input(
            f"\n{queue_size}개의 메일이 큐에 있습니다. 처리하시겠습니까? (y/N): "
        )

        if process_choice.lower() == "y":
            # 백그라운드 프로세서 시작
            await orchestrator.start_background_processor()
            print("\n⏳ 큐 처리 중...")

            # 처리 진행 모니터링
            processed_count = 0
            for i in range(60):  # 최대 5분 (5초 * 60 = 300초)
                await asyncio.sleep(5)

                current_status = await orchestrator.get_processing_stats()
                current_queue_size = current_status["queue"]["queue_size"]

                # 처리된 메일 수 계산
                newly_processed = queue_size - current_queue_size - processed_count
                processed_count += newly_processed

                print(
                    f"  [{(i+1)*5}초] 남은 큐: {current_queue_size}개 (처리됨: {processed_count}개)"
                )

                if current_queue_size == 0:
                    print(f"\n✅ 큐 처리 완료! 총 {processed_count}개 메일 처리됨")
                    break

                # 처리가 멈춘 것 같으면 확인
                if i > 0 and newly_processed == 0:
                    if not current_status["background_processor"]["running"]:
                        print("\n⚠️  백그라운드 프로세서가 중지되었습니다.")
                        break

            # 최종 통계
            final_status = await orchestrator.get_processing_stats()
            print(f"\n📊 최종 통계:")
            print(f"  - 남은 큐: {final_status['queue']['queue_size']}개")
            print(f"  - DB 전체 메일: {final_status['database']['total_mails']}개")
            print(f"  - 오늘 처리된 메일: {final_status['database']['today_mails']}개")

        else:
            print("\n큐 처리를 건너뛰었습니다.")

            # 큐 초기화 옵션
            clear_choice = input("\n큐를 초기화하시겠습니까? (y/N): ")
            if clear_choice.lower() == "y":
                cleared = await orchestrator.queue_service.clear_queue()
                print(f"✅ 큐가 초기화되었습니다. {cleared}개 아이템 제거됨")

    finally:
        await orchestrator.cleanup()
        print("\n✅ 리소스 정리 완료")


async def clear_mail_history_option():
    """메일 히스토리 초기화 옵션"""

    confirm = input("\n⚠️  메일 히스토리를 초기화하시겠습니까? (y/N): ")
    if confirm.lower() == "y":
        db = get_database_manager()
        db.execute_query("DELETE FROM mail_history")
        print("✅ 메일 히스토리가 초기화되었습니다.")
        return True
    return False


async def main():
    """메인 함수"""
    print("\n🚀 확장된 메일 큐 테스트 프로그램")
    print("=" * 80)

    user_id = input("테스트할 계정 ID를 입력하세요 (예: krsdtp): ").strip()

    if not user_id:
        print("❌ 계정 ID가 입력되지 않았습니다.")
        return

    print("\n테스트 모드를 선택하세요:")
    print("1. 기본 테스트 (최근 30일, 100개)")
    print("2. 확장 테스트 (최근 90일, 1000개)")
    print("3. 메일 히스토리 분석")
    print("4. 메일 히스토리 초기화 후 테스트")

    choice = input("\n선택 (1-4): ").strip()

    if choice == "1":
        # 기본 설정으로 간단히 테스트
        orchestrator = MailProcessorOrchestrator()
        db = get_database_manager()

        try:
            await orchestrator.start_background_processor()

            # 메일 조회
            mail_query_orchestrator = MailQueryOrchestrator()
            try:
                query_request = MailQueryRequest(
                    user_id=user_id,
                    filters=MailQueryFilters(
                        date_from=datetime.now() - timedelta(days=30)
                    ),
                    pagination=PaginationOptions(top=50, max_pages=2),
                )

                query_response = await mail_query_orchestrator.mail_query_user_emails(
                    query_request
                )

                # 큐에 저장
                if query_response.messages:
                    # account_id 조회
                    account_record = db.fetch_one(
                        "SELECT id FROM accounts WHERE user_id = ?", (user_id,)
                    )
                    if not account_record:
                        raise ValueError(f"계정을 찾을 수 없습니다: {user_id}")

                    account_id = account_record["id"]

                    result = await orchestrator.enqueue_mail_batch(
                        account_id=account_id, mails=query_response.messages
                    )
                else:
                    result = {"enqueued": 0, "duplicates": 0}

            finally:
                await mail_query_orchestrator.close()

            print(f"\n✅ 결과:")
            print(f"  - 큐에 저장: {result.get('enqueued', 0)}개")
            print(f"  - 중복: {result.get('duplicates', 0)}개")

        finally:
            await orchestrator.cleanup()

    elif choice == "2":
        await test_with_more_mails(user_id)

    elif choice == "3":
        await check_mail_history_duplicates(user_id)

    elif choice == "4":
        if await clear_mail_history_option():
            await test_with_more_mails(user_id)

    else:
        print("❌ 잘못된 선택입니다.")


if __name__ == "__main__":
    asyncio.run(main())
