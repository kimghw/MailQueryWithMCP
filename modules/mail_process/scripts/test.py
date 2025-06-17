#!/usr/bin/env python3
"""
Mail Query -> Mail Process 통합 테스트
mail_query에서 메일을 조회하고 mail_process로 처리하는 전체 플로우 테스트
"""

#uv run python script/ignore/mail_query_processor.py --clear-data
import asyncio
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json

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


class MailIntegrationTester:
    """Mail Query -> Mail Process 통합 테스터"""
    
    def __init__(self):
        self.mail_query = MailQueryOrchestrator()
        self.mail_processor = MailProcessorOrchestrator()
        self.db_manager = get_database_manager()
    
    async def test_integration_flow(
        self, 
        user_id: str = "kimghw",
        days_back: int = 7,
        max_mails: int = 10,
        filters: Optional[MailQueryFilters] = None
    ) -> Dict:
        """
        통합 플로우 테스트
        
        Args:
            user_id: 사용자 ID
            days_back: 조회할 과거 일수
            max_mails: 최대 처리할 메일 수
            filters: 추가 필터 조건
            
        Returns:
            테스트 결과 딕셔너리
        """
        start_time = datetime.now()
        results = {
            'success': False,
            'query_phase': {},
            'process_phase': {},
            'statistics': {},
            'errors': []
        }
        
        try:
            logger.info("=== Mail Query → Mail Process 통합 테스트 시작 ===")
            logger.info(f"사용자: {user_id}, 조회 기간: {days_back}일, 최대 메일: {max_mails}개")
            
            # Phase 1: Mail Query - 메일 조회
            logger.info("\n📥 Phase 1: Mail Query - 메일 데이터 조회")
            query_results = await self._phase1_query_mails(
                user_id, days_back, max_mails, filters
            )
            results['query_phase'] = query_results
            
            if not query_results['success']:
                results['errors'].append("메일 조회 실패")
                return results
            
            # Phase 2: Mail Process - 메일 처리
            logger.info("\n🔧 Phase 2: Mail Process - 메일 처리")
            process_results = await self._phase2_process_mails(
                user_id, 
                query_results['messages']
            )
            results['process_phase'] = process_results
            
            # Phase 3: 통계 및 분석
            logger.info("\n📊 Phase 3: 통계 분석")
            statistics = await self._phase3_analyze_results(
                user_id,
                query_results,
                process_results
            )
            results['statistics'] = statistics
            
            # 전체 실행 시간
            total_time = (datetime.now() - start_time).total_seconds()
            results['total_execution_time'] = round(total_time, 2)
            results['success'] = True
            
            logger.info(f"\n=== 통합 테스트 완료 (총 {total_time:.2f}초) ===")
            
        except Exception as e:
            logger.error(f"통합 테스트 실패: {str(e)}", exc_info=True)
            results['errors'].append(str(e))
            results['total_execution_time'] = (datetime.now() - start_time).total_seconds()
        
        finally:
            # 리소스 정리
            await self._cleanup()
        
        return results
    
    async def _phase1_query_mails(
        self,
        user_id: str,
        days_back: int,
        max_mails: int,
        additional_filters: Optional[MailQueryFilters]
    ) -> Dict:
        """Phase 1: 메일 조회"""
        try:
            # 기본 필터 설정
            date_from = datetime.now() - timedelta(days=days_back)
            
            if additional_filters:
                filters = additional_filters
                if not filters.date_from:
                    filters.date_from = date_from
            else:
                filters = MailQueryFilters(date_from=date_from)
            
            # 페이징 옵션
            pagination = PaginationOptions(
                top=min(max_mails, 50),  # 한 페이지당 최대 50개
                skip=0,
                max_pages=(max_mails // 50) + 1
            )
            
            # 필드 선택 (처리에 필요한 필드만)
            select_fields = [
                "id", "subject", "from", "sender", "receivedDateTime",
                "bodyPreview", "body", "hasAttachments", "importance", "isRead"
            ]
            
            # 메일 조회 요청
            request = MailQueryRequest(
                user_id=user_id,
                filters=filters,
                pagination=pagination,
                select_fields=select_fields
            )
            
            # 메일 조회 실행
            async with self.mail_query as query:
                response = await query.mail_query_user_emails(request)
            
            # 결과 정리
            messages = []
            for msg in response.messages[:max_mails]:  # 최대 개수 제한
                messages.append(msg.model_dump())
            
            return {
                'success': True,
                'total_fetched': response.total_fetched,
                'messages': messages,
                'query_time_ms': response.execution_time_ms,
                'query_info': response.query_info,
                'has_more': response.has_more
            }
            
        except Exception as e:
            logger.error(f"메일 조회 실패: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'messages': []
            }
    
    async def _phase2_process_mails(
        self,
        user_id: str,
        messages: List[Dict]
    ) -> Dict:
        """Phase 2: 메일 처리"""
        start_time = datetime.now()
        
        try:
            # 배치 처리 실행
            stats = await self.mail_processor.process_mail_batch(
                account_id=user_id,
                mails=messages,
                publish_batch_event=False  # 테스트에서는 이벤트 발행 안함
            )
            
            # 처리 시간 계산
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # 개별 메일 처리 결과 샘플 수집 (상위 3개)
            sample_results = []
            for mail in messages[:3]:
                result = await self.mail_processor.process_single_mail(user_id, mail)
                sample_results.append({
                    'mail_id': result.mail_id,
                    'subject': result.subject[:50] + '...' if len(result.subject) > 50 else result.subject,
                    'status': result.processing_status.value,
                    'keywords': result.keywords,
                    'error': result.error_message
                })
            
            return {
                'success': True,
                'statistics': stats,
                'processing_time': round(processing_time, 3),
                'average_time_per_mail': round(processing_time / len(messages), 3) if messages else 0,
                'sample_results': sample_results
            }
            
        except Exception as e:
            logger.error(f"메일 처리 실패: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'statistics': {
                    'processed': 0,
                    'skipped': 0,
                    'failed': len(messages),
                    'total': len(messages)
                }
            }
    
    async def _phase3_analyze_results(
        self,
        user_id: str,
        query_results: Dict,
        process_results: Dict
    ) -> Dict:
        """Phase 3: 결과 분석 및 통계"""
        try:
            # 기본 통계
            stats = {
                'query_stats': {
                    'total_mails_found': query_results.get('total_fetched', 0),
                    'mails_retrieved': len(query_results.get('messages', [])),
                    'query_time_ms': query_results.get('query_time_ms', 0),
                    'has_more_data': query_results.get('has_more', False)
                },
                'process_stats': process_results.get('statistics', {}),
                'performance': {
                    'total_processing_time': process_results.get('processing_time', 0),
                    'avg_time_per_mail': process_results.get('average_time_per_mail', 0),
                    'query_performance': query_results.get('query_info', {}).get('performance_estimate', 'UNKNOWN')
                }
            }
            
            # 처리율 계산
            if stats['query_stats']['mails_retrieved'] > 0:
                process_rate = (
                    stats['process_stats'].get('processed', 0) / 
                    stats['query_stats']['mails_retrieved']
                ) * 100
                stats['process_rate'] = round(process_rate, 2)
            else:
                stats['process_rate'] = 0
            
            # 필터 효율성
            filter_stats = self.mail_processor.get_filter_stats()
            stats['filter_efficiency'] = filter_stats
            
            # 키워드 분석 (샘플 결과에서)
            if process_results.get('sample_results'):
                all_keywords = []
                for result in process_results['sample_results']:
                    all_keywords.extend(result.get('keywords', []))
                
                # 키워드 빈도 분석
                from collections import Counter
                keyword_freq = Counter(all_keywords)
                stats['top_keywords'] = keyword_freq.most_common(10)
            
            # DB에서 추가 통계 조회
            recent_stats = self._get_recent_processing_stats(user_id)
            if recent_stats:
                stats['recent_history'] = recent_stats
            
            return stats
            
        except Exception as e:
            logger.error(f"통계 분석 실패: {str(e)}")
            return {'error': str(e)}
    
    def _get_recent_processing_stats(self, user_id: str) -> Optional[Dict]:
        """최근 처리 통계 조회"""
        try:
            # 최근 24시간 처리 통계
            query = """
                SELECT 
                    COUNT(*) as total_processed,
                    COUNT(DISTINCT sender) as unique_senders,
                    AVG(json_array_length(keywords)) as avg_keywords_per_mail
                FROM mail_history mh
                JOIN accounts a ON mh.account_id = a.id
                WHERE a.user_id = ? 
                AND mh.processed_at >= datetime('now', '-1 day')
            """
            
            result = self.db_manager.fetch_one(query, (user_id,))
            
            if result:
                return {
                    'last_24h_processed': result['total_processed'] or 0,
                    'unique_senders': result['unique_senders'] or 0,
                    'avg_keywords': round(result['avg_keywords_per_mail'] or 0, 2)
                }
            
        except Exception as e:
            logger.error(f"통계 조회 실패: {str(e)}")
        
        return None
    
    async def _cleanup(self):
        """리소스 정리"""
        try:
            await self.mail_processor.close()
            await self.mail_query.close()
        except Exception as e:
            logger.error(f"리소스 정리 실패: {str(e)}")
    
    def print_results(self, results: Dict):
        """결과를 보기 좋게 출력"""
        print("\n" + "="*70)
        print("📊 Mail Query → Mail Process 통합 테스트 결과")
        print("="*70)
        
        if not results.get('success'):
            print(f"\n❌ 테스트 실패")
            for error in results.get('errors', []):
                print(f"  - {error}")
            return
        
        # Query Phase 결과
        print("\n📥 Phase 1: Mail Query 결과")
        query = results['query_phase']
        print(f"  - 총 메일 수: {query['total_fetched']}개")
        print(f"  - 조회된 메일: {len(query['messages'])}개")
        print(f"  - 조회 시간: {query['query_time_ms']}ms")
        print(f"  - 추가 데이터: {'있음' if query['has_more'] else '없음'}")
        
        # Process Phase 결과
        print("\n🔧 Phase 2: Mail Process 결과")
        process = results['process_phase']
        stats = process['statistics']
        print(f"  - 처리됨: {stats['processed']}개")
        print(f"  - 건너뜀: {stats['skipped']}개")
        print(f"  - 실패: {stats['failed']}개")
        print(f"  - 처리 시간: {process['processing_time']}초")
        print(f"  - 평균 시간: {process['average_time_per_mail']}초/메일")
        
        # 샘플 결과
        if process.get('sample_results'):
            print("\n📋 처리 샘플:")
            for i, sample in enumerate(process['sample_results'][:3], 1):
                print(f"\n  메일 {i}:")
                print(f"    제목: {sample['subject']}")
                print(f"    상태: {sample['status']}")
                if sample['keywords']:
                    print(f"    키워드: {', '.join(sample['keywords'])}")
                if sample.get('error'):
                    print(f"    오류: {sample['error']}")
        
        # 통계 분석
        print("\n📊 Phase 3: 통계 분석")
        stats = results['statistics']
        print(f"  - 처리율: {stats['process_rate']}%")
        print(f"  - 쿼리 성능: {stats['performance']['query_performance']}")
        
        if stats.get('top_keywords'):
            print("\n🏷️  상위 키워드:")
            for keyword, count in stats['top_keywords'][:5]:
                print(f"    - {keyword}: {count}회")
        
        if stats.get('recent_history'):
            hist = stats['recent_history']
            print("\n📈 최근 24시간 통계:")
            print(f"    - 처리된 메일: {hist['last_24h_processed']}개")
            print(f"    - 고유 발신자: {hist['unique_senders']}명")
            print(f"    - 평균 키워드: {hist['avg_keywords']}개/메일")
        
        print(f"\n⏱️  전체 실행 시간: {results['total_execution_time']}초")
        print("="*70)


async def test_with_filters():
    """필터를 사용한 테스트"""
    print("\n🔍 필터링된 메일 처리 테스트")
    print("-"*50)
    
    tester = MailIntegrationTester()
    
    # 특정 조건의 메일만 처리
    filters = MailQueryFilters(
        date_from=datetime.now() - timedelta(days=3),  # 최근 3일
        has_attachments=True,                          # 첨부파일 있음
        is_read=False                                  # 읽지 않은 메일
    )
    
    results = await tester.test_integration_flow(
        user_id="kimghw",
        days_back=3,
        max_mails=20,
        filters=filters
    )
    
    tester.print_results(results)


async def test_large_batch():
    """대량 메일 처리 테스트"""
    print("\n📦 대량 메일 배치 처리 테스트")
    print("-"*50)
    
    tester = MailIntegrationTester()
    
    results = await tester.test_integration_flow(
        user_id="kimghw",
        days_back=30,  # 30일간의 메일
        max_mails=100  # 최대 100개 처리
    )
    
    tester.print_results(results)


async def main():
    """메인 실행 함수"""
    print("🚀 Mail Query → Mail Process 통합 테스트")
    print("="*50)
    
    # 명령행 인수 처리
    if len(sys.argv) > 1:
        if sys.argv[1] == "--filter":
            # 필터 테스트
            await test_with_filters()
        elif sys.argv[1] == "--large":
            # 대량 처리 테스트
            await test_large_batch()
        elif sys.argv[1] == "--custom":
            # 사용자 정의 테스트
            user_id = sys.argv[2] if len(sys.argv) > 2 else "kimghw"
            days = int(sys.argv[3]) if len(sys.argv) > 3 else 7
            count = int(sys.argv[4]) if len(sys.argv) > 4 else 10
            
            print(f"\n사용자 정의 테스트: user={user_id}, days={days}, count={count}")
            
            tester = MailIntegrationTester()
            results = await tester.test_integration_flow(user_id, days, count)
            tester.print_results(results)
        else:
            print("\n사용법:")
            print("  python test_integration.py              # 기본 테스트")
            print("  python test_integration.py --filter     # 필터 테스트")
            print("  python test_integration.py --large      # 대량 처리 테스트")
            print("  python test_integration.py --custom [user_id] [days] [count]")
            return
    else:
        # 기본 테스트
        print("\n📧 기본 통합 테스트 (최근 7일, 최대 10개)")
        print("-"*50)
        
        tester = MailIntegrationTester()
        results = await tester.test_integration_flow()
        tester.print_results(results)
        
        # JSON으로 결과 저장 옵션
        save_json = input("\n💾 결과를 JSON으로 저장하시겠습니까? (y/n): ")
        if save_json.lower() == 'y':
            filename = f"integration_test_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2, default=str)
            print(f"✅ 결과가 {filename}에 저장되었습니다.")
    
    print("\n🏁 테스트 종료")


if __name__ == "__main__":
    asyncio.run(main())
