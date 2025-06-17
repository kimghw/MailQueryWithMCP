#!/usr/bin/env python3
"""OpenRouter API 디버깅 테스트"""
import asyncio
import sys
import os

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.mail_processor.keyword_extractor_service import MailProcessorKeywordExtractorService
from infra.core.config import get_config


async def test_openrouter_api():
    """OpenRouter API 테스트"""
    print("=== OpenRouter API 디버깅 테스트 ===\n")
    
    # 설정 확인
    config = get_config()
    print(f"OpenRouter API Key 설정됨: {bool(config.openrouter_api_key)}")
    if config.openrouter_api_key:
        print(f"API Key 앞 10자리: {config.openrouter_api_key[:10]}...")
    print(f"OpenRouter Model: {config.openrouter_model}")
    print()
    
    # 키워드 추출 서비스 초기화
    extractor = MailProcessorKeywordExtractorService()
    print(f"서비스 API Key 설정됨: {bool(extractor.api_key)}")
    if extractor.api_key:
        print(f"서비스 API Key 앞 10자리: {extractor.api_key[:10]}...")
    print(f"서비스 Model: {extractor.model}")
    print(f"서비스 Base URL: {extractor.base_url}")
    print()
    
    # 테스트 텍스트
    test_text = "[EA004] 프로젝트 진행 상황 보고서 - 다음 회의는 6월 20일 예정입니다. 바이오가스 기반의 청정에너지 생산기술과 사업화방안에 대해 논의할 예정입니다."
    
    print(f"테스트 텍스트: {test_text}")
    print()
    
    # 키워드 추출 테스트
    print("키워드 추출 시작...")
    try:
        # 직접 OpenRouter API 호출 테스트
        print("\n=== 직접 OpenRouter API 호출 테스트 ===")
        keywords_direct = await extractor._call_openrouter_api(test_text, 5)
        print(f"직접 API 호출 결과: {keywords_direct}")
        
        print("\n=== 전체 키워드 추출 테스트 ===")
        result = await extractor.extract_keywords(test_text, max_keywords=5)
        print(f"결과: {result}")
        print(f"키워드: {result.keywords}")
        print(f"방법: {result.method}")
        print(f"실행시간: {result.execution_time_ms}ms")
        
        if result.method == "fallback" or result.method == "fallback_error":
            print("\n⚠️  OpenRouter API가 사용되지 않고 fallback이 사용되었습니다!")
            print("가능한 원인:")
            print("1. API 키가 올바르지 않음")
            print("2. API 호출 중 오류 발생")
            print("3. Rate limit 도달")
            print("4. 네트워크 연결 문제")
        else:
            print("\n✅ OpenRouter API가 정상적으로 사용되었습니다!")
            
    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")


if __name__ == "__main__":
    asyncio.run(test_openrouter_api())
