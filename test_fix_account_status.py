#!/usr/bin/env python3
"""
계정 상태 수정 및 토큰 서비스 문제 해결
"""

import asyncio
from datetime import datetime
from infra.core.database import get_database_manager
from infra.core.token_service import get_token_service

async def fix_account_status():
    """계정 상태를 수정하고 토큰 서비스 문제를 해결합니다."""
    print("=" * 60)
    print("계정 상태 수정 및 토큰 서비스 문제 해결")
    print("=" * 60)
    
    db = get_database_manager()
    token_service = get_token_service()
    
    try:
        # 1. 현재 계정 상태 확인
        print("\n1. 현재 계정 상태 확인...")
        account = db.fetch_one(
            """
            SELECT user_id, status, access_token, refresh_token, token_expiry
            FROM accounts 
            WHERE user_id = ?
            """,
            ("kimghw",)
        )
        
        if not account:
            print("❌ kimghw 계정을 찾을 수 없습니다.")
            return
        
        account_dict = dict(account)
        print(f"현재 상태: {account_dict['status']}")
        print(f"토큰 만료: {account_dict['token_expiry']}")
        
        # 2. 계정 상태를 ACTIVE로 변경
        print("\n2. 계정 상태를 ACTIVE로 변경...")
        db.execute_query(
            """
            UPDATE accounts 
            SET status = 'ACTIVE', updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
            """,
            ("kimghw",),
            fetch_result=False
        )
        print("✅ 계정 상태가 ACTIVE로 변경되었습니다.")
        
        # 3. 변경된 상태 확인
        print("\n3. 변경된 상태 확인...")
        updated_account = db.fetch_one(
            """
            SELECT user_id, status, access_token IS NOT NULL as has_token, token_expiry
            FROM accounts 
            WHERE user_id = ?
            """,
            ("kimghw",)
        )
        
        updated_dict = dict(updated_account)
        print(f"변경된 상태: {updated_dict['status']}")
        print(f"토큰 존재: {updated_dict['has_token']}")
        print(f"토큰 만료: {updated_dict['token_expiry']}")
        
        # 4. 토큰 만료 시간 확인
        print("\n4. 토큰 만료 시간 확인...")
        if updated_dict['token_expiry']:
            expiry_str = updated_dict['token_expiry']
            try:
                if isinstance(expiry_str, str):
                    expiry_time = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
                else:
                    expiry_time = expiry_str
                
                current_time = datetime.now()
                time_diff = expiry_time - current_time
                
                print(f"만료 시간: {expiry_time}")
                print(f"현재 시간: {current_time}")
                print(f"남은 시간: {time_diff}")
                
                is_expired = time_diff.total_seconds() <= 0
                print(f"만료 여부: {'만료됨' if is_expired else '유효함'}")
                
                if is_expired:
                    print("⚠️ 토큰이 만료되었습니다. 재인증이 필요합니다.")
                else:
                    print("✅ 토큰이 아직 유효합니다.")
                    
            except Exception as e:
                print(f"만료 시간 파싱 오류: {str(e)}")
        
        # 5. token_service로 다시 확인
        print("\n5. token_service로 상태 재확인...")
        try:
            auth_status = await token_service.check_authentication_status("kimghw")
            print(f"인증 상태: {auth_status}")
            
            if not auth_status.get("requires_reauth", True):
                print("✅ 토큰 서비스에서 인증 상태가 정상입니다.")
                
                # 유효한 토큰 가져오기 시도
                valid_token = await token_service.get_valid_access_token("kimghw")
                if valid_token:
                    print(f"✅ 유효한 토큰 획득: {valid_token[:20]}...")
                else:
                    print("❌ 유효한 토큰을 가져올 수 없습니다.")
            else:
                print("⚠️ 여전히 재인증이 필요합니다.")
                print(f"오류 메시지: {auth_status.get('message', 'N/A')}")
                
        except Exception as e:
            print(f"❌ 토큰 서비스 확인 실패: {str(e)}")
        
        # 6. 전체 계정 목록 최종 확인
        print("\n6. 전체 계정 목록 최종 확인...")
        all_accounts = db.fetch_all(
            """
            SELECT user_id, status, is_active, 
                   CASE WHEN access_token IS NOT NULL THEN 'YES' ELSE 'NO' END as has_token,
                   token_expiry, updated_at
            FROM accounts 
            ORDER BY updated_at DESC
            """
        )
        
        print(f"총 {len(all_accounts)}개 계정:")
        for acc in all_accounts:
            acc_dict = dict(acc)
            print(f"- {acc_dict['user_id']}: {acc_dict['status']} "
                  f"(활성: {acc_dict['is_active']}, 토큰: {acc_dict['has_token']}, "
                  f"수정: {acc_dict['updated_at']})")
        
    except Exception as e:
        print(f"\n❌ 처리 중 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(fix_account_status())
