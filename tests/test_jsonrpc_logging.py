#!/usr/bin/env python3
"""
JSON-RPC 로깅 기능 테스트
"""

import sys
import asyncio
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_logger_creation():
    """로거 생성 테스트"""
    print("=" * 80)
    print("🧪 JSON-RPC 로거 생성 테스트")
    print("=" * 80)

    try:
        from infra.core.jsonrpc_logger import get_jsonrpc_logger

        logger = get_jsonrpc_logger()
        print("✅ JSON-RPC 로거 생성 성공")
        print(f"   타입: {type(logger).__name__}")
        return True

    except Exception as e:
        print(f"❌ 로거 생성 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_table_creation():
    """테이블 생성 테스트"""
    print("\n" + "=" * 80)
    print("🧪 JSON-RPC 로그 테이블 생성 테스트")
    print("=" * 80)

    try:
        from infra.core.jsonrpc_logger import get_jsonrpc_logger
        from infra.core.database import get_database_manager

        logger = get_jsonrpc_logger()
        db = get_database_manager()

        # 테이블 확인
        with db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='jsonrpc_logs'"
            )
            table_exists = cursor.fetchone() is not None

        if table_exists:
            print("✅ jsonrpc_logs 테이블 존재")

            # 컬럼 확인
            with db.get_connection() as conn:
                cursor = conn.execute("PRAGMA table_info(jsonrpc_logs)")
                columns = cursor.fetchall()

            print(f"   컬럼 개수: {len(columns)}")
            print("   컬럼 목록:")
            for col in columns:
                print(f"     - {col[1]} ({col[2]})")

            return True
        else:
            print("❌ jsonrpc_logs 테이블이 없습니다")
            return False

    except Exception as e:
        print(f"❌ 테이블 확인 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_manual_logging():
    """수동 로깅 테스트"""
    print("\n" + "=" * 80)
    print("🧪 수동 로깅 테스트")
    print("=" * 80)

    try:
        from infra.core.jsonrpc_logger import get_jsonrpc_logger

        logger = get_jsonrpc_logger()

        # 테스트 로그 저장
        log_id = logger.log_request(
            tool_name="manage_sections_and_pages",
            arguments={
                "action": "list_sections",
                "user_id": "test_user"
            },
            response=[{"type": "text", "text": "Test response"}],
            success=True,
            execution_time_ms=123
        )

        if log_id > 0:
            print(f"✅ 로그 저장 성공 (ID: {log_id})")

            # 로그 조회
            logs = logger.get_logs(user_id="test_user", limit=1)

            if logs:
                log = logs[0]
                print(f"   도구: {log['tool_name']}")
                print(f"   액션: {log['action']}")
                print(f"   성공: {log['success']}")
                print(f"   실행시간: {log['execution_time_ms']}ms")
                return True
            else:
                print("❌ 로그 조회 실패")
                return False
        else:
            print("❌ 로그 저장 실패")
            return False

    except Exception as e:
        print(f"❌ 수동 로깅 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_stats():
    """통계 조회 테스트"""
    print("\n" + "=" * 80)
    print("🧪 통계 조회 테스트")
    print("=" * 80)

    try:
        from infra.core.jsonrpc_logger import get_jsonrpc_logger

        logger = get_jsonrpc_logger()

        # 여러 로그 저장
        for i in range(3):
            logger.log_request(
                tool_name="manage_page_content",
                arguments={
                    "action": "get",
                    "user_id": "test_user",
                    "page_id": f"page-{i}"
                },
                success=True,
                execution_time_ms=100 + i * 10
            )

        # 통계 조회
        stats = logger.get_stats(user_id="test_user")

        if stats and "tools" in stats:
            print(f"✅ 통계 조회 성공")
            print(f"   도구 개수: {len(stats['tools'])}")

            for tool_stat in stats['tools'][:3]:  # 최대 3개만 표시
                print(f"\n   📊 {tool_stat['tool_name']} ({tool_stat['action']})")
                print(f"      총 호출: {tool_stat['total_calls']}")
                print(f"      성공: {tool_stat['success_calls']}")
                print(f"      실패: {tool_stat['failed_calls']}")
                if tool_stat['avg_execution_time_ms']:
                    print(f"      평균 시간: {tool_stat['avg_execution_time_ms']}ms")

            return True
        else:
            print("❌ 통계가 비어있습니다")
            return False

    except Exception as e:
        print(f"❌ 통계 조회 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_decorator():
    """데코레이터 테스트"""
    print("\n" + "=" * 80)
    print("🧪 데코레이터 테스트")
    print("=" * 80)

    try:
        from infra.core.jsonrpc_logger import log_jsonrpc_call

        # 테스트 함수
        @log_jsonrpc_call
        async def test_function(name: str, arguments: dict):
            await asyncio.sleep(0.1)  # 실행 시간 시뮬레이션
            return [{"type": "text", "text": f"Hello from {name}"}]

        # 함수 호출
        result = await test_function("test_tool", {"user_id": "test_user", "action": "test"})

        if result:
            print("✅ 데코레이터 적용된 함수 실행 성공")
            print(f"   결과: {result}")

            # 로그 확인
            from infra.core.jsonrpc_logger import get_jsonrpc_logger
            logger = get_jsonrpc_logger()
            logs = logger.get_logs(tool_name="test_tool", limit=1)

            if logs:
                log = logs[0]
                print(f"   자동 로깅 확인:")
                print(f"     도구: {log['tool_name']}")
                print(f"     실행시간: {log['execution_time_ms']}ms")
                return True
            else:
                print("⚠️ 로그가 저장되지 않았습니다")
                return False
        else:
            print("❌ 함수 실행 실패")
            return False

    except Exception as e:
        print(f"❌ 데코레이터 테스트 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def cleanup():
    """테스트 데이터 정리"""
    print("\n" + "=" * 80)
    print("🧹 테스트 데이터 정리")
    print("=" * 80)

    try:
        from infra.core.database import get_database_manager

        db = get_database_manager()

        with db.get_connection() as conn:
            conn.execute("DELETE FROM jsonrpc_logs WHERE user_id = 'test_user'")
            conn.commit()

        print("✅ 테스트 데이터 정리 완료")
        return True

    except Exception as e:
        print(f"❌ 정리 실패: {str(e)}")
        return False


async def main():
    """메인 테스트 실행"""
    print("\n🚀 JSON-RPC 로깅 기능 테스트 시작\n")

    results = []

    # 1. 로거 생성
    results.append(("로거 생성", test_logger_creation()))

    # 2. 테이블 생성
    results.append(("테이블 생성", test_table_creation()))

    # 3. 수동 로깅
    results.append(("수동 로깅", test_manual_logging()))

    # 4. 통계 조회
    results.append(("통계 조회", test_stats()))

    # 5. 데코레이터
    results.append(("데코레이터", await test_decorator()))

    # 6. 정리
    results.append(("데이터 정리", cleanup()))

    # 결과 요약
    print("\n" + "=" * 80)
    print("📊 테스트 결과 요약")
    print("=" * 80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")

    print(f"\n총 {total}개 중 {passed}개 통과")

    if passed == total:
        print("\n🎉 모든 테스트 통과!")
        print("\n💡 다음 단계:")
        print("   1. modules/onenote_mcp/handlers.py에 데코레이터 추가")
        print("   2. @log_jsonrpc_call를 handle_call_tool 메서드에 적용")
        print("   3. 실제 API 호출 후 로그 확인")
        return 0
    else:
        print(f"\n⚠️ {total - passed}개 실패")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
