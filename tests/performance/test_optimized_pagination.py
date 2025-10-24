#!/usr/bin/env python3
"""
최적화된 페이지네이션 성능 테스트
Semaphore=3, top=100, max_pages=5 기본값
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
    user_id: str,
    top: int = None,
    max_pages: int = None,
    test_name: str = "테스트",
    use_default: bool = False
):
    """페이지네이션 성능 테스트"""

    print(f"\n📊 {test_name}")

    # 최근 30일 메일 조회
    date_from = datetime.now(timezone.utc) - timedelta(days=30)

    if use_default:
        # 기본값 사용
        pagination = None  # 기본값 사용
        print(f"   - 기본값 사용 (top=100, max_pages=5)")
    else:
        pagination = PaginationOptions(top=top, skip=0, max_pages=max_pages)
        print(f"   - top: {top}, max_pages: {max_pages}")
        print(f"   - 예상 조회: 최대 {top * max_pages}개 메일")

    request = MailQueryRequest(
        user_id=user_id,
        filters=MailQuerySeverFilters(
            date_from=date_from,
        ),
        pagination=pagination,
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
            print(f"   ✅ 메일당 평균: {(elapsed_time / max(response.total_fetched, 1)) * 1000:.1f}ms")

            return {
                "total_fetched": response.total_fetched,
                "pages_fetched": response.query_info.get("pages_fetched", 0),
                "elapsed_time": elapsed_time,
                "elapsed_ms": elapsed_time * 1000,
                "avg_per_page": elapsed_time / max(response.query_info.get("pages_fetched", 1), 1),
                "avg_per_mail": (elapsed_time / max(response.total_fetched, 1)) * 1000,
                "top": response.query_info.get("pagination", {}).get("top", 100),
                "max_pages": response.query_info.get("pagination", {}).get("max_pages", 5),
            }

        except Exception as e:
            print(f"   ❌ 오류 발생: {e}")
            import traceback
            traceback.print_exc()
            return None


async def run_optimized_test():
    """최적화된 성능 테스트 실행"""

    print_section("최적화된 페이지네이션 성능 테스트")
    print("\n✅ 최적화 내용:")
    print("   - Semaphore: 5개 → 3개 (API 동시성 제한 고려)")
    print("   - top 기본값: 50 → 100 (한 번에 더 많은 데이터)")
    print("   - max_pages 기본값: 10 → 5 (적절한 페이지 수)")

    # 1. 테스트 계정 확인
    user_id = await get_test_user_id()

    # 2. 다양한 시나리오 테스트
    test_scenarios = [
        {"use_default": True, "name": "✨ 기본값 테스트 (top=100, max_pages=5)"},
        {"top": 100, "max_pages": 3, "name": "시나리오 1: 중간 (3페이지 × 100개)"},
        {"top": 200, "max_pages": 3, "name": "시나리오 2: 큰 페이지 (3페이지 × 200개)"},
        {"top": 150, "max_pages": 4, "name": "시나리오 3: 균형 (4페이지 × 150개)"},
        {"top": 100, "max_pages": 5, "name": "시나리오 4: 기본 설정 (5페이지 × 100개)"},
    ]

    results = []

    for scenario in test_scenarios:
        result = await test_pagination_performance(
            user_id=user_id,
            top=scenario.get("top"),
            max_pages=scenario.get("max_pages"),
            test_name=scenario["name"],
            use_default=scenario.get("use_default", False),
        )

        if result:
            results.append(
                {
                    "scenario": scenario["name"],
                    **result,
                }
            )

        # 다음 테스트 전 대기 (API 레이트 리미트 방지)
        await asyncio.sleep(2)

    # 3. 결과 요약
    print_section("최적화 성능 테스트 결과 요약")

    if not results:
        print("❌ 테스트 결과가 없습니다.")
        return

    print(f"\n{'시나리오':<50} {'설정':>15} {'메일':>6} {'페이지':>6} {'시간(초)':>10} {'메일/ms':>10}")
    print("-" * 110)

    for result in results:
        setting = f"{result['top']}×{result['max_pages']}"
        print(
            f"{result['scenario']:<50} "
            f"{setting:>15} "
            f"{result['total_fetched']:>6} "
            f"{result['pages_fetched']:>6} "
            f"{result['elapsed_time']:>10.2f} "
            f"{result['avg_per_mail']:>10.1f}"
        )

    # 4. 최적 설정 분석
    print_section("최적 설정 분석")

    # 가장 빠른 테스트 찾기
    fastest = min(results, key=lambda x: x["elapsed_time"])
    most_efficient = min(results, key=lambda x: x["avg_per_mail"])

    print(f"\n🏆 가장 빠른 설정:")
    print(f"   - {fastest['scenario']}")
    print(f"   - 소요 시간: {fastest['elapsed_time']:.2f}초")
    print(f"   - 설정: top={fastest['top']}, max_pages={fastest['max_pages']}")

    print(f"\n⚡ 가장 효율적인 설정 (메일당):")
    print(f"   - {most_efficient['scenario']}")
    print(f"   - 메일당: {most_efficient['avg_per_mail']:.1f}ms")
    print(f"   - 설정: top={most_efficient['top']}, max_pages={most_efficient['max_pages']}")

    # 기본값 성능 확인
    default_result = next((r for r in results if "기본값" in r["scenario"]), None)
    if default_result:
        print(f"\n✅ 기본값 성능:")
        print(f"   - 소요 시간: {default_result['elapsed_time']:.2f}초")
        print(f"   - 조회 메일: {default_result['total_fetched']}개")
        print(f"   - 페이지 수: {default_result['pages_fetched']}개")

    print("\n" + "=" * 80)
    print("✅ 최적화 완료!")
    print(f"   권장 설정: top=100~200, max_pages=3~5, Semaphore=3")


if __name__ == "__main__":
    asyncio.run(run_optimized_test())
