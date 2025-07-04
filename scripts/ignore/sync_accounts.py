#!/usr/bin/env python3
"""
증분 동기화 기반 계정 관리 스크립트

Account 모듈의 증분 동기화 기능을 사용하여 enrollment 파일들을 처리합니다.
- 새로운 파일 → 계정 생성
- 변경된 파일 → 계정 업데이트
- 동일한 파일 → 자동 건너뛰기 (해시 비교)
"""

import sys
import traceback
from datetime import datetime
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from infra.core.config import get_config
from infra.core.logger import get_logger
from modules.account import get_account_orchestrator


def sync_accounts(verbose: bool = True) -> bool:
    """
    증분 동기화로 계정 처리

    Args:
        verbose: 상세 출력 여부

    Returns:
        bool: 성공 여부
    """
    logger = get_logger(__name__)
    config = get_config()

    if verbose:
        print("🔄 IACSGraph 증분 동기화 시작")
        print("=" * 50)

    try:
        # Account 오케스트레이터 초기화
        orchestrator = get_account_orchestrator()

        # enrollment 디렉터리 확인
        enrollment_dir = Path(config.enrollment_directory)
        if verbose:
            print(f"📁 Enrollment 디렉터리: {enrollment_dir}")

        if not enrollment_dir.exists():
            if verbose:
                print(f"❌ 오류: enrollment 디렉터리가 존재하지 않습니다")
            return False

        # YAML 파일 확인
        yaml_files = list(enrollment_dir.glob("*.yaml")) + list(
            enrollment_dir.glob("*.yml")
        )
        if not yaml_files:
            if verbose:
                print(f"⚠️  enrollment 디렉터리에 YAML 파일이 없습니다")
            return False

        if verbose:
            print(f"📋 발견된 파일: {len(yaml_files)}개")

        # 증분 동기화 실행
        start_time = datetime.now()

        if verbose:
            print(f"\n🔄 증분 동기화 실행 중...")

        sync_result = orchestrator.account_sync_all_enrollments()

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # 결과 출력
        if verbose:
            print(f"\n📊 동기화 결과")
            print("-" * 30)
            print(f"📁 처리된 파일: {sync_result.total_files}")
            print(f"✅ 생성된 계정: {sync_result.created_accounts}")
            print(f"🔄 업데이트된 계정: {sync_result.updated_accounts}")
            print(f"❌ 오류 발생: {len(sync_result.errors)}")
            print(f"⏱️  처리 시간: {duration:.2f}초")

        # 오류 상세 출력
        if sync_result.errors and verbose:
            print(f"\n❌ 발생한 오류:")
            for i, error in enumerate(sync_result.errors[:5], 1):  # 최대 5개
                print(f"   {i}. {error}")
            if len(sync_result.errors) > 5:
                print(f"   ... 및 {len(sync_result.errors) - 5}개 추가 오류")

        # 성공 판정
        total_processed = sync_result.created_accounts + sync_result.updated_accounts
        if total_processed > 0:
            if verbose:
                print(f"\n✅ 성공: {total_processed}개 계정이 처리되었습니다!")
            return True
        elif len(sync_result.errors) > 0:
            if verbose:
                print(f"\n❌ 실패: 모든 파일에서 오류가 발생했습니다")
            return False
        else:
            if verbose:
                print(f"\n✅ 완료: 모든 파일이 이미 최신 상태입니다")
            return True

    except Exception as e:
        logger.error(f"증분 동기화 오류: {e}")
        if verbose:
            print(f"\n❌ 예상치 못한 오류: {e}")
            traceback.print_exc()
        return False


def check_enrollment_status() -> None:
    """enrollment 파일 상태 확인"""
    config = get_config()

    print("📋 Enrollment 파일 상태 확인")
    print("=" * 40)

    enrollment_dir = Path(config.enrollment_directory)

    if not enrollment_dir.exists():
        print(f"❌ enrollment 디렉터리가 없습니다: {enrollment_dir}")
        return

    yaml_files = list(enrollment_dir.glob("*.yaml")) + list(
        enrollment_dir.glob("*.yml")
    )

    if not yaml_files:
        print(f"📁 디렉터리: {enrollment_dir}")
        print(f"📄 YAML 파일: 0개")
        print(f"⚠️  처리할 파일이 없습니다")
        return

    print(f"📁 디렉터리: {enrollment_dir}")
    print(f"📄 YAML 파일: {len(yaml_files)}개")
    print(f"\n📋 파일 목록:")

    for i, file_path in enumerate(yaml_files, 1):
        file_size = file_path.stat().st_size
        modified_time = datetime.fromtimestamp(file_path.stat().st_mtime)
        print(f"   {i}. {file_path.name}")
        print(f"      크기: {file_size:,} bytes")
        print(f"      수정: {modified_time.strftime('%Y-%m-%d %H:%M:%S')}")


def validate_files() -> bool:
    """enrollment 파일들의 유효성 검사"""
    print("🔍 Enrollment 파일 유효성 검사")
    print("=" * 40)

    try:
        orchestrator = get_account_orchestrator()
        config = get_config()

        enrollment_dir = Path(config.enrollment_directory)
        yaml_files = list(enrollment_dir.glob("*.yaml")) + list(
            enrollment_dir.glob("*.yml")
        )

        if not yaml_files:
            print("⚠️  검사할 파일이 없습니다")
            return False

        valid_count = 0
        invalid_count = 0

        for file_path in yaml_files:
            result = orchestrator.account_validate_enrollment_file(str(file_path))

            if result["valid"]:
                print(f"✅ {file_path.name}")
                valid_count += 1

                if result["warnings"]:
                    for warning in result["warnings"]:
                        print(f"   ⚠️  경고: {warning}")
            else:
                print(f"❌ {file_path.name}")
                invalid_count += 1

                for error in result["errors"]:
                    print(f"   🔸 {error}")

        print(f"\n📊 검사 결과:")
        print(f"   ✅ 유효: {valid_count}개")
        print(f"   ❌ 무효: {invalid_count}개")

        return invalid_count == 0

    except Exception as e:
        print(f"❌ 검사 중 오류: {e}")
        return False


def main():
    """메인 실행 함수"""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()

        if command in ["--check", "-c"]:
            check_enrollment_status()
            return
        elif command in ["--validate", "-v"]:
            valid = validate_files()
            sys.exit(0 if valid else 1)
        elif command in ["--quiet", "-q"]:
            success = sync_accounts(verbose=False)
            if success:
                print("SUCCESS")
            else:
                print("FAILED")
            sys.exit(0 if success else 1)
        elif command in ["--help", "-h"]:
            show_help()
            return
        else:
            print(f"❌ 알 수 없는 명령: {command}")
            print("사용법: python sync_accounts.py [--check|--validate|--quiet|--help]")
            sys.exit(1)

    # 기본 실행 (상세 출력 모드)
    success = sync_accounts(verbose=True)

    if success:
        print(f"\n🎉 증분 동기화가 완료되었습니다!")
        sys.exit(0)
    else:
        print(f"\n💥 증분 동기화에 실패했습니다.")
        sys.exit(1)


def show_help():
    """도움말 출력"""
    help_text = """
🔧 IACSGraph 증분 동기화 스크립트

이 스크립트는 Account 모듈의 증분 동기화 기능을 사용하여
enrollment 파일들을 효율적으로 처리합니다.

📋 동작 방식:
- 파일 해시 비교로 변경된 파일만 처리
- 새로운 파일 → 계정 생성
- 변경된 파일 → 계정 업데이트
- 동일한 파일 → 자동 건너뛰기

🚀 사용법:
   python sync_accounts.py              # 증분 동기화 실행 (상세 출력)
   python sync_accounts.py --check      # 파일 상태만 확인
   python sync_accounts.py --validate   # 파일 유효성 검사
   python sync_accounts.py --quiet      # 조용한 모드 (자동화용)
   python sync_accounts.py --help       # 이 도움말

🔍 옵션 설명:
   -c, --check      enrollment 디렉터리와 파일 목록 확인
   -v, --validate   모든 YAML 파일의 유효성 검사
   -q, --quiet      최소 출력 모드 (SUCCESS/FAILED만 출력)
   -h, --help       도움말 출력

💡 팁:
- 정기적으로 실행하면 변경된 내용만 자동으로 처리됩니다
- 여러 번 실행해도 안전합니다 (중복 처리 방지)
- 크론잡이나 스케줄러에서 --quiet 옵션 사용 권장

📖 더 자세한 정보는 modules/account/README.md를 참조하세요.
"""
    print(help_text)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n⏹️  사용자 중단 요청으로 스크립트를 종료합니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 예상치 못한 오류: {e}")
        sys.exit(1)
