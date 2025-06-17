"""계정 상태 조회 및 관리 서비스"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from infra.core.logger import get_logger
from infra.core.database import get_database_manager
from infra.core.token_service import get_token_service
from modules.account._account_helpers import AccountCryptoHelpers


class AuthAccountService:
    """계정 인증 상태 관리 서비스"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.db = get_database_manager()
        self.token_service = get_token_service()
        self.crypto_helper = AccountCryptoHelpers()
    
    async def get_oauth_config(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        계정별 OAuth 설정을 가져옵니다.
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            OAuth 설정 딕셔너리 또는 None
        """
        try:
            self.logger.debug(f"계정별 OAuth 설정 조회: user_id={user_id}")
            
            account = self.db.fetch_one(
                """
                SELECT oauth_client_id, oauth_client_secret, oauth_tenant_id, 
                       oauth_redirect_uri, delegated_permissions
                FROM accounts 
                WHERE user_id = ? AND is_active = 1
                """,
                (user_id,)
            )
            
            if not account:
                self.logger.debug(f"계정을 찾을 수 없음: user_id={user_id}")
                return None
            
            account_dict = dict(account)
            
            # OAuth 클라이언트 ID 확인
            if not account_dict.get("oauth_client_id"):
                self.logger.debug(f"OAuth 설정이 없음: user_id={user_id}")
                return None
            
            # 클라이언트 시크릿 복호화
            if account_dict.get("oauth_client_secret"):
                try:
                    decrypted_secret = self.crypto_helper.account_decrypt_sensitive_data(
                        account_dict["oauth_client_secret"]
                    )
                    account_dict["oauth_client_secret"] = decrypted_secret
                    self.logger.debug(f"클라이언트 시크릿 복호화 완료: user_id={user_id}")
                except Exception as e:
                    self.logger.error(f"클라이언트 시크릿 복호화 실패: {str(e)}")
                    return None
            
            self.logger.info(
                f"OAuth 설정 조회 성공: user_id={user_id}, "
                f"client_id={account_dict['oauth_client_id'][:8]}..."
            )
            
            return account_dict
            
        except Exception as e:
            self.logger.error(f"OAuth 설정 조회 실패: user_id={user_id}, error={str(e)}")
            return None
    
    async def requires_authentication(self, user_id: str) -> bool:
        """
        사용자가 재인증이 필요한지 확인합니다.
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            재인증 필요 여부
        """
        try:
            # 토큰 서비스를 통해 인증 상태 확인
            auth_status = await self.token_service.check_authentication_status(user_id)
            
            requires_reauth = auth_status.get("requires_reauth", True)
            
            if requires_reauth:
                self.logger.info(f"재인증 필요: user_id={user_id}")
            else:
                self.logger.info(f"유효한 토큰 보유: user_id={user_id}")
            
            return requires_reauth
            
        except Exception as e:
            self.logger.error(f"인증 상태 확인 실패: user_id={user_id}, error={str(e)}")
            return True  # 오류 시 재인증 필요로 처리
    
    async def get_all_accounts(self) -> List[Dict[str, Any]]:
        """
        모든 계정 정보를 조회합니다.
        
        Returns:
            계정 목록
        """
        try:
            accounts = self.db.fetch_all(
                """
                SELECT user_id, user_name, status, token_expiry, 
                       last_sync_time, is_active, created_at, updated_at
                FROM accounts 
                ORDER BY updated_at DESC
                """
            )
            
            account_list = []
            for account in accounts:
                account_dict = dict(account)
                
                # datetime 문자열을 datetime 객체로 변환
                if account_dict.get("token_expiry") and isinstance(account_dict["token_expiry"], str):
                    account_dict["token_expiry"] = datetime.fromisoformat(account_dict["token_expiry"])
                
                if account_dict.get("last_sync_time") and isinstance(account_dict["last_sync_time"], str):
                    account_dict["last_sync_time"] = datetime.fromisoformat(account_dict["last_sync_time"])
                
                account_list.append(account_dict)
            
            self.logger.info(f"전체 계정 조회: {len(account_list)}개")
            return account_list
            
        except Exception as e:
            self.logger.error(f"계정 조회 실패: {str(e)}")
            return []
    
    def is_token_expired(self, account: Dict[str, Any]) -> bool:
        """
        토큰 만료 여부를 확인합니다.
        
        Args:
            account: 계정 정보
            
        Returns:
            만료 여부
        """
        expiry_time = account.get("token_expiry")
        
        if not expiry_time:
            return True
        
        if isinstance(expiry_time, str):
            expiry_time = datetime.fromisoformat(expiry_time)
        
        return datetime.utcnow() >= expiry_time
    
    async def update_account_tokens(
        self, 
        user_id: str, 
        token_info: Dict[str, Any]
    ) -> int:
        """
        계정의 토큰 정보를 업데이트합니다.
        
        Args:
            user_id: 사용자 ID
            token_info: 토큰 정보
            
        Returns:
            계정 ID
        """
        try:
            # 토큰 서비스를 통해 저장
            account_id = await self.token_service.store_tokens(
                user_id=user_id,
                token_info=token_info
            )
            
            self.logger.info(f"토큰 저장 완료: user_id={user_id}, account_id={account_id}")
            return account_id
            
        except Exception as e:
            self.logger.error(f"토큰 저장 실패: user_id={user_id}, error={str(e)}")
            raise