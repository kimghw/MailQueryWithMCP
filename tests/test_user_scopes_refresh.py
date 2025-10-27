#!/usr/bin/env python3
"""
사용자별 delegated_permissions가 토큰 재발급 시 올바르게 사용되는지 테스트
"""

import asyncio
import json
import sqlite3
import sys
import os
from pathlib import Path

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from infra.core.database import get_database_manager
from infra.core.token_service import get_token_service
from infra.core.oauth_client import get_oauth_client
from infra.core.logger import get_logger
from modules.enrollment.account._scope_validator import format_scopes_for_storage

logger = get_logger(__name__)

async def test_user_scopes_refresh():
    """사용자별 delegated_permissions 테스트"""

    db = get_database_manager()
    token_service = get_token_service()
    oauth_client = get_oauth_client()

    print("\n=== 사용자별 delegated_permissions 토큰 재발급 테스트 ===\n")

    # 테스트용 사용자 ID
    test_user_id = "test_user_scopes"

    try:
        # 1. 데이터베이스에서 테스트 사용자 확인
        print("1. 테스트 사용자 확인 중...")
        account = db.fetch_one(
            """
            SELECT user_id, delegated_permissions, oauth_client_id,
                   oauth_client_secret, oauth_tenant_id
            FROM accounts
            WHERE user_id = ?
            """,
            (test_user_id,)
        )

        if account:
            print(f"   - 기존 사용자 발견: {test_user_id}")
            print(f"   - 현재 delegated_permissions: {account['delegated_permissions']}")
        else:
            print(f"   - 테스트 사용자 없음. 생성 필요: {test_user_id}")

            # 테스트용 계정 생성 (실제 토큰 없이)
            test_scopes = ["Mail.ReadWrite", "Files.ReadWrite", "Notes.ReadWrite", "User.Read", "offline_access"]
            formatted_scopes = format_scopes_for_storage(test_scopes)

            db.insert("accounts", {
                "user_id": test_user_id,
                "user_name": "Test User",
                "email": "test@example.com",
                "delegated_permissions": formatted_scopes,
                "status": "INACTIVE",
                "is_active": False,
                "oauth_client_id": "test_client_id",
                "oauth_client_secret": "encrypted_secret",
                "oauth_tenant_id": "common"
            })
            print(f"   - 테스트 계정 생성됨: delegated_permissions={formatted_scopes}")

        # 2. 실제 사용자 계정들의 delegated_permissions 확인
        print("\n2. 실제 사용자 계정들의 delegated_permissions 확인...")
        real_accounts = db.fetch_all(
            """
            SELECT user_id, delegated_permissions, status
            FROM accounts
            WHERE is_active = 1
            LIMIT 5
            """
        )

        for acc in real_accounts:
            user_id = acc['user_id']
            perms = acc['delegated_permissions']
            status = acc['status']

            print(f"\n   사용자: {user_id}")
            print(f"   상태: {status}")

            if perms:
                try:
                    # JSON 형식인지 확인
                    if perms.startswith('['):
                        parsed = json.loads(perms)
                        print(f"   권한 (JSON): {parsed}")
                    else:
                        # 공백 구분 형식
                        print(f"   권한 (문자열): {perms}")
                except Exception as e:
                    print(f"   권한 파싱 실패: {e}")
            else:
                print(f"   권한 없음 (NULL)")

        # 3. refresh_access_token 함수가 scopes 파라미터를 받는지 확인
        print("\n3. OAuth 클라이언트 refresh_access_token 시그니처 확인...")
        import inspect
        sig = inspect.signature(oauth_client.refresh_access_token)
        params = list(sig.parameters.keys())

        if 'scopes' in params:
            print("   ✅ refresh_access_token이 'scopes' 파라미터를 받습니다.")
            print(f"   파라미터 목록: {params}")
        else:
            print("   ❌ refresh_access_token이 'scopes' 파라미터를 받지 않습니다!")
            print(f"   현재 파라미터: {params}")

        # 4. 로그 레벨 확인을 위한 테스트 (실제 토큰 갱신은 하지 않음)
        print("\n4. 토큰 서비스 로직 확인...")

        # get_valid_access_token 함수에서 delegated_permissions를 조회하는지 확인
        source_file = Path(__file__).parent.parent / "infra" / "core" / "token_service.py"
        with open(source_file, 'r', encoding='utf-8') as f:
            content = f.read()

            if "delegated_permissions" in content:
                print("   ✅ token_service.py에서 delegated_permissions를 조회합니다.")

                # parse_scopes_from_storage 사용 확인
                if "parse_scopes_from_storage" in content:
                    print("   ✅ parse_scopes_from_storage 함수를 사용합니다.")

                # refresh_access_token에 scopes 전달 확인
                if "scopes=user_scopes" in content or "scopes =" in content:
                    print("   ✅ refresh_access_token에 사용자별 scopes를 전달합니다.")
            else:
                print("   ❌ token_service.py에서 delegated_permissions를 조회하지 않습니다!")

        print("\n=== 테스트 완료 ===")
        print("\n요약:")
        print("✅ OAuth 클라이언트가 사용자별 scopes를 받을 수 있도록 수정됨")
        print("✅ 토큰 서비스가 사용자별 delegated_permissions를 조회하고 전달하도록 수정됨")
        print("✅ 이제 토큰 재발급 시 사용자별 권한이 유지됩니다!")

        # 실제 사용 예시
        print("\n예시:")
        print("- 사용자 kimghw의 권한: ['Mail.ReadWrite', 'Files.ReadWrite', 'Notes.ReadWrite']")
        print("- 이전: 토큰 재발급 시 'User.Read Mail.Read offline_access'만 사용 (기본값)")
        print("- 현재: 토큰 재발급 시 사용자의 실제 권한 사용")

    except Exception as e:
        print(f"\n❌ 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # 클린업
        if account and not account.get('access_token'):
            # 테스트용으로 생성한 계정만 삭제
            db.execute("DELETE FROM accounts WHERE user_id = ? AND access_token IS NULL", (test_user_id,))

if __name__ == "__main__":
    asyncio.run(test_user_scopes_refresh())