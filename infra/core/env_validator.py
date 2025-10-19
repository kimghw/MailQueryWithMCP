"""
환경변수 검증 시스템

환경변수를 체계적으로 검증하고 누락된 설정을 명확히 보고합니다.
"""

import os
import sys
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from dotenv import load_dotenv


class EnvVarCategory(Enum):
    """환경변수 카테고리"""
    REQUIRED = "required"  # 필수 (애플리케이션 실행 불가)
    RECOMMENDED = "recommended"  # 권장 (기능 제한)
    OPTIONAL = "optional"  # 선택적


class EnvVarDefinition:
    """환경변수 정의"""

    def __init__(
        self,
        name: str,
        category: EnvVarCategory,
        description: str,
        default: Optional[str] = None,
        validator: Optional[callable] = None,
        example: Optional[str] = None
    ):
        self.name = name
        self.category = category
        self.description = description
        self.default = default
        self.validator = validator
        self.example = example


class EnvValidator:
    """환경변수 검증 클래스"""

    # 환경변수 정의
    ENV_DEFINITIONS = [
        # 필수 환경변수
        EnvVarDefinition(
            "DATABASE_PATH",
            EnvVarCategory.REQUIRED,
            "SQLite 데이터베이스 파일 경로",
            default="./data/iacsgraph.db",
            example="./data/iacsgraph.db"
        ),
        EnvVarDefinition(
            "ENCRYPTION_KEY",
            EnvVarCategory.REQUIRED,
            "데이터 암호화용 Fernet 키 (32 bytes base64 encoded)",
            validator=lambda x: len(x) == 44,  # Fernet key는 정확히 44자
            example="your-44-character-fernet-key-here=========="
        ),

        # 권장 환경변수
        EnvVarDefinition(
            "KAFKA_BOOTSTRAP_SERVERS",
            EnvVarCategory.RECOMMENDED,
            "Kafka 부트스트랩 서버 주소",
            default="localhost:9092",
            example="localhost:9092"
        ),

        # 선택적 환경변수
        EnvVarDefinition(
            "LOG_LEVEL",
            EnvVarCategory.OPTIONAL,
            "로깅 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
            default="INFO",
            validator=lambda x: x.upper() in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            example="INFO"
        ),
        EnvVarDefinition(
            "ENVIRONMENT",
            EnvVarCategory.OPTIONAL,
            "실행 환경 (development, staging, production)",
            default="development",
            validator=lambda x: x.lower() in ["development", "staging", "production"],
            example="development"
        ),
        EnvVarDefinition(
            "OAUTH_REDIRECT_PORT",
            EnvVarCategory.OPTIONAL,
            "OAuth 콜백 서버 포트",
            default="5000",
            validator=lambda x: x.isdigit() and 1024 <= int(x) <= 65535,
            example="5000"
        ),
        EnvVarDefinition(
            "HTTP_TIMEOUT",
            EnvVarCategory.OPTIONAL,
            "HTTP 요청 타임아웃 (초)",
            default="30",
            validator=lambda x: x.isdigit() and int(x) > 0,
            example="30"
        ),
        EnvVarDefinition(
            "BATCH_SIZE",
            EnvVarCategory.OPTIONAL,
            "배치 처리 크기",
            default="20",
            validator=lambda x: x.isdigit() and int(x) > 0,
            example="20"
        ),
        EnvVarDefinition(
            "MAX_KEYWORDS_PER_MAIL",
            EnvVarCategory.OPTIONAL,
            "메일당 최대 키워드 수",
            default="5",
            validator=lambda x: x.isdigit() and int(x) > 0,
            example="5"
        ),
        EnvVarDefinition(
            "MAX_MAILS_PER_ACCOUNT",
            EnvVarCategory.OPTIONAL,
            "계정당 최대 메일 처리 수",
            default="200",
            validator=lambda x: x.isdigit() and int(x) > 0,
            example="200"
        ),
    ]

    def __init__(self):
        """환경변수 검증기 초기화"""
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []
        self._load_env_file()

    def _load_env_file(self) -> None:
        """환경변수 파일 로드"""
        project_root = Path(__file__).parent.parent.parent
        env_file = project_root / ".env"

        if env_file.exists():
            load_dotenv(env_file)
            self.info.append(f"✅ .env 파일 로드 완료: {env_file}")
        else:
            self.warnings.append(f"⚠️  .env 파일을 찾을 수 없습니다: {env_file}")
            self.warnings.append(f"   .env.example 파일을 복사하여 .env 파일을 생성해주세요.")

    def validate(self) -> Tuple[bool, Dict[str, List[str]]]:
        """
        환경변수 검증 수행

        Returns:
            Tuple[bool, Dict]: (성공 여부, 검증 결과 딕셔너리)
        """
        required_missing = []
        recommended_missing = []
        validation_errors = []

        for env_def in self.ENV_DEFINITIONS:
            value = os.getenv(env_def.name, env_def.default)

            # 값 존재 여부 확인
            if not value:
                if env_def.category == EnvVarCategory.REQUIRED:
                    required_missing.append(env_def)
                elif env_def.category == EnvVarCategory.RECOMMENDED:
                    recommended_missing.append(env_def)
                continue

            # 검증 함수가 있으면 실행
            if env_def.validator:
                try:
                    if not env_def.validator(value):
                        validation_errors.append(
                            f"❌ {env_def.name}: 유효하지 않은 값 (현재값: {value[:20]}...)"
                        )
                except Exception as e:
                    validation_errors.append(
                        f"❌ {env_def.name}: 검증 실패 - {str(e)}"
                    )

        # 결과 정리
        if required_missing:
            self.errors.append("\n🚨 필수 환경변수 누락:")
            for env_def in required_missing:
                self.errors.append(f"  • {env_def.name}")
                self.errors.append(f"    설명: {env_def.description}")
                if env_def.example:
                    self.errors.append(f"    예시: {env_def.name}={env_def.example}")

        if recommended_missing:
            self.warnings.append("\n⚠️  권장 환경변수 누락 (일부 기능 제한):")
            for env_def in recommended_missing:
                self.warnings.append(f"  • {env_def.name}")
                self.warnings.append(f"    설명: {env_def.description}")
                if env_def.example:
                    self.warnings.append(f"    예시: {env_def.name}={env_def.example}")

        if validation_errors:
            self.errors.extend(validation_errors)

        # 성공 여부 판단
        success = len(self.errors) == 0

        # 설정된 환경변수 수 계산
        total_vars = len(self.ENV_DEFINITIONS)
        configured_vars = sum(
            1 for env_def in self.ENV_DEFINITIONS
            if os.getenv(env_def.name, env_def.default)
        )

        self.info.append(f"\n📊 환경변수 설정 상태: {configured_vars}/{total_vars}")

        return success, {
            "errors": self.errors,
            "warnings": self.warnings,
            "info": self.info,
            "required_missing": [e.name for e in required_missing],
            "recommended_missing": [e.name for e in recommended_missing]
        }

    def print_report(self, file=sys.stdout):
        """검증 결과를 출력"""
        print("\n" + "=" * 60, file=file)
        print("🔍 환경변수 검증 보고서", file=file)
        print("=" * 60, file=file)

        # 정보 출력
        for msg in self.info:
            print(msg, file=file)

        # 경고 출력
        if self.warnings:
            print("\n⚠️  경고:", file=file)
            for msg in self.warnings:
                print(msg, file=file)

        # 오류 출력
        if self.errors:
            print("\n❌ 오류:", file=file)
            for msg in self.errors:
                print(msg, file=file)

        # 최종 상태
        print("\n" + "=" * 60, file=file)
        if not self.errors:
            print("✅ 환경변수 검증 성공!", file=file)
        else:
            print("❌ 환경변수 검증 실패! 위의 오류를 해결해주세요.", file=file)
        print("=" * 60 + "\n", file=file)

    def get_missing_required(self) -> List[str]:
        """누락된 필수 환경변수 목록 반환"""
        return [
            env_def.name for env_def in self.ENV_DEFINITIONS
            if env_def.category == EnvVarCategory.REQUIRED
            and not os.getenv(env_def.name, env_def.default)
        ]

    def generate_example_env(self) -> str:
        """예제 .env 파일 내용 생성"""
        lines = ["# MCP 서버 환경변수 설정\n"]

        # 카테고리별로 그룹화
        for category in EnvVarCategory:
            category_vars = [
                env_def for env_def in self.ENV_DEFINITIONS
                if env_def.category == category
            ]

            if not category_vars:
                continue

            if category == EnvVarCategory.REQUIRED:
                lines.append("\n# ===== 필수 설정 =====\n")
            elif category == EnvVarCategory.RECOMMENDED:
                lines.append("\n# ===== 권장 설정 (기능 활성화) =====\n")
            else:
                lines.append("\n# ===== 선택적 설정 =====\n")

            for env_def in category_vars:
                lines.append(f"# {env_def.description}\n")
                if env_def.example:
                    lines.append(f"{env_def.name}={env_def.example}\n")
                elif env_def.default:
                    lines.append(f"{env_def.name}={env_def.default}\n")
                else:
                    lines.append(f"# {env_def.name}=\n")
                lines.append("\n")

        return "".join(lines)


def validate_environment() -> bool:
    """
    환경변수를 검증하고 결과를 출력

    Returns:
        bool: 검증 성공 여부
    """
    validator = EnvValidator()
    success, result = validator.validate()
    validator.print_report()
    return success


def check_required_only() -> Tuple[bool, List[str]]:
    """
    필수 환경변수만 빠르게 체크

    Returns:
        Tuple[bool, List[str]]: (성공 여부, 누락된 환경변수 목록)
    """
    validator = EnvValidator()
    validator.validate()
    missing = validator.get_missing_required()
    return len(missing) == 0, missing


if __name__ == "__main__":
    # 직접 실행 시 검증 수행
    import sys
    success = validate_environment()

    # 예제 .env 파일 생성 옵션
    if "--generate-example" in sys.argv:
        validator = EnvValidator()
        example = validator.generate_example_env()

        example_file = Path(".env.generated")
        example_file.write_text(example)
        print(f"\n✅ 예제 환경변수 파일 생성: {example_file}")

    sys.exit(0 if success else 1)