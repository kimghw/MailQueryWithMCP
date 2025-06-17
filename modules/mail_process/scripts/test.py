#!/usr/bin/env python3
"""
Mail Processor 간소화 버전 테스트 스크립트
외부에서 메일을 가져와서 처리하는 테스트
"""
import asyncio
import sys
from datetime import datetime, timedelta
from typing import List, Dict

# 모듈 임포트
from modules.mail_query import (
    MailQueryOrchestrator,
    MailQueryRequest,
    MailQueryFilters,
    PaginationOptions
)
from modules.mail_process import (
    MailProcessorOrchestrator,
    ProcessingStatus
)
from infra.core.logger import get_logger, update_all_loggers_level
from infra.core.database import get_database_manager
import logging

# Kafka 관련 디버깅 메시지 숨기기
logging.getLogger("infra.core.kafka_client").setLevel(logging.ERROR)
logging.getLogger("kafka").setLevel(logging.ERROR)
logging.getLogger("aiokafka").setLevel(logging.ERROR)

# 전체 로그 레벨 설정
update_all_loggers_level("INFO")
logger = get_logger(__name__)


class MailProcessorTester:
    """Mail Processor 간소화 버전 테스터"""
    
    def __init__(self):
        self.mail_query = MailQueryOrchestrator()
        self.mail_processor = MailProcessorOrchestrator()
        self.db_manager = get_database_manager()
    
    async def test_mail_processing(self, user_id: str = "kimghw", mail_count: int = 5) -> dict:
        """메일 처리 테스트 메인 함수"""
        start_time = datetime.now()
        
        try:
            logger.info("=== Mail Processor 테스트 시작 ===")
            logger.info(f"대상 사용자: {user_id}, 처리할 메일 수: {mail_count}")
            
            # 1단계: 외부에서 메일 데이터 가져오기 (Mail Query 사용)
            logger.info("\n📥 1단계: 외부에서 메일 데이터 가져오기")
            mails = await self._fetch_mails_from_external(user_id, mail_count)
            
            if not mails:
                logger.warning("가져온 메일이 없습니다.")
                return {
                    'success': False,
                    'error': '메일을 가져오지 못했습니다.',
                    'stage': 'fetch'
                }
            
            logger.info(f"✅ {len(mails)}개 메일 가져오기 완료")
            
            # 2단계: Mail Processor로 처리
            logger.info("\n🔧 2단계: Mail Processor로 처리")
            
            # 단일 메일 처리 테스트
            if len(mails) == 1:
                result = await self._test_single_mail_processing(user_id, mails[0])
            else:
                # 배치 처리 테스트
                result = await self._test_batch_mail_processing(user_id, mails)
            
            # 3단계: 필터 통계 확인
            logger.info("\n📊 3단계: 필터 통계 확인")
            filter_stats = self.mail_processor.get_filter_stats()
            result['filter_stats'] = filter_stats
            
            # 실행 시간 계산
            execution_time = (datetime.now() - start_time).total_seconds()
            result['total_execution_time'] = round(execution_time, 2)
            
            logger.info(f"\n=== 테스트 완료 (총 {execution_time:.2f}초) ===")
            
            return result
            
        except Exception as e:
            logger.error(f"테스트 실패: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'stage': 'test',
                'execution_time': (datetime.now() - start_time).total_seconds()
            }
        finally:
            # 리소스 정리
            await self._cleanup()
    
    async def _fetch_mails_from_external(self, user_id: str, mail_count: int) -> List[Dict]:
        """외부 소스에서 메일 가져오기 (Mail Query 사용)"""
        try:
            # 최근 7일간의 메일 조회
            date_from = datetime.now() - timedelta(days=7)
            
            request = MailQueryRequest(
                user_id=user_id,
                filters=MailQueryFilters(
                    date_from=date_from
                ),
                pagination=PaginationOptions(
                    top=mail_count,
                    skip=0,
                    max_pages=1
                ),
                select_fields=[
                    "id", "subject", "from", "sender", "receivedDateTime", 
                    "bodyPreview", "body", "hasAttachments", "importance", "isRead"
                ]
            )
            
            async with self.mail_query as query:
                response = await query.mail_query_user_emails(request)
            
            # GraphMailItem을 Dict로 변환
            mails = []
            for message in response.messages:
                mail_dict = message.model_dump()
                mails.append(mail_dict)
            
            logger.info(f"외부에서 {len(mails)}개 메일 가져옴")
            return mails
            
        except Exception as e:
            logger.error(f"메일 가져오기 실패: {str(e)}")
            return []
    
    async def _test_single_mail_processing(self, user_id: str, mail: Dict) -> dict:
        """단일 메일 처리 테스트"""
        logger.info("\n🔬 단일 메일 처리 테스트")
        logger.info(f"메일 제목: {mail.get('subject', 'No Subject')[:50]}...")
        
        try:
            # process_single_mail 직접 호출
            start_time = datetime.now()
            result = await self.mail_processor.process_single_mail(user_id, mail)
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # 결과 정리
            return {
                'success': True,
                'test_type': 'single',
                'mail_id': result.mail_id,
                'subject': result.subject,
                'sender': result.sender_address,
                'status': result.processing_status.value,
                'keywords': result.keywords,
                'error_message': result.error_message,
                'processing_time': round(processing_time, 3),
                'details': {
                    'sent_time': result.sent_time.isoformat(),
                    'processed_at': result.processed_at.isoformat(),
                    'body_preview': result.body_preview[:100] + '...' if len(result.body_preview) > 100 else result.body_preview
                }
            }
            
        except Exception as e:
            logger.error(f"단일 메일 처리 실패: {str(e)}")
            return {
                'success': False,
                'test_type': 'single',
                'error': str(e)
            }
    
    async def _test_batch_mail_processing(self, user_id: str, mails: List[Dict]) -> dict:
        """배치 메일 처리 테스트"""
        logger.info(f"\n🔬 배치 메일 처리 테스트 ({len(mails)}개)")
        
        try:
            # process_mail_batch 호출
            start_time = datetime.now()
            stats = await self.mail_processor.process_mail_batch(
                user_id, 
                mails, 
                publish_batch_event=False  # 배치 완료 이벤트 발행 안함
            )
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # 각 메일의 상세 결과 수집
            individual_results = []
            
            # 개별 메일 처리 결과를 위해 다시 처리 (실제로는 DB에서 조회 가능)
            for mail in mails[:3]:  # 처음 3개만 상세 표시
                result = await self.mail_processor.process_single_mail(user_id, mail)
                individual_results.append({
                    'mail_id': result.mail_id,
                    'subject': result.subject[:50] + '...' if len(result.subject) > 50 else result.subject,
                    'status': result.processing_status.value,
                    'keywords': result.keywords
                })
            
            return {
                'success': True,
                'test_type': 'batch',
                'statistics': stats,
                'processing_time': round(processing_time, 3),
                'average_time_per_mail': round(processing_time / len(mails), 3),
                'sample_results': individual_results
            }
            
        except Exception as e:
            logger.error(f"배치 메일 처리 실패: {str(e)}")
            return {
                'success': False,
                'test_type': 'batch',
                'error': str(e)
            }
    
    async def _cleanup(self):
        """리소스 정리"""
        try:
            await self.mail_processor.close()
            await self.mail_query.close()
        except Exception as e:
            logger.error(f"리소스 정리 실패: {str(e)}")
    
    def print_results(self, results: dict):
        """결과를 보기 좋게 출력"""
        print("\n" + "="*60)
        print("📊 Mail Processor 테스트 결과")
        print("="*60)
        
        if not results.get('success'):
            print(f"❌ 테스트 실패: {results.get('error', 'Unknown error')}")
            print(f"실패 단계: {results.get('stage', 'unknown')}")
            return
        
        test_type = results.get('test_type', 'unknown')
        
        if test_type == 'single':
            print("\n✅ 단일 메일 처리 테스트 성공")
            print(f"📧 메일 ID: {results['mail_id']}")
            print(f"📋 제목: {results['subject']}")
            print(f"👤 발신자: {results['sender']}")
            print(f"📊 상태: {results['status']}")
            
            if results['keywords']:
                print(f"🏷️  키워드: {', '.join(results['keywords'])}")
            else:
                print("🏷️  키워드: 없음")
            
            if results.get('error_message'):
                print(f"⚠️  오류: {results['error_message']}")
            
            print(f"⏱️  처리 시간: {results['processing_time']}초")
            
        elif test_type == 'batch':
            print("\n✅ 배치 메일 처리 테스트 성공")
            stats = results['statistics']
            print(f"📊 전체 통계:")
            print(f"  - 총 메일: {stats['total']}개")
            print(f"  - 처리됨: {stats['processed']}개")
            print(f"  - 건너뜀: {stats['skipped']}개")
            print(f"  - 실패: {stats['failed']}개")
            print(f"⏱️  총 처리 시간: {results['processing_time']}초")
            print(f"⏱️  평균 처리 시간: {results['average_time_per_mail']}초/메일")
            
            if results.get('sample_results'):
                print("\n📋 샘플 결과:")
                for i, sample in enumerate(results['sample_results'], 1):
                    print(f"\n  메일 {i}:")
                    print(f"    제목: {sample['subject']}")
                    print(f"    상태: {sample['status']}")
                    if sample['keywords']:
                        print(f"    키워드: {', '.join(sample['keywords'])}")
        
        # 필터 통계
        if results.get('filter_stats'):
            stats = results['filter_stats']
            print("\n🔍 필터 통계:")
            print(f"  - 필터링 활성화: {stats['filtering_enabled']}")
            print(f"  - 차단 도메인: {stats['blocked_domains_count']}개")
            print(f"  - 차단 키워드: {stats['blocked_keywords_count']}개")
            print(f"  - 차단 패턴: {stats['blocked_patterns_count']}개")
        
        print(f"\n⏱️  전체 실행 시간: {results.get('total_execution_time', 0)}초")
        print("="*60)


async def main():
    """메인 실행 함수"""
    print("🚀 Mail Processor 간소화 버전 테스트")
    print("="*50)
    
    # 설정
    user_id = "kimghw"  # 테스트할 사용자 ID
    mail_count = 5      # 처리할 메일 개수
    
    # 명령행 인수 처리
    if len(sys.argv) > 1:
        if sys.argv[1] == "--single":
            mail_count = 1
            print("📧 단일 메일 처리 모드")
        elif sys.argv[1] == "--batch":
            if len(sys.argv) > 2:
                mail_count = int(sys.argv[2])
            print(f"📦 배치 처리 모드 ({mail_count}개)")
        elif sys.argv[1] == "--clear-data":
            print("🗑️  데이터 초기화 모드")
            db_manager = get_database_manager()
            
            # 테이블 데이터 초기화
            result1 = db_manager.clear_table_data("mail_history")
            print(f"📧 mail_history: {result1['message']}")
            
            result2 = db_manager.clear_table_data("processing_logs")
            print(f"📝 processing_logs: {result2['message']}")
            
            print("\n✅ 데이터 초기화 완료")
            return
    
    # 테스터 실행
    tester = MailProcessorTester()
    
    try:
        # 테스트 실행
        results = await tester.test_mail_processing(user_id, mail_count)
        
        # 결과 출력
        tester.print_results(results)
        
    except KeyboardInterrupt:
        print("\n⚠️ 사용자에 의해 중단됨")
    except Exception as e:
        print(f"\n💥 예상치 못한 오류: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n🏁 테스트 종료")


if __name__ == "__main__":
    asyncio.run(main())
