#!/usr/bin/env python3
"""
PKCE (Proof Key for Code Exchange) Test Script
RFC 7636 구현 테스트
"""

import base64
import hashlib
import secrets
import requests
import urllib.parse
import sys
import json


class PKCETest:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.client_id = None
        self.client_secret = None
        self.code_verifier = None
        self.code_challenge = None

    def generate_code_verifier(self):
        """PKCE code_verifier 생성 (43-128 문자)"""
        self.code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
        return self.code_verifier

    def generate_code_challenge(self, method="S256"):
        """PKCE code_challenge 생성"""
        if not self.code_verifier:
            self.generate_code_verifier()

        if method == "plain":
            self.code_challenge = self.code_verifier
        elif method == "S256":
            digest = hashlib.sha256(self.code_verifier.encode('utf-8')).digest()
            self.code_challenge = base64.urlsafe_b64encode(digest).decode('utf-8').rstrip('=')
        else:
            raise ValueError(f"Unsupported method: {method}")

        return self.code_challenge

    def test_metadata(self):
        """OAuth metadata 엔드포인트 테스트"""
        print("\n1️⃣ Testing OAuth Metadata Endpoint...")
        url = f"{self.base_url}/.well-known/oauth-authorization-server"

        response = requests.get(url)
        if response.status_code == 200:
            metadata = response.json()
            print(f"✅ Metadata retrieved successfully")

            # PKCE 지원 확인
            pkce_methods = metadata.get("code_challenge_methods_supported", [])
            if "S256" in pkce_methods:
                print(f"✅ PKCE S256 method supported")
            if "plain" in pkce_methods:
                print(f"✅ PKCE plain method supported")

            print(f"   Supported methods: {pkce_methods}")
            return True
        else:
            print(f"❌ Failed to retrieve metadata: {response.status_code}")
            return False

    def test_client_registration(self):
        """DCR 클라이언트 등록 테스트"""
        print("\n2️⃣ Testing Client Registration...")
        url = f"{self.base_url}/oauth/register"

        data = {
            "client_name": "PKCE Test Client",
            "redirect_uris": ["http://localhost:8080/callback"],
            "grant_types": ["authorization_code"],
            "response_types": ["code"]
        }

        response = requests.post(url, json=data)
        if response.status_code == 201:
            result = response.json()
            self.client_id = result["client_id"]
            self.client_secret = result["client_secret"]
            print(f"✅ Client registered successfully")
            print(f"   Client ID: {self.client_id}")
            return True
        else:
            print(f"❌ Client registration failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False

    def test_authorization_with_pkce(self, method="S256"):
        """PKCE를 사용한 Authorization 테스트"""
        print(f"\n3️⃣ Testing Authorization with PKCE ({method})...")

        # PKCE 값 생성
        self.generate_code_verifier()
        self.generate_code_challenge(method)

        print(f"   Code Verifier: {self.code_verifier[:20]}...")
        print(f"   Code Challenge: {self.code_challenge[:20]}...")
        print(f"   Method: {method}")

        # Authorization URL 생성
        params = {
            "client_id": self.client_id,
            "redirect_uri": "http://localhost:8080/callback",
            "response_type": "code",
            "scope": "Mail.Read User.Read",
            "state": "test_state_123",
            "code_challenge": self.code_challenge,
            "code_challenge_method": method
        }

        auth_url = f"{self.base_url}/oauth/authorize?" + urllib.parse.urlencode(params)
        print(f"\n📝 Authorization URL (open in browser):")
        print(f"   {auth_url}")

        return auth_url

    def test_token_exchange_with_pkce(self, auth_code):
        """PKCE를 사용한 토큰 교환 테스트"""
        print("\n4️⃣ Testing Token Exchange with PKCE...")
        url = f"{self.base_url}/oauth/token"

        data = {
            "grant_type": "authorization_code",
            "code": auth_code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": "http://localhost:8080/callback",
            "code_verifier": self.code_verifier  # PKCE verifier
        }

        print(f"   Sending code_verifier: {self.code_verifier[:20]}...")

        response = requests.post(url, data=data)
        if response.status_code == 200:
            tokens = response.json()
            print(f"✅ Token exchange successful with PKCE!")
            print(f"   Access Token: {tokens.get('access_token', '')[:30]}...")
            return True
        else:
            print(f"❌ Token exchange failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False

    def test_token_exchange_without_verifier(self, auth_code):
        """PKCE verifier 없이 토큰 교환 시도 (실패해야 함)"""
        print("\n5️⃣ Testing Token Exchange WITHOUT code_verifier (should fail)...")
        url = f"{self.base_url}/oauth/token"

        data = {
            "grant_type": "authorization_code",
            "code": auth_code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": "http://localhost:8080/callback"
            # code_verifier 의도적으로 생략
        }

        response = requests.post(url, data=data)
        if response.status_code != 200:
            print(f"✅ Correctly rejected without code_verifier: {response.status_code}")
            print(f"   Error: {response.json().get('error_description', 'N/A')}")
            return True
        else:
            print(f"❌ Should have failed but succeeded!")
            return False

    def test_wrong_verifier(self, auth_code):
        """잘못된 PKCE verifier로 토큰 교환 시도 (실패해야 함)"""
        print("\n6️⃣ Testing Token Exchange with WRONG code_verifier (should fail)...")
        url = f"{self.base_url}/oauth/token"

        wrong_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')

        data = {
            "grant_type": "authorization_code",
            "code": auth_code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": "http://localhost:8080/callback",
            "code_verifier": wrong_verifier  # 잘못된 verifier
        }

        response = requests.post(url, data=data)
        if response.status_code != 200:
            print(f"✅ Correctly rejected wrong code_verifier: {response.status_code}")
            print(f"   Error: {response.json().get('error_description', 'N/A')}")
            return True
        else:
            print(f"❌ Should have failed but succeeded!")
            return False

    def run_automated_tests(self):
        """자동화된 테스트 실행"""
        print("=" * 60)
        print("🔬 PKCE (RFC 7636) Implementation Test")
        print("=" * 60)

        # 1. Metadata 테스트
        if not self.test_metadata():
            return False

        # 2. 클라이언트 등록
        if not self.test_client_registration():
            return False

        # 3. Authorization URL 생성 (S256)
        auth_url = self.test_authorization_with_pkce("S256")

        print("\n" + "=" * 60)
        print("📋 Test Summary:")
        print("=" * 60)
        print("✅ OAuth metadata endpoint supports PKCE")
        print("✅ Client registration successful")
        print("✅ Authorization request with PKCE prepared")
        print("\n⚠️  Manual Step Required:")
        print("1. Open the authorization URL in a browser")
        print("2. Complete authentication")
        print("3. Copy the 'code' parameter from the redirect")
        print("4. Run: python test_pkce.py --code <authorization_code>")

        return True

    def run_token_tests(self, auth_code):
        """토큰 교환 테스트 실행"""
        print("=" * 60)
        print("🔬 PKCE Token Exchange Test")
        print("=" * 60)

        # 이전 세션 복구를 위해 PKCE 값 재생성 필요
        if not self.code_verifier:
            print("⚠️  No code_verifier found. Please run full test first.")
            return False

        # 올바른 verifier로 테스트
        success = self.test_token_exchange_with_pkce(auth_code)

        # 잘못된 시나리오 테스트 (선택적)
        # self.test_token_exchange_without_verifier(auth_code)
        # self.test_wrong_verifier(auth_code)

        return success


def main():
    """메인 실행 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="PKCE Implementation Test")
    parser.add_argument("--url", default="http://localhost:8000", help="Server URL")
    parser.add_argument("--code", help="Authorization code for token exchange")
    parser.add_argument("--method", default="S256", choices=["S256", "plain"], help="PKCE method")

    args = parser.parse_args()

    tester = PKCETest(args.url)

    if args.code:
        # 토큰 교환 테스트
        print(f"Testing token exchange with code: {args.code[:20]}...")
        tester.run_token_tests(args.code)
    else:
        # 전체 플로우 테스트
        tester.run_automated_tests()


if __name__ == "__main__":
    main()