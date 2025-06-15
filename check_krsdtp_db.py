#!/usr/bin/env python3
"""
데이터베이스에서 krsdtp 계정 정보 확인
"""

from infra.core.database import get_database_manager
from infra.core.logger import get_logger

logger = get_logger(__name__)

def check_krsdtp_account():
    """데이터베이스에서 krsdtp 계정 정보 확인"""
    
    try:
        db = get_database_manager()
        
        print("🔍 krsdtp@krs.co.kr 계정 정보 확인")
        print("=" * 60)
        
        # krsdtp 계정 조회
        account = db.fetch_one(
            """
            SELECT id, user_id, user_name, email, status, 
                   oauth_client_id, oauth_client_secret, oauth_tenant_id, oauth_redirect_uri,
                   access_token, refresh_token, token_expiry, is_active,
                   created_at, updated_at
            FROM accounts 
            WHERE user_id = ?
            """,
            ("krsdtp@krs.co.kr",)
        )
        
        if account:
            account_dict = dict(account)
            print("✅ krsdtp 계정 발견!")
            print(f"   - ID: {account_dict['id']}")
            print(f"   - 사용자 ID: {account_dict['user_id']}")
            print(f"   - 사용자 이름: {account_dict['user_name']}")
            print(f"   - 이메일: {account_dict['email']}")
            print(f"   - 상태: {account_dict['status']}")
            print(f"   - 활성화: {account_dict['is_active']}")
            print()
            
            print("🔐 OAuth 설정:")
            print(f"   - 클라이언트 ID: {account_dict['oauth_client_id'][:8] + '...' if account_dict['oauth_client_id'] else 'None'}")
            print(f"   - 클라이언트 시크릿: {'설정됨' if account_dict['oauth_client_secret'] else 'None'}")
            print(f"   - 테넌트 ID: {account_dict['oauth_tenant_id'][:8] + '...' if account_dict['oauth_tenant_id'] else 'None'}")
            print(f"   - 리다이렉트 URI: {account_dict['oauth_redirect_uri'] or 'None'}")
            print()
            
            print("🎫 토큰 정보:")
            print(f"   - 액세스 토큰: {'있음' if account_dict['access_token'] else 'None'}")
            print(f"   - 리프레시 토큰: {'있음' if account_dict['refresh_token'] else 'None'}")
            print(f"   - 토큰 만료: {account_dict['token_expiry'] or 'None'}")
            print()
            
            print("📅 시간 정보:")
            print(f"   - 생성일: {account_dict['created_at']}")
            print(f"   - 수정일: {account_dict['updated_at']}")
            
            return account_dict
        else:
            print("❌ krsdtp 계정을 찾을 수 없습니다.")
            
            # 모든 계정 목록 확인
            all_accounts = db.fetch_all("SELECT user_id, user_name, status FROM accounts")
            print("\n📋 데이터베이스의 모든 계정:")
            for acc in all_accounts:
                print(f"   - {acc['user_id']} ({acc['user_name']}) - {acc['status']}")
            
            return None
        
    except Exception as e:
        print(f"\n❌ 계정 조회 실패: {str(e)}")
        logger.error(f"krsdtp 계정 조회 실패: {str(e)}", exc_info=True)
        return None

if __name__ == "__main__":
    check_krsdtp_account()
