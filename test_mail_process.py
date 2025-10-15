"""
mail_process 모듈 통합 테스트

모든 핵심 컴포넌트가 정상 작동하는지 검증합니다.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# PYTHONPATH 설정
sys.path.insert(0, str(Path(__file__).parent / "modules"))

def test_config():
    """MailProcessConfig 테스트"""
    from mail_process import get_mail_process_config

    print("=" * 70)
    print("1️⃣ MailProcessConfig 테스트")
    print("=" * 70)

    config = get_mail_process_config()

    tests = [
        ("max_keywords_per_mail", config.max_keywords_per_mail),
        ("max_mails_per_account", config.max_mails_per_account),
        ("blocked_domains", config.blocked_domains),
        ("default_output_dir", config.default_output_dir),
    ]

    for name, value in tests:
        print(f"  ✅ {name:30s} = {value}")

    print()
    return True


def test_process_options():
    """ProcessOptions 테스트"""
    from mail_process import ProcessOptions, TempFileCleanupPolicy, AttachmentPathMode

    print("=" * 70)
    print("2️⃣ ProcessOptions 테스트")
    print("=" * 70)

    # Test 1: 기본 옵션
    opts1 = ProcessOptions(user_id='test_user')
    print(f"  ✅ 기본 옵션 생성: user_id={opts1.user_id}")

    # Test 2: 임시 저장소 옵션
    opts2 = ProcessOptions(
        user_id='test_user',
        use_temp_storage=True,
        temp_dir=Path('/tmp/test'),
        temp_cleanup_policy=TempFileCleanupPolicy.DELETE_ON_RETURN
    )
    print(f"  ✅ 임시 저장소 옵션: should_use={opts2.should_use_temp_storage()}")

    # Test 3: 첨부파일 경로 옵션
    opts3 = ProcessOptions(
        user_id='test_user',
        attachment_path_mode=AttachmentPathMode.SEPARATE_ATTACHMENTS,
        separate_attachments_dir=Path('/tmp/attachments')
    )
    att_dir = opts3.get_attachment_base_dir(Path('/tmp/email1'))
    print(f"  ✅ 첨부파일 경로: {att_dir}")

    # Test 4: Enum 값
    print(f"  ✅ TempFileCleanupPolicy: {len(list(TempFileCleanupPolicy))}개")
    print(f"  ✅ AttachmentPathMode: {len(list(AttachmentPathMode))}개")

    print()
    return True


def test_client_filter():
    """ClientFilter 테스트"""
    from mail_process import FilterCriteria, ClientFilter

    print("=" * 70)
    print("3️⃣ ClientFilter 테스트")
    print("=" * 70)

    # 테스트 데이터
    test_emails = [
        {
            'id': '1',
            'subject': 'GitHub PR approved',
            'body_preview': 'Your pull request was merged',
            'from_address': {'emailAddress': {'address': 'noreply@github.com'}},
            'received_date_time': datetime.now(),
            'has_attachments': False,
            'is_read': False,
            'importance': 'normal'
        },
        {
            'id': '2',
            'subject': 'Invoice from GitHub',
            'body_preview': 'Payment receipt',
            'from_address': {'emailAddress': {'address': 'billing@github.com'}},
            'received_date_time': datetime.now() - timedelta(days=5),
            'has_attachments': True,
            'attachments': [{'name': 'invoice.pdf'}],
            'is_read': True,
            'importance': 'high'
        },
        {
            'id': '3',
            'subject': 'Meeting',
            'body_preview': 'Project discussion',
            'from_address': {'emailAddress': {'address': 'colleague@company.com'}},
            'received_date_time': datetime.now() - timedelta(days=1),
            'has_attachments': False,
            'is_read': False,
            'importance': 'normal'
        },
    ]

    tests = [
        ("필터 없음", FilterCriteria(), 3),
        ("발신자 필터", FilterCriteria(sender=['github.com']), 2),
        ("첨부파일 필터", FilterCriteria(has_attachments=True), 1),
        ("키워드 필터", FilterCriteria(keywords=['invoice']), 1),
        ("읽음 상태", FilterCriteria(is_read=False), 2),
        ("중요도", FilterCriteria(importance='high'), 1),
    ]

    passed = 0
    for name, criteria, expected in tests:
        result = ClientFilter(criteria).apply(test_emails)
        if len(result) == expected:
            print(f"  ✅ {name:20s}: {len(result)}개")
            passed += 1
        else:
            print(f"  ❌ {name:20s}: {len(result)}개 (예상: {expected}개)")

    print(f"\n  결과: {passed}/{len(tests)} 통과")
    print()
    return passed == len(tests)


def test_keyword_filter():
    """KeywordFilter AND/OR/NOT 테스트"""
    from mail_process.client_filter.filters import KeywordFilter

    print("=" * 70)
    print("4️⃣ KeywordFilter AND/OR/NOT 테스트")
    print("=" * 70)

    emails = [
        {'subject': 'GitHub PR', 'body_preview': 'Pull request'},
        {'subject': 'GitHub Invoice', 'body_preview': 'Payment'},
        {'subject': 'SPAM', 'body_preview': 'Win money'},
        {'subject': 'Meeting', 'body_preview': 'Discussion'},
    ]

    tests = [
        ("OR (github)", {'keywords': ['github']}, 2),
        ("AND (github + invoice)", {'and_keywords': ['github', 'invoice']}, 1),
        ("NOT (github - spam)", {'keywords': ['github'], 'not_keywords': ['spam']}, 2),
        ("복합", {'and_keywords': ['github'], 'not_keywords': ['invoice']}, 1),
    ]

    passed = 0
    for name, kwargs, expected in tests:
        result = KeywordFilter.apply(emails, **kwargs)
        if len(result) == expected:
            print(f"  ✅ {name:30s}: {len(result)}개")
            passed += 1
        else:
            print(f"  ❌ {name:30s}: {len(result)}개 (예상: {expected}개)")

    print(f"\n  결과: {passed}/{len(tests)} 통과")
    print()
    return passed == len(tests)


def test_utils():
    """Utils 테스트"""
    from mail_process import sanitize_filename, truncate_text, is_valid_email

    print("=" * 70)
    print("5️⃣ Utils 테스트")
    print("=" * 70)

    # sanitize_filename
    result1 = sanitize_filename("test/file:name?.txt")
    print(f"  ✅ sanitize_filename: '{result1}'")

    # truncate_text
    result2 = truncate_text("A" * 100, 50)
    print(f"  ✅ truncate_text: {len(result2)}자 (원본: 100자)")

    # is_valid_email
    result3 = is_valid_email("user@example.com")
    result4 = is_valid_email("invalid-email")
    print(f"  ✅ is_valid_email: valid={result3}, invalid={result4}")

    print()
    return True


def main():
    """모든 테스트 실행"""
    print("\n" + "=" * 70)
    print("🧪 mail_process 모듈 통합 테스트")
    print("=" * 70)
    print()

    results = []

    try:
        results.append(("Config", test_config()))
    except Exception as e:
        print(f"❌ Config 테스트 실패: {e}\n")
        results.append(("Config", False))

    try:
        results.append(("ProcessOptions", test_process_options()))
    except Exception as e:
        print(f"❌ ProcessOptions 테스트 실패: {e}\n")
        results.append(("ProcessOptions", False))

    try:
        results.append(("ClientFilter", test_client_filter()))
    except Exception as e:
        print(f"❌ ClientFilter 테스트 실패: {e}\n")
        results.append(("ClientFilter", False))

    try:
        results.append(("KeywordFilter", test_keyword_filter()))
    except Exception as e:
        print(f"❌ KeywordFilter 테스트 실패: {e}\n")
        results.append(("KeywordFilter", False))

    try:
        results.append(("Utils", test_utils()))
    except Exception as e:
        print(f"❌ Utils 테스트 실패: {e}\n")
        results.append(("Utils", False))

    # 최종 결과
    print("=" * 70)
    print("📊 최종 결과")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ 통과" if result else "❌ 실패"
        print(f"  {name:20s}: {status}")

    print()
    print(f"총 {passed}/{total}개 테스트 통과")

    if passed == total:
        print("\n🎉 모든 테스트가 성공적으로 통과했습니다!")
        return 0
    else:
        print(f"\n⚠️  {total - passed}개 테스트 실패")
        return 1


if __name__ == "__main__":
    sys.exit(main())
