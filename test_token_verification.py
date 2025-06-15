#!/usr/bin/env python3
"""
토큰 저장 및 유효성 확인 테스트
"""

import asyncio
from datetime import datetime
from infra.core.database import get_database_manager
from infra.core.token_service import get_token_service
from infra.core.oauth_client import get_oauth_client

async def test_token_verification():
    """저장된 토큰 확인 및 검증"""
    print("=" * 60)
    print("토큰 저장 및 유효성 확인 테스트")
    print("=" * 60)
    
    db = get_database_manager()
    token_service = get_token_service()
    oauth_client = get_oauth_client()
    
    try:
        # 1. 데이터베이스에서 토큰 정보 조회
        print("\n1. 데이터베이스 토큰 정보 조회...")
        account = db.fetch_one(
            """
            SELECT user_id, user_name, access_token, refresh_token, token_expiry, 
                   status, is_active, last_sync_time, created_at, updated_at
            FROM accounts 
            WHERE user_id = ?
            """,
            ("kimghw",)
        )
        
        if not account:
            print("❌ kimghw 계정을 찾을 수 없습니다.")
            return
        
        account_dict = dict(account)
        print(f"✅ 계정 발견: {account_dict['user_id']}")
        print(f"   - 사용자명: {account_dict['user_name']}")
        print(f"   - 상태: {account_dict['status']}")
        print(f"   - 활성화: {account_dict['is_active']}")
        print(f"   - 토큰 만료: {account_dict['token_expiry']}")
        print(f"   - 마지막 동기화: {account_dict['last_sync_time']}")
        print(f"   - 생성일: {account_dict['created_at']}")
        print(f"   - 수정일: {account_dict['updated_at']}")
        
        # 토큰 존재 여부 확인
        has_access_token = bool(account_dict['access_token'])
        has_refresh_token = bool(account_dict['refresh_token'])
        
        print(f"   - Access Token 존재: {has_access_token}")
        print(f"   - Refresh Token 존재: {has_refresh_token}")
        
        if has_access_token:
            access_token = account_dict['access_token']
            print(f"   - Access Token (앞 20자): {access_token[:20]}...")
            print(f"   - Access Token 길이: {len(access_token)}")
        
        if has_refresh_token:
            refresh_token = account_dict['refresh_token']
            print(f"   - Refresh Token (앞 20자): {refresh_token[:20]}...")
            print(f"   - Refresh Token 길이: {len(refresh_token)}")
        
        # 2. 토큰 만료 시간 확인
        print("\n2. 토큰 만료 시간 분석...")
        if account_dict['token_expiry']:
            expiry_str = account_dict['token_expiry']
            try:
                if isinstance(expiry_str, str):
                    expiry_time = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
                else:
                    expiry_time = expiry_str
                
                current_time = datetime.utcnow()
                time_diff = expiry_time - current_time
                
                print(f"   - 만료 시간: {expiry_time}")
                print(f"   - 현재 시간: {current_time}")
                print(f"   - 남은 시간: {time_diff}")
                print(f"   - 만료 여부: {'만료됨' if time_diff.total_seconds() <= 0 else '유효함'}")
                
            except Exception as e:
                print(f"   - 만료 시간 파싱 오류: {str(e)}")
        
        # 3. token_service를 통한 토큰 상태 확인
        print("\n3. token_service를 통한 토큰 상태 확인...")
        try:
            auth_status = await token_service.check_authentication_status("kimghw")
            print(f"   - 인증 상태: {auth_status}")
            
            if not auth_status.get("requires_reauth", True):
                print("   ✅ 토큰이 유효합니다.")
                
                # 유효한 액세스 토큰 가져오기
                valid_token = await token_service.get_valid_access_token("kimghw")
                if valid_token:
                    print(f"   - 유효한 토큰 (앞 20자): {valid_token[:20]}...")
                    print(f"   - 유효한 토큰 길이: {len(valid_token)}")
                else:
                    print("   ❌ 유효한 토큰을 가져올 수 없습니다.")
            else:
                print("   ⚠️ 재인증이 필요합니다.")
                
        except Exception as e:
            print(f"   ❌ 토큰 상태 확인 실패: {str(e)}")
        
        # 4. Microsoft Graph API 토큰 검증
        print("\n4. Microsoft Graph API 토큰 검증...")
        if has_access_token:
            try:
                is_valid = await oauth_client.validate_token(account_dict['access_token'])
                print(f"   - Graph API 검증 결과: {'유효함' if is_valid else '무효함'}")
                
                if is_valid:
                    print("   ✅ Microsoft Graph API에서 토큰이 유효함을 확인했습니다.")
                else:
                    print("   ⚠️ Microsoft Graph API에서 토큰이 무효하다고 응답했습니다.")
                    
            except Exception as e:
                print(f"   ❌ Graph API 검증 실패: {str(e)}")
        
        # 5. 전체 계정 목록 확인
        print("\n5. 전체 계정 목록 확인...")
        all_accounts = db.fetch_all(
            """
            SELECT user_id, status, is_active, 
                   CASE WHEN access_token IS NOT NULL THEN 'YES' ELSE 'NO' END as has_token,
                   token_expiry
            FROM accounts 
            ORDER BY updated_at DESC
            """
        )
        
        print(f"   총 {len(all_accounts)}개 계정:")
        for acc in all_accounts:
            acc_dict = dict(acc)
            print(f"   - {acc_dict['user_id']}: {acc_dict['status']} "
                  f"(활성: {acc_dict['is_active']}, 토큰: {acc_dict['has_token']}, "
                  f"만료: {acc_dict['token_expiry']})")
        
    except Exception as e:
        print(f"\n❌ 테스트 중 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_token_verification())
