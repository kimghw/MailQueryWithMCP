#!/usr/bin/env python3
"""DCR OAuth 인증 테스트 - 인증 URL 생성 및 처리"""

import os
import sys
import webbrowser
import secrets
import base64
import hashlib
from pathlib import Path
from urllib.parse import urlencode

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

def generate_pkce():
    """PKCE 코드 생성"""
    code_verifier = base64.urlsafe_b64encode(os.urandom(32)).decode('utf-8').rstrip('=')
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode('utf-8')).digest()
    ).decode('utf-8').rstrip('=')
    return code_verifier, code_challenge

def generate_auth_url():
    """DCR OAuth 인증 URL 생성"""

    # Azure AD 설정
    client_id = os.getenv("DCR_AZURE_CLIENT_ID")
    tenant_id = os.getenv("DCR_AZURE_TENANT_ID")
    redirect_uri = os.getenv("DCR_OAUTH_REDIRECT_URI", "https://governmental-read-having-mails.trycloudflare.com/oauth/azure_callback")

    if not all([client_id, tenant_id]):
        print("❌ DCR_AZURE_CLIENT_ID 또는 DCR_AZURE_TENANT_ID가 설정되지 않았습니다")
        return None

    # PKCE 생성
    code_verifier, code_challenge = generate_pkce()

    # State 생성 (CSRF 보호)
    state = secrets.token_urlsafe(16)[:32]  # Azure AD는 32자 제한

    # 인증 URL 구성
    auth_endpoint = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize"

    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "response_mode": "query",
        "scope": "openid profile email offline_access Mail.Read Mail.ReadWrite User.Read",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "prompt": "select_account"  # 계정 선택 화면 표시
    }

    auth_url = f"{auth_endpoint}?{urlencode(params)}"

    print("\n=== DCR OAuth 인증 정보 ===")
    print(f"Client ID: {client_id}")
    print(f"Tenant ID: {tenant_id}")
    print(f"Redirect URI: {redirect_uri}")
    print(f"State: {state}")
    print(f"Code Verifier: {code_verifier}")
    print(f"Code Challenge: {code_challenge}")

    return auth_url, state, code_verifier

def main():
    print("\n" + "=" * 60)
    print("DCR OAuth 인증 URL 생성")
    print("=" * 60)

    result = generate_auth_url()

    if not result:
        return

    auth_url, state, code_verifier = result

    print("\n" + "=" * 60)
    print("🔐 인증 URL (브라우저에서 열어주세요):")
    print("=" * 60)
    print("\n" + auth_url)
    print("\n" + "=" * 60)

    print("\n📝 인증 후 콜백 URL의 code 파라미터를 복사해서 사용하세요")
    print("   콜백 URL 예시: https://...?code=XXX&state=YYY")

    print("\n💾 다음 정보를 저장해두세요 (토큰 교환 시 필요):")
    print(f"   State: {state}")
    print(f"   Code Verifier: {code_verifier}")

    print("\n브라우저에서 열기를 원하시면 'y'를 입력하세요: ", end="")
    if input().lower() == 'y':
        webbrowser.open(auth_url)
        print("✅ 브라우저에서 인증 페이지를 열었습니다")

    print("\n인증 완료 후 콜백 URL을 여기에 붙여넣으세요:")
    print("(전체 URL을 복사해서 붙여넣으세요)")
    callback_url = input("> ").strip()

    if callback_url:
        # URL에서 code 추출
        from urllib.parse import urlparse, parse_qs

        parsed = urlparse(callback_url)
        params = parse_qs(parsed.query)

        auth_code = params.get('code', [None])[0]
        returned_state = params.get('state', [None])[0]

        if auth_code:
            print(f"\n✅ Authorization Code: {auth_code[:20]}...")

            if returned_state == state:
                print("✅ State 검증 성공")
            else:
                print("⚠️  State 불일치 (CSRF 위험)")

            # 토큰 교환을 위한 curl 명령 생성
            print("\n토큰 교환 명령 (터미널에서 실행):")
            print("=" * 60)

            curl_command = f"""
curl -X POST https://login.microsoftonline.com/{os.getenv('DCR_AZURE_TENANT_ID')}/oauth2/v2.0/token \\
  -H "Content-Type: application/x-www-form-urlencoded" \\
  -d "client_id={os.getenv('DCR_AZURE_CLIENT_ID')}" \\
  -d "client_secret={os.getenv('DCR_AZURE_CLIENT_SECRET')}" \\
  -d "grant_type=authorization_code" \\
  -d "code={auth_code}" \\
  -d "redirect_uri={os.getenv('DCR_OAUTH_REDIRECT_URI')}" \\
  -d "code_verifier={code_verifier}"
"""
            print(curl_command)

            print("\n또는 Python으로 토큰 교환:")
            print("=" * 60)
            print(f"""
import requests

response = requests.post(
    "https://login.microsoftonline.com/{os.getenv('DCR_AZURE_TENANT_ID')}/oauth2/v2.0/token",
    data={{
        "client_id": "{os.getenv('DCR_AZURE_CLIENT_ID')}",
        "client_secret": "{os.getenv('DCR_AZURE_CLIENT_SECRET')}",
        "grant_type": "authorization_code",
        "code": "{auth_code}",
        "redirect_uri": "{os.getenv('DCR_OAUTH_REDIRECT_URI')}",
        "code_verifier": "{code_verifier}"
    }}
)

if response.status_code == 200:
    tokens = response.json()
    print("Access Token:", tokens['access_token'][:50] + "...")
    print("Refresh Token:", tokens.get('refresh_token', 'N/A')[:50] + "...")
else:
    print("Error:", response.status_code, response.text)
""")
        else:
            print("❌ Authorization Code를 찾을 수 없습니다")

if __name__ == "__main__":
    main()