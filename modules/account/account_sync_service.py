"""
Account Sync Service - Enrollment 파일 동기화 서비스

enrollment 디렉터리의 YAML 파일들을 읽어서 계정 정보를 동기화합니다.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from infra.core.config import get_config
from infra.core.logger import get_logger
from infra.core.exceptions import ValidationError, DatabaseError
from .account_schema import (
    EnrollmentFileData,
    AccountCreate,
    AccountUpdate,
    AccountSyncResult,
    AccountStatus,
    AuthType,
    OAuthConfig,
)
from .account_repository import AccountRepository
from ._account_helpers import AccountFileHelpers

logger = get_logger(__name__)
config = get_config()


class AccountSyncService:
    """Enrollment 파일 동기화 서비스"""

    def __init__(self):
        self.repository = AccountRepository()
        self.file_helper = AccountFileHelpers()

    def account_sync_all_enrollments(self) -> AccountSyncResult:
        """
        모든 enrollment 파일을 동기화

        Returns:
            AccountSyncResult: 동기화 결과
        """
        logger.info("enrollment 파일 전체 동기화 시작")

        result = AccountSyncResult(
            total_files=0,
            created_accounts=0,
            updated_accounts=0,
            deactivated_accounts=0,
            errors=[],
            sync_time=datetime.utcnow(),
        )

        try:
            enrollment_dir = config.enrollment_directory
            enrollment_files = self.file_helper.account_list_enrollment_files(
                enrollment_dir
            )
            result.total_files = len(enrollment_files)

            if not enrollment_files:
                logger.warning(f"enrollment 파일이 없습니다: {enrollment_dir}")
                return result

            # 파일별로 동기화 처리
            processed_user_ids = set()

            for file_path in enrollment_files:
                try:
                    sync_file_result = self._account_sync_single_enrollment(file_path)

                    if sync_file_result["success"]:
                        user_id = sync_file_result["user_id"]
                        processed_user_ids.add(user_id)

                        if sync_file_result["action"] == "created":
                            result.created_accounts += 1
                        elif sync_file_result["action"] == "updated":
                            result.updated_accounts += 1

                        logger.info(
                            f"enrollment 동기화 성공: {file_path} -> {sync_file_result['action']}"
                        )
                    else:
                        result.errors.append(
                            f"{file_path}: {sync_file_result['error']}"
                        )
                        logger.error(
                            f"enrollment 동기화 실패: {file_path} -> {sync_file_result['error']}"
                        )

                except Exception as e:
                    error_msg = f"{file_path}: {str(e)}"
                    result.errors.append(error_msg)
                    logger.error(f"enrollment 파일 처리 오류: {error_msg}")

            # 파일에 없는 계정들은 비활성화 (선택적)
            deactivated_count = self._account_deactivate_orphaned_accounts(
                processed_user_ids
            )
            result.deactivated_accounts = deactivated_count

            logger.info(
                f"enrollment 동기화 완료: 생성={result.created_accounts}, "
                f"업데이트={result.updated_accounts}, 비활성화={result.deactivated_accounts}, "
                f"오류={len(result.errors)}"
            )

            return result

        except Exception as e:
            logger.error(f"enrollment 전체 동기화 오류: {e}")
            result.errors.append(f"전체 동기화 오류: {str(e)}")
            return result

    def _account_sync_single_enrollment(self, file_path: str) -> Dict[str, Any]:
        """
        단일 enrollment 파일 동기화

        Args:
            file_path: enrollment 파일 경로

        Returns:
            Dict: 동기화 결과 {'success': bool, 'action': str, 'user_id': str, 'error': str}
        """
        try:
            # 파일 읽기 및 검증
            file_data = self.file_helper.account_read_enrollment_file(file_path)

            if not self.file_helper.account_validate_enrollment_structure(file_data):
                return {
                    "success": False,
                    "error": "파일 구조가 올바르지 않습니다",
                    "action": None,
                    "user_id": None,
                }

            # 파일 해시 계산
            file_hash = self.file_helper.account_calculate_file_hash(file_path)

            # EnrollmentFileData 객체 생성
            enrollment_data = self._account_parse_enrollment_file(
                file_data, file_path, file_hash
            )

            # 사용자 ID 생성 (이메일에서 @ 앞부분 추출)
            user_id = enrollment_data.account_email.split("@")[0]

            # 기존 계정 확인
            existing_account = self.repository.account_get_by_user_id(user_id)

            if existing_account:
                # 기존 계정 업데이트
                action = self._account_update_existing_account(
                    existing_account, enrollment_data
                )
                return {
                    "success": True,
                    "action": action,
                    "user_id": user_id,
                    "error": None,
                }
            else:
                # 새 계정 생성
                account_id = self._account_create_new_account(enrollment_data, user_id)
                return {
                    "success": True,
                    "action": "created",
                    "user_id": user_id,
                    "account_id": account_id,
                    "error": None,
                }

        except ValidationError as e:
            return {
                "success": False,
                "error": f"검증 오류: {str(e)}",
                "action": None,
                "user_id": None,
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"처리 오류: {str(e)}",
                "action": None,
                "user_id": None,
            }

    def _account_parse_enrollment_file(
        self, file_data: Dict[str, Any], file_path: str, file_hash: str
    ) -> EnrollmentFileData:
        """
        파일 데이터를 EnrollmentFileData 객체로 변환

        Args:
            file_data: YAML에서 읽은 데이터
            file_path: 파일 경로
            file_hash: 파일 해시

        Returns:
            EnrollmentFileData: 파싱된 enrollment 데이터
        """
        try:
            # OAuth 설정 구성
            oauth_config = OAuthConfig(
                client_id=file_data["microsoft_graph"]["client_id"],
                client_secret=file_data["microsoft_graph"]["client_secret"],
                tenant_id=file_data["microsoft_graph"]["tenant_id"],
                redirect_uri=file_data["oauth"]["redirect_uri"],
                auth_type=AuthType(file_data["oauth"]["auth_type"]),
                delegated_permissions=file_data["oauth"]["delegated_permissions"],
            )

            # EnrollmentFileData 생성
            enrollment_data = EnrollmentFileData(
                account_email=file_data["account"]["email"],
                account_name=file_data["account"]["name"],
                oauth_config=oauth_config,
                file_path=file_path,
                file_hash=file_hash,
            )

            return enrollment_data

        except KeyError as e:
            raise ValidationError(f"필수 필드 누락: {e}")
        except ValueError as e:
            raise ValidationError(f"필드 값 오류: {e}")

    def _account_create_new_account(
        self, enrollment_data: EnrollmentFileData, user_id: str
    ) -> int:
        """
        새로운 계정 생성

        Args:
            enrollment_data: enrollment 파일 데이터
            user_id: 사용자 ID

        Returns:
            int: 생성된 계정 ID
        """
        account_create = AccountCreate(
            user_id=user_id,
            user_name=enrollment_data.account_name,
            email=enrollment_data.account_email,
            enrollment_file_path=enrollment_data.file_path,
            enrollment_file_hash=enrollment_data.file_hash,
            oauth_client_id=enrollment_data.oauth_config.client_id,
            oauth_client_secret=enrollment_data.oauth_config.client_secret,
            oauth_tenant_id=enrollment_data.oauth_config.tenant_id,
            oauth_redirect_uri=enrollment_data.oauth_config.redirect_uri,
            auth_type=enrollment_data.oauth_config.auth_type,
            delegated_permissions=enrollment_data.oauth_config.delegated_permissions,
        )

        account_id = self.repository.account_create_from_enrollment(account_create)
        logger.info(f"새 계정 생성: user_id={user_id}, account_id={account_id}")
        return account_id

    def _account_update_existing_account(
        self, existing_account, enrollment_data: EnrollmentFileData
    ) -> str:
        """
        기존 계정 업데이트

        Args:
            existing_account: 기존 계정 정보
            enrollment_data: enrollment 파일 데이터

        Returns:
            str: 수행된 액션 ('updated' 또는 'no_change')
        """
        # 파일 해시가 동일하면 업데이트 불필요
        if existing_account.enrollment_file_hash == enrollment_data.file_hash:
            logger.debug(
                f"파일 해시 동일 - 업데이트 불필요: {existing_account.user_id}"
            )
            return "no_change"

        # 업데이트할 데이터 구성
        update_data = AccountUpdate(
            user_name=enrollment_data.account_name,
            enrollment_file_path=enrollment_data.file_path,
            enrollment_file_hash=enrollment_data.file_hash,
            oauth_client_secret=enrollment_data.oauth_config.client_secret,
            oauth_redirect_uri=enrollment_data.oauth_config.redirect_uri,
            delegated_permissions=enrollment_data.oauth_config.delegated_permissions,
        )

        # 계정 업데이트
        success = self.repository.account_update_by_id(existing_account.id, update_data)

        if success:
            logger.info(f"계정 업데이트 완료: user_id={existing_account.user_id}")
            return "updated"
        else:
            logger.warning(f"계정 업데이트 실패: user_id={existing_account.user_id}")
            return "no_change"

    def _account_deactivate_orphaned_accounts(self, processed_user_ids: set) -> int:
        """
        파일에 없는 계정들을 비활성화 (선택적 기능)

        Args:
            processed_user_ids: 처리된 사용자 ID 집합

        Returns:
            int: 비활성화된 계정 수
        """
        # 현재 구현에서는 자동 비활성화를 하지 않음
        # 필요시 나중에 구현 가능
        logger.debug(f"처리된 사용자 ID: {len(processed_user_ids)}개")
        return 0

    def account_sync_single_file(self, file_path: str) -> Dict[str, Any]:
        """
        단일 파일 동기화 (외부 호출용)

        Args:
            file_path: enrollment 파일 경로

        Returns:
            Dict: 동기화 결과
        """
        logger.info(f"단일 파일 동기화 시작: {file_path}")

        if not Path(file_path).exists():
            return {
                "success": False,
                "error": f"파일이 존재하지 않습니다: {file_path}",
                "action": None,
                "user_id": None,
            }

        return self._account_sync_single_enrollment(file_path)

    def account_validate_enrollment_file(self, file_path: str) -> Dict[str, Any]:
        """
        Enrollment 파일 유효성 검사

        Args:
            file_path: 검사할 파일 경로

        Returns:
            Dict: 검사 결과 {'valid': bool, 'errors': List[str], 'warnings': List[str]}
        """
        result = {"valid": True, "errors": [], "warnings": []}

        try:
            # 파일 존재 확인
            if not Path(file_path).exists():
                result["valid"] = False
                result["errors"].append(f"파일이 존재하지 않습니다: {file_path}")
                return result

            # 파일 읽기
            file_data = self.file_helper.account_read_enrollment_file(file_path)

            # 구조 검증
            if not self.file_helper.account_validate_enrollment_structure(file_data):
                result["valid"] = False
                result["errors"].append("파일 구조가 올바르지 않습니다")
                return result

            # Pydantic 모델로 검증
            try:
                enrollment_data = self._account_parse_enrollment_file(
                    file_data, file_path, "temp_hash"
                )

                # 추가 비즈니스 로직 검증
                if (
                    enrollment_data.oauth_config.client_secret
                    == "YOUR_CLIENT_SECRET_HERE"
                ):
                    result["warnings"].append(
                        "클라이언트 시크릿이 placeholder 값입니다"
                    )

            except ValidationError as e:
                result["valid"] = False
                result["errors"].append(f"데이터 검증 오류: {str(e)}")

        except Exception as e:
            result["valid"] = False
            result["errors"].append(f"파일 처리 오류: {str(e)}")

        return result
