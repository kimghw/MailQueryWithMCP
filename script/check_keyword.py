#!/usr/bin/env python3
"""
키워드 추출 기능 확인 스크립트
"""

import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import asyncio
from datetime import datetime
from modules.mail_process.services.keyword_service import MailKeywordService
from modules.mail_process.utilities.text_cleaner import TextCleaner
from infra.core.logger import get_logger, update_all_loggers_level
from infra.core.config import get_config

# 로그 레벨 설정
update_all_loggers_level("DEBUG")
logger = get_logger(__name__)


async def test_keyword_extraction():
    """키워드 추출 테스트"""
    
    # 테스트 메일 샘플
    test_mails = [
        {
            "subject": "프로젝트 진행 상황 보고",
            "body": "안녕하세요. 이번 주 프로젝트 진행 상황을 보고드립니다. 개발팀에서는 신규 기능 구현을 완료했고, 테스트팀에서는 품질 검증을 진행 중입니다."
        },
        {
            "subject": "월간 매출 보고서",
            "body": "2024년 12월 매출 보고서입니다. 전월 대비 15% 성장했으며, 주요 고객사로부터 긍정적인 피드백을 받았습니다."
        },
        {
            "subject": "회의 일정 안내",
            "body": "다음 주 화요일 오후 3시에 정기 회의가 있습니다. 안건은 신규 프로젝트 계획과 예산 검토입니다."
        }
    ]
    
    # 서비스 초기화
    text_cleaner = TextCleaner()
    keyword_service = MailKeywordService()
    config = get_config()
    
    print("\n🔍 키워드 추출 테스트")
    print("=" * 60)
    
    # OpenRouter API 키 확인
    if config.openrouter_api_key:
        print(f"✅ OpenRouter API 키 설정됨")
        print(f"   모델: {config.openrouter_model}")
    else:
        print("❌ OpenRouter API 키 없음 - Fallback 모드 사용")
    
    print("\n" + "-" * 60)
    
    async with keyword_service:
        for i, mail in enumerate(test_mails, 1):
            print(f"\n📧 메일 {i}:")
            print(f"   제목: {mail['subject']}")
            print(f"   본문: {mail['body'][:50]}...")
            
            # 텍스트 정제
            clean_content = text_cleaner.clean_text(f"{mail['subject']} {mail['body']}")
            print(f"   정제된 텍스트: {clean_content[:100]}...")
            
            # 키워드 추출
            start_time = datetime.now()
            keywords = await keyword_service.extract_keywords(clean_content)
            elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            print(f"   추출된 키워드: {keywords}")
            print(f"   소요 시간: {elapsed_ms}ms")
    
    print("\n" + "=" * 60)
    print("✅ 테스트 완료")


async def check_mail_process_keywords():
    """실제 메일 처리에서 키워드 추출 확인"""
    
    from modules.mail_process.mail_processor_orchestrator import MailProcessorOrchestrator
    
    # 테스트용 메일 데이터
    test_mails = [
        {
            "id": "test-mail-001",
            "subject": "중요한 프로젝트 회의 안내",
            "from": {"emailAddress": {"address": "sender@example.com"}},
            "body": {"content": "안녕하세요. 다음 주 월요일에 신규 프로젝트 킥오프 미팅이 있습니다. 개발팀, 기획팀, 디자인팀 모두 참석 부탁드립니다."},
            "bodyPreview": "안녕하세요. 다음 주 월요일에 신규 프로젝트...",
            "receivedDateTime": "2025-01-15T10:00:00Z",
            "isRead": False,
            "hasAttachments": False,
            "importance": "high"
        }
    ]
    
    orchestrator = MailProcessorOrchestrator()
    
    try:
        print("\n🔧 메일 처리 파이프라인 테스트")
        print("=" * 60)
        
        # ENABLE_MAIL_DUPLICATE_CHECK 설정 확인
        dup_check = os.getenv("ENABLE_MAIL_DUPLICATE_CHECK", "true").lower() == "true"
        print(f"중복 체크: {'ON' if dup_check else 'OFF'}")
        
        # 메일 처리
        result = await orchestrator.process_mails(
            account_id="test_user",
            mails=test_mails,
            publish_batch_event=False
        )
        
        print(f"\n처리 결과:")
        print(f"  - 전체 메일: {result.get('total_mails', 0)}")
        print(f"  - 처리된 메일: {result.get('processed_mails', 0)}")
        print(f"  - 저장된 메일: {result.get('saved_mails', 0)}")
        print(f"  - 필터링된 메일: {result.get('filtered_mails', 0)}")
        print(f"  - 이벤트 발행: {result.get('events_published', 0)}")
        
        # 키워드 확인
        if 'keywords' in result:
            print(f"\n추출된 키워드:")
            for kw in result['keywords']:
                print(f"  - {kw}")
        else:
            print(f"\n❌ 키워드가 결과에 포함되지 않음")
            
    finally:
        await orchestrator.close()


async def main():
    """메인 함수"""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--process":
        # 전체 처리 파이프라인 테스트
        await check_mail_process_keywords()
    else:
        # 키워드 추출만 테스트
        await test_keyword_extraction()
    
    print("\n💡 팁:")
    print("  - 키워드 추출만 테스트: python check_keyword.py")
    print("  - 전체 파이프라인 테스트: python check_keyword.py --process")
    print("  - OpenRouter API 키 설정: .env 파일에 OPENROUTER_API_KEY 추가")


if __name__ == "__main__":
    asyncio.run(main())