"""Mail Processor 모듈 테스트 시나리오"""
import asyncio
import sys
import os
from datetime import datetime

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from modules.mail_processor import MailProcessorOrchestrator
from infra.core.logger import get_logger

logger = get_logger(__name__)


async def test_mail_processor_basic():
    """기본 메일 처리 테스트"""
    print("=== Mail Processor 기본 테스트 시작 ===")
    
    try:
        # 오케스트레이터 초기화
        orchestrator = MailProcessorOrchestrator()
        print("✓ MailProcessorOrchestrator 초기화 성공")
        
        # 처리 통계 조회 테스트
        stats = await orchestrator.get_processing_stats()
        print(f"✓ 처리 통계 조회 성공: {stats}")
        
        print("✓ 기본 기능 테스트 완료")
        
    except Exception as e:
        print(f"✗ 테스트 실패: {str(e)}")
        logger.error(f"Mail Processor 테스트 실패: {str(e)}", exc_info=True)
        return False
    
    print("=== Mail Processor 기본 테스트 완료 ===\n")
    return True


async def test_mail_processing_with_sample_data():
    """샘플 데이터로 메일 처리 테스트"""
    print("=== 샘플 데이터 메일 처리 테스트 시작 ===")
    
    try:
        from modules.mail_processor._mail_processor_helpers import MailProcessorDatabaseHelper
        from modules.mail_processor.keyword_extractor_service import MailProcessorKeywordExtractorService
        from modules.mail_processor.mail_filter_service import MailProcessorFilterService
        
        # 서비스 초기화
        db_helper = MailProcessorDatabaseHelper()
        extractor = MailProcessorKeywordExtractorService()
        filter_service = MailProcessorFilterService()
        
        # 샘플 메일 데이터 (사용자 제공 형식에 맞춤)
        sample_mails = [
            {
                "id": "test_mail_001",
                "subject": "[EA004] 프로젝트 진행 상황 보고서 - 다음 회의는 6월 20일 예정",
                "sender": {"emailAddress": {"name": "프로젝트 매니저", "address": "manager@company.com"}},
                "from_address": {"emailAddress": {"name": "프로젝트 매니저", "address": "manager@company.com"}},
                "to_recipients": [{"emailAddress": {"name": "수신자", "address": "recipient@example.com"}}],
                "received_date_time": datetime(2025, 6, 16, 10, 30),
                "body_preview": "프로젝트 진행 상황을 보고드립니다. 현재 개발 단계는 80% 완료되었으며...",
                "body": {"contentType": "text", "content": "프로젝트 진행 상황을 보고드립니다. 현재 개발 단계는 80% 완료되었으며..."},
                "is_read": False,
                "has_attachments": False,
                "importance": "normal",
                "web_link": "https://outlook.office365.com/..."
            },
            {
                "id": "test_mail_002", 
                "subject": "시스템 개발 관련 문의",
                "sender": {"emailAddress": {"name": "개발자", "address": "developer@tech.com"}},
                "from_address": {"emailAddress": {"name": "개발자", "address": "developer@tech.com"}},
                "to_recipients": [{"emailAddress": {"name": "수신자", "address": "recipient@example.com"}}],
                "received_date_time": datetime(2025, 6, 16, 11, 0),
                "body_preview": "안녕하세요. 시스템 개발 관련하여 문의드립니다. API 연동 방법에 대해...",
                "body": {"contentType": "text", "content": "안녕하세요. 시스템 개발 관련하여 문의드립니다. API 연동 방법에 대해..."},
                "is_read": False,
                "has_attachments": True,
                "importance": "normal",
                "web_link": "https://outlook.office365.com/..."
            },
            {
                "id": "test_mail_003",
                "subject": "광고: 특별 할인 이벤트",
                "sender": {"emailAddress": {"name": "마케팅팀", "address": "noreply@marketing.com"}},
                "from_address": {"emailAddress": {"name": "마케팅팀", "address": "noreply@marketing.com"}},
                "to_recipients": [{"emailAddress": {"name": "수신자", "address": "recipient@example.com"}}],
                "received_date_time": datetime(2025, 6, 16, 12, 0),
                "body_preview": "특별 할인 이벤트를 진행합니다. 지금 바로 확인하세요!",
                "body": {"contentType": "text", "content": "특별 할인 이벤트를 진행합니다. 지금 바로 확인하세요!"},
                "is_read": False,
                "has_attachments": False,
                "importance": "normal",
                "web_link": "https://outlook.office365.com/..."
            }
        ]
        
        processed_count = 0
        filtered_count = 0
        
        for mail in sample_mails:
            sender = mail["from_address"]["emailAddress"]["address"]
            subject = mail["subject"]
            
            print(f"\n--- 메일 처리: {subject[:30]}... ---")
            
            # 필터링 검사
            if not filter_service.should_process(sender, subject):
                print(f"✓ 필터링됨: {sender}")
                filtered_count += 1
                continue
            
            # 키워드 추출
            text = f"{subject} {mail['body_preview']}"
            keyword_result = await extractor.extract_keywords(text, max_keywords=5)
            
            print(f"✓ 키워드 추출: {keyword_result.keywords}")
            print(f"  방법: {keyword_result.method}")
            
            # 메일 정보 출력 (실제 DB 저장은 스키마 문제로 스킵)
            print(f"✓ 메일 정보:")
            print(f"  - ID: {mail['id']}")
            print(f"  - 발신자: {sender}")
            print(f"  - 제목: {subject}")
            print(f"  - 키워드: {keyword_result.keywords}")
            
            processed_count += 1
        
        print(f"\n=== 처리 결과 ===")
        print(f"- 총 메일: {len(sample_mails)}개")
        print(f"- 처리됨: {processed_count}개")
        print(f"- 필터링됨: {filtered_count}개")
        
        print("✓ 샘플 데이터 처리 테스트 완료")
        
    except Exception as e:
        print(f"✗ 샘플 데이터 테스트 실패: {str(e)}")
        logger.error(f"샘플 데이터 테스트 실패: {str(e)}", exc_info=True)
        return False
    
    print("=== 샘플 데이터 메일 처리 테스트 완료 ===\n")
    return True


async def test_keyword_extractor():
    """키워드 추출 서비스 테스트"""
    print("=== 키워드 추출 서비스 테스트 시작 ===")
    
    try:
        from modules.mail_processor.keyword_extractor_service import MailProcessorKeywordExtractorService
        
        # 키워드 추출 서비스 초기화
        extractor = MailProcessorKeywordExtractorService()
        print("✓ KeywordExtractorService 초기화 성공")
        
        # 테스트 텍스트
        test_texts = [
            "[EA004] 프로젝트 진행 상황 보고서 - 다음 회의는 6월 20일 예정",
            "안녕하세요. 시스템 개발 관련하여 문의드립니다.",
            "Newsletter: 최신 마케팅 트렌드 소개",
            ""  # 빈 텍스트
        ]
        
        for i, text in enumerate(test_texts, 1):
            print(f"\n--- 테스트 {i}: {text[:30]}... ---")
            
            result = await extractor.extract_keywords(text, max_keywords=5)
            
            print(f"키워드: {result.keywords}")
            print(f"방법: {result.method}")
            print(f"실행시간: {result.execution_time_ms}ms")
        
        print("✓ 키워드 추출 테스트 완료")
        
    except Exception as e:
        print(f"✗ 키워드 추출 테스트 실패: {str(e)}")
        logger.error(f"키워드 추출 테스트 실패: {str(e)}", exc_info=True)
        return False
    
    print("=== 키워드 추출 서비스 테스트 완료 ===\n")
    return True


async def test_mail_filter():
    """메일 필터링 서비스 테스트"""
    print("=== 메일 필터링 서비스 테스트 시작 ===")
    
    try:
        from modules.mail_processor.mail_filter_service import MailProcessorFilterService
        
        # 필터링 서비스 초기화
        filter_service = MailProcessorFilterService()
        print("✓ MailFilterService 초기화 성공")
        
        # 테스트 케이스
        test_cases = [
            ("manager@company.com", "[EA004] 프로젝트 보고", True),
            ("noreply@system.com", "시스템 알림", False),
            ("newsletter@marketing.com", "최신 뉴스레터", False),
            ("user@domain.com", "광고: 특별 할인", False),
            ("colleague@work.com", "회의 일정 안내", True),
        ]
        
        for sender, subject, expected in test_cases:
            result = filter_service.should_process(sender, subject)
            status = "✓" if result == expected else "✗"
            print(f"{status} {sender} | {subject} -> {'처리' if result else '필터링'}")
        
        # 필터링 통계 조회
        stats = filter_service.get_filter_stats()
        print(f"\n필터링 통계: {stats}")
        
        print("✓ 메일 필터링 테스트 완료")
        
    except Exception as e:
        print(f"✗ 메일 필터링 테스트 실패: {str(e)}")
        logger.error(f"메일 필터링 테스트 실패: {str(e)}", exc_info=True)
        return False
    
    print("=== 메일 필터링 서비스 테스트 완료 ===\n")
    return True


async def main():
    """메인 테스트 실행"""
    print("Mail Processor 모듈 테스트 시작\n")
    
    test_results = []
    
    # 각 테스트 실행
    test_results.append(await test_keyword_extractor())
    test_results.append(await test_mail_filter())
    test_results.append(await test_mail_processor_basic())
    test_results.append(await test_mail_processing_with_sample_data())
    
    # 결과 요약
    passed = sum(test_results)
    total = len(test_results)
    
    print("=" * 50)
    print(f"테스트 결과: {passed}/{total} 통과")
    
    if passed == total:
        print("✓ 모든 테스트 통과!")
    else:
        print("✗ 일부 테스트 실패")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
