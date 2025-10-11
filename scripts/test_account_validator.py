#!/usr/bin/env python3
"""
Account Validator 테스트 스크립트
"""

import re
from typing import Dict, List, Optional, Tuple


# Copy AccountValidator class to avoid import dependencies
class AccountValidator:
    """Validator for account enrollment data"""

    # Valid OAuth permission patterns
    VALID_PERMISSIONS = [
        "Mail.Read",
        "Mail.ReadWrite",
        "Mail.Send",
        "Files.Read",
        "Files.ReadWrite",
        "Files.ReadWrite.All",
        "Sites.Read.All",
        "Sites.ReadWrite.All",
        "offline_access",
        "User.Read",
        "Calendars.ReadWrite"
    ]

    @staticmethod
    def validate_user_id(user_id: str) -> Tuple[bool, Optional[str]]:
        if not user_id:
            return False, "user_id cannot be empty"
        if not isinstance(user_id, str):
            return False, "user_id must be a string"
        if len(user_id) < 3:
            return False, "user_id must be at least 3 characters long"
        if len(user_id) > 50:
            return False, "user_id must be at most 50 characters long"
        if not re.match(r'^[a-zA-Z0-9._-]+$', user_id):
            return False, "user_id can only contain letters, numbers, dots, underscores, and hyphens"
        if not re.match(r'^[a-zA-Z0-9]', user_id):
            return False, "user_id must start with a letter or number"
        return True, None

    @staticmethod
    def validate_email(email: str) -> Tuple[bool, Optional[str]]:
        if not email:
            return False, "email cannot be empty"
        if not isinstance(email, str):
            return False, "email must be a string"
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return False, "email format is invalid (expected: user@domain.com)"
        if len(email) > 254:
            return False, "email is too long (max 254 characters)"
        local_part = email.split('@')[0]
        if len(local_part) > 64:
            return False, "email local part is too long (max 64 characters)"
        return True, None

    @staticmethod
    def validate_oauth_client_id(client_id: str) -> Tuple[bool, Optional[str]]:
        if not client_id:
            return False, "oauth_client_id cannot be empty"
        if not isinstance(client_id, str):
            return False, "oauth_client_id must be a string"
        guid_pattern = r'^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$'
        if not re.match(guid_pattern, client_id):
            return False, "oauth_client_id must be a valid GUID format (e.g., 12345678-1234-1234-1234-123456789012)"
        return True, None

    @staticmethod
    def validate_oauth_client_secret(client_secret: str) -> Tuple[bool, Optional[str]]:
        if not client_secret:
            return False, "oauth_client_secret cannot be empty"
        if not isinstance(client_secret, str):
            return False, "oauth_client_secret must be a string"
        if len(client_secret) < 8:
            return False, "oauth_client_secret is too short (minimum 8 characters)"
        if len(client_secret) > 256:
            return False, "oauth_client_secret is too long (maximum 256 characters)"
        return True, None

    @staticmethod
    def validate_oauth_tenant_id(tenant_id: str) -> Tuple[bool, Optional[str]]:
        if not tenant_id:
            return False, "oauth_tenant_id cannot be empty"
        if not isinstance(tenant_id, str):
            return False, "oauth_tenant_id must be a string"
        guid_pattern = r'^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$'
        if not re.match(guid_pattern, tenant_id):
            return False, "oauth_tenant_id must be a valid GUID format (e.g., 12345678-1234-1234-1234-123456789012)"
        return True, None

    @staticmethod
    def validate_redirect_uri(redirect_uri: str) -> Tuple[bool, Optional[str]]:
        if not redirect_uri:
            return False, "oauth_redirect_uri cannot be empty"
        if not isinstance(redirect_uri, str):
            return False, "oauth_redirect_uri must be a string"
        url_pattern = r'^https?://[a-zA-Z0-9.-]+(:[0-9]+)?(/.*)?$'
        if not re.match(url_pattern, redirect_uri):
            return False, "oauth_redirect_uri must be a valid HTTP/HTTPS URL"
        return True, None

    @classmethod
    def validate_permissions(cls, permissions: List[str]) -> Tuple[bool, Optional[str]]:
        if not permissions:
            return False, "delegated_permissions cannot be empty"
        if not isinstance(permissions, list):
            return False, "delegated_permissions must be a list"
        invalid_perms = []
        for perm in permissions:
            if not isinstance(perm, str):
                return False, f"permission must be a string, got: {type(perm)}"
            if perm not in cls.VALID_PERMISSIONS:
                invalid_perms.append(perm)
        if invalid_perms:
            return False, f"invalid permissions: {', '.join(invalid_perms)}. Valid permissions: {', '.join(cls.VALID_PERMISSIONS)}"
        return True, None

    @classmethod
    def validate_enrollment_data(cls, data: Dict) -> Tuple[bool, List[str]]:
        errors = []

        user_id = data.get("user_id")
        is_valid, error = cls.validate_user_id(user_id)
        if not is_valid:
            errors.append(f"user_id: {error}")

        email = data.get("email")
        is_valid, error = cls.validate_email(email)
        if not is_valid:
            errors.append(f"email: {error}")

        client_id = data.get("oauth_client_id")
        is_valid, error = cls.validate_oauth_client_id(client_id)
        if not is_valid:
            errors.append(f"oauth_client_id: {error}")

        client_secret = data.get("oauth_client_secret")
        is_valid, error = cls.validate_oauth_client_secret(client_secret)
        if not is_valid:
            errors.append(f"oauth_client_secret: {error}")

        tenant_id = data.get("oauth_tenant_id")
        is_valid, error = cls.validate_oauth_tenant_id(tenant_id)
        if not is_valid:
            errors.append(f"oauth_tenant_id: {error}")

        redirect_uri = data.get("oauth_redirect_uri")
        if redirect_uri:
            is_valid, error = cls.validate_redirect_uri(redirect_uri)
            if not is_valid:
                errors.append(f"oauth_redirect_uri: {error}")

        permissions = data.get("delegated_permissions")
        if permissions:
            is_valid, error = cls.validate_permissions(permissions)
            if not is_valid:
                errors.append(f"delegated_permissions: {error}")

        return len(errors) == 0, errors


def test_user_id():
    """User ID 검증 테스트"""
    print("\n=== Test 1: User ID Validation ===")

    test_cases = [
        ("kimghw", True, "Valid user_id"),
        ("user123", True, "Valid with numbers"),
        ("user.name", True, "Valid with dot"),
        ("user-name", True, "Valid with hyphen"),
        ("user_name", True, "Valid with underscore"),
        ("ab", False, "Too short"),
        ("a" * 51, False, "Too long"),
        ("123user", True, "Starting with number is OK"),
        ("user@name", False, "Invalid character @"),
        (".username", False, "Starting with dot"),
        ("", False, "Empty string"),
        (None, False, "None value"),
    ]

    for user_id, expected_valid, description in test_cases:
        is_valid, error = AccountValidator.validate_user_id(user_id)
        status = "✓" if is_valid == expected_valid else "✗"
        print(f"{status} {description}: '{user_id}' -> {is_valid} {f'({error})' if error else ''}")


def test_email():
    """Email 검증 테스트"""
    print("\n=== Test 2: Email Validation ===")

    test_cases = [
        ("kimghw@krs.co.kr", True, "Valid email"),
        ("user@example.com", True, "Valid email"),
        ("user.name@example.co.kr", True, "Valid with dot"),
        ("user+tag@example.com", True, "Valid with plus"),
        ("user@", False, "Missing domain"),
        ("@example.com", False, "Missing local part"),
        ("user@example", False, "Missing TLD"),
        ("user example@test.com", False, "Space in email"),
        ("", False, "Empty string"),
        (None, False, "None value"),
    ]

    for email, expected_valid, description in test_cases:
        is_valid, error = AccountValidator.validate_email(email)
        status = "✓" if is_valid == expected_valid else "✗"
        print(f"{status} {description}: '{email}' -> {is_valid} {f'({error})' if error else ''}")


def test_client_id():
    """OAuth Client ID 검증 테스트"""
    print("\n=== Test 3: OAuth Client ID Validation ===")

    test_cases = [
        ("12345678-1234-1234-1234-123456789012", True, "Valid GUID"),
        ("abcdef12-ab12-cd34-ef56-1234567890ab", True, "Valid GUID with letters"),
        ("12345678-1234-1234-1234-12345678901", False, "Too short"),
        ("12345678-1234-1234-1234-1234567890123", False, "Too long"),
        ("not-a-guid", False, "Invalid format"),
        ("", False, "Empty string"),
        (None, False, "None value"),
    ]

    for client_id, expected_valid, description in test_cases:
        is_valid, error = AccountValidator.validate_oauth_client_id(client_id)
        status = "✓" if is_valid == expected_valid else "✗"
        print(f"{status} {description}: -> {is_valid} {f'({error})' if error else ''}")


def test_client_secret():
    """OAuth Client Secret 검증 테스트"""
    print("\n=== Test 4: OAuth Client Secret Validation ===")

    test_cases = [
        ("SecretKey123456", True, "Valid secret"),
        ("a1b2c3d4e5f6g7h8", True, "Valid secret with mixed chars"),
        ("short", False, "Too short (< 8)"),
        ("a" * 257, False, "Too long (> 256)"),
        ("", False, "Empty string"),
        (None, False, "None value"),
    ]

    for secret, expected_valid, description in test_cases:
        is_valid, error = AccountValidator.validate_oauth_client_secret(secret)
        status = "✓" if is_valid == expected_valid else "✗"
        print(f"{status} {description}: -> {is_valid} {f'({error})' if error else ''}")


def test_tenant_id():
    """OAuth Tenant ID 검증 테스트"""
    print("\n=== Test 5: OAuth Tenant ID Validation ===")

    test_cases = [
        ("87654321-4321-4321-4321-210987654321", True, "Valid GUID"),
        ("not-a-guid", False, "Invalid format"),
        ("", False, "Empty string"),
    ]

    for tenant_id, expected_valid, description in test_cases:
        is_valid, error = AccountValidator.validate_oauth_tenant_id(tenant_id)
        status = "✓" if is_valid == expected_valid else "✗"
        print(f"{status} {description}: -> {is_valid} {f'({error})' if error else ''}")


def test_redirect_uri():
    """OAuth Redirect URI 검증 테스트"""
    print("\n=== Test 6: OAuth Redirect URI Validation ===")

    test_cases = [
        ("http://localhost:5000/auth/callback", True, "Valid localhost"),
        ("https://example.com/callback", True, "Valid HTTPS"),
        ("http://192.168.1.1:8080/auth", True, "Valid with IP and port"),
        ("ftp://example.com", False, "Invalid protocol"),
        ("not-a-url", False, "Not a URL"),
        ("", False, "Empty string"),
    ]

    for uri, expected_valid, description in test_cases:
        is_valid, error = AccountValidator.validate_redirect_uri(uri)
        status = "✓" if is_valid == expected_valid else "✗"
        print(f"{status} {description}: '{uri}' -> {is_valid} {f'({error})' if error else ''}")


def test_permissions():
    """Permissions 검증 테스트"""
    print("\n=== Test 7: Permissions Validation ===")

    test_cases = [
        (["Mail.ReadWrite", "Mail.Send"], True, "Valid permissions"),
        (["offline_access"], True, "Valid single permission"),
        (["Mail.ReadWrite", "InvalidPermission"], False, "Invalid permission included"),
        ([], False, "Empty list"),
        (None, False, "None value"),
        ("not_a_list", False, "Not a list"),
    ]

    for perms, expected_valid, description in test_cases:
        is_valid, error = AccountValidator.validate_permissions(perms)
        status = "✓" if is_valid == expected_valid else "✗"
        print(f"{status} {description}: -> {is_valid} {f'({error})' if error else ''}")


def test_full_enrollment():
    """전체 Enrollment 데이터 검증 테스트"""
    print("\n=== Test 8: Full Enrollment Data Validation ===")

    # Valid data
    valid_data = {
        "user_id": "kimghw",
        "email": "kimghw@krs.co.kr",
        "oauth_client_id": "12345678-1234-1234-1234-123456789012",
        "oauth_client_secret": "SecretKey123456",
        "oauth_tenant_id": "87654321-4321-4321-4321-210987654321",
        "oauth_redirect_uri": "http://localhost:5000/auth/callback",
        "delegated_permissions": ["Mail.ReadWrite", "Mail.Send", "offline_access"]
    }

    is_valid, errors = AccountValidator.validate_enrollment_data(valid_data)
    if is_valid:
        print("✓ Valid enrollment data: All fields passed validation")
    else:
        print(f"✗ Valid data failed: {errors}")

    # Invalid data (multiple errors)
    invalid_data = {
        "user_id": "ab",  # Too short
        "email": "invalid-email",  # Invalid format
        "oauth_client_id": "not-a-guid",  # Invalid GUID
        "oauth_client_secret": "short",  # Too short
        "oauth_tenant_id": "also-not-guid",  # Invalid GUID
        "oauth_redirect_uri": "ftp://invalid",  # Invalid protocol
        "delegated_permissions": ["InvalidPerm"]  # Invalid permission
    }

    is_valid, errors = AccountValidator.validate_enrollment_data(invalid_data)
    if not is_valid:
        print(f"✓ Invalid data correctly rejected with {len(errors)} errors:")
        for err in errors:
            print(f"    - {err}")
    else:
        print("✗ Invalid data should have been rejected")

    # Minimal valid data (without optional fields)
    minimal_data = {
        "user_id": "testuser",
        "email": "test@example.com",
        "oauth_client_id": "12345678-1234-1234-1234-123456789012",
        "oauth_client_secret": "MinimalSecret123",
        "oauth_tenant_id": "87654321-4321-4321-4321-210987654321"
    }

    is_valid, errors = AccountValidator.validate_enrollment_data(minimal_data)
    if is_valid:
        print("✓ Minimal valid data: Passed validation without optional fields")
    else:
        print(f"✗ Minimal data failed: {errors}")


def main():
    print("=" * 60)
    print("Account Validator Test")
    print("=" * 60)

    test_user_id()
    test_email()
    test_client_id()
    test_client_secret()
    test_tenant_id()
    test_redirect_uri()
    test_permissions()
    test_full_enrollment()

    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
