"""GraphMailItem 테스트 시나리오"""
import asyncio
import sys
import os
from datetime import datetime

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from modules.mail_processor import MailProcessorOrchestrator, GraphMailItem
from infra.core.logger import get_logger

logger = get_logger(__name__)


async def test_graph_mail_item_processing():
    """GraphMailItem 객체 처리 테스트"""
    print("=== GraphMailItem 처리 테스트 시작 ===")
    
    try:
        # 오케스트레이터 초기화
        orchestrator = MailProcessorOrchestrator()
        print("✓ MailProcessorOrchestrator 초기화 성공")
        
        # GraphMailItem 객체 생성
        mail_item = GraphMailItem(
            id="test_graph_mail_001",
            subject="[테스트] GraphMailItem 처리 테스트",
            sender={"emailAddress": {"name": "테스트 발신자", "address": "test@example.com"}},
            from_address={"emailAddress": {"name": "테스트 발신자", "address": "test@example.com"}},
            to_recipients=[{"emailAddress": {"name": "수신자", "address": "recipient@example.com"}}],
            received_date_time=datetime.now(),
            body_preview="GraphMailItem 객체를 사용한 메일 처리 테스트입니다.",
            body={"contentType": "text", "content": "GraphMailItem 객체를 사용한 메일 처리 테스트입니다. 키워드 추출이 정상적으로 작동하는지 확인합니다."},
            is_read=False,
            has_attachments=False,
            importance="normal",
            web_link="https://outlook.office365.com/test"
        )
        
        print(f"✓ GraphMailItem 객체 생성 성공: {mail_item.id}")
        
        # 메일 처리
        result = await orchestrator.process_graph_mail_item("test_account", mail_item)
        
        print(f"✓ 메일 처리 완료:")
        print(f"  - 메일 ID: {result.mail_id}")
        print(f"  - 계정 ID: {result.account_id}")
        print(f"  - 발신자: {result.sender_address}")
        print(f"  - 제목: {result.subject}")
        print(f"  - 처리 상태: {result.processing_status}")
        print(f"  - 키워드: {result.keywords}")
        
        if result.error_message:
            print(f"  - 에러 메시지: {result.error_message}")
        
        print("✓ GraphMailItem 처리 테스트 완료")
        
    except Exception as e:
        print(f"✗ 테스트 실패: {str(e)}")
        logger.error(f"GraphMailItem 테스트 실패: {str(e)}", exc_info=True)
        return False
    
    print("=== GraphMailItem 처리 테스트 완료 ===\n")
    return True


async def test_graph_mail_item_validation():
    """GraphMailItem 유효성 검사 테스트"""
    print("=== GraphMailItem 유효성 검사 테스트 시작 ===")
    
    try:
        # 필수 필드만 있는 최소 객체
        minimal_mail = GraphMailItem(
            id="minimal_test",
            received_date_time=datetime.now()
        )
        print(f"✓ 최소 필드 객체 생성 성공: {minimal_mail.id}")
        
        # 모든 필드가 있는 완전한 객체
        complete_mail = GraphMailItem(
            id="complete_test",
            subject="완전한 테스트 메일",
            sender={"emailAddress": {"name": "발신자", "address": "sender@test.com"}},
            from_address={"emailAddress": {"name": "발신자", "address": "sender@test.com"}},
            to_recipients=[
                {"emailAddress": {"name": "수신자1", "address": "recipient1@test.com"}},
                {"emailAddress": {"name": "수신자2", "address": "recipient2@test.com"}}
            ],
            received_date_time=datetime.now(),
            body_preview="완전한 테스트 메일입니다.",
            body={"contentType": "html", "content": "<p>완전한 테스트 메일입니다.</p>"},
            is_read=True,
            has_attachments=True,
            importance="high",
            web_link="https://outlook.office365.com/complete"
        )
        print(f"✓ 완전한 객체 생성 성공: {complete_mail.id}")
        
        # 객체 직렬화 테스트
        minimal_dict = minimal_mail.model_dump()
        complete_dict = complete_mail.model_dump()
        
        print(f"✓ 객체 직렬화 성공")
        print(f"  - 최소 객체 필드 수: {len(minimal_dict)}")
        print(f"  - 완전한 객체 필드 수: {len(complete_dict)}")
        
        print("✓ GraphMailItem 유효성 검사 테스트 완료")
        
    except Exception as e:
        print(f"✗ 유효성 검사 테스트 실패: {str(e)}")
        logger.error(f"GraphMailItem 유효성 검사 실패: {str(e)}", exc_info=True)
        return False
    
    print("=== GraphMailItem 유효성 검사 테스트 완료 ===\n")
    return True


async def main():
    """메인 테스트 실행"""
    print("GraphMailItem 테스트 시작\n")
    
    test_results = []
    
    # 각 테스트 실행
    test_results.append(await test_graph_mail_item_validation())
    test_results.append(await test_graph_mail_item_processing())
    
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
