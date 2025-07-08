#!/usr/bin/env python3
"""
메일 조회 후 큐에 저장하는 테스트 스크립트
scripts/test_mail_queue_enqueue.py
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import sys
import os

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infra.core.database import get_database_manager
from infra.core.logger import get_logger

# 직접 import 경로 수정
from modules.mail_process.mail_processor_orchestrator import MailProcessorOrchestrator
from modules.mail_query import (
    MailQueryFilters,
    PaginationOptions,
)

logger = get_logger(__name__)


class MailQueueEnqueueTester:
    """메일 조회 후 큐에 저장하는 테스터"""

    def __init__(self):
        self.db = get_database_manager()
        self.orchestrator = None
        self.start_time = datetime.now()

    async def setup(self):
        """오케스트레이터 초기화"""
        self.orchestrator = MailProcessorOrchestrator()
        await self.orchestrator.__aenter__()
        logger.info("오케스트레이터 초기화 완료")

    async def cleanup(self):
        """리소스 정리"""
        if self.orchestrator:
            await self.orchestrator.__aexit__(None, None, None)
        logger.info("리소스 정리 완료")

    async def get_active_accounts(
        self, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """활성화된 계정 조회"""
        query = """
            SELECT 
                user_id, 
                user_name, 
                email,
                is_active,
                status,
                last_sync_time
            FROM accounts 
            WHERE is_active = 1
            ORDER BY user_id
        """

        if limit:
            query += f" LIMIT {limit}"

        accounts = self.db.fetch_all(query)
        return [dict(account) for account in accounts]

    async def enqueue_account_mails(
        self,
        user_id: str,
        days_back: int = 30,
        max_pages: int = 5,
        mails_per_page: int = 50,
    ) -> Dict[str, Any]:
        """특정 계정의 메일을 큐에 저장"""

        try:
            # 필터 설정
            filters = MailQueryFilters(
                date_from=datetime.now() - timedelta(days=days_back)
            )

            # 페이지네이션 설정
            pagination = PaginationOptions(top=mails_per_page, max_pages=max_pages)

            # 큐에 메일 저장
            result = await self.orchestrator.enqueue_user_mails(
                user_id=user_id, filters=filters, pagination=pagination
            )

            return {"success": True, "user_id": user_id, **result}

        except Exception as e:
            logger.error(f"계정 {user_id} 메일 큐 저장 실패: {str(e)}")
            return {
                "success": False,
                "user_id": user_id,
                "error": str(e),
                "total_fetched": 0,
                "enqueued": 0,
                "duplicates": 0,
            }

    async def test_enqueue_single_account(self, user_id: str):
        """단일 계정 테스트"""
        print(f"\n🧪 단일 계정 큐 저장 테스트: {user_id}")
        print("=" * 80)

        result = await self.enqueue_account_mails(
            user_id=user_id, days_back=30, max_pages=2, mails_per_page=50
        )

        if result["success"]:
            print(f"✅ 성공!")
            print(f"  - 조회된 메일: {result['total_fetched']}개")
            print(f"  - 필터링 후: {result['filtered_count']}개")
            print(f"  - 큐에 저장: {result['enqueued']}개")
            print(f"  - 중복 건너뜀: {result['duplicates']}개")
            print(f"  - 큐 크기: {result['queue_size']}개")
            print(f"  - 실행 시간: {result['execution_time_ms']}ms")
        else:
            print(f"❌ 실패: {result['error']}")

    async def test_enqueue_all_accounts(
        self,
        max_accounts: Optional[int] = None,
        days_back: int = 30,
        max_pages_per_account: int = 5,
    ):
        """모든 계정 큐 저장 테스트"""
        print("\n🚀 모든 계정 메일 큐 저장 테스트")
        print("=" * 80)
        print(f"설정:")
        print(f"  - 최근 {days_back}일 메일")
        print(f"  - 계정당 최대 {max_pages_per_account} 페이지")
        print(f"  - 시작 시간: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)

        # 활성 계정 조회
        accounts = await self.get_active_accounts(limit=max_accounts)
        print(f"\n📋 활성 계정 수: {len(accounts)}개")

        # 큐 상태 확인
        initial_queue_status = await self.orchestrator.queue_service.get_queue_status()
        print(f"\n📊 초기 큐 상태:")
        print(f"  - 큐 크기: {initial_queue_status['queue_size']}개")
        print(f"  - 배치 크기: {initial_queue_status['batch_size']}개")

        # 각 계정별 처리
        print(f"\n📧 계정별 메일 큐 저장 시작...")
        print("-" * 80)

        results = []
        total_enqueued = 0
        total_duplicates = 0
        success_count = 0

        for i, account in enumerate(accounts, 1):
            user_id = account["user_id"]
            print(
                f"\n[{i}/{len(accounts)}] {user_id} ({account['user_name']}) 처리 중..."
            )

            result = await self.enqueue_account_mails(
                user_id=user_id, days_back=days_back, max_pages=max_pages_per_account
            )

            results.append(result)

            if result["success"]:
                success_count += 1
                total_enqueued += result.get("enqueued", 0)
                total_duplicates += result.get("duplicates", 0)

                print(
                    f"  ✅ 성공: 조회 {result['total_fetched']}개 → "
                    f"큐 저장 {result['enqueued']}개 (중복 {result['duplicates']}개)"
                )
            else:
                print(f"  ❌ 실패: {result.get('error', 'Unknown error')}")

            # 진행 상황 표시
            if i % 5 == 0:
                current_queue_status = (
                    await self.orchestrator.queue_service.get_queue_status()
                )
                print(
                    f"\n  📊 진행 상황: 큐 크기 = {current_queue_status['queue_size']}개"
                )

        # 최종 큐 상태
        final_queue_status = await self.orchestrator.queue_service.get_queue_status()

        # 결과 요약
        print("\n" + "=" * 80)
        print("📊 전체 결과 요약")
        print("=" * 80)

        print(f"\n✅ 성공: {success_count}/{len(accounts)} 계정")
        print(f"📧 큐에 저장된 메일: {total_enqueued}개")
        print(f"🔄 중복 메일: {total_duplicates}개")

        print(f"\n📈 큐 상태 변화:")
        print(f"  - 초기: {initial_queue_status['queue_size']}개")
        print(f"  - 최종: {final_queue_status['queue_size']}개")
        print(
            f"  - 증가: {final_queue_status['queue_size'] - initial_queue_status['queue_size']}개"
        )

        # 계정별 상세 통계
        print(f"\n📊 계정별 상세:")
        print(
            f"{'계정 ID':<20} {'조회':<10} {'큐 저장':<10} {'중복':<10} {'실행(ms)':<10}"
        )
        print("-" * 70)

        for result in results:
            if result["success"]:
                print(
                    f"{result['user_id']:<20} "
                    f"{result.get('total_fetched', 0):<10} "
                    f"{result.get('enqueued', 0):<10} "
                    f"{result.get('duplicates', 0):<10} "
                    f"{result.get('execution_time_ms', 0):<10}"
                )

        # 실행 시간 분석
        total_time = (datetime.now() - self.start_time).total_seconds()
        print(f"\n⏱️  실행 시간 분석:")
        print(f"  - 총 실행 시간: {total_time:.2f}초")
        print(f"  - 평균 시간/계정: {total_time/len(accounts):.2f}초")

        print(f"\n✅ 테스트 완료!")
        print(f"종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        return {
            "total_accounts": len(accounts),
            "success_count": success_count,
            "total_enqueued": total_enqueued,
            "total_duplicates": total_duplicates,
            "final_queue_size": final_queue_status["queue_size"],
        }

    async def test_queue_processing(self, wait_seconds: int = 10):
        """큐 처리 모니터링"""
        print(f"\n🔄 큐 처리 모니터링 ({wait_seconds}초)...")
        print("-" * 50)

        # 프로세서 상태 확인
        initial_stats = await self.orchestrator.get_processing_status()
        print(f"초기 상태:")
        print(f"  - 큐 크기: {initial_stats['queue']['queue_size']}개")
        print(f"  - 처리됨: {initial_stats['processor']['stats']['total_processed']}개")

        # 대기하면서 주기적으로 상태 확인
        for i in range(wait_seconds):
            await asyncio.sleep(1)

            if (i + 1) % 5 == 0:  # 5초마다 상태 출력
                current_stats = await self.orchestrator.get_processing_status()
                print(f"\n[{i+1}초] 현재 상태:")
                print(f"  - 큐 크기: {current_stats['queue']['queue_size']}개")
                print(
                    f"  - 처리됨: {current_stats['processor']['stats']['total_processed']}개"
                )
                print(
                    f"  - 저장됨: {current_stats['processor']['stats']['total_saved']}개"
                )

        # 최종 상태
        final_stats = await self.orchestrator.get_processing_status()
        print(f"\n최종 상태:")
        print(f"  - 큐 크기: {final_stats['queue']['queue_size']}개")
        print(f"  - 총 처리: {final_stats['processor']['stats']['total_processed']}개")
        print(f"  - 총 저장: {final_stats['processor']['stats']['total_saved']}개")
        print(f"  - 총 실패: {final_stats['processor']['stats']['total_failed']}개")

    async def clear_queue(self):
        """큐 초기화 (테스트용)"""
        cleared = await self.orchestrator.queue_service.clear_queue()
        print(f"\n🗑️  큐 초기화 완료: {cleared}개 아이템 제거됨")


async def main():
    """메인 실행 함수"""
    tester = MailQueueEnqueueTester()

    try:
        # 초기화
        await tester.setup()

        # 테스트 모드 선택
        print("\n📋 테스트 모드 선택:")
        print("1. 단일 계정 테스트")
        print("2. 모든 계정 테스트 (소규모)")
        print("3. 모든 계정 테스트 (전체)")
        print("4. 큐 상태 확인")
        print("5. 큐 초기화")

        choice = input("\n선택 (1-5): ").strip()

        if choice == "1":
            user_id = input("계정 ID 입력: ").strip()
            await tester.test_enqueue_single_account(user_id)

        elif choice == "2":
            # 소규모 테스트 (최대 5개 계정)
            await tester.test_enqueue_all_accounts(
                max_accounts=5, days_back=30, max_pages_per_account=3
            )

        elif choice == "3":
            # 전체 테스트
            confirm = input("⚠️  모든 계정을 처리합니다. 계속하시겠습니까? (y/N): ")
            if confirm.lower() == "y":
                await tester.test_enqueue_all_accounts(
                    days_back=60, max_pages_per_account=10
                )

        elif choice == "4":
            # 큐 상태 확인 및 모니터링
            status = await tester.orchestrator.get_processing_status()
            print(f"\n📊 현재 큐 상태:")
            print(f"  - 큐 크기: {status['queue']['queue_size']}개")
            print(f"  - 처리 중: {status['processor']['is_running']}")

            if status["queue"]["queue_size"] > 0:
                monitor = input("\n처리 과정을 모니터링하시겠습니까? (y/N): ")
                if monitor.lower() == "y":
                    await tester.test_queue_processing(wait_seconds=30)

        elif choice == "5":
            # 큐 초기화
            confirm = input("⚠️  큐를 초기화하시겠습니까? (y/N): ")
            if confirm.lower() == "y":
                await tester.clear_queue()

        else:
            print("❌ 잘못된 선택입니다.")

    except KeyboardInterrupt:
        print("\n\n⚠️  사용자에 의해 중단됨")
    except Exception as e:
        logger.error(f"테스트 실행 중 오류: {str(e)}", exc_info=True)
    finally:
        await tester.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
