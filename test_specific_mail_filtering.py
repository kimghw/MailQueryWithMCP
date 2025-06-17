#!/usr/bin/env python3
"""특정 메일 필터링 테스트"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.mail_processor.mail_filter_service import MailProcessorFilterService

def test_specific_mail():
    """사용자가 제공한 특정 메일 필터링 테스트"""
    
    print("=== 특정 메일 필터링 테스트 ===")
    
    # 필터 서비스 초기화
    filter_service = MailProcessorFilterService()
    
    # 실제 메일 정보
    sender_address = "ejlee@krs.co.kr"
    subject = "전문가 자문 관련 요청"
    
    print(f"발신자: {sender_address}")
    print(f"제목: {subject}")
    print()
    
    # 현재 필터 설정 확인
    print("=== 현재 필터 설정 ===")
    print(f"차단된 도메인: {filter_service.blocked_domains}")
    print(f"차단된 키워드: {filter_service.blocked_keywords}")
    print(f"차단된 발신자 패턴: {filter_service.blocked_sender_patterns}")
    print(f"필터링 활성화: {filter_service.enable_filtering}")
    print(f"의심스러운 발신자 검사: {filter_service.enable_suspicious_check}")
    print()
    
    # 필터링 테스트
    should_process = filter_service.should_process(sender_address, subject)
    print(f"=== 필터링 결과 ===")
    print(f"처리 여부: {should_process}")
    
    if should_process:
        print("✅ 이 메일은 처리됩니다 (필터링되지 않음)")
    else:
        print("❌ 이 메일은 필터링됩니다 (처리되지 않음)")
    
    # 단계별 필터링 검사
    print("\n=== 단계별 필터링 검사 ===")
    
    # 1. 도메인 검사
    sender_domain = sender_address.split('@')[-1] if '@' in sender_address else ''
    domain_blocked = sender_domain in filter_service.blocked_domains
    print(f"1. 도메인 검사 ({sender_domain}): {'차단됨' if domain_blocked else '통과'}")
    
    # 2. 발신자 패턴 검사
    pattern_blocked = any(pattern in sender_address for pattern in filter_service.blocked_sender_patterns)
    print(f"2. 발신자 패턴 검사: {'차단됨' if pattern_blocked else '통과'}")
    
    # 3. 키워드 검사
    keyword_blocked = any(keyword in subject for keyword in filter_service.blocked_keywords)
    print(f"3. 제목 키워드 검사: {'차단됨' if keyword_blocked else '통과'}")
    
    # 4. 의심스러운 발신자 검사
    suspicious = filter_service._is_suspicious_sender(sender_address)
    print(f"4. 의심스러운 발신자 검사: {'의심스러움' if suspicious else '정상'}")
    
    print("\n=== 필터링 개선 제안 ===")
    if should_process:
        print("이 메일이 처리되는 이유:")
        print("- krs.co.kr 도메인은 차단 목록에 없음")
        print("- 발신자 패턴이 차단 목록에 없음") 
        print("- 제목에 차단 키워드가 없음")
        print("- 정상적인 업무 메일로 판단됨")
        print("\n만약 이 메일을 필터링하려면:")
        print("1. krs.co.kr 도메인을 BLOCKED_DOMAINS에 추가")
        print("2. 또는 ejlee@krs.co.kr을 BLOCKED_SENDER_PATTERNS에 추가")
        print("3. 또는 '자문', '요청' 등을 BLOCKED_KEYWORDS에 추가")

if __name__ == "__main__":
    test_specific_mail()
