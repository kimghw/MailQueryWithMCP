"""Phase 1: Utils 통합 테스트"""

import sys
sys.path.insert(0, '/home/kimghw/IACSGRAPH')

def test_utils_import():
    """utils 모듈 import 테스트"""
    try:
        from mail_process.utils import (
            sanitize_filename,
            ensure_directory_exists,
            truncate_text,
            format_file_size,
            is_valid_email
        )
        print("✅ All utils functions imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def test_sanitize_filename():
    """파일명 정리 함수 테스트"""
    from mail_process.utils import sanitize_filename

    test_cases = [
        ("hello/world.txt", "hello_world.txt"),
        ("test<file>.doc", "test_file_.doc"),
        ("normal_file.pdf", "normal_file.pdf"),
        ("a" * 200 + ".txt", "a" * 96 + ".txt"),  # max_length test
    ]

    for input_name, expected in test_cases:
        result = sanitize_filename(input_name)
        assert result == expected, f"Expected {expected}, got {result}"
        print(f"✅ sanitize_filename('{input_name[:20]}...') = '{result[:20]}...'")

def test_format_file_size():
    """파일 크기 포맷 테스트"""
    from mail_process.utils import format_file_size

    test_cases = [
        (1024, "1.0 KB"),
        (1048576, "1.0 MB"),
        (500, "500.0 B"),
    ]

    for size, expected in test_cases:
        result = format_file_size(size)
        assert result == expected, f"Expected {expected}, got {result}"
        print(f"✅ format_file_size({size}) = '{result}'")

def test_is_valid_email():
    """이메일 검증 테스트"""
    from mail_process.utils import is_valid_email

    valid_emails = ["test@example.com", "user.name@domain.co.kr"]
    invalid_emails = ["invalid", "test@", "@domain.com"]

    for email in valid_emails:
        assert is_valid_email(email), f"{email} should be valid"
        print(f"✅ is_valid_email('{email}') = True")

    for email in invalid_emails:
        assert not is_valid_email(email), f"{email} should be invalid"
        print(f"✅ is_valid_email('{email}') = False")

def test_truncate_text():
    """텍스트 자르기 테스트"""
    from mail_process.utils import truncate_text

    long_text = "This is a very long text that needs to be truncated"
    result = truncate_text(long_text, max_length=20)
    assert len(result) <= 20, f"Text should be truncated to 20 chars"
    assert result.endswith("..."), f"Truncated text should end with ..."
    print(f"✅ truncate_text works correctly: '{result}'")

if __name__ == "__main__":
    print("=" * 60)
    print("Phase 1: Utils 통합 테스트")
    print("=" * 60)

    tests = [
        ("Import 테스트", test_utils_import),
        ("sanitize_filename 테스트", test_sanitize_filename),
        ("format_file_size 테스트", test_format_file_size),
        ("is_valid_email 테스트", test_is_valid_email),
        ("truncate_text 테스트", test_truncate_text),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        print(f"\n[TEST] {name}")
        try:
            test_func()
            passed += 1
            print(f"✅ {name} PASSED")
        except Exception as e:
            failed += 1
            print(f"❌ {name} FAILED: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    sys.exit(0 if failed == 0 else 1)
