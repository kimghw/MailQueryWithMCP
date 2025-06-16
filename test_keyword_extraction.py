#!/usr/bin/env python3
"""키워드 추출 서비스 테스트"""
import asyncio
import sys
import os

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.mail_processor.keyword_extractor_service import MailProcessorKeywordExtractorService


async def test_keyword_extraction():
    """키워드 추출 서비스 테스트"""
    print("=== 키워드 추출 서비스 테스트 ===\n")
    
    service = MailProcessorKeywordExtractorService()
    
    # 테스트 텍스트
    test_text = "[EA004] 프로젝트 진행 상황 보고서 - 다음 주 회의 일정 및 기술 검토 사항"
    
    print(f"📝 테스트 텍스트: {test_text}")
    print(f"🔧 API Key 설정: {'✅' if service.api_key else '❌'}")
    print(f"🤖 모델: {service.model}")
    
    try:
        # 키워드 추출 실행
        print("\n🔄 키워드 추출 중...")
        result = await service.extract_keywords(test_text, max_keywords=5)
        
        print(f"\n📊 추출 결과:")
        print(f"  - 키워드: {result.keywords}")
        print(f"  - 방법: {result.method}")
        print(f"  - 실행 시간: {result.execution_time_ms}ms")
        
        if result.keywords:
            print(f"\n✅ 키워드 추출 성공! {len(result.keywords)}개 키워드 추출됨")
            for i, keyword in enumerate(result.keywords, 1):
                print(f"  {i}. {keyword}")
        else:
            print("\n⚠️ 키워드가 추출되지 않았습니다")
            
    except Exception as e:
        print(f"\n❌ 키워드 추출 실패: {str(e)}")
        import traceback
        traceback.print_exc()


async def test_parsing_logic():
    """파싱 로직 테스트"""
    print("\n=== 파싱 로직 테스트 ===\n")
    
    service = MailProcessorKeywordExtractorService()
    
    # 다양한 형식의 응답 테스트
    test_cases = [
        ("콤마 구분", "EA004, 프로젝트, 진행, 상황, 보고서"),
        ("번호 매김", "1. EA004\n2. 프로젝트\n3. 진행\n4. 상황\n5. 보고서"),
        ("줄바꿈 구분", "EA004\n프로젝트\n진행\n상황\n보고서"),
        ("공백 구분", "EA004 프로젝트 진행 상황 보고서")
    ]
    
    for test_name, test_content in test_cases:
        print(f"📝 {test_name} 테스트:")
        print(f"   입력: {repr(test_content)}")
        
        keywords = service._parse_keywords(test_content)
        print(f"   결과: {keywords}")
        print()


if __name__ == "__main__":
    asyncio.run(test_keyword_extraction())
    asyncio.run(test_parsing_logic())
