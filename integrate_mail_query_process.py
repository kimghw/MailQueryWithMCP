#!/usr/bin/env python3
"""
Mail Query + Mail Processor 통합 테스트 스크립트
최근 메일을 조회하고 처리하며 Kafka 이벤트 발행까지 확인
"""
import asyncio
import sys
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any

# 모듈 임포트
from modules.mail_query import (
    MailQueryOrchestrator,
    MailQueryRequest,
    MailQueryFilters,
    PaginationOptions
)
from modules.mail_processor import (
    MailProcessorOrchestrator,
    GraphMailItem,
    ProcessingStatus
)
from infra.core.logger import get_logger
from infra.core.database import get_database_manager
from infra.core.kafka_client import get_kafka_client

logger = get_logger(__name__)


class MailIntegrationProcessor:
    """메일 조회 및 처리 통합 클래스"""
    
    def __init__(self):
        self.mail_query_orchestrator = MailQueryOrchestrator()
        self.mail_processor_orchestrator = MailProcessorOrchestrator()
        self.db_manager = get_database_manager()
        self.kafka_client = get_kafka_client()
        
        # Kafka 이벤트 발행 통계
        self.kafka_events_published = []
        self.kafka_publish_errors = []
    
    async def process_recent_mails(self, user_id: str = "kimghw", mail_count: int = 6) -> dict:
        """최근 메일 조회 및 처리 통합 워크플로우"""
        start_time = datetime.now()
        
        # 통계 초기화
        self.kafka_events_published = []
        self.kafka_publish_errors = []
        
        try:
            logger.info(f"🚀 메일 통합 처리 시작")
            logger.info(f"==================================================")
            logger.info(f"🔄 [CALL STACK] MailIntegrationProcessor.process_recent_mails() 시작")
            logger.info(f"📋 [PARAMS] 사용자: {user_id}, 조회 개수: {mail_count}")
            logger.info(f"=== 메일 통합 처리 시작 ===")
            
            # 1단계: Mail Query로 최근 메일 조회
            logger.info(f"🔄 [CALL STACK] → 1단계: _query_recent_mails() 호출")
            logger.info("1단계: 최근 메일 조회 중...")
            query_result = await self._query_recent_mails(user_id, mail_count)
            
            if not query_result['success']:
                return {
                    'success': False,
                    'error': query_result['error'],
                    'stage': 'mail_query'
                }
            
            messages = query_result['messages']
            logger.info(f"조회 완료: {len(messages)}개 메일")
            
            # 2단계: Mail Processor로 각 메일 처리 + Kafka 이벤트 발행
            logger.info("2단계: 메일 처리 중...")
            logger.info(f"🔄 [CALL STACK] → 2단계: _process_messages() 실행")
            processing_results = await self._process_messages(user_id, messages)
            
            # 3단계: Kafka 이벤트 발행 상태 확인
            await self._verify_kafka_events()
            
            # 4단계: 결과 집계
            execution_time = (datetime.now() - start_time).total_seconds()
            
            result = {
                'success': True,
                'user_id': user_id,
                'total_queried': len(messages),
                'processing_results': processing_results,
                'kafka_stats': {
                    'events_published': len(self.kafka_events_published),
                    'publish_errors': len(self.kafka_publish_errors),
                    'published_event_ids': [e['event_id'] for e in self.kafka_events_published]
                },
                'summary': self._create_summary(processing_results),
                'execution_time_seconds': round(execution_time, 2),
                'query_info': query_result.get('query_info', {}),
                'timestamp': start_time.isoformat()
            }
            
            logger.info(f"=== 통합 처리 완료 ===")
            logger.info(f"총 실행 시간: {execution_time:.2f}초")
            
            return result
            
        except Exception as e:
            logger.error(f"통합 처리 실패: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'stage': 'integration',
                'execution_time_seconds': (datetime.now() - start_time).total_seconds()
            }
    
    async def _query_recent_mails(self, user_id: str, mail_count: int) -> dict:
        """Mail Query 모듈로 최근 메일 조회"""
        try:
            logger.info(f"🔄 [CALL STACK] → → _query_recent_mails() 실행")
            logger.info(f"📋 [PARAMS] user_id={user_id}, mail_count={mail_count}")
            
            # 최근 7일간의 메일만 조회 (성능 최적화)
            date_from = datetime.now() - timedelta(days=7)
            logger.info(f"📅 [FILTER] 조회 기간: {date_from.strftime('%Y-%m-%d')} ~ 현재")
            
            # 메일 조회 요청 구성
            logger.info(f"🔧 [CONFIG] MailQueryRequest 구성 중...")
            request = MailQueryRequest(
                user_id=user_id,
                filters=MailQueryFilters(
                    date_from=date_from
                ),
                pagination=PaginationOptions(
                    top=mail_count,  # 요청한 개수만큼만 조회
                    skip=0,
                    max_pages=1  # 1페이지만 조회
                ),
                select_fields=[
                    "id", "subject", "from", "sender", "receivedDateTime", 
                    "bodyPreview", "body", "hasAttachments", "importance", "isRead"
                ]
            )
            
            # Mail Query 실행
            logger.info(f"🔗 [MODULE] MailQueryOrchestrator.mail_query_user_emails() 호출")
            async with self.mail_query_orchestrator as orchestrator:
                response = await orchestrator.mail_query_user_emails(request)
            
            logger.info(f"✅ [SUCCESS] 메일 조회 성공: {response.total_fetched}개")
            logger.info(f"⏱️ [PERF] Mail Query 실행시간: {response.execution_time_ms}ms")
            
            return {
                'success': True,
                'messages': response.messages,
                'query_info': {
                    'total_fetched': response.total_fetched,
                    'execution_time_ms': response.execution_time_ms,
                    'has_more': response.has_more,
                    'performance_estimate': response.query_info.get('performance_estimate', 'UNKNOWN')
                }
            }
            
        except Exception as e:
            logger.error(f"메일 조회 실패: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'messages': []
            }
    
    async def _process_messages(self, user_id: str, messages: List[GraphMailItem]) -> List[dict]:
        """Mail Processor 모듈로 각 메일 처리"""
        logger.info(f"📋 [PARAMS] user_id={user_id}, messages_count={len(messages)}")
        processing_results = []
        
        # 원래 Kafka 발행 함수를 래핑하여 모니터링
        original_publish = self.mail_processor_orchestrator.kafka_helper.publish_kafka_event
        
        async def monitored_publish(account_id: str, mail: Dict, keywords: List[str] = None):
            """Kafka 발행을 모니터링하는 래퍼 함수"""
            try:
                # 원래 함수 호출
                await original_publish(account_id, mail, keywords)
                
                # 발행 성공 기록
                event_info = {
                    'event_id': mail.get('id', 'unknown'),
                    'account_id': account_id,
                    'subject': mail.get('subject', ''),
                    'keywords': keywords or [],
                    'timestamp': datetime.now().isoformat()
                }
                self.kafka_events_published.append(event_info)
                logger.info(f"📤 [KAFKA] 이벤트 발행 성공: {event_info['event_id']}")
                
            except Exception as e:
                # 발행 실패 기록
                error_info = {
                    'event_id': mail.get('id', 'unknown'),
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
                self.kafka_publish_errors.append(error_info)
                logger.error(f"❌ [KAFKA] 이벤트 발행 실패: {error_info['event_id']} - {str(e)}")
                raise
        
        # 모니터링 함수로 교체
        self.mail_processor_orchestrator.kafka_helper.publish_kafka_event = monitored_publish
        
        try:
            for i, message in enumerate(messages, 1):
                try:
                    logger.info(f"📧 [MAIL {i}/{len(messages)}] 처리 중: {message.subject[:50]}...")
                    logger.info(f"🔗 [MODULE] MailProcessorOrchestrator.process_graph_mail_item() 호출")
                    
                    # Mail Processor로 개별 메일 처리
                    processed_result = await self.mail_processor_orchestrator.process_graph_mail_item(
                        mail_item=message,
                        account_id=user_id
                    )
                    
                    # 결과 정리
                    result = {
                        'mail_id': message.id,
                        'subject': message.subject or 'No Subject',
                        'sender': self._extract_sender_address(message),
                        'received_time': message.received_date_time.isoformat(),
                        'processing_status': processed_result.processing_status.value,
                        'keywords': processed_result.keywords,
                        'error_message': processed_result.error_message
                    }
                    
                    processing_results.append(result)
                    
                    # 간단한 로그
                    status_emoji = {
                        ProcessingStatus.SUCCESS: "✅",
                        ProcessingStatus.SKIPPED: "⏭️",
                        ProcessingStatus.FAILED: "❌"
                    }
                    
                    emoji = status_emoji.get(processed_result.processing_status, "❓")
                    logger.info(f"{emoji} [RESULT] 메일 {i}: {processed_result.processing_status.value}")
                    
                    if processed_result.keywords:
                        logger.info(f"📊 [DATA] 키워드 추출: {len(processed_result.keywords)}개")
                        logger.info(f"🏷️ [KEYWORDS] {', '.join(processed_result.keywords)}")
                    
                    if processed_result.error_message:
                        logger.warning(f"⚠️ [ERROR] 오류: {processed_result.error_message}")
                    
                except Exception as e:
                    logger.error(f"메일 {i} 처리 실패: {str(e)}")
                    processing_results.append({
                        'mail_id': message.id,
                        'subject': message.subject or 'No Subject',
                        'sender': self._extract_sender_address(message),
                        'received_time': message.received_date_time.isoformat(),
                        'processing_status': 'ERROR',
                        'keywords': [],
                        'error_message': str(e)
                    })
        
        finally:
            # 원래 함수로 복원
            self.mail_processor_orchestrator.kafka_helper.publish_kafka_event = original_publish
        
        return processing_results
    
    async def _verify_kafka_events(self):
        """Kafka 이벤트 발행 상태 검증"""
        logger.info("🔍 [KAFKA] 이벤트 발행 상태 검증 중...")
        
        if self.kafka_events_published:
            logger.info(f"✅ [KAFKA] 총 {len(self.kafka_events_published)}개 이벤트 발행 성공")
            for event in self.kafka_events_published[:3]:  # 처음 3개만 표시
                logger.info(f"   - {event['event_id']}: {len(event['keywords'])}개 키워드")
        
        if self.kafka_publish_errors:
            logger.warning(f"❌ [KAFKA] 총 {len(self.kafka_publish_errors)}개 이벤트 발행 실패")
            for error in self.kafka_publish_errors:
                logger.warning(f"   - {error['event_id']}: {error['error']}")
    
    def _extract_sender_address(self, message: GraphMailItem) -> str:
        """메시지에서 발신자 주소 추출"""
        try:
            # from_address 필드 확인
            if message.from_address and isinstance(message.from_address, dict):
                email_addr = message.from_address.get('emailAddress', {})
                if email_addr and email_addr.get('address'):
                    return email_addr['address']
            
            # sender 필드 확인
            if message.sender and isinstance(message.sender, dict):
                email_addr = message.sender.get('emailAddress', {})
                if email_addr and email_addr.get('address'):
                    return email_addr['address']
            
            return 'Unknown Sender'
            
        except Exception:
            return 'Unknown Sender'
    
    def _create_summary(self, processing_results: List[dict]) -> dict:
        """처리 결과 요약 생성"""
        total = len(processing_results)
        success_count = sum(1 for r in processing_results if r['processing_status'] == 'SUCCESS')
        skipped_count = sum(1 for r in processing_results if r['processing_status'] == 'SKIPPED')
        failed_count = sum(1 for r in processing_results if r['processing_status'] in ['FAILED', 'ERROR'])
        
        # 키워드 통계
        all_keywords = []
        for result in processing_results:
            all_keywords.extend(result.get('keywords', []))
        
        # 키워드 빈도 계산
        from collections import Counter
        keyword_counter = Counter(all_keywords)
        top_keywords = [kw for kw, _ in keyword_counter.most_common(10)]
        
        return {
            'total_mails': total,
            'success_count': success_count,
            'skipped_count': skipped_count,
            'failed_count': failed_count,
            'success_rate': round((success_count / total * 100) if total > 0 else 0, 1),
            'total_keywords_extracted': len(all_keywords),
            'unique_keywords_count': len(set(all_keywords)),
            'top_keywords': top_keywords,
            'kafka_events_published': len(self.kafka_events_published),
            'kafka_publish_errors': len(self.kafka_publish_errors)
        }
    
    async def close(self):
        """리소스 정리"""
        try:
            await self.mail_query_orchestrator.close()
            # Kafka flush
            self.kafka_client.flush()
        except Exception as e:
            logger.error(f"리소스 정리 실패: {str(e)}")


async def main():
    """메인 실행 함수"""
    print("🚀 Mail Integration Test 시작")
    print("=" * 50)
    
    # 사용자 설정
    user_id = "kimghw"  # 실제 사용자 ID
    mail_count = 6      # 조회할 메일 개수
    
    processor = MailIntegrationProcessor()
    
    try:
        # 명령행 인수 확인
        if len(sys.argv) > 1:
            if sys.argv[1] == "--clear-data":
                print("🗑️  데이터 초기화 모드")
                print("=" * 50)
                
                # 테이블 정리
                mail_history_result = processor.db_manager.clear_table_data("mail_history")
                print(f"📧 mail_history: {mail_history_result['message']}")
                
                logs_result = processor.db_manager.clear_table_data("processing_logs")
                print(f"📝 processing_logs: {logs_result['message']}")
                
                print("\n✅ 데이터 초기화 완료")
                return
            
            elif sys.argv[1] == "--check-kafka":
                print("🔍 Kafka 토픽 확인 모드")
                print("=" * 50)
                
                # Kafka 토픽 메타데이터 확인
                try:
                    metadata = processor.kafka_client.get_topic_metadata('email-raw-data')
                    print(f"✅ Kafka 토픽 상태: {metadata}")
                    
                    # 연결 상태 확인
                    if processor.kafka_client.health_check():
                        print("✅ Kafka 연결 상태: 정상")
                    else:
                        print("❌ Kafka 연결 상태: 비정상")
                except Exception as e:
                    print(f"❌ Kafka 확인 실패: {str(e)}")
                return
        
        # 통합 처리 실행
        result = await processor.process_recent_mails(user_id, mail_count)
        
        # 결과 출력
        print("\n📊 처리 결과:")
        print("=" * 50)
        
        if result['success']:
            summary = result['summary']
            print(f"✅ 성공적으로 완료")
            print(f"📧 총 메일: {summary['total_mails']}개")
            print(f"✅ 성공: {summary['success_count']}개")
            print(f"⏭️  건너뜀: {summary['skipped_count']}개")
            print(f"❌ 실패: {summary['failed_count']}개")
            print(f"📈 성공률: {summary['success_rate']}%")
            print(f"🔑 추출된 키워드: {summary['total_keywords_extracted']}개")
            print(f"📤 Kafka 이벤트 발행: {summary['kafka_events_published']}개")
            if summary['kafka_publish_errors'] > 0:
                print(f"❌ Kafka 발행 실패: {summary['kafka_publish_errors']}개")
            print(f"⏱️  실행 시간: {result['execution_time_seconds']}초")
            
            if summary['top_keywords']:
                print(f"\n🏷️  주요 키워드: {', '.join(summary['top_keywords'])}")
            
            # Kafka 이벤트 정보
            if result['kafka_stats']['events_published'] > 0:
                print(f"\n📤 Kafka 이벤트 ID:")
                for event_id in result['kafka_stats']['published_event_ids'][:5]:
                    print(f"   - {event_id}")
            
            # 처리 상태별 카운트
            print(f"\n📋 처리 상태:")
            status_counts = {}
            for mail_result in result['processing_results']:
                status = mail_result['processing_status']
                status_counts[status] = status_counts.get(status, 0) + 1
            
            for status, count in status_counts.items():
                print(f"  {status}: {count}개")
        
        else:
            print(f"❌ 처리 실패: {result['error']}")
            print(f"📍 실패 단계: {result.get('stage', 'unknown')}")
    
    except KeyboardInterrupt:
        print("\n⚠️ 사용자에 의해 중단됨")
    except Exception as e:
        print(f"\n💥 예상치 못한 오류: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 리소스 정리
        await processor.close()
        print("\n🏁 테스트 완료")


if __name__ == "__main__":
    # 비동기 실행
    asyncio.run(main())