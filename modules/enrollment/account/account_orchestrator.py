"""
Account Orchestrator - 계정 관리 비즈니스 로직 오케스트레이터

계정 관련 모든 비즈니스 플로우를 조정하고 관리합니다.
오케스트레이터 패턴을 적용하여 의존성 주입과 호출 순서를 담당합니다.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from infra.core.exceptions import BusinessLogicError, DatabaseError, ValidationError
from infra.core.logger import get_logger

from ._env_account_loader import env_load_account_from_env
from .account_repository import AccountRepository
from .account_schema import (
    AccountCreate,
    AccountListFilter,
    AccountResponse,
    AccountStatus,
    AccountSyncResult,
    AccountUpdate,
    TokenInfo,
)
from .account_sync_service import AccountSyncService

logger = get_logger(__name__)


class AccountOrchestrator:
    """계정 관리 오케스트레이터"""

    def __init__(self):
        # 의존성 주입 - 각 서비스는 독립적으로 생성
        self.repository = AccountRepository()
        self.sync_service = AccountSyncService()

        logger.info("Account Orchestrator 초기화 완료")

    def account_sync_all_enrollments(self) -> AccountSyncResult:
        """
        모든 enrollment 파일을 동기화

        Returns:
            AccountSyncResult: 동기화 결과

        Raises:
            BusinessLogicError: 비즈니스 로직 오류
        """
        try:
            logger.info("모든 enrollment 파일 동기화 시작")

            # 동기화 서비스를 통해 처리
            result = self.sync_service.account_sync_all_enrollments()

            # 결과에 따른 후처리 로직
            if result.errors:
                logger.warning(f"동기화 중 {len(result.errors)}개 오류 발생")
                for error in result.errors[:5]:  # 최대 5개만 로그
                    logger.warning(f"동기화 오류: {error}")

            # 성공적으로 생성/업데이트된 계정이 있으면 추가 처리
            if result.created_accounts > 0 or result.updated_accounts > 0:
                logger.info(
                    f"계정 변경사항: 생성={result.created_accounts}, "
                    f"업데이트={result.updated_accounts}"
                )

                # 필요시 이벤트 발행 등 추가 처리 가능
                self._account_notify_sync_completion(result)

            return result

        except Exception as e:
            logger.error(f"enrollment 동기화 오케스트레이션 오류: {e}")
            raise BusinessLogicError(f"enrollment 동기화 실패: {str(e)}")

    def account_sync_single_file(self, file_path: str) -> Dict[str, Any]:
        """
        단일 enrollment 파일 동기화

        Args:
            file_path: 동기화할 파일 경로

        Returns:
            Dict: 동기화 결과
        """
        try:
            logger.info(f"단일 파일 동기화: {file_path}")

            # 파일 유효성 검사
            validation_result = self.sync_service.account_validate_enrollment_file(
                file_path
            )

            if not validation_result["valid"]:
                return {
                    "success": False,
                    "error": f"파일 검증 실패: {', '.join(validation_result['errors'])}",
                    "validation_result": validation_result,
                }

            # 경고가 있으면 로그
            if validation_result["warnings"]:
                for warning in validation_result["warnings"]:
                    logger.warning(f"파일 검증 경고: {warning}")

            # 동기화 실행
            sync_result = self.sync_service.account_sync_single_file(file_path)

            # 성공한 경우 추가 처리
            if sync_result.get("success"):
                user_id = sync_result.get("user_id")
                action = sync_result.get("action")
                logger.info(
                    f"단일 파일 동기화 완료: user_id={user_id}, action={action}"
                )

            return sync_result

        except Exception as e:
            logger.error(f"단일 파일 동기화 오류: {file_path}, {e}")
            return {
                "success": False,
                "error": f"처리 오류: {str(e)}",
                "action": None,
                "user_id": None,
            }

    def account_get_by_user_id(self, user_id: str) -> Optional[AccountResponse]:
        """
        사용자 ID로 계정 조회

        Args:
            user_id: 조회할 사용자 ID

        Returns:
            Optional[AccountResponse]: 계정 정보
        """
        try:
            if not user_id or not user_id.strip():
                raise ValidationError("user_id는 필수입니다")

            logger.debug(f"계정 조회: user_id={user_id}")
            account = self.repository.account_get_by_user_id(user_id.strip())

            if account:
                logger.debug(
                    f"계정 조회 성공: user_id={user_id}, status={account.status}"
                )
            else:
                logger.debug(f"계정을 찾을 수 없음: user_id={user_id}")

            return account

        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"계정 조회 오류: user_id={user_id}, {e}")
            raise BusinessLogicError(f"계정 조회 실패: {str(e)}")

    def account_get_by_id(self, account_id: int) -> Optional[AccountResponse]:
        """
        계정 ID로 계정 조회

        Args:
            account_id: 조회할 계정 ID

        Returns:
            Optional[AccountResponse]: 계정 정보
        """
        try:
            if account_id <= 0:
                raise ValidationError("account_id는 양수여야 합니다")

            logger.debug(f"계정 조회: account_id={account_id}")
            account = self.repository.account_get_by_id(account_id)

            if account:
                logger.debug(
                    f"계정 조회 성공: account_id={account_id}, user_id={account.user_id}"
                )
            else:
                logger.debug(f"계정을 찾을 수 없음: account_id={account_id}")

            return account

        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"계정 조회 오류: account_id={account_id}, {e}")
            raise BusinessLogicError(f"계정 조회 실패: {str(e)}")

    def account_activate(self, user_id: str) -> bool:
        """
        계정 활성화

        Args:
            user_id: 활성화할 사용자 ID

        Returns:
            bool: 활성화 성공 여부
        """
        try:
            logger.info(f"계정 활성화 시작: user_id={user_id}")

            # 계정 존재 확인
            account = self.account_get_by_user_id(user_id)
            if not account:
                raise ValidationError(f"계정을 찾을 수 없습니다: {user_id}")

            # 이미 활성화된 경우
            if account.status == AccountStatus.ACTIVE:
                logger.info(f"이미 활성화된 계정: user_id={user_id}")
                return True

            # 계정 상태를 ACTIVE로 변경
            from .account_schema import AccountUpdate

            update_data = AccountUpdate(status=AccountStatus.ACTIVE)

            success = self.repository.account_update_by_id(account.id, update_data)

            if success:
                logger.info(f"계정 활성화 완료: user_id={user_id}")
            else:
                logger.error(f"계정 활성화 실패: user_id={user_id}")

            return success

        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"계정 활성화 오류: user_id={user_id}, {e}")
            raise BusinessLogicError(f"계정 활성화 실패: {str(e)}")

    def account_deactivate(self, user_id: str) -> bool:
        """
        계정 비활성화

        Args:
            user_id: 비활성화할 사용자 ID

        Returns:
            bool: 비활성화 성공 여부
        """
        try:
            logger.info(f"계정 비활성화 시작: user_id={user_id}")

            # 계정 존재 확인
            account = self.account_get_by_user_id(user_id)
            if not account:
                raise ValidationError(f"계정을 찾을 수 없습니다: {user_id}")

            # 이미 비활성화된 경우
            if account.status == AccountStatus.INACTIVE:
                logger.info(f"이미 비활성화된 계정: user_id={user_id}")
                return True

            # 계정 상태를 INACTIVE로 변경
            from .account_schema import AccountUpdate

            update_data = AccountUpdate(status=AccountStatus.INACTIVE)

            success = self.repository.account_update_by_id(account.id, update_data)

            if success:
                logger.info(f"계정 비활성화 완료: user_id={user_id}")
                # 추가로 토큰 정리 등의 처리 가능
                self._account_cleanup_on_deactivation(account)
            else:
                logger.error(f"계정 비활성화 실패: user_id={user_id}")

            return success

        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"계정 비활성화 오류: user_id={user_id}, {e}")
            raise BusinessLogicError(f"계정 비활성화 실패: {str(e)}")

    def account_update_token_info(self, user_id: str, token_info: TokenInfo) -> bool:
        """
        계정의 토큰 정보 업데이트

        Args:
            user_id: 사용자 ID
            token_info: 업데이트할 토큰 정보

        Returns:
            bool: 업데이트 성공 여부
        """
        try:
            logger.debug(f"토큰 정보 업데이트: user_id={user_id}")

            # 계정 존재 확인
            account = self.account_get_by_user_id(user_id)
            if not account:
                raise ValidationError(f"계정을 찾을 수 없습니다: {user_id}")

            # 업데이트 데이터 구성
            from .account_schema import AccountUpdate

            update_data = AccountUpdate(
                access_token=token_info.access_token,
                refresh_token=token_info.refresh_token,
                token_expiry=token_info.token_expiry,
                last_sync_time=datetime.now(timezone.utc).isoformat(),
            )

            success = self.repository.account_update_by_id(account.id, update_data)

            if success:
                logger.debug(f"토큰 정보 업데이트 완료: user_id={user_id}")
            else:
                logger.error(f"토큰 정보 업데이트 실패: user_id={user_id}")

            return success

        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"토큰 정보 업데이트 오류: user_id={user_id}, {e}")
            raise BusinessLogicError(f"토큰 정보 업데이트 실패: {str(e)}")

    def account_validate_enrollment_file(self, file_path: str) -> Dict[str, Any]:
        """
        Enrollment 파일 유효성 검사

        Args:
            file_path: 검사할 파일 경로

        Returns:
            Dict: 검사 결과
        """
        try:
            logger.debug(f"enrollment 파일 검증: {file_path}")

            result = self.sync_service.account_validate_enrollment_file(file_path)

            if not result["valid"]:
                logger.warning(f"enrollment 파일 검증 실패: {file_path}")
                for error in result["errors"]:
                    logger.warning(f"검증 오류: {error}")

            return result

        except Exception as e:
            logger.error(f"enrollment 파일 검증 오류: {file_path}, {e}")
            return {
                "valid": False,
                "errors": [f"검증 처리 오류: {str(e)}"],
                "warnings": [],
            }

    def _account_notify_sync_completion(self, sync_result: AccountSyncResult) -> None:
        """
        동기화 완료 알림 처리 (내부 메서드)

        Args:
            sync_result: 동기화 결과
        """
        logger.debug(f"동기화 완료 알림: 총 {sync_result.total_files}개 파일 처리")
        pass

    def _account_cleanup_on_deactivation(self, account: AccountResponse) -> None:
        """
        계정 비활성화 시 정리 작업 (내부 메서드)

        Args:
            account: 비활성화된 계정 정보
        """
        # 향후 토큰 무효화, 세션 정리 등의 기능 구현 가능
        logger.debug(f"계정 비활성화 정리 작업: user_id={account.user_id}")
        pass

    def account_register_from_env(self) -> Optional[AccountResponse]:
        """
        환경변수로부터 계정을 자동 등록

        Returns:
            Optional[AccountResponse]: 등록된 계정 정보 또는 None
        """
        try:
            logger.info("환경변수 기반 계정 자동 등록 시도")

            # 환경변수에서 계정 정보 로드
            account_data = env_load_account_from_env()

            if not account_data:
                logger.debug("환경변수에 계정 정보가 없거나 검증 실패")
                return None

            # 이미 등록된 계정인지 확인 (user_id 기준)
            existing_account = self.account_get_by_user_id(account_data.user_id)

            if existing_account:
                logger.info(
                    f"환경변수 계정이 이미 등록되어 있음: user_id={account_data.user_id}"
                )

                # 핵심 OAuth 식별자 비교 (email, tenant_id, client_id, client_secret)
                # 이 중 하나라도 다르면 완전히 다른 계정으로 간주하여 새 계정 생성
                oauth_identity_changed = (
                    str(existing_account.email) != str(account_data.email) or
                    existing_account.oauth_tenant_id != account_data.oauth_tenant_id or
                    existing_account.oauth_client_id != account_data.oauth_client_id
                )

                # client_secret은 암호화되어 있어서 직접 비교 불가
                # 일단 다른 식별자가 다르면 새 계정으로 간주
                if oauth_identity_changed:
                    logger.warning(
                        f"⚠️ OAuth 식별자가 변경되었습니다 - 새 계정으로 등록합니다:\n"
                        f"   기존 email: {existing_account.email}\n"
                        f"   신규 email: {account_data.email}\n"
                        f"   기존 tenant_id: {existing_account.oauth_tenant_id}\n"
                        f"   신규 tenant_id: {account_data.oauth_tenant_id}\n"
                        f"   기존 client_id: {existing_account.oauth_client_id}\n"
                        f"   신규 client_id: {account_data.oauth_client_id}"
                    )

                    # 기존 계정 비활성화 (선택적)
                    logger.info(f"기존 계정 유지: user_id={existing_account.user_id}")

                    # 새로운 user_id 생성 (타임스탬프 추가)
                    import time
                    new_user_id = f"{account_data.user_id}_{int(time.time())}"
                    logger.info(f"새 user_id 생성: {new_user_id}")

                    # 새 계정 데이터 생성
                    from .account_schema import AccountCreate
                    new_account_data = AccountCreate(
                        user_id=new_user_id,
                        user_name=account_data.user_name,
                        email=account_data.email,
                        enrollment_file_path="<ENV_AUTO_REGISTERED>",
                        enrollment_file_hash="<ENV_AUTO_REGISTERED>",
                        oauth_client_id=account_data.oauth_client_id,
                        oauth_client_secret=account_data.oauth_client_secret,
                        oauth_tenant_id=account_data.oauth_tenant_id,
                        oauth_redirect_uri=account_data.oauth_redirect_uri,
                        auth_type=account_data.auth_type,
                        delegated_permissions=account_data.delegated_permissions,
                        status=account_data.status,
                    )

                    # 새 계정 등록
                    new_account_id = self.repository.account_create_from_enrollment(new_account_data)
                    new_account = self.repository.account_get_by_id(new_account_id)

                    logger.info(
                        f"✅ OAuth 식별자 변경으로 새 계정 생성 완료: user_id={new_user_id}, "
                        f"account_id={new_account_id}"
                    )
                    return new_account

                # 모든 설정 필드 변경 여부 확인
                # 하나라도 다르면 업데이트 수행
                changes = []

                if existing_account.user_name != account_data.user_name:
                    changes.append(
                        f"user_name: {existing_account.user_name} → {account_data.user_name}"
                    )
                if existing_account.oauth_redirect_uri != account_data.oauth_redirect_uri:
                    changes.append(
                        f"redirect_uri: {existing_account.oauth_redirect_uri} → {account_data.oauth_redirect_uri}"
                    )
                if existing_account.delegated_permissions != account_data.delegated_permissions:
                    changes.append(
                        f"permissions: {existing_account.delegated_permissions} → {account_data.delegated_permissions}"
                    )

                # 변경사항이 있으면 업데이트
                if changes:
                    logger.warning(
                        f"⚠️ 계정 설정이 변경되었습니다:\n   " + "\n   ".join(changes)
                    )
                    logger.info("환경변수 기반 계정 정보로 업데이트합니다...")

                    # delegated_permissions scope 검증
                    from ._scope_validator import validate_delegated_scope

                    permissions_str = account_data.delegated_permissions
                    if isinstance(account_data.delegated_permissions, list):
                        permissions_str = ' '.join(account_data.delegated_permissions)

                    is_valid, valid_scopes, invalid_scopes = validate_delegated_scope(permissions_str)

                    if not is_valid:
                        logger.warning(
                            f"⚠️ 환경변수에 허용되지 않은 scope 발견: {invalid_scopes}\n"
                            f"   허용된 scope만 사용합니다: {valid_scopes}"
                        )

                    # 계정 업데이트 (검증된 권한만 사용)
                    update_data = AccountUpdate(
                        user_name=account_data.user_name,
                        oauth_client_id=account_data.oauth_client_id,
                        oauth_client_secret=account_data.oauth_client_secret,
                        oauth_tenant_id=account_data.oauth_tenant_id,
                        oauth_redirect_uri=account_data.oauth_redirect_uri,
                        delegated_permissions=valid_scopes,
                    )

                    # Repository를 통해 직접 업데이트
                    self.repository.account_update_by_id(existing_account.id, update_data)

                    # YAML 파일도 업데이트 (검증된 scope만 사용)
                    import yaml
                    import traceback
                    yaml_path = existing_account.enrollment_file_path
                    if yaml_path and yaml_path != "<ENV_AUTO_REGISTERED>":
                        try:
                            with open(yaml_path, 'r') as f:
                                yaml_data = yaml.safe_load(f)

                            # 변경된 내용 업데이트 (검증된 권한만 저장)
                            yaml_data['oauth']['redirect_uri'] = account_data.oauth_redirect_uri
                            yaml_data['oauth']['delegated_permissions'] = valid_scopes
                            yaml_data['account']['name'] = account_data.user_name

                            logger.warning(f"📝 YAML 파일 업데이트 시작:")
                            logger.warning(f"   ├─ 파일 경로: {yaml_path}")
                            logger.warning(f"   ├─ 호출 함수: account_register_from_env")
                            logger.warning(f"   └─ 이유: 환경변수 설정 변경 감지")

                            # 호출 스택 출력
                            stack = traceback.extract_stack()
                            logger.warning(f"📋 호출 스택 추적 (최근 5개):")
                            for i, frame in enumerate(stack[-5:], 1):
                                logger.warning(f"   [{i}] {frame.filename}:{frame.lineno} in {frame.name}")

                            with open(yaml_path, 'w') as f:
                                yaml.safe_dump(yaml_data, f, allow_unicode=True, sort_keys=False)

                            logger.warning(f"✅ YAML 파일 업데이트 완료: {yaml_path}")
                        except Exception as e:
                            logger.warning(f"⚠️ YAML 파일 업데이트 실패: {e}")

                    # 업데이트된 계정 조회
                    updated_account = self.account_get_by_user_id(account_data.user_id)
                    logger.info(f"✅ 환경변수 기반 계정 업데이트 완료: user_id={account_data.user_id}")
                    return updated_account

                # 변경사항이 없으면 기존 계정 반환
                logger.debug(
                    f"계정 설정 변경사항 없음: user_id={account_data.user_id}, "
                    f"status={existing_account.status}, "
                    f"has_valid_token={existing_account.has_valid_token}"
                )
                return existing_account

            # 새 계정 등록
            account_id = self.repository.account_create_from_enrollment(account_data)

            # 등록된 계정 조회
            new_account = self.repository.account_get_by_id(account_id)

            logger.info(
                f"✅ 환경변수 기반 계정 등록 완료: user_id={account_data.user_id}, "
                f"account_id={account_id}"
            )

            return new_account

        except ValidationError as e:
            logger.error(f"환경변수 계정 등록 검증 오류: {str(e)}")
            return None
        except DatabaseError as e:
            logger.error(f"환경변수 계정 등록 DB 오류: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"환경변수 계정 등록 오류: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def account_get_health_status(self) -> Dict[str, Any]:
        """
        Account 모듈의 상태 확인

        Returns:
            Dict: 모듈 상태 정보
        """
        try:
            status = {
                "module": "account",
                "status": "healthy",
                "timestamp": datetime.now(timezone.utc),
                "components": {"repository": "healthy", "sync_service": "healthy"},
                "statistics": {},
            }

            # 간단한 상태 체크 (실제 DB 쿼리 수행)
            try:
                # 임의 user_id로 조회 시도 (존재하지 않아도 됨)
                self.repository.account_get_by_user_id("health_check_dummy")
                status["components"]["repository"] = "healthy"
            except Exception as e:
                status["components"]["repository"] = f"error: {str(e)}"
                status["status"] = "degraded"

            return status

        except Exception as e:
            logger.error(f"상태 확인 오류: {e}")
            return {
                "module": "account",
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc),
            }
