#!/usr/bin/env python3
"""
Refresh Token을 사용한 토큰 갱신 테스트
"""

import asyncio
from datetime import datetime, timezone
from infra.core.database import get_database_manager
from infra.core.token_service import get_token_service
from infra.core.oauth_client import get_oauth_client

async def test_refresh_token():
    """Refresh Token을 사용하여 토큰을 갱신합니다."""
    print("=" * 60)
    print("Refresh Token을 사용한 토큰 갱신 테스트")
    print("=" * 60)
    
    db = get_database_manager()
    token_service = get_token_service()
    oauth_client = get_oauth_client()
    
    try:
        # 1. 현재 토큰 상태 확인
        print("\n1. 현재 토큰 상태 확인...")
        account = db.fetch_one(
            """
            SELECT user_id, access_token, refresh_token, token_expiry
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
        
        # 토큰 존재 확인
        has_access_token = bool(account_dict['access_token'])
        has_refresh_token = bool(account_dict['refresh_token'])
        
        print(f"Access Token 존재: {has_access_token}")
        print(f"Refresh Token 존재: {has_refresh_token}")
        
        if has_refresh_token:
            refresh_token = account_dict['refresh_token']
            print(f"Refresh Token (앞 20자): {refresh_token[:20]}...")
            print(f"Refresh Token 길이: {len(refresh_token)}")
        
        # 2. 토큰 만료 시간 정확히 확인 (UTC 고려)
        print("\n2. 토큰 만료 시간 정확히 확인 (UTC 고려)...")
        if account_dict['token_expiry']:
            expiry_str = account_dict['token_expiry']
            try:
                if isinstance(expiry_str, str):
                    # UTC 시간으로 파싱
                    expiry_time = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
                    if expiry_time.tzinfo is None:
                        expiry_time = expiry_time.replace(tzinfo=timezone.utc)
                else:
                    expiry_time = expiry_str
                    if expiry_time.tzinfo is None:
                        expiry_time = expiry_time.replace(tzinfo=timezone.utc)
                
                # 현재 시간도 UTC로
                current_time = datetime.now(timezone.utc)
                time_diff = expiry_time - current_time
                
                print(f"만료 시간 (UTC): {expiry_time}")
                print(f"현재 시간 (UTC): {current_time}")
                print(f"시간 차이: {time_diff}")
                
                is_expired = time_diff.total_seconds() <= 0
                print(f"만료 여부: {'만료됨' if is_expired else '유효함'}")
                
                if not is_expired:
                    print(f"✅ 토큰이 아직 {time_diff} 남았습니다!")
                    
                    # 유효한 토큰이면 바로 사용 가능한지 확인
                    print("\n3. 유효한 토큰으로 Graph API 테스트...")
                    is_valid = await oauth_client.validate_token(account_dict['access_token'])
                    print(f"Graph API 검증 결과: {'유효함' if is_valid else '무효함'}")
                    
                    if is_valid:
                        print("🎉 현재 토큰이 완전히 유효합니다! 갱신 불필요!")
                        return
                
            except Exception as e:
                print(f"만료 시간 파싱 오류: {str(e)}")
        
        # 3. Refresh Token으로 토큰 갱신 시도
        if has_refresh_token:
            print("\n3. Refresh Token으로 토큰 갱신 시도...")
            try:
                refresh_token = account_dict['refresh_token']
                print(f"사용할 Refresh Token: {refresh_token[:30]}...")
                
                # OAuth 클라이언트를 통해 토큰 갱신
                new_token_info = await oauth_client.refresh_access_token(refresh_token)
                
                if new_token_info:
                    print("✅ 토큰 갱신 성공!")
                    print(f"새 Access Token (앞 20자): {new_token_info.get('access_token', '')[:20]}...")
                    print(f"새 토큰 만료 시간: {new_token_info.get('expires_in', 0)}초 후")
                    
                    # 4. 갱신된 토큰을 데이터베이스에 저장
                    print("\n4. 갱신된 토큰을 데이터베이스에 저장...")
                    account_id = await token_service.store_tokens(
                        user_id="kimghw",
                        token_info=new_token_info,
                        user_name="kimghw"
                    )
                    print(f"✅ 토큰 저장 완료: account_id={account_id}")
                    
                    # 5. 갱신된 토큰 검증
                    print("\n5. 갱신된 토큰 검증...")
                    is_valid = await oauth_client.validate_token(new_token_info['access_token'])
                    print(f"새 토큰 Graph API 검증: {'유효함' if is_valid else '무효함'}")
                    
                    if is_valid:
                        print("🎉 토큰 갱신 및 검증 완료!")
                    
                else:
                    print("❌ 토큰 갱신 실패: 응답이 없음")
                    
            except Exception as e:
                print(f"❌ 토큰 갱신 실패: {str(e)}")
                import traceback
                traceback.print_exc()
        else:
            print("\n❌ Refresh Token이 없어서 갱신할 수 없습니다.")
        
        # 6. token_service를 통한 자동 갱신 테스트
        print("\n6. token_service를 통한 자동 갱신 테스트...")
        try:
            valid_token = await token_service.get_valid_access_token("kimghw")
            if valid_token:
                print(f"✅ token_service에서 유효한 토큰 획득: {valid_token[:20]}...")
                
                # 최종 검증
                is_valid = await oauth_client.validate_token(valid_token)
                print(f"최종 토큰 검증: {'유효함' if is_valid else '무효함'}")
            else:
                print("❌ token_service에서 유효한 토큰을 가져올 수 없습니다.")
                
        except Exception as e:
            print(f"❌ token_service 자동 갱신 실패: {str(e)}")
        
        # 7. 최종 상태 확인
        print("\n7. 최종 토큰 상태 확인...")
        final_account = db.fetch_one(
            """
            SELECT user_id, status, token_expiry, updated_at,
                   CASE WHEN access_token IS NOT NULL THEN 'YES' ELSE 'NO' END as has_token
            FROM accounts 
            WHERE user_id = ?
            """,
            ("kimghw",)
        )
        
        if final_account:
            final_dict = dict(final_account)
            print(f"최종 상태: {final_dict['status']}")
            print(f"토큰 존재: {final_dict['has_token']}")
            print(f"토큰 만료: {final_dict['token_expiry']}")
            print(f"마지막 업데이트: {final_dict['updated_at']}")
        
    except Exception as e:
        print(f"\n❌ 테스트 중 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_refresh_token())
