#!/usr/bin/env python3
"""
실제 메일 배치 처리 테스트 - 오케스트레이터 활용 버전
메일 조회 → 오케스트레이터로 처리 → 결과 분석
"""

import asyncio
from datetime import datetime, timedelta
import sys
import os
import json
from collections import Counter
from typing import List, Dict, Any

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.mail_query.mail_query_orchestrator import MailQueryOrchestrator
from modules.mail_query.mail_query_schema import (
    MailQueryFilters,
    PaginationOptions,
    MailQueryRequest,
)
from modules.mail_process.mail_processor_orchestrator import MailProcessorOrchestrator
from modules.mail_process.services.db_service import MailDatabaseService
from infra.core.logger import get_logger
from infra.core.database import get_database_manager

logger = get_logger(__name__)


async def batch_process_with_orchestrator(
    user_id: str, days_back: int = 7, max_mails: int = 10
):
    """
    오케스트레이터를 활용한 메일 배치 처리

    Args:
        user_id: 사용자 ID
        days_back: 조회할 과거 일수
        max_mails: 처리할 최대 메일 수
    """
    print(f"\n📧 오케스트레이터를 활용한 메일 배치 처리 테스트")
    print("=" * 80)
    print(f"👤 사용자: {user_id}")
    print(f"📅 기간: 최근 {days_back}일")
    print(f"📊 최대 메일: {max_mails}개")

    try:
        # ===== 1단계: 메일 조회 =====
        print(f"\n[1단계] 메일 조회")
        print("-" * 40)

        mail_query_orchestrator = MailQueryOrchestrator()
        mail_processor_orchestrator = MailProcessorOrchestrator()

        try:
            query_request = MailQueryRequest(
                user_id=user_id,
                filters=MailQueryFilters(
                    date_from=datetime.now() - timedelta(days=days_back)
                ),
                pagination=PaginationOptions(top=max_mails, max_pages=1),
            )

            print(f"⏳ 메일 조회 중...")
            start_time = datetime.now()

            query_response = await mail_query_orchestrator.mail_query_user_emails(
                query_request
            )

            query_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            if not query_response.messages:
                print("❌ 조회된 메일이 없습니다.")
                return

            print(
                f"✅ 메일 조회 완료: {len(query_response.messages)}개 (소요시간: {query_time_ms:.0f}ms)"
            )

            # 조회된 메일 요약
            print(f"\n📋 조회된 메일 목록:")
            for i, mail in enumerate(query_response.messages[:5]):
                sender_info = mail.sender or mail.from_address or {}
                sender_addr = ""
                if isinstance(sender_info, dict):
                    email_addr = sender_info.get("emailAddress", {})
                    if isinstance(email_addr, dict):
                        sender_addr = email_addr.get("address", "")

                print(f"  [{i+1}] {mail.subject[:60]}...")
                print(f"      발신자: {sender_addr}")
                print(f"      수신: {mail.received_date_time}")

            if len(query_response.messages) > 5:
                print(f"  ... 외 {len(query_response.messages) - 5}개")

        finally:
            await mail_query_orchestrator.close()

        # ===== 2단계: 오케스트레이터로 메일 처리 =====
        print(f"\n[2단계] 오케스트레이터로 메일 배치 처리")
        print("-" * 40)

        print(f"⏳ 메일을 큐에 추가 중...")
        start_time = datetime.now()

        # enqueue_mail_batch 호출
        enqueue_result = await mail_processor_orchestrator.enqueue_mail_batch(
            account_id=user_id,
            mails=query_response.messages,  # GraphMailItem 리스트를 그대로 전달
        )

        enqueue_time_ms = (datetime.now() - start_time).total_seconds() * 1000

        print(f"\n✅ 큐 추가 완료!")
        print(f"📊 큐 추가 결과:")
        print(f"  - 전체: {enqueue_result['total']}개")
        print(f"  - 큐 저장: {enqueue_result['enqueued']}개")
        print(f"  - 필터링: {enqueue_result['filtered']}개")
        print(f"  - 중복: {enqueue_result['duplicates']}개")
        print(f"  - 오류: {enqueue_result['errors']}개")
        print(f"  - 현재 큐 크기: {enqueue_result['queue_size']}개")
        print(f"  - 소요시간: {enqueue_time_ms:.0f}ms")

        # ===== 3단계: 배치 처리 실행 =====
        print(f"\n[3단계] 배치 처리 실행")
        print("-" * 40)

        # 큐에 데이터가 있는 경우 처리
        if enqueue_result["queue_size"] > 0:
            print(f"⏳ 큐에 있는 {enqueue_result['queue_size']}개 메일 처리 중...")
            start_time = datetime.now()

            # process_batch 호출
            process_results = await mail_processor_orchestrator.process_batch()

            process_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            if process_results:
                success_count = sum(1 for r in process_results if r.success)
                print(f"\n✅ 배치 처리 완료!")
                print(f"📊 처리 결과:")
                print(f"  - 전체: {len(process_results)}개")
                print(f"  - 성공: {success_count}개")
                print(f"  - 실패: {len(process_results) - success_count}개")
                print(f"  - 소요시간: {process_time_ms:.0f}ms")

                # 키워드 통계
                all_keywords = []
                for result in process_results:
                    if result.success and result.keywords:
                        all_keywords.extend(result.keywords)

                if all_keywords:
                    keyword_counter = Counter(all_keywords)
                    print(f"\n🏷️  상위 키워드 (Top 10):")
                    for keyword, count in keyword_counter.most_common(10):
                        print(f"  - {keyword}: {count}회")

        # ===== 4단계: 처리 통계 조회 =====
        print(f"\n[4단계] 처리 통계")
        print("-" * 40)

        stats = await mail_processor_orchestrator.get_processing_stats()

        print(f"📊 큐 상태:")
        print(f"  - 현재 큐 크기: {stats['queue']['queue_size']}개")
        print(f"  - 총 추가됨: {stats['queue']['statistics']['total_enqueued']}개")
        print(f"  - 총 처리됨: {stats['queue']['statistics']['total_dequeued']}개")

        print(f"\n📊 데이터베이스 통계:")
        print(f"  - 전체 메일: {stats['database']['total_mails']}개")
        print(f"  - 오늘 처리: {stats['database']['today_mails']}개")
        print(f"  - 최근 7일: {stats['database']['week_mails']}개")

        if stats["database"]["top_accounts"]:
            print(f"\n👥 상위 계정:")
            for account in stats["database"]["top_accounts"][:5]:
                print(f"  - {account['user_id']}: {account['mail_count']}개")

        # ===== 5단계: 구조화된 분석 결과 확인 =====
        print(f"\n[5단계] 구조화된 분석 결과")
        print("-" * 40)

        # DB에서 최근 처리된 메일 조회
        db_service = MailDatabaseService()
        mail_stats = db_service.get_mail_statistics(user_id, days=1)

        print(f"📄 오늘 처리된 메일 통계:")
        print(f"  - 전체: {mail_stats['total_mails']}개")
        print(f"  - 고유 발신자: {mail_stats['unique_senders']}개")
        print(f"  - 평균 키워드: {mail_stats['avg_keywords']}개/메일")

        # 저장된 분석 파일 확인
        from pathlib import Path

        data_dir = Path("./data/mail_analysis_results")

        if data_dir.exists():
            today_str = datetime.now().strftime("%Y%m%d")
            result_file = data_dir / f"mail_analysis_results_{today_str}.jsonl"

            if result_file.exists():
                with open(result_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                recent_results = []
                for line in lines[-10:]:  # 최근 10개만
                    try:
                        recent_results.append(json.loads(line))
                    except:
                        continue

                if recent_results:
                    print(f"\n📋 최근 구조화된 분석 샘플:")
                    for result in recent_results[-3:]:
                        analysis = result.get("analysis_result", {})
                        print(f"\n  📧 {result.get('subject', '')[:50]}...")
                        print(f"     요약: {analysis.get('summary', '')[:80]}...")
                        print(f"     메일타입: {analysis.get('mail_type', 'N/A')}")
                        print(
                            f"     발신조직: {analysis.get('sender_organization', 'N/A')}"
                        )

                        if analysis.get("agenda_no"):
                            print(f"     아젠다: {analysis['agenda_no']}")
                        if analysis.get("has_deadline"):
                            print(f"     마감일: {analysis.get('deadline', 'N/A')}")

        # 오케스트레이터 정리
        await mail_processor_orchestrator.cleanup()

    except Exception as e:
        logger.error(f"배치 처리 중 오류: {str(e)}", exc_info=True)
        print(f"\n❌ 오류 발생: {str(e)}")


async def test_continuous_processing(user_id: str, duration_seconds: int = 30):
    """백그라운드 프로세서 테스트"""

    print(f"\n🔄 백그라운드 프로세서 테스트")
    print("=" * 80)
    print(f"👤 사용자: {user_id}")
    print(f"⏱️  실행 시간: {duration_seconds}초")

    mail_processor_orchestrator = MailProcessorOrchestrator()

    try:
        # 백그라운드 프로세서 시작
        await mail_processor_orchestrator.start_background_processor()
        print("✅ 백그라운드 프로세서 시작됨")

        # 메일 조회 및 큐 추가
        mail_query_orchestrator = MailQueryOrchestrator()

        try:
            query_request = MailQueryRequest(
                user_id=user_id,
                filters=MailQueryFilters(date_from=datetime.now() - timedelta(days=7)),
                pagination=PaginationOptions(top=20, max_pages=1),
            )

            query_response = await mail_query_orchestrator.mail_query_user_emails(
                query_request
            )

            if query_response.messages:
                enqueue_result = await mail_processor_orchestrator.enqueue_mail_batch(
                    account_id=user_id, mails=query_response.messages
                )
                print(f"✅ {enqueue_result['enqueued']}개 메일이 큐에 추가됨")

        finally:
            await mail_query_orchestrator.close()

        # 백그라운드 처리 진행 상황 모니터링
        print("\n⏳ 백그라운드 처리 진행 중...")
        for i in range(duration_seconds // 5):
            await asyncio.sleep(5)
            stats = await mail_processor_orchestrator.get_processing_stats()
            print(
                f"  [{(i+1)*5}초] 큐: {stats['queue']['queue_size']}개, "
                f"프로세서: {'실행중' if stats['background_processor']['running'] else '중지됨'}"
            )

        # 백그라운드 프로세서 중지
        await mail_processor_orchestrator.stop_background_processor()
        print("\n✅ 백그라운드 프로세서 중지됨")

        # 최종 통계
        final_stats = await mail_processor_orchestrator.get_processing_stats()
        print(f"\n📊 최종 통계:")
        print(f"  - 총 처리: {final_stats['queue']['statistics']['total_dequeued']}개")
        print(f"  - 큐 잔여: {final_stats['queue']['queue_size']}개")

    finally:
        await mail_processor_orchestrator.cleanup()


async def main():
    """메인 함수"""
    print("\n🚀 오케스트레이터 기반 메일 배치 처리 테스트")
    print("=" * 80)

    user_id = input("사용자 ID 입력 (예: krsdtp): ").strip()

    if not user_id:
        print("❌ 사용자 ID가 입력되지 않았습니다.")
        return

    print("\n테스트 옵션:")
    print("1. 빠른 테스트 (최근 7일, 5개)")
    print("2. 표준 테스트 (최근 14일, 20개)")
    print("3. 대량 테스트 (최근 30일, 50개)")
    print("4. 백그라운드 프로세서 테스트 (30초)")
    print("5. 사용자 정의")

    choice = input("\n선택 (1-5): ").strip()

    if choice == "1":
        await batch_process_with_orchestrator(user_id, days_back=7, max_mails=5)

    elif choice == "2":
        await batch_process_with_orchestrator(user_id, days_back=14, max_mails=20)

    elif choice == "3":
        await batch_process_with_orchestrator(user_id, days_back=30, max_mails=50)

    elif choice == "4":
        await test_continuous_processing(user_id, duration_seconds=30)

    elif choice == "5":
        days = int(input("조회할 과거 일수: "))
        mails = int(input("처리할 메일 수: "))
        await batch_process_with_orchestrator(user_id, days_back=days, max_mails=mails)

    else:
        print("❌ 잘못된 선택입니다.")


if __name__ == "__main__":
    asyncio.run(main())
