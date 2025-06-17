#!/usr/bin/env python3
"""메일 필터링 서비스 테스트"""

import os
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from modules.mail_processor.mail_filter_service import MailProcessorFilterService


def test_mail_filter():
    """메일 필터링 서비스 테스트"""
    print("=== 메일 필터링 서비스 테스트 ===\n")
    
    # 필터링 서비스 초기화
    filter_service = MailProcessorFilterService()
    
    # 테스트 케이스들
    test_cases = [
        # (발신자, 제목, 예상결과, 설명)
        ("user@example.com", "일반 메일", True, "일반 메일"),
        ("noreply@company.com", "알림", False, "noreply 패턴"),
        ("newsletter@marketing.com", "뉴스레터", False, "newsletter 패턴"),
        ("user@newsletter.com", "일반 메일", False, "차단된 도메인"),
        ("user@example.com", "광고 메일입니다", False, "제목에 차단 키워드"),
        ("marketing123@example.com", "일반 메일", False, "발신자에 차단 키워드"),
        ("abc123def456@example.com", "일반 메일", False, "의심스러운 발신자 패턴"),
        ("user@example.org", "일반 메일", True, "example.org는 차단되지 않음"),
        ("", "제목", False, "빈 발신자"),
        ("user@example.com", "", True, "빈 제목"),
    ]
    
    print("필터링 설정 정보:")
    stats = filter_service.get_filter_stats()
    print(f"- 차단 도메인: {stats['blocked_domains_count']}개")
    print(f"- 차단 키워드: {stats['blocked_keywords_count']}개")
    print(f"- 차단 패턴: {stats['blocked_patterns_count']}개")
    print(f"- 필터링 활성화: {filter_service.filtering_enabled}")
    print(f"- 의심스러운 발신자 검사: {filter_service.suspicious_check_enabled}")
    print()
    
    # 테스트 실행
    passed = 0
    failed = 0
    
    for sender, subject, expected, description in test_cases:
        result = filter_service.should_process(sender, subject)
        status = "✅ PASS" if result == expected else "❌ FAIL"
        
        if result == expected:
            passed += 1
        else:
            failed += 1
            
        print(f"{status} | {description}")
        print(f"      발신자: '{sender}', 제목: '{subject}'")
        print(f"      예상: {expected}, 실제: {result}")
        print()
    
    print(f"=== 테스트 결과 ===")
    print(f"통과: {passed}개, 실패: {failed}개")
    print(f"성공률: {passed/(passed+failed)*100:.1f}%")
    
    return failed == 0


def test_dynamic_filter_management():
    """동적 필터 관리 테스트"""
    print("\n=== 동적 필터 관리 테스트 ===\n")
    
    filter_service = MailProcessorFilterService()
    
    # 새 도메인 추가 테스트
    test_domain = "testdomain.com"
    print(f"1. 도메인 '{test_domain}' 추가 전 테스트")
    result_before = filter_service.should_process(f"user@{test_domain}", "테스트")
    print(f"   처리 여부: {result_before}")
    
    filter_service.add_blocked_domain(test_domain)
    print(f"2. 도메인 '{test_domain}' 추가 후 테스트")
    result_after = filter_service.should_process(f"user@{test_domain}", "테스트")
    print(f"   처리 여부: {result_after}")
    
    # 키워드 추가 테스트
    test_keyword = "테스트키워드"
    print(f"\n3. 키워드 '{test_keyword}' 추가 전 테스트")
    result_before = filter_service.should_process("user@example.com", f"{test_keyword} 메일")
    print(f"   처리 여부: {result_before}")
    
    filter_service.add_blocked_keyword(test_keyword)
    print(f"4. 키워드 '{test_keyword}' 추가 후 테스트")
    result_after = filter_service.should_process("user@example.com", f"{test_keyword} 메일")
    print(f"   처리 여부: {result_after}")
    
    # 제거 테스트
    filter_service.remove_blocked_domain(test_domain)
    filter_service.remove_blocked_keyword(test_keyword)
    print(f"\n5. 도메인과 키워드 제거 후 테스트")
    result_removed = filter_service.should_process(f"user@{test_domain}", f"{test_keyword} 메일")
    print(f"   처리 여부: {result_removed}")


def test_environment_variables():
    """환경변수 설정 테스트"""
    print("\n=== 환경변수 설정 테스트 ===\n")
    
    # 현재 환경변수 출력
    env_vars = [
        'ENABLE_MAIL_FILTERING',
        'ENABLE_SUSPICIOUS_SENDER_CHECK',
        'BLOCKED_DOMAINS',
        'BLOCKED_KEYWORDS',
        'BLOCKED_SENDER_PATTERNS'
    ]
    
    for var in env_vars:
        value = os.getenv(var, "설정되지 않음")
        print(f"{var}: {value}")


if __name__ == "__main__":
    try:
        # 기본 필터링 테스트
        success = test_mail_filter()
        
        # 동적 필터 관리 테스트
        test_dynamic_filter_management()
        
        # 환경변수 테스트
        test_environment_variables()
        
        if success:
            print("\n🎉 모든 테스트가 성공했습니다!")
            sys.exit(0)
        else:
            print("\n❌ 일부 테스트가 실패했습니다.")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 테스트 실행 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
