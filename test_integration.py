"""통합 테스트: 전체 리팩토링 검증"""

import sys
sys.path.insert(0, '/home/kimghw/IACSGRAPH/modules')

from dataclasses import dataclass
from typing import List

def test_full_email_query_flow():
    """전체 메일 조회 플로우 테스트"""
    print("\n[INTEGRATION] Testing full email query flow...")

    # 여기서는 실제 MCP 서버를 실행하지 않고
    # 필요한 컴포넌트들이 제대로 import되고 사용 가능한지만 확인

    try:
        # 1. Core imports
        from mail_process import (
            EmailSaver,
            AttachmentDownloader,
            FileConverterOrchestrator
        )
        print("  ✅ mail_process components imported")

        # 2. Filter imports
        from mail_query_without_db.filters import (
            KeywordFilter,
            ConversationFilter,
            SenderBlocker
        )
        print("  ✅ Filter classes imported")

        # 3. 각 컴포넌트 인스턴스 생성 테스트
        email_saver = EmailSaver(output_dir="/tmp/test_emails")
        attachment_downloader = AttachmentDownloader(output_dir="/tmp/test_attachments")
        file_converter = FileConverterOrchestrator()
        print("  ✅ mail_process components instantiated")

        blocker = SenderBlocker(["spam@example.com"])
        print("  ✅ SenderBlocker instantiated")

        # 4. 필터 로직 간단 테스트
        @dataclass
        class MockMail:
            from_address: dict
            subject: str = ""
            body_preview: str = ""
            to_recipients: List[dict] = None

        test_messages = [
            MockMail(
                from_address={"emailAddress": {"address": "spam@example.com"}},
                subject="Spam",
                body_preview="Buy now"
            ),
            MockMail(
                from_address={"emailAddress": {"address": "friend@example.com"}},
                subject="Meeting tomorrow",
                body_preview="Let's meet at 10am"
            ),
        ]

        # 차단 필터 적용
        filtered = blocker.filter_messages(test_messages)
        assert len(filtered) == 1, "Blocker should remove spam"
        print("  ✅ Blocker filter works")

        # 키워드 필터 적용
        @dataclass
        class KeywordFilterConfig:
            and_keywords: list = None
            or_keywords: list = None
            not_keywords: list = None

        kw_config = KeywordFilterConfig(and_keywords=["meeting"])
        keyword_filtered = KeywordFilter.filter_by_keywords(filtered, kw_config)
        assert len(keyword_filtered) == 1, "Keyword filter should work"
        print("  ✅ Keyword filter works")

        # 대화 필터 테스트
        conversation_messages = [
            MockMail(
                from_address={"emailAddress": {"address": "alice@example.com"}},
                subject="Hello from Alice"
            ),
            MockMail(
                from_address={"emailAddress": {"address": "bob@example.com"}},
                subject="Hello from Bob"
            ),
        ]

        conv_filtered = ConversationFilter.filter_conversation(
            conversation_messages, "kimghw", ["alice@example.com"]
        )
        assert len(conv_filtered) == 1, "Conversation filter should work"
        print("  ✅ Conversation filter works")

        print("\n✅ Full integration test PASSED")

        return True

    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_email_query_tool_import():
    """EmailQueryTool import 및 초기화 테스트"""
    print("\n[INTEGRATION] Testing EmailQueryTool...")

    try:
        # EmailQueryTool 자체 import는 config 의존성 때문에 스킵
        # 대신 필요한 모든 import가 정상인지만 확인
        from mail_process import AttachmentDownloader, EmailSaver, FileConverterOrchestrator
        from mail_query_without_db.filters import KeywordFilter, ConversationFilter, SenderBlocker

        print("  ✅ All EmailQueryTool dependencies can be imported")
        return True

    except Exception as e:
        print(f"  ❌ EmailQueryTool dependencies import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_no_core_imports():
    """core 모듈이 더 이상 import되지 않는지 확인"""
    print("\n[INTEGRATION] Testing core module removal...")

    try:
        # core 모듈을 import하려고 하면 실패해야 함
        try:
            from mail_query_without_db.core import utils
            print("  ❌ core.utils should not be importable!")
            return False
        except ImportError:
            print("  ✅ core.utils correctly removed")

        try:
            from mail_query_without_db.core.converters import FileConverterOrchestrator
            print("  ❌ core.converters should not be importable!")
            return False
        except ImportError:
            print("  ✅ core.converters correctly removed")

        return True

    except Exception as e:
        print(f"  ❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("통합 테스트")
    print("=" * 60)

    tests = [
        ("Full email query flow", test_full_email_query_flow),
        ("EmailQueryTool dependencies", test_email_query_tool_import),
        ("Core module removal", test_no_core_imports),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"Testing: {name}")
        print(f"{'='*60}")
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
        print("\n🎉 Integration test PASSED!")
        print("Ready to test with live MCP server.")
    else:
        print("\n❌ Integration test FAILED!")

    sys.exit(0 if failed == 0 else 1)
