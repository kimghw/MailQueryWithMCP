#!/usr/bin/env python3
"""DCR 인증 및 GraphAPI 호출 통합 테스트"""

import os
import sys
import json
import sqlite3
import asyncio
from datetime import datetime, timezone
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from infra.core.database import get_database_manager
from modules.enrollment.account import AccountCryptoHelpers

async def test_dcr_tokens():
    """DCR 토큰 상태 확인"""
    print("\n=== DCR 토큰 상태 확인 ===\n")

    dcr_db_path = "./data/claudedcr.db"
    if not Path(dcr_db_path).exists():
        print("❌ claudedcr.db 파일이 없습니다")
        return False

    conn = sqlite3.connect(dcr_db_path)
    cursor = conn.cursor()

    # Azure 토큰 확인
    cursor.execute("""
        SELECT user_email, user_name, expires_at, scope, created_at
        FROM dcr_azure_tokens
        WHERE user_email = ?
        ORDER BY created_at DESC
        LIMIT 1
    """, (os.getenv("AUTO_REGISTER_EMAIL", "testuser@example.com"),))

    result = cursor.fetchone()
    conn.close()

    if result:
        email, name, expires_at, scope, created_at = result
        print(f"✅ DCR Azure 토큰 발견:")
        print(f"  - 이메일: {email}")
        print(f"  - 이름: {name}")
        print(f"  - 만료: {expires_at}")
        print(f"  - 스코프: {scope}")
        print(f"  - 생성: {created_at}")

        # 만료 확인
        if expires_at:
            expiry_dt = datetime.fromisoformat(expires_at)
            if expiry_dt.tzinfo is None:
                expiry_dt = expiry_dt.replace(tzinfo=timezone.utc)

            if expiry_dt > datetime.now(timezone.utc):
                print(f"  - 상태: ✅ 유효")
                return True
            else:
                print(f"  - 상태: ❌ 만료됨")
                return False
    else:
        print("❌ DCR Azure 토큰이 없습니다")
        return False

async def test_accounts_table():
    """accounts 테이블 상태 확인"""
    print("\n=== Accounts 테이블 상태 확인 ===\n")

    db_manager = get_database_manager()
    crypto = AccountCryptoHelpers()

    user_id = os.getenv("AUTO_REGISTER_USER_ID", "testuser")

    account = db_manager.fetch_one("""
        SELECT user_id, email, access_token, refresh_token, token_expiry,
               status, oauth_client_id, last_used_at
        FROM accounts
        WHERE user_id = ?
    """, (user_id,))

    if account:
        print(f"✅ 계정 발견: {account[0]}")
        print(f"  - 이메일: {account[1]}")
        print(f"  - Access Token: {'있음' if account[2] else '없음'}")
        print(f"  - Refresh Token: {'있음' if account[3] else '없음'}")
        print(f"  - 토큰 만료: {account[4]}")
        print(f"  - 상태: {account[5]}")
        print(f"  - Client ID: {account[6][:20]}..." if account[6] else "  - Client ID: 없음")
        print(f"  - 마지막 사용: {account[7]}")

        # 토큰 만료 확인
        if account[4]:
            expiry_dt = datetime.fromisoformat(account[4])
            if expiry_dt.tzinfo is None:
                expiry_dt = expiry_dt.replace(tzinfo=timezone.utc)

            if expiry_dt > datetime.now(timezone.utc):
                print(f"  - 토큰 상태: ✅ 유효")

                # 토큰 복호화 테스트
                if account[2]:
                    try:
                        decrypted_token = crypto.account_decrypt_sensitive_data(account[2])
                        print(f"  - 토큰 복호화: ✅ 성공 (길이: {len(decrypted_token)})")
                        return True
                    except Exception as e:
                        print(f"  - 토큰 복호화: ❌ 실패 - {e}")
                        return False
            else:
                print(f"  - 토큰 상태: ❌ 만료됨")
                return False
        else:
            print(f"  - 토큰 상태: ❌ 만료 시간 없음")
            return False
    else:
        print(f"❌ 계정을 찾을 수 없습니다: {user_id}")
        return False

async def test_graphapi_call():
    """GraphAPI 호출 테스트"""
    print("\n=== GraphAPI 호출 테스트 ===\n")

    try:
        import requests

        # 사용자 ID 설정
        user_id = os.getenv("AUTO_REGISTER_USER_ID", "testuser")

        print(f"테스트 사용자: {user_id}")

        # accounts 테이블에서 토큰 가져오기
        db_manager = get_database_manager()
        crypto = AccountCryptoHelpers()

        account = db_manager.fetch_one("""
            SELECT access_token, refresh_token, oauth_client_id, oauth_client_secret, oauth_tenant_id
            FROM accounts
            WHERE user_id = ?
        """, (user_id,))

        if not account or not account[0]:
            print("❌ 계정 또는 토큰이 없습니다")
            return False

        # 토큰 복호화
        access_token = crypto.account_decrypt_sensitive_data(account[0])

        print("Microsoft Graph API 호출 중...")

        # Graph API 호출 - 사용자 프로필 조회
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        # 1. 사용자 정보 조회
        response = requests.get('https://graph.microsoft.com/v1.0/me', headers=headers)

        if response.status_code == 200:
            user_info = response.json()
            print(f"\n✅ 사용자 정보 조회 성공!")
            print(f"  - 이름: {user_info.get('displayName', 'N/A')}")
            print(f"  - 이메일: {user_info.get('mail', user_info.get('userPrincipalName', 'N/A'))}")
            print(f"  - ID: {user_info.get('id', 'N/A')}")
        elif response.status_code == 401:
            print(f"❌ 토큰이 만료되었거나 유효하지 않습니다")

            # 토큰 갱신 시도
            if account[1]:  # refresh_token이 있으면
                print("\n토큰 갱신 시도 중...")
                refresh_token = crypto.account_decrypt_sensitive_data(account[1])
                client_id = account[2]
                client_secret = crypto.account_decrypt_sensitive_data(account[3]) if account[3] else None
                tenant_id = account[4]

                if client_secret:
                    token_url = f'https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token'
                    token_data = {
                        'client_id': client_id,
                        'client_secret': client_secret,
                        'refresh_token': refresh_token,
                        'grant_type': 'refresh_token'
                    }

                    token_response = requests.post(token_url, data=token_data)
                    if token_response.status_code == 200:
                        new_tokens = token_response.json()
                        new_access_token = new_tokens['access_token']

                        # 새 토큰으로 재시도
                        headers['Authorization'] = f'Bearer {new_access_token}'
                        response = requests.get('https://graph.microsoft.com/v1.0/me', headers=headers)

                        if response.status_code == 200:
                            print("✅ 토큰 갱신 성공!")

                            # 새 토큰 저장
                            from datetime import timedelta
                            expires_at = datetime.now(timezone.utc) + timedelta(seconds=new_tokens['expires_in'])

                            db_manager.execute_query("""
                                UPDATE accounts
                                SET access_token = ?, refresh_token = ?, token_expiry = ?,
                                    last_used_at = datetime('now')
                                WHERE user_id = ?
                            """, (
                                crypto.account_encrypt_sensitive_data(new_access_token),
                                crypto.account_encrypt_sensitive_data(new_tokens.get('refresh_token', refresh_token)),
                                expires_at.isoformat(),
                                user_id
                            ))

                            user_info = response.json()
                            print(f"  - 이름: {user_info.get('displayName', 'N/A')}")
                            print(f"  - 이메일: {user_info.get('mail', user_info.get('userPrincipalName', 'N/A'))}")
                        else:
                            print(f"❌ 갱신된 토큰도 실패: {response.status_code}")
                            return False
                    else:
                        print(f"❌ 토큰 갱신 실패: {token_response.status_code}")
                        return False
            else:
                return False
        else:
            print(f"❌ API 호출 실패: {response.status_code}")
            print(f"응답: {response.text}")
            return False

        # 2. 메일 목록 조회
        print("\n최근 메일 3개 조회 중...")
        mail_response = requests.get(
            'https://graph.microsoft.com/v1.0/me/messages?$top=3&$select=subject,from,receivedDateTime',
            headers=headers
        )

        if mail_response.status_code == 200:
            mails = mail_response.json()
            mail_list = mails.get('value', [])
            print(f"✅ 메일 조회 성공! ({len(mail_list)}개)")

            for i, mail in enumerate(mail_list, 1):
                print(f"\n  메일 {i}:")
                print(f"    - 제목: {mail.get('subject', 'N/A')}")
                print(f"    - 발신자: {mail.get('from', {}).get('emailAddress', {}).get('address', 'N/A')}")
                print(f"    - 날짜: {mail.get('receivedDateTime', 'N/A')[:19]}")
        else:
            print(f"⚠️ 메일 조회 실패: {mail_response.status_code}")

        return True

    except Exception as e:
        print(f"❌ GraphAPI 호출 중 오류: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_sync_status():
    """DCR과 accounts 테이블 동기화 상태 확인"""
    print("\n=== DCR-Accounts 동기화 상태 확인 ===\n")

    # DCR에서 토큰 정보 가져오기
    dcr_db_path = "./data/claudedcr.db"
    dcr_token_info = None

    if Path(dcr_db_path).exists():
        conn = sqlite3.connect(dcr_db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT access_token, expires_at
            FROM dcr_azure_tokens
            WHERE user_email = ?
            ORDER BY created_at DESC
            LIMIT 1
        """, (os.getenv("AUTO_REGISTER_EMAIL", "testuser@example.com"),))

        result = cursor.fetchone()
        if result:
            crypto = AccountCryptoHelpers()
            try:
                dcr_token = crypto.account_decrypt_sensitive_data(result[0])
                dcr_token_info = {
                    "token_preview": dcr_token[:20] + "..." if dcr_token else None,
                    "expires_at": result[1]
                }
            except:
                pass
        conn.close()

    # accounts 테이블에서 토큰 정보 가져오기
    db_manager = get_database_manager()
    crypto = AccountCryptoHelpers()

    account = db_manager.fetch_one("""
        SELECT access_token, token_expiry
        FROM accounts
        WHERE user_id = ?
    """, (os.getenv("AUTO_REGISTER_USER_ID", "testuser"),))

    account_token_info = None
    if account and account[0]:
        try:
            account_token = crypto.account_decrypt_sensitive_data(account[0])
            account_token_info = {
                "token_preview": account_token[:20] + "..." if account_token else None,
                "expires_at": account[1]
            }
        except:
            pass

    # 비교
    if dcr_token_info and account_token_info:
        print("DCR Azure 토큰:")
        print(f"  - 토큰: {dcr_token_info['token_preview']}")
        print(f"  - 만료: {dcr_token_info['expires_at']}")

        print("\nAccounts 테이블 토큰:")
        print(f"  - 토큰: {account_token_info['token_preview']}")
        print(f"  - 만료: {account_token_info['expires_at']}")

        if dcr_token_info['token_preview'] == account_token_info['token_preview']:
            print("\n✅ 토큰이 동기화되어 있습니다")
            return True
        else:
            print("\n⚠️  토큰이 다릅니다 (동기화 필요)")
            return False
    else:
        print("❌ 토큰 정보를 확인할 수 없습니다")
        return False

async def main():
    """메인 테스트 실행"""
    print("\n" + "=" * 60)
    print("DCR 인증 및 GraphAPI 호출 통합 테스트")
    print("=" * 60)

    results = {}

    # 1. DCR 토큰 확인
    results['dcr'] = await test_dcr_tokens()

    # 2. Accounts 테이블 확인
    results['accounts'] = await test_accounts_table()

    # 3. 동기화 상태 확인
    results['sync'] = await test_sync_status()

    # 4. GraphAPI 호출 테스트
    if results['accounts']:
        results['graphapi'] = await test_graphapi_call()
    else:
        print("\n⚠️  accounts 테이블에 유효한 토큰이 없어 GraphAPI 테스트 건너뜀")
        results['graphapi'] = False

    # 결과 요약
    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)

    print(f"DCR 토큰 상태: {'✅ 성공' if results['dcr'] else '❌ 실패'}")
    print(f"Accounts 테이블: {'✅ 성공' if results['accounts'] else '❌ 실패'}")
    print(f"동기화 상태: {'✅ 성공' if results['sync'] else '❌ 실패'}")
    print(f"GraphAPI 호출: {'✅ 성공' if results['graphapi'] else '❌ 실패'}")

    all_passed = all(results.values())
    print(f"\n전체 결과: {'✅ 모든 테스트 통과' if all_passed else '❌ 일부 테스트 실패'}")

    return all_passed

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)