#!/usr/bin/env python3
"""
JSON-RPC 테스트 케이스 파일을 읽어서 실행

사용법:
    python tests/handlers/run_jsonrpc_tests.py <module> [test_numbers]

예시:
    python tests/handlers/run_jsonrpc_tests.py enrollment        # 모든 테스트
    python tests/handlers/run_jsonrpc_tests.py enrollment 1      # 1번 테스트만
    python tests/handlers/run_jsonrpc_tests.py enrollment 1,3,5  # 1,3,5번 테스트만
    python tests/handlers/run_jsonrpc_tests.py mail-query 2-4    # 2~4번 테스트
    python tests/handlers/run_jsonrpc_tests.py all               # 모든 모듈
"""

import sys
import json
import asyncio
import re
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime, timezone

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from modules.enrollment.mcp_server.handlers import AuthAccountHandlers
from modules.mail_query_MCP.mcp_server.handlers import MCPHandlers
from modules.onenote_mcp.handlers import OneNoteHandlers
from modules.teams_mcp.handlers import TeamsHandlers
from modules.onedrive_mcp.handlers import OneDriveHandlers
from infra.core.database import get_database_manager


class TestRunner:
    """JSON-RPC 테스트 실행기"""

    def __init__(self, test_case_dir: Path, selected_tests: set = None):
        self.test_case_dir = test_case_dir
        self.handlers = {}
        self.selected_tests = selected_tests  # None이면 모든 테스트, 아니면 선택된 번호 set
        self.results = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0
        }

    def get_handler(self, module: str):
        """핸들러 인스턴스 반환 (캐싱)"""
        if module not in self.handlers:
            if module == "enrollment":
                self.handlers[module] = AuthAccountHandlers()
            elif module == "mail-query":
                self.handlers[module] = MCPHandlers()
            elif module == "onenote":
                self.handlers[module] = OneNoteHandlers()
            elif module == "teams":
                self.handlers[module] = TeamsHandlers()
            elif module == "onedrive":
                self.handlers[module] = OneDriveHandlers()
            else:
                raise ValueError(f"Unknown module: {module}")
        return self.handlers[module]

    def load_test_cases(self, module: str) -> Dict[str, Any]:
        """테스트 케이스 JSON 파일 로드"""
        json_file = self.test_case_dir / f"{module}.json"
        if not json_file.exists():
            raise FileNotFoundError(f"Test case file not found: {json_file}")

        with open(json_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def _parse_datetime_aware(self, dt_str: str) -> datetime:
        """
        ISO 형식 문자열을 timezone-aware datetime으로 파싱

        Args:
            dt_str: ISO 형식 datetime 문자열

        Returns:
            timezone-aware datetime 객체
        """
        if not dt_str:
            return None

        try:
            # ISO 형식 파싱
            dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            # timezone 정보가 없으면 UTC로 간주
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            return None

    async def wait_for_oauth_callback(
        self,
        user_id: str,
        timeout_seconds: int = 180
    ) -> bool:
        """
        OAuth 콜백을 기다립니다 (redirect_uri로 토큰이 전달될 때까지)

        Args:
            user_id: 사용자 ID
            timeout_seconds: 타임아웃 (초) - 기본 3분

        Returns:
            콜백 성공 여부
        """
        print()
        print("⏳ OAuth 인증 콜백 대기 중...")
        print(f"   브라우저에서 Microsoft 로그인을 완료하세요")
        print(f"   타임아웃: {timeout_seconds}초")

        db = get_database_manager()
        start_time = datetime.now(timezone.utc)
        poll_interval = 2  # 2초마다 체크

        # 현재 토큰 상태 저장 (변경 감지용)
        initial_token = db.fetch_one(
            "SELECT access_token, updated_at FROM accounts WHERE user_id = ?",
            (user_id,)
        )
        initial_token_value = initial_token['access_token'] if initial_token else None
        initial_updated_at_str = initial_token['updated_at'] if initial_token else None
        initial_updated_at = self._parse_datetime_aware(initial_updated_at_str)

        dots = 0
        while True:
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()

            if elapsed > timeout_seconds:
                print(f"\n❌ 타임아웃: {timeout_seconds}초 내에 콜백을 받지 못했습니다")
                return False

            # 토큰 상태 확인
            current = db.fetch_one(
                "SELECT access_token, updated_at FROM accounts WHERE user_id = ?",
                (user_id,)
            )

            if current:
                current_token = current['access_token']
                current_updated_at_str = current['updated_at']
                current_updated_at = self._parse_datetime_aware(current_updated_at_str)

                # 토큰이 새로 생성되었거나 업데이트되었는지 확인 (timezone-aware 비교)
                token_changed = current_token and current_token != initial_token_value
                time_changed = (
                    current_updated_at and initial_updated_at and
                    current_updated_at > initial_updated_at
                )

                if current_token and (token_changed or time_changed):
                    print(f"\n✅ OAuth 콜백 수신 완료! (경과 시간: {elapsed:.1f}초)")
                    return True

            # 진행 상황 표시
            dots = (dots + 1) % 4
            print(f"\r   대기 중{'.' * dots}{' ' * (3 - dots)} ({elapsed:.0f}초 경과)", end='', flush=True)

            await asyncio.sleep(poll_interval)

    async def run_single_test(
        self,
        module: str,
        test_case: Dict[str, Any],
        test_num: int,
        total_tests: int
    ) -> bool:
        """단일 테스트 케이스 실행"""
        name = test_case.get("name", "Unnamed")
        enabled = test_case.get("enabled", True)
        tool = test_case.get("tool")
        arguments = test_case.get("arguments", {})
        expect = test_case.get("expect", {})

        print(f"\n{'='*80}")
        print(f"[{test_num}/{total_tests}] {name}")
        print(f"{'='*80}")
        print(f"📦 모듈: {module}")
        print(f"🔧 툴: {tool}")
        print(f"📝 인자: {json.dumps(arguments, indent=2, ensure_ascii=False)}")

        if not enabled:
            print("⏭️  SKIPPED - 비활성화됨")
            self.results["skipped"] += 1
            return True

        try:
            # 핸들러 호출
            handler = self.get_handler(module)
            result = await handler.handle_call_tool(tool, arguments)

            # 결과 추출
            result_text = result[0].text if result else ""

            # 결과 출력
            print()
            print("📥 결과:")
            print("-" * 80)
            print(result_text[:500])
            if len(result_text) > 500:
                print(f"... (총 {len(result_text)} 글자)")

            # start_authentication인 경우 OAuth 콜백 대기
            if tool == "start_authentication" and "인증 URL" in result_text:
                # user_id 추출
                user_id_match = re.search(r"사용자 ID:\s*(\S+)", result_text)
                if user_id_match:
                    user_id = user_id_match.group(1)
                    print()
                    print(f"🔐 OAuth 인증 프로세스 시작")
                    print(f"   User ID: {user_id}")

                    # 콜백 대기
                    callback_success = await self.wait_for_oauth_callback(user_id)

                    if not callback_success:
                        print("❌ FAIL - OAuth 콜백 타임아웃")
                        self.results["failed"] += 1
                        return False
                else:
                    print("⚠️  경고: 결과에서 user_id를 추출할 수 없어 콜백 대기를 건너뜁니다")

            # 검증
            expected_contains = expect.get("contains", [])
            validation_passed = False

            if expected_contains:
                # 리스트 중 하나라도 포함되면 성공
                for expected in expected_contains:
                    if expected in result_text:
                        validation_passed = True
                        break
            else:
                # expect가 없으면 에러가 발생하지 않았다면 성공
                validation_passed = True

            print()
            if validation_passed:
                print("✅ PASS")
                self.results["passed"] += 1
                return True
            else:
                print("❌ FAIL - 예상된 결과를 찾을 수 없음")
                print(f"기대값: {expected_contains}")
                self.results["failed"] += 1
                return False

        except Exception as e:
            print()
            print(f"❌ FAIL - Exception: {type(e).__name__}: {e}")
            self.results["failed"] += 1
            return False

    async def run_module_tests(self, module: str):
        """특정 모듈의 모든 테스트 실행"""
        print(f"\n{'='*80}")
        print(f"🧪 {module.upper()} 모듈 테스트 시작")
        print(f"{'='*80}")

        try:
            test_data = self.load_test_cases(module)
            test_cases = test_data.get("test_cases", [])
            description = test_data.get("description", "")

            print(f"📄 {description}")
            print(f"📊 테스트 케이스: {len(test_cases)}개")

            # 선택된 테스트 필터링
            if self.selected_tests is not None:
                print(f"🎯 선택된 테스트: {sorted(self.selected_tests)}")

            enabled_count = sum(1 for tc in test_cases if tc.get("enabled", True))
            print(f"✅ 활성화: {enabled_count}개")
            print(f"⏭️  비활성화: {len(test_cases) - enabled_count}개")

            total_tests = len(test_cases)
            for i, test_case in enumerate(test_cases, 1):
                # 선택된 테스트만 실행
                if self.selected_tests is not None and i not in self.selected_tests:
                    continue

                self.results["total"] += 1
                await self.run_single_test(module, test_case, i, total_tests)

        except FileNotFoundError as e:
            print(f"❌ 테스트 케이스 파일을 찾을 수 없습니다: {e}")
        except Exception as e:
            print(f"❌ 테스트 실행 실패: {e}")
            import traceback
            traceback.print_exc()

    def print_summary(self):
        """테스트 결과 요약 출력"""
        print(f"\n{'='*80}")
        print("📊 테스트 결과 요약")
        print(f"{'='*80}")
        print(f"총 테스트: {self.results['total']}개")
        print(f"✅ 성공: {self.results['passed']}개")
        print(f"❌ 실패: {self.results['failed']}개")
        print(f"⏭️  건너뜀: {self.results['skipped']}개")
        print(f"{'='*80}")

        if self.results['failed'] == 0:
            print("\n✅ 모든 테스트 통과!")
            return 0
        else:
            print(f"\n❌ {self.results['failed']}개의 테스트 실패")
            return 1


def parse_test_numbers(number_str: str) -> set:
    """
    테스트 번호 문자열을 파싱하여 set으로 반환

    예시:
        "1" -> {1}
        "1,3,5" -> {1, 3, 5}
        "2-4" -> {2, 3, 4}
        "1,3-5,7" -> {1, 3, 4, 5, 7}
    """
    result = set()
    parts = number_str.split(',')

    for part in parts:
        part = part.strip()
        if '-' in part:
            # 범위 처리 (예: "2-4")
            start, end = part.split('-', 1)
            try:
                start_num = int(start.strip())
                end_num = int(end.strip())
                result.update(range(start_num, end_num + 1))
            except ValueError:
                print(f"⚠️  경고: 잘못된 범위 형식 '{part}' (무시됨)")
        else:
            # 단일 번호 처리
            try:
                result.add(int(part))
            except ValueError:
                print(f"⚠️  경고: 잘못된 번호 '{part}' (무시됨)")

    return result


async def main():
    """메인 함수"""
    if len(sys.argv) < 2:
        print("사용법: python run_jsonrpc_tests.py <module> [test_numbers]")
        print()
        print("모듈:")
        print("  enrollment  - Enrollment MCP 테스트")
        print("  mail-query  - Mail Query MCP 테스트")
        print("  onenote     - OneNote MCP 테스트")
        print("  teams       - Teams MCP 테스트")
        print("  onedrive    - OneDrive MCP 테스트")
        print("  all         - 모든 모듈 테스트")
        print()
        print("테스트 번호 (선택사항):")
        print("  1           - 1번 테스트만")
        print("  1,3,5       - 1, 3, 5번 테스트")
        print("  2-4         - 2~4번 테스트")
        print("  1,3-5,7     - 1, 3, 4, 5, 7번 테스트")
        print()
        print("예시:")
        print("  python run_jsonrpc_tests.py enrollment")
        print("  python run_jsonrpc_tests.py enrollment 1")
        print("  python run_jsonrpc_tests.py enrollment 1,3,5")
        print("  python run_jsonrpc_tests.py mail-query 2-4")
        print("  python run_jsonrpc_tests.py all")
        return 1

    module = sys.argv[1]
    test_case_dir = Path(__file__).parent / "jsonrpc_cases"

    # 테스트 번호 파싱
    selected_tests = None
    if len(sys.argv) >= 3:
        selected_tests = parse_test_numbers(sys.argv[2])
        if not selected_tests:
            print("❌ 유효한 테스트 번호가 없습니다.")
            return 1

    runner = TestRunner(test_case_dir, selected_tests)

    if module == "all":
        if selected_tests:
            print("⚠️  경고: 'all' 모드에서는 테스트 번호 선택이 무시됩니다.")
        for mod in ["enrollment", "mail-query", "onenote", "teams", "onedrive"]:
            await runner.run_module_tests(mod)
    else:
        await runner.run_module_tests(module)

    return runner.print_summary()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
