#!/usr/bin/env python3
"""
계정 등록 스크립트

enrollment 디렉토리의 계정 설정 파일을 기반으로 계정을 등록합니다.

사용법:
    # 모든 계정 등록
    python enroll_account.py

    # 특정 계정만 등록
    python enroll_account.py kimghw
    python enroll_account.py krsdpt
"""

import argparse
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from infra.core.logger import get_logger
from modules.account import AccountOrchestrator

logger = get_logger(__name__)

ENROLLMENT_DIR = project_root / "enrollment"


def enroll_all_accounts():
    """모든 계정 등록"""
    logger.info("=== 모든 계정 등록 시작 ===")

    orchestrator = AccountOrchestrator()

    try:
        result = orchestrator.account_sync_all_enrollments()

        # 결과 출력
        print("\n" + "="*60)
        print("계정 등록 결과")
        print("="*60)
        print(f"처리된 파일 수: {result.total_files}")
        print(f"생성된 계정: {result.created_accounts}")
        print(f"업데이트된 계정: {result.updated_accounts}")
        print(f"비활성화된 계정: {result.deactivated_accounts}")
        print(f"오류 발생: {len(result.errors)}")

        if result.errors:
            print("\n오류 목록:")
            for error in result.errors:
                print(f"  - {error}")

        print("="*60)

        return result.created_accounts + result.updated_accounts > 0

    except Exception as e:
        logger.error(f"계정 등록 중 오류 발생: {e}")
        print(f"\n❌ 오류 발생: {e}")
        return False


def enroll_single_account(user_id: str):
    """특정 계정만 등록"""
    logger.info(f"=== 계정 등록: {user_id} ===")

    # .yaml 확장자가 이미 있으면 제거
    if user_id.endswith('.yaml'):
        user_id = user_id[:-5]

    # enrollment 파일 경로 찾기
    enrollment_file = ENROLLMENT_DIR / f"{user_id}.yaml"

    if not enrollment_file.exists():
        print(f"❌ enrollment 파일을 찾을 수 없습니다: {enrollment_file}")
        logger.error(f"파일이 존재하지 않음: {enrollment_file}")
        return False

    orchestrator = AccountOrchestrator()

    try:
        # 파일 검증
        validation_result = orchestrator.account_validate_enrollment_file(str(enrollment_file))

        if not validation_result["valid"]:
            print(f"❌ enrollment 파일 검증 실패:")
            for error in validation_result["errors"]:
                print(f"  - {error}")
            return False

        if validation_result["warnings"]:
            print("⚠️  경고:")
            for warning in validation_result["warnings"]:
                print(f"  - {warning}")

        # 계정 등록
        result = orchestrator.account_sync_single_file(str(enrollment_file))

        # 결과 출력
        print("\n" + "="*60)
        print(f"계정 등록 결과: {user_id}")
        print("="*60)

        if result.get("success"):
            action = result.get("action")
            if action == "created":
                print(f"✅ 계정이 생성되었습니다: {user_id}")
            elif action == "updated":
                print(f"✅ 계정이 업데이트되었습니다: {user_id}")
            elif action == "skipped":
                print(f"ℹ️  계정이 이미 최신 상태입니다: {user_id}")
        else:
            error = result.get("error", "알 수 없는 오류")
            print(f"❌ 계정 등록 실패: {error}")

        print("="*60)

        return result.get("success", False)

    except Exception as e:
        logger.error(f"계정 등록 중 오류 발생: {e}")
        print(f"\n❌ 오류 발생: {e}")
        return False


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="enrollment 파일을 기반으로 계정을 등록합니다.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예제:
  # 모든 계정 등록
  python enroll_account.py

  # 특정 계정만 등록
  python enroll_account.py kimghw
  python enroll_account.py krsdpt
        """
    )

    parser.add_argument(
        "user_id",
        nargs="?",
        help="등록할 계정의 user_id (생략 시 모든 계정 등록)"
    )

    args = parser.parse_args()

    # enrollment 디렉토리 확인
    if not ENROLLMENT_DIR.exists():
        print(f"❌ enrollment 디렉토리를 찾을 수 없습니다: {ENROLLMENT_DIR}")
        return 1

    # 인자에 따라 분기
    if args.user_id:
        # 특정 계정 등록
        success = enroll_single_account(args.user_id)
    else:
        # 모든 계정 등록
        success = enroll_all_accounts()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
