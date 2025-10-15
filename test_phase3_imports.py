"""Phase 3: Import 경로 수정 테스트"""

import sys
sys.path.insert(0, '/home/kimghw/IACSGRAPH/modules')

def test_mail_process_internal_imports():
    """mail_process 내부 import 테스트"""
    print("\n[1] Testing mail_process internal imports...")

    try:
        from mail_process import email_saver
        from mail_process import attachment_downloader
        from mail_process import file_collector
        from mail_process import email_scanner
        print("✅ All mail_process modules imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_mail_process_exports():
    """mail_process __init__.py export 테스트"""
    print("\n[2] Testing mail_process exports...")

    try:
        from mail_process import (
            sanitize_filename,
            ensure_directory_exists,
            truncate_text,
            format_file_size,
            is_valid_email,
            AttachmentDownloader,
            EmailSaver,
            FileConverterOrchestrator,
            SubscriptionEmailScanner,
            SubscriptionFileCollector
        )
        print("✅ All exports available from mail_process")
        return True
    except ImportError as e:
        print(f"❌ Export failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_filters_imports():
    """filters 모듈 import 테스트"""
    print("\n[3] Testing filters imports...")

    try:
        from mail_query_without_db.filters import (
            KeywordFilter,
            ConversationFilter,
            SenderBlocker
        )
        print("✅ All filter classes imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Filter import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_email_query_imports():
    """email_query.py의 새 import 테스트"""
    print("\n[4] Testing email_query tool imports...")

    try:
        # email_query.py가 사용할 import들
        from mail_process import (
            AttachmentDownloader,
            EmailSaver,
            FileConverterOrchestrator,
            sanitize_filename
        )
        from mail_query_without_db.filters import (
            KeywordFilter,
            ConversationFilter,
            SenderBlocker
        )
        print("✅ email_query.py imports ready")
        return True
    except ImportError as e:
        print(f"❌ email_query imports failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_no_circular_imports():
    """순환 import 체크"""
    print("\n[5] Checking for circular imports...")

    try:
        # 순서대로 import 시도
        import mail_process
        print("  - mail_process imported")

        import mail_query_without_db.filters
        print("  - mail_query_without_db.filters imported")

        from mail_query_without_db.mcp_server.tools import email_query
        print("  - email_query tool imported")

        print("✅ No circular imports detected")
        return True
    except ImportError as e:
        print(f"❌ Circular import detected: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Phase 3: Import 경로 수정 테스트")
    print("=" * 60)

    tests = [
        test_mail_process_internal_imports,
        test_mail_process_exports,
        test_filters_imports,
        test_email_query_imports,
        test_no_circular_imports,
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            failed += 1
            print(f"❌ Test crashed: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    if failed == 0:
        print("\n🎉 All import tests passed! Ready for Phase 4.")
    else:
        print("\n⚠️  Some tests failed. Fix imports before proceeding.")

    sys.exit(0 if failed == 0 else 1)
