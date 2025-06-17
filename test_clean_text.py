#!/usr/bin/env python3
"""_clean_text 함수 테스트"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.mail_processor.keyword_extractor_service import MailProcessorKeywordExtractorService

def test_clean_text():
    """_clean_text 함수 테스트"""
    
    # 테스트 데이터
    test_content = "수신: 한나래호 이진영 3항사님\r\n발신: 한국선급 이은주 선임\r\n\r\n이진영 3항사님께,\r\n\r\n안녕하세요. 한국선급 이은주입니다.\r\n\r\n항상 방선"
    
    print("=== _clean_text 함수 테스트 ===")
    print(f"원본 텍스트:")
    print(repr(test_content))
    print(f"원본 텍스트 (표시):")
    print(test_content)
    print()
    
    # 서비스 인스턴스 생성
    service = MailProcessorKeywordExtractorService()
    
    # _clean_text 함수 호출
    cleaned = service._clean_text(test_content)
    
    print(f"정제된 텍스트:")
    print(repr(cleaned))
    print(f"정제된 텍스트 (표시):")
    print(cleaned)
    print()
    
    # 단계별 확인
    print("=== 단계별 정제 과정 ===")
    
    # 1단계: \r\n -> \n 변환
    step1 = test_content.replace('\r\n', '\n')
    print(f"1단계 (\\r\\n -> \\n): {repr(step1)}")
    
    # 2단계: \r -> \n 변환
    step2 = step1.replace('\r', '\n')
    print(f"2단계 (\\r -> \\n): {repr(step2)}")
    
    # 최종 결과에 \r\n이 있는지 확인
    has_rn = '\r\n' in cleaned
    has_r = '\r' in cleaned
    has_n = '\n' in cleaned
    
    print(f"\n=== 결과 분석 ===")
    print(f"\\r\\n 포함 여부: {has_rn}")
    print(f"\\r 포함 여부: {has_r}")
    print(f"\\n 포함 여부: {has_n}")
    
    if has_rn or has_r:
        print("⚠️ 여전히 캐리지 리턴 문자가 남아있습니다!")
    else:
        print("✅ 캐리지 리턴 문자가 성공적으로 제거되었습니다.")

if __name__ == "__main__":
    test_clean_text()
