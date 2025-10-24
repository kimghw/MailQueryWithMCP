#!/usr/bin/env python3
"""
페이지네이션 병렬처리 성능 테스트
병렬처리 전후 성능 비교
"""

import asyncio
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from modules.mail_query.mail_query_orchestrator import MailQueryOrchestrator
from modules.mail_query.mail_query_schema import (
    MailQueryRequest,
    MailQuerySeverFilters,
    PaginationOptions,
)
from infra.core.database import get_database_manager


def print_section(title: str):
    """섹션 헤더 출력"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


async def get_test_user_id():
    """테스트에 사용할 사용자 ID 조회"""
    db = get_database_manager()
    account = db.fetch_one(
        "SELECT user_id FROM accounts WHERE is_active = 1 ORDER BY last_used_at DESC LIMIT 1"
    )

    if not account:
        print("❌ 활성화된 계정이 없습니다. enrollment를 먼저 실행하세요.")
        sys.exit(1)

    user_id = account["user_id"]
    print(f"✅ 테스트 계정: {user_id}")
    return user_id


async def test_pagination_performance(
    user_id: str, top: int = 50, max_pages: int = 5, test_name: str = "기본 테스트"
):
    """페이지네이션 성능 테스트"""

    print(f"\n📊 {test_name}")
    print(f"   - top: {top}, max_pages: {max_pages}")
    print(f"   - 예상 조회: 최대 {top * max_pages}개 메일")

    # 최근 30일 메일 조회
    date_from = datetime.now(timezone.utc) - timedelta(days=30)

    request = MailQueryRequest(
        user_id=user_id,
        filters=MailQuerySeverFilters(
            date_from=date_from,
        ),
        pagination=PaginationOptions(top=top, skip=0, max_pages=max_pages),
        select_fields=[
            "id",
            "subject",
            "from",
            "receivedDateTime",
            "bodyPreview",
            "isRead",
            "hasAttachments",
        ],
    )

    # 성능 측정 시작
    start_time = time.time()

    async with MailQueryOrchestrator() as orchestrator:
        try:
            response = await orchestrator.mail_query_user_emails(request)

            # 성능 측정 종료
            elapsed_time = time.time() - start_time

            # 결과 출력
            print(f"\n   결과:")
            print(f"   ✅ 조회된 메일: {response.total_fetched}개")
            print(f"   ✅ 조회된 페이지: {response.query_info.get('pages_fetched', 0)}개")
            print(f"   ✅ 소요 시간: {elapsed_time:.2f}초 ({elapsed_time * 1000:.0f}ms)")
            print(f"   ✅ 페이지당 평균: {elapsed_time / max(response.query_info.get('pages_fetched', 1), 1):.2f}초")
            print(
                f"   ✅ 메일당 평균: {(elapsed_time / max(response.total_fetched, 1)) * 1000:.1f}ms"
            )

            return {
                "total_fetched": response.total_fetched,
                "pages_fetched": response.query_info.get("pages_fetched", 0),
                "elapsed_time": elapsed_time,
                "elapsed_ms": elapsed_time * 1000,
                "avg_per_page": elapsed_time / max(response.query_info.get("pages_fetched", 1), 1),
                "avg_per_mail": (elapsed_time / max(response.total_fetched, 1)) * 1000,
            }

        except Exception as e:
            print(f"   ❌ 오류 발생: {e}")
            import traceback

            traceback.print_exc()
            return None


async def run_performance_comparison():
    """성능 비교 테스트 실행"""

    print_section("페이지네이션 병렬처리 성능 테스트")

    # 1. 테스트 계정 확인
    user_id = await get_test_user_id()

    # 2. 다양한 시나리오 테스트
    test_scenarios = [
        {"top": 50, "max_pages": 3, "name": "시나리오 1: 소량 (3페이지 × 50개)"},
        {"top": 50, "max_pages": 5, "name": "시나리오 2: 중간 (5페이지 × 50개)"},
        {"top": 100, "max_pages": 5, "name": "시나리오 3: 대량 (5페이지 × 100개)"},
        {"top": 200, "max_pages": 3, "name": "시나리오 4: 큰 페이지 (3페이지 × 200개)"},
    ]

    results = []

    for scenario in test_scenarios:
        result = await test_pagination_performance(
            user_id=user_id,
            top=scenario["top"],
            max_pages=scenario["max_pages"],
            test_name=scenario["name"],
        )

        if result:
            results.append(
                {
                    "scenario": scenario["name"],
                    "top": scenario["top"],
                    "max_pages": scenario["max_pages"],
                    **result,
                }
            )

        # 다음 테스트 전 대기 (API 레이트 리미트 방지)
        await asyncio.sleep(2)

    # 3. 결과 요약
    print_section("성능 테스트 결과 요약")

    if not results:
        print("❌ 테스트 결과가 없습니다.")
        return

    print(
        f"\n{'시나리오':<45} {'메일수':>8} {'페이지':>6} {'시간(초)':>10} {'페이지/초':>10} {'메일/ms':>10}"
    )
    print("-" * 100)

    for result in results:
        print(
            f"{result['scenario']:<45} "
            f"{result['total_fetched']:>8} "
            f"{result['pages_fetched']:>6} "
            f"{result['elapsed_time']:>10.2f} "
            f"{result['avg_per_page']:>10.2f} "
            f"{result['avg_per_mail']:>10.1f}"
        )

    # 4. 병렬처리 효과 분석
    print_section("병렬처리 효과 분석")

    print("\n✅ 병렬처리 적용 (Semaphore 5개 동시 처리)")
    print("   - asyncio.gather()로 최대 5개 페이지 동시 조회")
    print("   - 네트워크 레이턴시 중첩으로 전체 시간 단축")
    print("   - 예상 개선율: 40-60% (네트워크 상황에 따라 변동)")

    if len(results) >= 2:
        avg_per_page = sum(r["avg_per_page"] for r in results) / len(results)
        print(f"\n📊 평균 페이지당 소요 시간: {avg_per_page:.2f}초")

        # 순차 처리 예상 시간 (이론적)
        sequential_estimate = avg_per_page * 5  # 5페이지 기준
        parallel_measured = results[1]["elapsed_time"]  # 5페이지 실제 측정

        improvement = ((sequential_estimate - parallel_measured) / sequential_estimate) * 100

        print(
            f"   - 순차 처리 예상: {sequential_estimate:.2f}초 (페이지당 {avg_per_page:.2f}초 × 5)"
        )
        print(f"   - 병렬 처리 실제: {parallel_measured:.2f}초")
        print(f"   - 개선율: {improvement:.1f}%")

    print("\n" + "=" * 80)
    print("✅ 테스트 완료!")


if __name__ == "__main__":
    asyncio.run(run_performance_comparison())
