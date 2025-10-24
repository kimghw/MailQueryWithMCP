#!/usr/bin/env python3
"""
현재 토큰의 권한 확인 스크립트
"""

import sys
import base64
import json

sys.path.insert(0, '.')

from infra.core.database import get_database_manager


def decode_token(token):
    """JWT 토큰 디코딩 (검증 없이)"""
    try:
        # JWT는 header.payload.signature 형식
        parts = token.split('.')
        if len(parts) != 3:
            return None

        # payload 부분 디코딩
        payload = parts[1]

        # Base64 패딩 추가
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += '=' * padding

        # 디코딩
        decoded = base64.urlsafe_b64decode(payload)
        return json.loads(decoded)

    except Exception as e:
        print(f"❌ 토큰 디코딩 실패: {e}")
        return None


def main():
    """메인"""
    print("=" * 60)
    print("토큰 권한 확인")
    print("=" * 60)

    db = get_database_manager()

    # kimghw 계정 조회
    query = """
        SELECT user_id, access_token, token_expiry
        FROM accounts
        WHERE user_id = 'kimghw' AND is_active = 1
    """
    rows = db.fetch_all(query)

    if not rows:
        print("\n❌ kimghw 계정을 찾을 수 없습니다")
        return

    row = rows[0]
    user_id = row['user_id']
    access_token = row['access_token']
    token_expiry = row['token_expiry']

    print(f"\n✅ 계정: {user_id}")
    print(f"✅ 토큰 만료: {token_expiry}")

    if not access_token:
        print("\n❌ 액세스 토큰이 없습니다")
        return

    # 토큰 디코딩
    print("\n" + "-" * 60)
    print("토큰 디코딩 중...")
    print("-" * 60)

    payload = decode_token(access_token)

    if not payload:
        print("\n❌ 토큰 디코딩 실패")
        return

    # 주요 정보 출력
    print(f"\n📋 토큰 정보:")
    print(f"   - 발급자: {payload.get('iss', 'N/A')}")
    print(f"   - 대상: {payload.get('aud', 'N/A')}")
    print(f"   - 사용자: {payload.get('upn', payload.get('email', 'N/A'))}")
    print(f"   - 앱 ID: {payload.get('appid', 'N/A')}")

    # 권한 확인
    scopes = payload.get('scp', '')
    if scopes:
        print(f"\n🔑 권한 (Scopes):")
        scope_list = scopes.split(' ')
        for scope in sorted(scope_list):
            print(f"   ✅ {scope}")

        # Calendar 권한 확인
        print("\n📅 Calendar 권한 확인:")
        calendar_perms = [s for s in scope_list if 'Calendar' in s]
        if calendar_perms:
            print("   ✅ Calendar 권한이 있습니다:")
            for perm in calendar_perms:
                print(f"      • {perm}")
        else:
            print("   ❌ Calendar 권한이 없습니다!")
            print("      → Calendars.ReadWrite 권한 추가 필요")

        # OnlineMeetings 권한 확인
        meeting_perms = [s for s in scope_list if 'OnlineMeeting' in s]
        if meeting_perms:
            print("\n📞 OnlineMeetings 권한:")
            for perm in meeting_perms:
                print(f"   ✅ {perm}")
        else:
            print("\n📞 OnlineMeetings 권한:")
            print("   ℹ️ OnlineMeetings 권한이 없습니다 (선택적)")

    else:
        print("\n⚠️ 권한 정보를 찾을 수 없습니다")

    print("\n" + "=" * 60)
    print("✅ 확인 완료")
    print("=" * 60)

    if not scopes or 'Calendars' not in scopes:
        print("\n💡 다음 단계:")
        print("   1. Azure Portal에서 앱 등록 열기")
        print("   2. API 권한 → 권한 추가")
        print("   3. Microsoft Graph → 위임된 권한")
        print("   4. Calendars.ReadWrite 선택 및 추가")
        print("   5. 관리자 동의 부여")
        print("   6. enrollment 페이지에서 재로그인")
        print("\n   자세한 내용: scripts/setup_calendar_permissions.md")


if __name__ == "__main__":
    main()
