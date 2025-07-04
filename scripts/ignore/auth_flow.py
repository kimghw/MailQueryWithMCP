#!/usr/bin/env python3
"""
간단한 자동 인증 스크립트

기존 AuthOrchestrator의 메서드들을 활용하여
인증이 필요한 계정들을 자동으로 처리합니다.
"""

import argparse
import asyncio
import time
import webbrowser
from typing import Any, Dict, List

from modules.auth import AuthBulkRequest, AuthStartRequest, get_auth_orchestrator


class SimpleAutoAuth:
    """간단한 자동 인증 클래스"""

    def __init__(self):
        self.orchestrator = get_auth_orchestrator()

    async def check_and_auth_all(self):
        """모든 계정 상태 확인 후 필요한 경우 인증"""
        print("🔍 모든 계정 상태 확인 중...")

        # 오케스트레이터의 기존 메서드 활용
        accounts = await self.orchestrator.auth_orchestrator_get_all_accounts_status()

        # 인증이 필요한 계정들 필터링
        needs_auth = []
        for account in accounts:
            user_id = account["user_id"]
            is_active = account["is_active"]
            token_expired = account.get("token_expired", True)
            status = account.get("status", "UNKNOWN")

            # 인증 필요 조건 체크
            if is_active and (
                token_expired or status in ["INACTIVE", "REAUTH_REQUIRED"]
            ):
                reason = self._get_auth_reason(account)
                needs_auth.append({"user_id": user_id, "reason": reason})
                print(f"   ❗ {user_id}: {reason}")
            else:
                print(f"   ✅ {user_id}: 인증 상태 양호")

        if not needs_auth:
            print("✅ 모든 계정이 유효한 인증 상태입니다!")
            return

        print(f"\n📋 총 {len(needs_auth)}개 계정이 인증을 필요로 합니다")

        # 사용자 확인
        response = input("인증을 진행하시겠습니까? (y/N): ")
        if response.lower() not in ["y", "yes"]:
            print("취소되었습니다.")
            return

        # 일괄 인증 진행
        user_ids = [item["user_id"] for item in needs_auth]
        await self.bulk_authenticate(user_ids)

    async def single_authenticate(self, user_id: str):
        """단일 사용자 인증"""
        print(f"🚀 {user_id} 인증 시작...")

        # 오케스트레이터의 기존 메서드 활용
        request = AuthStartRequest(user_id=user_id)
        response = await self.orchestrator.auth_orchestrator_start_authentication(
            request
        )

        print(f"세션 ID: {response.session_id}")
        print(f"인증 URL: {response.auth_url}")
        print("\n🌐 브라우저에서 인증 URL을 엽니다...")

        webbrowser.open(response.auth_url)

        # 인증 완료 대기
        await self._wait_for_completion(response.session_id, user_id)

    async def bulk_authenticate(self, user_ids: List[str]):
        """일괄 인증"""
        print(f"🚀 일괄 인증 시작 ({len(user_ids)}명)...")

        # 오케스트레이터의 기존 메서드 활용
        request = AuthBulkRequest(user_ids=user_ids)
        response = await self.orchestrator.auth_orchestrator_bulk_authentication(
            request
        )

        print(f"대기 중: {response.pending_count}명")
        print(f"이미 완료: {response.completed_count}명")
        print(f"실패: {response.failed_count}명")

        # 대기 중인 사용자들의 브라우저 열기
        pending_sessions = {}
        for user_status in response.user_statuses:
            if user_status.auth_url:
                print(f"\n👤 {user_status.user_id}")
                print(f"   인증 URL: {user_status.auth_url}")

                # 자동으로 브라우저 열기 (2초 간격)
                webbrowser.open(user_status.auth_url)
                pending_sessions[user_status.user_id] = user_status.session_id
                time.sleep(2)

        # 모든 인증 완료 대기
        if pending_sessions:
            await self._wait_for_bulk_completion(pending_sessions)

    async def _wait_for_completion(self, session_id: str, user_id: str):
        """단일 인증 완료 대기"""
        max_wait = 300  # 5분
        check_interval = 3

        for i in range(0, max_wait, check_interval):
            await asyncio.sleep(check_interval)

            # 오케스트레이터의 기존 메서드 활용
            status = await self.orchestrator.auth_orchestrator_get_session_status(
                session_id
            )

            print(f"⏳ [{i+check_interval:3d}s] {user_id}: {status.status.value}")

            if status.status.value == "COMPLETED":
                print(f"✅ {user_id} 인증 완료!")
                return True
            elif status.status.value in ["FAILED", "EXPIRED"]:
                print(f"❌ {user_id} 인증 실패: {status.message}")
                return False

        print(f"⏰ {user_id} 인증 대기 시간 초과")
        return False

    async def _wait_for_bulk_completion(self, pending_sessions: Dict[str, str]):
        """일괄 인증 완료 대기"""
        max_wait = 600  # 10분
        check_interval = 5
        completed = {}

        print(f"\n⏳ 인증 완료 대기 중... (최대 {max_wait//60}분)")

        for i in range(0, max_wait, check_interval):
            await asyncio.sleep(check_interval)

            new_completions = []

            for user_id, session_id in pending_sessions.items():
                if user_id in completed:
                    continue

                # 오케스트레이터의 기존 메서드 활용
                status = await self.orchestrator.auth_orchestrator_get_session_status(
                    session_id
                )

                if status.status.value == "COMPLETED":
                    completed[user_id] = True
                    new_completions.append(user_id)
                    print(f"✅ {user_id} 인증 완료!")
                elif status.status.value in ["FAILED", "EXPIRED"]:
                    completed[user_id] = False
                    new_completions.append(user_id)
                    print(f"❌ {user_id} 인증 실패: {status.message}")

            # 모든 인증이 완료되었으면 종료
            if len(completed) >= len(pending_sessions):
                break

            # 진행 상황 출력 (30초마다)
            if i % 30 == 0:
                remaining = len(pending_sessions) - len(completed)
                print(
                    f"⏳ [{i+check_interval:3d}s] {len(completed)}명 완료, {remaining}명 대기 중"
                )

        # 결과 요약
        success_count = sum(1 for success in completed.values() if success)
        print(f"\n📊 최종 결과: {success_count}/{len(pending_sessions)}명 성공")

    def _get_auth_reason(self, account: Dict[str, Any]) -> str:
        """인증이 필요한 이유 반환"""
        status = account.get("status", "UNKNOWN")
        token_expired = account.get("token_expired", True)

        if status == "INACTIVE":
            return "계정 상태가 INACTIVE"
        elif status == "REAUTH_REQUIRED":
            return "재인증 필요"
        elif token_expired:
            return "토큰 만료"
        else:
            return "인증 필요"

    async def cleanup(self):
        """리소스 정리"""
        await self.orchestrator.auth_orchestrator_shutdown()


async def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="간단한 자동 인증 스크립트")
    parser.add_argument(
        "--mode",
        choices=["single", "bulk", "check-all"],
        required=True,
        help="single: 단일 인증, bulk: 일괄 인증, check-all: 전체 확인 후 인증",
    )
    parser.add_argument("--user-id", help="단일 모드용 사용자 ID")
    parser.add_argument("--user-ids", nargs="+", help="일괄 모드용 사용자 ID 목록")

    args = parser.parse_args()

    print("=" * 60)
    print("간단한 자동 인증 스크립트 (AuthOrchestrator 기반)")
    print("=" * 60)

    auth = SimpleAutoAuth()

    try:
        if args.mode == "single":
            if not args.user_id:
                print("❌ --user-id 필요")
                return
            await auth.single_authenticate(args.user_id)

        elif args.mode == "bulk":
            if not args.user_ids:
                print("❌ --user-ids 필요")
                return
            await auth.bulk_authenticate(args.user_ids)

        elif args.mode == "check-all":
            await auth.check_and_auth_all()

    except KeyboardInterrupt:
        print("\n⚠️ 사용자 중단")
    except Exception as e:
        print(f"❌ 오류: {str(e)}")
        import traceback

        traceback.print_exc()
    finally:
        await auth.cleanup()
        print("✅ 완료")


if __name__ == "__main__":
    asyncio.run(main())
