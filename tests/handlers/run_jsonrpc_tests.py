#!/usr/bin/env python3
"""
JSON-RPC 테스트 케이스 파일을 읽어서 실행

사용법:
    python tests/handlers/run_jsonrpc_tests.py <module>
    python tests/handlers/run_jsonrpc_tests.py enrollment
    python tests/handlers/run_jsonrpc_tests.py mail-query
    python tests/handlers/run_jsonrpc_tests.py onenote
    python tests/handlers/run_jsonrpc_tests.py all
"""

import sys
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Any

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from modules.enrollment.mcp_server.handlers import AuthAccountHandlers
from modules.mail_query_MCP.mcp_server.handlers import MCPHandlers
from modules.onenote_mcp.handlers import OneNoteHandlers


class TestRunner:
    """JSON-RPC 테스트 실행기"""

    def __init__(self, test_case_dir: Path):
        self.test_case_dir = test_case_dir
        self.handlers = {}
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

            # 결과 출력
            print()
            print("📥 결과:")
            print("-" * 80)
            print(result_text[:500])
            if len(result_text) > 500:
                print(f"... (총 {len(result_text)} 글자)")

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

            enabled_count = sum(1 for tc in test_cases if tc.get("enabled", True))
            print(f"✅ 활성화: {enabled_count}개")
            print(f"⏭️  비활성화: {len(test_cases) - enabled_count}개")

            total_tests = len(test_cases)
            for i, test_case in enumerate(test_cases, 1):
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


async def main():
    """메인 함수"""
    if len(sys.argv) < 2:
        print("사용법: python run_jsonrpc_tests.py <module>")
        print()
        print("모듈:")
        print("  enrollment  - Enrollment MCP 테스트")
        print("  mail-query  - Mail Query MCP 테스트")
        print("  onenote     - OneNote MCP 테스트")
        print("  all         - 모든 모듈 테스트")
        print()
        print("예시:")
        print("  python run_jsonrpc_tests.py enrollment")
        print("  python run_jsonrpc_tests.py mail-query")
        print("  python run_jsonrpc_tests.py all")
        return 1

    module = sys.argv[1]
    test_case_dir = Path(__file__).parent / "jsonrpc_cases"

    runner = TestRunner(test_case_dir)

    if module == "all":
        for mod in ["enrollment", "mail-query", "onenote"]:
            await runner.run_module_tests(mod)
    else:
        await runner.run_module_tests(module)

    return runner.print_summary()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
