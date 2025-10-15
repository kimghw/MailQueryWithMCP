"""Phase 2: Filters 모듈 테스트"""

import sys
sys.path.insert(0, '/home/kimghw/IACSGRAPH/modules')

from dataclasses import dataclass
from typing import List, Optional

# Mock objects for testing
@dataclass
class MockMail:
    """테스트용 메일 Mock"""
    subject: str = ""
    body_preview: str = ""
    from_address: dict = None
    to_recipients: List[dict] = None

@dataclass
class MockKeywordFilter:
    """키워드 필터 설정"""
    and_keywords: Optional[List[str]] = None
    or_keywords: Optional[List[str]] = None
    not_keywords: Optional[List[str]] = None


def test_keyword_filter():
    """KeywordFilter 테스트"""
    from mail_query_without_db.filters import KeywordFilter

    print("\n[1] AND keywords test")
    messages = [
        MockMail(subject="GitHub notification", body_preview="Pull request merged"),
        MockMail(subject="GitHub alert", body_preview="Issue created"),
        MockMail(subject="GitLab update", body_preview="Merge request"),
    ]

    filter_config = MockKeywordFilter(and_keywords=["github", "pull"])
    result = KeywordFilter.filter_by_keywords(messages, filter_config)
    assert len(result) == 1, f"Expected 1 result, got {len(result)}"
    print(f"✅ AND filter: {len(result)} messages matched")

    print("\n[2] OR keywords test")
    messages = [
        MockMail(subject="Invoice from AWS", body_preview="Your monthly bill"),
        MockMail(subject="Receipt from Azure", body_preview="Payment received"),
        MockMail(subject="Newsletter", body_preview="Weekly updates"),
    ]

    filter_config = MockKeywordFilter(or_keywords=["invoice", "receipt"])
    result = KeywordFilter.filter_by_keywords(messages, filter_config)
    assert len(result) == 2, f"Expected 2 results, got {len(result)}"
    print(f"✅ OR filter: {len(result)} messages matched")

    print("\n[3] NOT keywords test")
    messages = [
        MockMail(subject="Important update", body_preview="New features"),
        MockMail(subject="Spam message", body_preview="Buy now!"),
        MockMail(subject="Team meeting", body_preview="Tomorrow at 10am"),
    ]

    filter_config = MockKeywordFilter(not_keywords=["spam"])
    result = KeywordFilter.filter_by_keywords(messages, filter_config)
    assert len(result) == 2, f"Expected 2 results, got {len(result)}"
    print(f"✅ NOT filter: {len(result)} messages matched")


def test_conversation_filter():
    """ConversationFilter 테스트"""
    from mail_query_without_db.filters import ConversationFilter

    print("\n[1] Received messages test")
    messages = [
        MockMail(
            subject="Hello from Alice",
            from_address={"emailAddress": {"address": "alice@example.com"}}
        ),
        MockMail(
            subject="Hello from Bob",
            from_address={"emailAddress": {"address": "bob@example.com"}}
        ),
        MockMail(
            subject="Hello from Charlie",
            from_address={"emailAddress": {"address": "charlie@example.com"}}
        ),
    ]

    result = ConversationFilter.filter_conversation(
        messages, "kimghw", ["alice@example.com", "bob@example.com"]
    )
    assert len(result) == 2, f"Expected 2 results, got {len(result)}"
    print(f"✅ Received messages filter: {len(result)} messages matched")

    print("\n[2] Sent messages test")
    messages = [
        MockMail(
            subject="To Alice",
            from_address={"emailAddress": {"address": "kimghw@example.com"}},
            to_recipients=[{"emailAddress": {"address": "alice@example.com"}}]
        ),
        MockMail(
            subject="To Bob",
            from_address={"emailAddress": {"address": "kimghw@example.com"}},
            to_recipients=[{"emailAddress": {"address": "bob@example.com"}}]
        ),
        MockMail(
            subject="To Charlie",
            from_address={"emailAddress": {"address": "kimghw@example.com"}},
            to_recipients=[{"emailAddress": {"address": "charlie@example.com"}}]
        ),
    ]

    result = ConversationFilter.filter_conversation(
        messages, "kimghw", ["alice@example.com"]
    )
    assert len(result) == 1, f"Expected 1 result, got {len(result)}"
    print(f"✅ Sent messages filter: {len(result)} messages matched")


def test_sender_blocker():
    """SenderBlocker 테스트"""
    from mail_query_without_db.filters import SenderBlocker

    print("\n[1] Exact email blocking test")
    blocker = SenderBlocker(["spam@example.com"])

    messages = [
        MockMail(
            subject="Spam message",
            from_address={"emailAddress": {"address": "spam@example.com"}}
        ),
        MockMail(
            subject="Valid message",
            from_address={"emailAddress": {"address": "legitimate@example.com"}}
        ),
    ]

    result = blocker.filter_messages(messages)
    assert len(result) == 1, f"Expected 1 result, got {len(result)}"
    assert "Valid" in result[0].subject
    print(f"✅ Exact blocking: {len(result)} messages passed")

    print("\n[2] Domain blocking test")
    blocker = SenderBlocker(["spam-domain.com"])

    messages = [
        MockMail(
            subject="Spam 1",
            from_address={"emailAddress": {"address": "user1@spam-domain.com"}}
        ),
        MockMail(
            subject="Spam 2",
            from_address={"emailAddress": {"address": "user2@spam-domain.com"}}
        ),
        MockMail(
            subject="Valid message",
            from_address={"emailAddress": {"address": "user@good-domain.com"}}
        ),
    ]

    result = blocker.filter_messages(messages)
    assert len(result) == 1, f"Expected 1 result, got {len(result)}"
    print(f"✅ Domain blocking: {len(result)} messages passed")

    print("\n[3] Case-insensitive blocking test")
    blocker = SenderBlocker(["SPAM@EXAMPLE.COM"])

    messages = [
        MockMail(
            subject="Lowercase spam",
            from_address={"emailAddress": {"address": "spam@example.com"}}
        ),
        MockMail(
            subject="Mixed case spam",
            from_address={"emailAddress": {"address": "Spam@Example.Com"}}
        ),
        MockMail(
            subject="Valid",
            from_address={"emailAddress": {"address": "valid@example.com"}}
        ),
    ]

    result = blocker.filter_messages(messages)
    assert len(result) == 1, f"Expected 1 result, got {len(result)}"
    print(f"✅ Case-insensitive: {len(result)} messages passed")


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 2: Filters 모듈 테스트")
    print("=" * 60)

    tests = [
        ("KeywordFilter", test_keyword_filter),
        ("ConversationFilter", test_conversation_filter),
        ("SenderBlocker", test_sender_blocker),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"Testing {name}")
        print(f"{'='*60}")
        try:
            test_func()
            passed += 1
            print(f"\n✅ {name} PASSED")
        except Exception as e:
            failed += 1
            print(f"\n❌ {name} FAILED: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    sys.exit(0 if failed == 0 else 1)
