#!/usr/bin/env python3
"""
Mail Query 모듈 핸들러 직접 테스트

사용법:
    python tests/handlers/test_mail_query_handlers.py
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from modules.mail_query_MCP.mcp_server.handlers import MCPHandlers


def print_test_result(test_name: str, passed: bool, details: str = ""):
    """테스트 결과 출력"""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} - {test_name}")
    if details:
        print(f"  {details}")


def test_help():
    """help 핸들러 테스트"""
    print("\n📖 [1/4] help 핸들러 테스트...")

    try:
        handler = MCPHandlers()
        result = handler.help()

        # 결과 검증
        success = "MCP Mail Query Server" in result or "Available Tools" in result
        print_test_result("help", success, result[:200])

        return success

    except Exception as e:
        print_test_result("help", False, f"Exception: {e}")
        return False


def test_query_email_help():
    """query_email_help 핸들러 테스트"""
    print("\n📖 [2/4] query_email_help 핸들러 테스트...")

    try:
        handler = MCPHandlers()
        result = handler.query_email_help()

        # 결과 검증
        success = "query_email 툴 사용 가이드" in result
        print_test_result("query_email_help", success, result[:200])

        return success

    except Exception as e:
        print_test_result("query_email_help", False, f"Exception: {e}")
        return False


def test_query_email():
    """query_email 핸들러 테스트"""
    print("\n📧 [3/4] query_email 핸들러 테스트...")

    try:
        handler = MCPHandlers()

        # 최근 3일간 메일 조회
        start_date = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")

        result = handler.query_email(
            user_id="kimghw",
            start_date=start_date,
            end_date=end_date,
            include_body=False
        )

        # 결과 검증 (메일 조회 결과 또는 인증 필요 메시지)
        success = "메일 조회 결과" in result or "인증이 필요합니다" in result
        print_test_result("query_email", success, result[:300])

        return success

    except Exception as e:
        print_test_result("query_email", False, f"Exception: {e}")
        return False


def test_attachment_manager():
    """attachmentManager 핸들러 테스트"""
    print("\n📎 [4/4] attachmentManager 핸들러 테스트...")

    try:
        handler = MCPHandlers()

        # 최근 3일간 PDF 첨부파일 검색
        start_date = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")

        result = handler.attachmentManager(
            user_id="kimghw",
            start_date=start_date,
            end_date=end_date,
            filename_keywords=["pdf"],
            save_enabled=False
        )

        # 결과 검증
        success = "첨부파일 관리 결과" in result or "첨부파일 관리 완료" in result or "인증이 필요합니다" in result
        print_test_result("attachmentManager", success, result[:300])

        return success

    except Exception as e:
        print_test_result("attachmentManager", False, f"Exception: {e}")
        return False


def main():
    """메인 테스트 실행"""
    print("=" * 80)
    print("🧪 Mail Query 핸들러 직접 테스트")
    print("=" * 80)

    results = []

    # 테스트 실행
    results.append(test_help())
    results.append(test_query_email_help())
    results.append(test_query_email())
    results.append(test_attachment_manager())

    # 결과 요약
    print("\n" + "=" * 80)
    print("📊 테스트 결과 요약")
    print("=" * 80)

    total = len(results)
    passed = sum(results)
    failed = total - passed

    print(f"총 테스트: {total}개")
    print(f"✅ 성공: {passed}개")
    print(f"❌ 실패: {failed}개")

    if failed == 0:
        print("\n✅ 모든 테스트 통과!")
        return 0
    else:
        print(f"\n❌ {failed}개의 테스트 실패")
        return 1


if __name__ == "__main__":
    sys.exit(main())
