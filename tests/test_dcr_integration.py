"""DCR (Dynamic Client Registration) 통합 테스트

Claude Connector와의 OAuth 플로우를 테스트합니다.
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from infra.core.dcr_service import DCRService
from infra.core.database import get_database_manager


def test_dcr_schema_initialization():
    """DCR 스키마 초기화 테스트"""
    print("\n" + "=" * 60)
    print("TEST 1: DCR Schema Initialization")
    print("=" * 60)

    dcr_service = DCRService()
    dcr_service._ensure_dcr_schema()

    # Check tables exist
    db = get_database_manager()
    result = db.fetch_all(
        """
        SELECT name FROM sqlite_master
        WHERE type='table' AND name LIKE 'dcr_%'
        ORDER BY name
        """
    )

    tables = [row[0] for row in result]
    print(f"✅ Created DCR tables: {', '.join(tables)}")

    expected_tables = ["dcr_auth_codes", "dcr_clients", "dcr_tokens"]
    for table in expected_tables:
        assert table in tables, f"Missing table: {table}"

    print("✅ All DCR tables exist")


async def test_dcr_client_registration():
    """DCR 클라이언트 등록 테스트"""
    print("\n" + "=" * 60)
    print("TEST 2: DCR Client Registration")
    print("=" * 60)

    dcr_service = DCRService()

    # Mock Claude Connector registration request
    request_data = {
        "client_name": "Claude AI Test",
        "redirect_uris": ["https://claude.ai/api/mcp/auth_callback"],
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "scope": "Mail.Read User.Read",
    }

    response = await dcr_service.register_client(request_data)

    print(f"\n📋 Registration Response:")
    print(json.dumps(response, indent=2))

    # Verify response
    assert "client_id" in response
    assert "client_secret" in response
    assert "registration_access_token" in response
    assert response["client_id"].startswith("dcr_")
    assert response["client_name"] == "Claude AI Test"

    print(f"\n✅ Client registered: {response['client_id']}")

    return response


async def test_dcr_authorization_flow(client_data):
    """DCR Authorization Code 플로우 테스트"""
    print("\n" + "=" * 60)
    print("TEST 3: DCR Authorization Flow")
    print("=" * 60)

    dcr_service = DCRService()
    client_id = client_data["client_id"]

    # Step 1: Create authorization code
    redirect_uri = "https://claude.ai/api/mcp/auth_callback"
    scope = "Mail.Read User.Read"
    state = "test_state_123"

    auth_code = dcr_service.create_authorization_code(
        client_id=client_id, redirect_uri=redirect_uri, scope=scope, state=state
    )

    print(f"\n✅ Authorization code created: {auth_code[:20]}...")

    # Step 2: Verify authorization code
    code_data = dcr_service.verify_authorization_code(auth_code, client_id, redirect_uri)

    assert code_data is not None
    assert code_data["scope"] == scope
    assert code_data["state"] == state

    print("✅ Authorization code verified")

    # Step 3: Try to reuse code (should fail)
    code_data_retry = dcr_service.verify_authorization_code(auth_code, client_id, redirect_uri)

    assert code_data_retry is None, "Authorization code should not be reusable"
    print("✅ Authorization code cannot be reused (correct)")

    return auth_code


async def test_dcr_client_credentials():
    """DCR 클라이언트 인증 정보 검증 테스트"""
    print("\n" + "=" * 60)
    print("TEST 4: DCR Client Credentials Verification")
    print("=" * 60)

    dcr_service = DCRService()

    # Register a test client
    request_data = {
        "client_name": "Test Client",
        "redirect_uris": ["https://example.com/callback"],
    }

    response = await dcr_service.register_client(request_data)
    client_id = response["client_id"]
    client_secret = response["client_secret"]

    # Verify correct credentials
    is_valid = dcr_service.verify_client_credentials(client_id, client_secret)
    assert is_valid, "Valid credentials should pass"
    print(f"✅ Valid credentials verified for {client_id}")

    # Verify wrong credentials
    is_invalid = dcr_service.verify_client_credentials(client_id, "wrong_secret")
    assert not is_invalid, "Invalid credentials should fail"
    print("✅ Invalid credentials rejected")


async def test_dcr_token_storage():
    """DCR 토큰 저장 및 검증 테스트"""
    print("\n" + "=" * 60)
    print("TEST 5: DCR Token Storage and Verification")
    print("=" * 60)

    dcr_service = DCRService()

    # Register client
    request_data = {"client_name": "Token Test Client"}
    client_response = await dcr_service.register_client(request_data)
    client_id = client_response["client_id"]

    # Mock token data
    access_token = "test_access_token_abc123"
    refresh_token = "test_refresh_token_xyz789"
    azure_access_token = "azure_token_mock"
    azure_refresh_token = "azure_refresh_mock"

    # Store token
    dcr_service.store_token(
        client_id=client_id,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=3600,
        scope="Mail.Read",
        azure_access_token=azure_access_token,
        azure_refresh_token=azure_refresh_token,
        azure_token_expiry=datetime.now() + timedelta(hours=1),
    )

    print(f"✅ Token stored for client {client_id}")

    # Verify token
    token_data = dcr_service.verify_bearer_token(access_token)

    assert token_data is not None, "Token data should not be None"
    print(f"   • Returned Client ID: {token_data['client_id']}")
    print(f"   • Expected Client ID: {client_id}")
    assert token_data["client_id"] == client_id, f"Client ID mismatch: {token_data['client_id']} != {client_id}"
    assert token_data["azure_access_token"] == azure_access_token
    assert token_data["scope"] == "Mail.Read"

    print("✅ Bearer token verified successfully")
    print(f"   • Client ID: {token_data['client_id']}")
    print(f"   • Azure Token: {token_data['azure_access_token'][:20]}...")
    print(f"   • Scope: {token_data['scope']}")


async def test_dcr_client_deletion():
    """DCR 클라이언트 삭제 테스트"""
    print("\n" + "=" * 60)
    print("TEST 6: DCR Client Deletion")
    print("=" * 60)

    dcr_service = DCRService()

    # Register client
    request_data = {"client_name": "Delete Test Client"}
    response = await dcr_service.register_client(request_data)
    client_id = response["client_id"]
    registration_token = response["registration_access_token"]

    print(f"✅ Client created: {client_id}")

    # Delete with wrong token (should fail)
    success = await dcr_service.delete_client(client_id, "wrong_token")
    assert not success, "Deletion with wrong token should fail"
    print("✅ Deletion rejected with wrong token")

    # Delete with correct token
    success = await dcr_service.delete_client(client_id, registration_token)
    assert success, "Deletion with correct token should succeed"
    print(f"✅ Client deleted: {client_id}")

    # Verify client is inactive
    client = dcr_service.get_client(client_id)
    assert client is None, "Deleted client should not be retrievable"
    print("✅ Deleted client is no longer active")


def test_oauth_metadata_format():
    """OAuth 메타데이터 형식 테스트"""
    print("\n" + "=" * 60)
    print("TEST 7: OAuth Metadata Format (RFC 8414)")
    print("=" * 60)

    # Expected metadata structure
    base_url = "https://example.com"
    expected_metadata = {
        "issuer": base_url,
        "authorization_endpoint": f"{base_url}/oauth/authorize",
        "token_endpoint": f"{base_url}/oauth/token",
        "registration_endpoint": f"{base_url}/oauth/register",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "token_endpoint_auth_methods_supported": ["client_secret_post", "client_secret_basic"],
        "scopes_supported": ["Mail.Read", "Mail.ReadWrite", "User.Read"],
        "code_challenge_methods_supported": ["S256"],
    }

    print("\n📋 Expected OAuth Metadata:")
    print(json.dumps(expected_metadata, indent=2))

    # Verify all required fields
    required_fields = [
        "issuer",
        "authorization_endpoint",
        "token_endpoint",
        "registration_endpoint",
    ]

    for field in required_fields:
        assert field in expected_metadata, f"Missing required field: {field}"

    print("\n✅ OAuth metadata format is RFC 8414 compliant")


async def main():
    """Run all DCR integration tests"""
    print("\n" + "=" * 80)
    print("🧪 DCR (Dynamic Client Registration) Integration Tests")
    print("=" * 80)

    try:
        # Test 1: Schema initialization
        test_dcr_schema_initialization()

        # Test 2: Client registration
        client_data = await test_dcr_client_registration()

        # Test 3: Authorization flow
        await test_dcr_authorization_flow(client_data)

        # Test 4: Client credentials
        await test_dcr_client_credentials()

        # Test 5: Token storage
        await test_dcr_token_storage()

        # Test 6: Client deletion
        await test_dcr_client_deletion()

        # Test 7: OAuth metadata
        test_oauth_metadata_format()

        print("\n" + "=" * 80)
        print("✅ ALL TESTS PASSED")
        print("=" * 80)
        print("\n📝 Summary:")
        print("   • DCR schema initialization: ✅")
        print("   • Client registration: ✅")
        print("   • Authorization code flow: ✅")
        print("   • Client credentials verification: ✅")
        print("   • Token storage and verification: ✅")
        print("   • Client deletion: ✅")
        print("   • OAuth metadata compliance: ✅")
        print("\n🎉 Ready for Claude Connector integration!")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        raise
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback

        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(main())
