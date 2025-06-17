#!/usr/bin/env python3
"""실제 메일 처리 과정에서 _clean_text 호출 확인"""

import sys
import os
import asyncio
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.mail_processor.keyword_extractor_service import MailProcessorKeywordExtractorService
from modules.mail_processor._mail_processor_helpers import MailProcessorDataHelper

async def test_real_mail_processing():
    """실제 메일 처리 과정 테스트"""
    
    # 테스트 메일 데이터 (실제 Graph API 응답 형식)
    test_mail = {
        "id": "test_mail_id",
        "subject": "테스트 메일",
        "body": {
            "content": "수신: 한나래호 이진영 3항사님\r\n발신: 한국선급 이은주 선임\r\n\r\n이진영 3항사님께,\r\n\r\n안녕하세요. 한국선급 이은주입니다.\r\n\r\n항상 방선"
        },
        "bodyPreview": "수신: 한나래호 이진영 3항사님\r\n발신: 한국선급 이은주 선임\r\n\r\n이진영 3항사님께,\r\n\r\n안녕하세요. 한국선급 이은주입니다.\r\n\r\n항상 방선"
    }
    
    print("=== 실제 메일 처리 과정 테스트 ===")
    
    # 1. MailProcessorDataHelper.extract_mail_content() 호출
    print("1. MailProcessorDataHelper.extract_mail_content() 호출")
    extracted_content = MailProcessorDataHelper.extract_mail_content(test_mail)
    print(f"추출된 내용: {repr(extracted_content)}")
    print(f"\\r\\n 포함 여부: {'\\r\\n' in extracted_content}")
    print()
    
    # 2. KeywordExtractorService.extract_keywords() 호출
    print("2. KeywordExtractorService.extract_keywords() 호출")
    service = MailProcessorKeywordExtractorService()
    
    try:
        # 키워드 추출 (내부에서 _clean_text 호출됨)
        result = await service.extract_keywords(extracted_content)
        print(f"키워드 추출 결과: {result.keywords}")
        print(f"추출 방식: {result.method}")
        print(f"실행 시간: {result.execution_time_ms}ms")
        
        # 내부적으로 _clean_text가 호출되었는지 확인하기 위해 직접 호출
        print("\n3. _clean_text 직접 호출 확인")
        cleaned = service._clean_text(extracted_content)
        print(f"정제된 텍스트: {repr(cleaned)}")
        print(f"\\r\\n 포함 여부: {'\\r\\n' in cleaned}")
        
    except Exception as e:
        print(f"오류 발생: {e}")
    
    finally:
        await service.close()

if __name__ == "__main__":
    asyncio.run(test_real_mail_processing())
