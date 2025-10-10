#!/usr/bin/env python3
"""
환경변수 검증 스크립트

MCP 서버 실행 전 환경변수를 검증합니다.
"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from infra.core.env_validator import validate_environment, EnvValidator


def main():
    """환경변수 검증 실행"""
    print("\n🔍 MCP 서버 환경변수 검증 시작...\n")

    # 검증 실행
    success = validate_environment()

    # 예제 .env 파일 생성 옵션
    if "--generate-example" in sys.argv:
        validator = EnvValidator()
        example = validator.generate_example_env()

        example_file = project_root / ".env.generated"
        example_file.write_text(example)
        print(f"\n✅ 예제 환경변수 파일 생성: {example_file}")
        print("   이 파일을 참고하여 .env 파일을 작성하세요.")

    # 도움말
    if "--help" in sys.argv or "-h" in sys.argv:
        print("\n사용법:")
        print("  python scripts/validate_env.py       # 환경변수 검증")
        print("  python scripts/validate_env.py --generate-example  # 예제 .env 파일 생성")
        print("  python scripts/validate_env.py --help  # 도움말\n")
        sys.exit(0)

    # 결과에 따른 종료 코드
    if success:
        print("\n✅ MCP 서버를 시작할 준비가 되었습니다!\n")
        sys.exit(0)
    else:
        print("\n❌ 환경변수 설정을 완료한 후 다시 실행해주세요.\n")
        sys.exit(1)


if __name__ == "__main__":
    main()