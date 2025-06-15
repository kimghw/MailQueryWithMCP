"""
IACSGraph 프로젝트의 토큰 관리 서비스

데이터베이스와 연동하여 사용자별 토큰을 관리하고, 만료 시 자동으로 갱신하는 서비스입니다.
OAuth 클라이언트와 함께 작동하여 안전한 토큰 라이프사이클을 제공합니다.
"""

import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from functools import lru_cache

from .config import get_config
from .database import get_database_manager
from .oauth_client import get_oauth_client
from .exceptions import (
    DatabaseError, 
    TokenError, 
    TokenExpiredError, 
    TokenRefreshError,
    AuthenticationError
)
from .logger import get_logger

logger = get_logger(__name__)


class TokenService:
    """사용자별 토큰을 관리하는 서비스"""

    def __init__(self):
        """토큰 서비스 초기화"""
        self.config = get_config()
        self.db = get_database_manager()
        self.oauth_client = get_oauth_client()

    async def store_tokens(
        self, 
        user_id: str, 
        token_info: Dict[str, Any],
        user_name: Optional[str] = None
    ) -> int:
        """
        사용자 토큰을 데이터베이스에 저장합니다.
        
        Args:
            user_id: 사용자 ID
            token_info: 토큰 정보 딕셔너리
            user_name: 사용자 이름
            
        Returns:
            계정 ID
        """
        try:
            # 기존 계정 확인
            existing_account = self.db.fetch_one(
                "SELECT id FROM accounts WHERE user_id = ?",
                (user_id,)
            )

            access_token = token_info.get("access_token")
            refresh_token = token_info.get("refresh_token")
            expiry_time = token_info.get("expiry_time")
            
            if isinstance(expiry_time, datetime):
                expiry_time = expiry_time.isoformat()

            # 유효한 토큰이 있으면 상태를 ACTIVE로, 없으면 INACTIVE로 설정
            status = "ACTIVE" if access_token and refresh_token else "INACTIVE"

            account_data = {
                "user_id": user_id,
                "user_name": user_name or user_id,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_expiry": expiry_time,
                "status": status,
                "is_active": True,
                "updated_at": datetime.utcnow().isoformat()
            }

            if existing_account:
                # 기존 계정 업데이트
                account_id = existing_account["id"]
                self.db.update(
                    table="accounts",
                    data=account_data,
                    where_clause="id = ?",
                    where_params=(account_id,)
                )
                logger.info(f"기존 계정 토큰 업데이트: user_id={user_id}, status={status}")
            else:
                # 새 계정 생성 - 최초 등록시 INACTIVE 상태로 설정
                account_data["status"] = "INACTIVE"
                account_data["created_at"] = datetime.utcnow().isoformat()
                account_id = self.db.insert("accounts", account_data)
                logger.info(f"새 계정 생성: user_id={user_id}, account_id={account_id}, status=INACTIVE")

            return account_id

        except Exception as e:
            raise DatabaseError(
                f"토큰 저장 실패: {str(e)}",
                operation="store_tokens",
                table="accounts",
                details={"user_id": user_id}
            ) from e

    async def get_valid_access_token(self, user_id: str) -> Optional[str]:
        """
        유효한 액세스 토큰을 반환합니다. 필요시 자동으로 갱신합니다.
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            유효한 액세스 토큰 또는 None
        """
        try:
            # 계정 정보 조회 (status 필드 포함)
            account = self.db.fetch_one(
                """
                SELECT id, user_id, user_name, access_token, refresh_token, 
                       token_expiry, is_active, status
                FROM accounts 
                WHERE user_id = ? AND is_active = 1
                """,
                (user_id,)
            )

            if not account:
                logger.warning(f"계정을 찾을 수 없음: user_id={user_id}")
                return None

            # 토큰 만료 확인
            expiry_time = account["token_expiry"]
            if expiry_time:
                if isinstance(expiry_time, str):
                    expiry_time = datetime.fromisoformat(expiry_time)
                
                # 토큰이 아직 유효한 경우
                if datetime.utcnow() < expiry_time:
                    # 계정 상태를 ACTIVE로 업데이트
                    await self.update_account_status(user_id, "ACTIVE")
                    logger.debug(f"유효한 액세스 토큰 반환: user_id={user_id}")
                    return account["access_token"]

            # 토큰이 만료된 경우 갱신 시도
            refresh_token = account["refresh_token"]
            if not refresh_token:
                logger.warning(f"리프레시 토큰이 없음: user_id={user_id}")
                await self.update_account_status(user_id, "INACTIVE")
                return None

            logger.info(f"토큰 갱신 시도: user_id={user_id}")
            new_token_info = await self.oauth_client.refresh_access_token(refresh_token)
            
            # 갱신된 토큰 저장
            await self.store_tokens(
                user_id=user_id,
                token_info=new_token_info,
                user_name=account["user_name"]
            )

            # 계정 상태를 ACTIVE로 업데이트
            await self.update_account_status(user_id, "ACTIVE")
            logger.info(f"토큰 갱신 성공: user_id={user_id}")
            return new_token_info["access_token"]

        except TokenExpiredError:
            # 리프레시 토큰도 만료된 경우
            logger.warning(f"리프레시 토큰 만료: user_id={user_id}")
            await self.update_account_status(user_id, "REAUTH_REQUIRED")
            await self.deactivate_account(user_id)
            return None
            
        except Exception as e:
            logger.error(f"토큰 조회/갱신 실패: user_id={user_id}, error={str(e)}")
            return None

    async def validate_and_refresh_token(self, user_id: str) -> Dict[str, Any]:
        """
        토큰을 검증하고 필요시 갱신합니다.
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            토큰 상태 정보
        """
        try:
            access_token = await self.get_valid_access_token(user_id)
            
            if not access_token:
                return {
                    "status": "invalid",
                    "message": "유효한 토큰이 없습니다. 재인증이 필요합니다.",
                    "requires_reauth": True
                }

            # 토큰 유효성 검증
            try:
                user_info = await self.oauth_client.validate_token(access_token)
                return {
                    "status": "valid",
                    "access_token": access_token,
                    "user_info": user_info,
                    "requires_reauth": False
                }
            except TokenExpiredError:
                # 액세스 토큰이 유효하지 않은 경우 재갱신 시도
                logger.info(f"액세스 토큰 재검증 실패, 강제 갱신: user_id={user_id}")
                await self.force_token_refresh(user_id)
                
                new_access_token = await self.get_valid_access_token(user_id)
                if new_access_token:
                    user_info = await self.oauth_client.validate_token(new_access_token)
                    return {
                        "status": "refreshed",
                        "access_token": new_access_token,
                        "user_info": user_info,
                        "requires_reauth": False
                    }
                else:
                    return {
                        "status": "invalid",
                        "message": "토큰 갱신에 실패했습니다. 재인증이 필요합니다.",
                        "requires_reauth": True
                    }

        except Exception as e:
            logger.error(f"토큰 검증 실패: user_id={user_id}, error={str(e)}")
            return {
                "status": "error",
                "message": f"토큰 검증 중 오류 발생: {str(e)}",
                "requires_reauth": True
            }

    async def force_token_refresh(self, user_id: str) -> bool:
        """
        강제로 토큰을 갱신합니다.
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            갱신 성공 여부
        """
        try:
            account = self.db.fetch_one(
                "SELECT refresh_token, user_name FROM accounts WHERE user_id = ? AND is_active = 1",
                (user_id,)
            )

            if not account or not account["refresh_token"]:
                logger.warning(f"갱신할 토큰이 없음: user_id={user_id}")
                return False

            new_token_info = await self.oauth_client.refresh_access_token(
                account["refresh_token"]
            )
            
            await self.store_tokens(
                user_id=user_id,
                token_info=new_token_info,
                user_name=account["user_name"]
            )

            logger.info(f"강제 토큰 갱신 성공: user_id={user_id}")
            return True

        except TokenExpiredError:
            logger.warning(f"리프레시 토큰 만료로 강제 갱신 실패: user_id={user_id}")
            await self.deactivate_account(user_id)
            return False
        except Exception as e:
            logger.error(f"강제 토큰 갱신 실패: user_id={user_id}, error={str(e)}")
            return False

    async def deactivate_account(self, user_id: str) -> bool:
        """
        계정을 비활성화합니다.
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            비활성화 성공 여부
        """
        try:
            rows_affected = self.db.update(
                table="accounts",
                data={
                    "is_active": False,
                    "updated_at": datetime.utcnow().isoformat()
                },
                where_clause="user_id = ?",
                where_params=(user_id,)
            )

            if rows_affected > 0:
                logger.info(f"계정 비활성화: user_id={user_id}")
                return True
            else:
                logger.warning(f"비활성화할 계정을 찾을 수 없음: user_id={user_id}")
                return False

        except Exception as e:
            logger.error(f"계정 비활성화 실패: user_id={user_id}, error={str(e)}")
            return False

    async def get_account_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        계정 정보를 조회합니다.
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            계정 정보 딕셔너리 또는 None
        """
        try:
            account = self.db.fetch_one(
                """
                SELECT id, user_id, user_name, token_expiry, is_active, 
                       last_sync_time, created_at, updated_at
                FROM accounts 
                WHERE user_id = ?
                """,
                (user_id,)
            )

            if account:
                account_dict = dict(account)
                
                # 토큰 만료 상태 확인
                expiry_time = account_dict.get("token_expiry")
                if expiry_time:
                    if isinstance(expiry_time, str):
                        expiry_time = datetime.fromisoformat(expiry_time)
                    account_dict["token_expired"] = datetime.utcnow() >= expiry_time
                else:
                    account_dict["token_expired"] = True

                return account_dict
            
            return None

        except Exception as e:
            logger.error(f"계정 정보 조회 실패: user_id={user_id}, error={str(e)}")
            return None

    async def get_all_active_accounts(self) -> List[Dict[str, Any]]:
        """
        모든 활성 계정을 조회합니다.
        
        Returns:
            활성 계정 목록
        """
        try:
            accounts = self.db.fetch_all(
                """
                SELECT id, user_id, user_name, token_expiry, last_sync_time, 
                       created_at, updated_at
                FROM accounts 
                WHERE is_active = 1
                ORDER BY updated_at DESC
                """
            )

            account_list = []
            for account in accounts:
                account_dict = dict(account)
                
                # 토큰 만료 상태 확인
                expiry_time = account_dict.get("token_expiry")
                if expiry_time:
                    if isinstance(expiry_time, str):
                        expiry_time = datetime.fromisoformat(expiry_time)
                    account_dict["token_expired"] = datetime.utcnow() >= expiry_time
                else:
                    account_dict["token_expired"] = True

                account_list.append(account_dict)

            return account_list

        except Exception as e:
            logger.error(f"활성 계정 목록 조회 실패: {str(e)}")
            return []

    async def update_last_sync_time(self, user_id: str) -> bool:
        """
        마지막 동기화 시간을 업데이트합니다.
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            업데이트 성공 여부
        """
        try:
            rows_affected = self.db.update(
                table="accounts",
                data={
                    "last_sync_time": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                },
                where_clause="user_id = ? AND is_active = 1",
                where_params=(user_id,)
            )

            if rows_affected > 0:
                logger.debug(f"마지막 동기화 시간 업데이트: user_id={user_id}")
                return True
            else:
                logger.warning(f"동기화 시간 업데이트할 계정을 찾을 수 없음: user_id={user_id}")
                return False

        except Exception as e:
            logger.error(f"동기화 시간 업데이트 실패: user_id={user_id}, error={str(e)}")
            return False

    async def cleanup_expired_tokens(self) -> int:
        """
        만료된 토큰을 정리합니다.
        
        Returns:
            정리된 계정 수
        """
        try:
            # 30일 이상 된 비활성 계정들을 찾아서 토큰 정보 삭제
            cutoff_date = (datetime.utcnow() - timedelta(days=30)).isoformat()
            
            rows_affected = self.db.update(
                table="accounts",
                data={
                    "access_token": None,
                    "refresh_token": None,
                    "token_expiry": None,
                    "updated_at": datetime.utcnow().isoformat()
                },
                where_clause="is_active = 0 AND updated_at < ?",
                where_params=(cutoff_date,)
            )

            if rows_affected > 0:
                logger.info(f"만료된 토큰 정리 완료: {rows_affected}개 계정")
            
            return rows_affected

        except Exception as e:
            logger.error(f"토큰 정리 실패: {str(e)}")
            return 0

    async def revoke_tokens(self, user_id: str) -> bool:
        """
        사용자 토큰을 무효화합니다.
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            무효화 성공 여부
        """
        try:
            rows_affected = self.db.update(
                table="accounts",
                data={
                    "access_token": None,
                    "refresh_token": None,
                    "token_expiry": None,
                    "status": "INACTIVE",
                    "is_active": False,
                    "updated_at": datetime.utcnow().isoformat()
                },
                where_clause="user_id = ?",
                where_params=(user_id,)
            )

            if rows_affected > 0:
                logger.info(f"토큰 무효화 완료: user_id={user_id}")
                return True
            else:
                logger.warning(f"무효화할 토큰을 찾을 수 없음: user_id={user_id}")
                return False

        except Exception as e:
            logger.error(f"토큰 무효화 실패: user_id={user_id}, error={str(e)}")
            return False

    async def update_account_status(self, user_id: str, status: str) -> bool:
        """
        계정 상태를 업데이트합니다.
        
        Args:
            user_id: 사용자 ID
            status: 새로운 상태 (ACTIVE, INACTIVE, LOCKED, REAUTH_REQUIRED)
            
        Returns:
            업데이트 성공 여부
        """
        try:
            rows_affected = self.db.update(
                table="accounts",
                data={
                    "status": status,
                    "updated_at": datetime.utcnow().isoformat()
                },
                where_clause="user_id = ?",
                where_params=(user_id,)
            )

            if rows_affected > 0:
                logger.debug(f"계정 상태 업데이트: user_id={user_id}, status={status}")
                return True
            else:
                logger.warning(f"상태 업데이트할 계정을 찾을 수 없음: user_id={user_id}")
                return False

        except Exception as e:
            logger.error(f"계정 상태 업데이트 실패: user_id={user_id}, error={str(e)}")
            return False

    async def check_authentication_status(self, user_id: str) -> Dict[str, Any]:
        """
        계정의 인증 상태를 확인하고 재인증 필요 여부를 판단합니다.
        refresh_token 유효성을 기반으로 status를 업데이트합니다.
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            인증 상태 정보
        """
        try:
            # 계정 정보 조회
            account = self.db.fetch_one(
                """
                SELECT id, user_id, user_name, refresh_token, token_expiry, 
                       status, is_active, created_at
                FROM accounts 
                WHERE user_id = ?
                """,
                (user_id,)
            )

            if not account:
                return {
                    "user_id": user_id,
                    "status": "NOT_FOUND",
                    "requires_reauth": True,
                    "message": "계정을 찾을 수 없습니다."
                }

            current_status = account["status"] if account["status"] else "INACTIVE"
            refresh_token = account["refresh_token"]
            
            # refresh_token이 없는 경우
            if not refresh_token:
                await self.update_account_status(user_id, "INACTIVE")
                return {
                    "user_id": user_id,
                    "status": "INACTIVE",
                    "requires_reauth": True,
                    "message": "refresh token이 없습니다. 최초 인증이 필요합니다."
                }

            # refresh_token 유효성 확인
            try:
                # OAuth 클라이언트를 통해 refresh_token 유효성 검증
                new_token_info = await self.oauth_client.refresh_access_token(refresh_token)
                
                # refresh_token이 유효한 경우 - 상태를 ACTIVE로 업데이트
                await self.update_account_status(user_id, "ACTIVE")
                
                # 새로운 토큰 정보 저장
                await self.store_tokens(
                    user_id=user_id,
                    token_info=new_token_info,
                    user_name=account["user_name"]
                )
                
                return {
                    "user_id": user_id,
                    "status": "ACTIVE",
                    "requires_reauth": False,
                    "message": "인증이 유효합니다."
                }
                
            except TokenExpiredError:
                # refresh_token이 만료된 경우
                await self.update_account_status(user_id, "REAUTH_REQUIRED")
                return {
                    "user_id": user_id,
                    "status": "REAUTH_REQUIRED",
                    "requires_reauth": True,
                    "message": "refresh token이 만료되었습니다. 재인증이 필요합니다."
                }
                
        except Exception as e:
            logger.error(f"인증 상태 확인 실패: user_id={user_id}, error={str(e)}")
            await self.update_account_status(user_id, "REAUTH_REQUIRED")
            return {
                "user_id": user_id,
                "status": "ERROR",
                "requires_reauth": True,
                "message": f"인증 상태 확인 중 오류 발생: {str(e)}"
            }

    async def get_accounts_by_status(self, status: str) -> List[Dict[str, Any]]:
        """
        특정 상태의 계정들을 조회합니다.
        
        Args:
            status: 조회할 계정 상태
            
        Returns:
            해당 상태의 계정 목록
        """
        try:
            accounts = self.db.fetch_all(
                """
                SELECT id, user_id, user_name, email, status, token_expiry, 
                       last_sync_time, is_active, created_at, updated_at
                FROM accounts 
                WHERE status = ?
                ORDER BY updated_at DESC
                """,
                (status,)
            )

            account_list = []
            for account in accounts:
                account_dict = dict(account)
                
                # 토큰 만료 상태 확인
                expiry_time = account_dict.get("token_expiry")
                if expiry_time:
                    if isinstance(expiry_time, str):
                        expiry_time = datetime.fromisoformat(expiry_time)
                    account_dict["token_expired"] = datetime.utcnow() >= expiry_time
                else:
                    account_dict["token_expired"] = True
                    
                account_list.append(account_dict)

            return account_list

        except Exception as e:
            logger.error(f"상태별 계정 조회 실패: status={status}, error={str(e)}")
            return []

    async def get_accounts_requiring_reauth(self) -> List[Dict[str, Any]]:
        """
        재인증이 필요한 계정들을 조회합니다.
        
        Returns:
            재인증이 필요한 계정 목록
        """
        return await self.get_accounts_by_status("REAUTH_REQUIRED")

    async def get_inactive_accounts(self) -> List[Dict[str, Any]]:
        """
        비활성 계정들을 조회합니다.
        
        Returns:
            비활성 계정 목록
        """
        return await self.get_accounts_by_status("INACTIVE")


@lru_cache(maxsize=1)
def get_token_service() -> TokenService:
    """
    토큰 서비스 인스턴스를 반환하는 레이지 싱글톤 함수
    
    Returns:
        TokenService: 토큰 서비스 인스턴스
    """
    return TokenService()


# 편의를 위한 전역 토큰 서비스 인스턴스
token_service = get_token_service()
