"""Kafka 이벤트 발행 테스트"""
import asyncio
import json
from datetime import datetime
from modules.mail_processor.mail_processor_orchestrator import MailProcessorOrchestrator
from modules.mail_processor.mail_processor_schema import GraphMailItem
from infra.core.logger import get_logger

logger = get_logger(__name__)

async def test_kafka_event_publishing():
    """Kafka 이벤트 발행 테스트"""
    print("=== Kafka 이벤트 발행 테스트 시작 ===")
    
    try:
        # MailProcessorOrchestrator 초기화
        orchestrator = MailProcessorOrchestrator()
        print("✓ MailProcessorOrchestrator 초기화 성공")
        
        # 테스트용 GraphMailItem 생성 (고유한 ID 사용)
        import uuid
        unique_id = f"kafka_test_mail_{str(uuid.uuid4())[:8]}"
        
        test_mail = GraphMailItem(
            id=unique_id,
            subject="[테스트] Kafka 이벤트 발행 테스트",
            sender={  # sender 필드 사용
                "emailAddress": {
                    "address": "manager@company.com",
                    "name": "Test Manager"
                }
            },
            body_preview="Kafka 이벤트 발행을 테스트하는 메일입니다.",
            received_date_time=datetime.now(),
            has_attachments=False,
            importance="normal",
            is_read=False
        )
        print(f"✓ GraphMailItem 객체 생성 성공: {test_mail.id}")
        
        # 메일 처리 (Kafka 이벤트 발행 포함)
        result = await orchestrator.process_graph_mail_item(test_mail, "kafka_test_account")
        
        print("✓ 메일 처리 완료:")
        print(f"  - 메일 ID: {result.mail_id}")
        print(f"  - 계정 ID: {result.account_id}")
        print(f"  - 발신자: {result.sender_address}")
        print(f"  - 제목: {result.subject}")
        print(f"  - 처리 상태: {result.processing_status}")
        print(f"  - 키워드: {result.keywords}")
        if result.error_message:
            print(f"  - 에러 메시지: {result.error_message}")
        
        print("✓ Kafka 이벤트 발행 테스트 완료")
        return True
        
    except Exception as e:
        print(f"✗ Kafka 이벤트 발행 테스트 실패: {str(e)}")
        logger.error(f"Kafka 이벤트 테스트 실패: {str(e)}")
        return False

async def test_kafka_event_data_structure():
    """Kafka 이벤트 데이터 구조 테스트"""
    print("\n=== Kafka 이벤트 데이터 구조 테스트 시작 ===")
    
    try:
        from modules.mail_processor.mail_processor_schema import MailReceivedEvent
        import uuid
        
        # 테스트용 이벤트 생성
        event = MailReceivedEvent(
            event_id=str(uuid.uuid4()),
            account_id="test_account",
            occurred_at=datetime.now(),
            request_params={
                "$select": "id,subject,from,body,bodyPreview,receivedDateTime",
                "$top": 50
            },
            response_data={
                "value": [{
                    "id": "test_mail_001",
                    "subject": "테스트 메일",
                    "from": {"emailAddress": {"address": "test@example.com"}},
                    "bodyPreview": "테스트 내용",
                    "receivedDateTime": "2025-06-16T14:30:00Z"
                }]
            },
            response_timestamp=datetime.now()
        )
        
        # 이벤트 직렬화 테스트
        event_data = event.model_dump()
        
        # datetime 필드들을 ISO 형식 문자열로 변환
        if 'occurred_at' in event_data and isinstance(event_data['occurred_at'], datetime):
            event_data['occurred_at'] = event_data['occurred_at'].isoformat()
        if 'response_timestamp' in event_data and isinstance(event_data['response_timestamp'], datetime):
            event_data['response_timestamp'] = event_data['response_timestamp'].isoformat()
        
        # JSON 직렬화 테스트
        json_data = json.dumps(event_data, ensure_ascii=False, indent=2)
        
        print("✓ 이벤트 객체 생성 성공")
        print("✓ 이벤트 직렬화 성공")
        print("✓ JSON 변환 성공")
        print(f"✓ 이벤트 데이터 크기: {len(json_data)} bytes")
        print(f"✓ 이벤트 필드 수: {len(event_data)}")
        
        # 이벤트 구조 출력
        print("\n--- 이벤트 데이터 구조 ---")
        for key, value in event_data.items():
            if key == 'response_data':
                print(f"  {key}: [메일 데이터 포함]")
            else:
                print(f"  {key}: {type(value).__name__}")
        
        print("✓ Kafka 이벤트 데이터 구조 테스트 완료")
        return True
        
    except Exception as e:
        print(f"✗ Kafka 이벤트 데이터 구조 테스트 실패: {str(e)}")
        logger.error(f"Kafka 이벤트 데이터 구조 테스트 실패: {str(e)}")
        return False

async def main():
    """메인 테스트 함수"""
    print("Kafka 이벤트 테스트 시작\n")
    
    test_results = []
    
    # 테스트 1: Kafka 이벤트 발행
    result1 = await test_kafka_event_publishing()
    test_results.append(result1)
    
    # 테스트 2: 이벤트 데이터 구조
    result2 = await test_kafka_event_data_structure()
    test_results.append(result2)
    
    # 결과 출력
    passed = sum(test_results)
    total = len(test_results)
    
    print(f"\n{'='*50}")
    print(f"테스트 결과: {passed}/{total} 통과")
    
    if passed == total:
        print("✓ 모든 Kafka 이벤트 테스트 통과!")
    else:
        print("✗ 일부 테스트 실패")
    
    return passed == total

if __name__ == "__main__":
    asyncio.run(main())
