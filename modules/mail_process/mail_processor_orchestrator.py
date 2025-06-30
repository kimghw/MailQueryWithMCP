"""메일 처리 오케스트레이터 - 순수 흐름 제어만 담당"""

from typing import Dict, List, Any, Optional
from infra.core import get_logger
from .services import (
    FilteringService,
    ProcessingService, 
    PersistenceService,
    StatisticsService
)
from .mail_processor_schema import ProcessingStatus

logger = get_logger(__name__)


class MailProcessorOrchestrator:
    """메일 처리 흐름만 관리하는 오케스트레이터"""
    
    def __init__(self, 
                 filtering_service: Optional[FilteringService] = None,
                 processing_service: Optional[ProcessingService] = None,
                 persistence_service: Optional[PersistenceService] = None,
                 statistics_service: Optional[StatisticsService] = None):
        """
        의존성 주입을 지원하는 초기화
        
        Args:
            filtering_service: 필터링 서비스 (테스트 시 모킹 가능)
            processing_service: 처리 서비스 (테스트 시 모킹 가능)
            persistence_service: 저장 서비스 (테스트 시 모킹 가능)
            statistics_service: 통계 서비스 (테스트 시 모킹 가능)
        """
        self.logger = get_logger(__name__)
        
        # 서비스 초기화 (의존성 주입 지원)
        self.filtering_service = filtering_service or FilteringService()
        self.processing_service = processing_service or ProcessingService()
        self.persistence_service = persistence_service or PersistenceService()
        self.statistics_service = statistics_service or StatisticsService()
    
    async def __aenter__(self):
        """컨텍스트 매니저 진입"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """컨텍스트 매니저 종료 - 자동 리소스 정리"""
        await self.close()
    
    async def process_mails(
        self, 
        account_id: str, 
        mails: List[Dict],
        publish_batch_event: bool = True
    ) -> Dict[str, Any]:
        """
        메일 처리 메인 플로우
        
        Args:
            account_id: 계정 ID
            mails: 메일 리스트
            publish_batch_event: 배치 이벤트 발행 여부
            
        Returns:
            처리 통계
        """
        self.logger.info(f"메일 처리 시작: account_id={account_id}, count={len(mails)}")
        
        try:
            # Phase 1: 초기화 및 필터링
            filtered_mails = await self._phase1_filter(account_id, mails)
            
            # Phase 2: 정제 및 키워드 추출
            processed_mails = await self._phase2_process(account_id, filtered_mails)
            
            # Phase 3: 저장 및 이벤트 발행
            saved_results = await self._phase3_persist(account_id, processed_mails)
            
            # Phase 4: 통계 기록 - processed_mails 전달 추가!
            statistics = await self._phase4_statistics(
                account_id, 
                len(mails),
                len(filtered_mails),
                saved_results,
                publish_batch_event,
                processed_mails  # 이 부분 추가!
            )
            
            self.logger.info(f"메일 처리 완료: {statistics}")
            return statistics
            
        except Exception as e:
            self.logger.error(f"메일 처리 중 예외 발생: {str(e)}", exc_info=True)
            # 부분 실패 허용 - 현재까지 처리된 통계 반환
            return self.statistics_service.get_current_statistics()
        finally:
            # 리소스 정리는 항상 수행
            await self._cleanup_resources()
    
    async def _phase1_filter(self, account_id: str, mails: List[Dict]) -> List[Dict]:
        """Phase 1: 초기화 및 필터링"""
        self.logger.debug(f"Phase 1 시작: 필터링 ({len(mails)}개)")
        return await self.filtering_service.filter_mails(mails)
    
    async def _phase2_process(self, account_id: str, mails: List[Dict]) -> List[Dict]:
        """Phase 2: 정제 및 키워드 추출"""
        self.logger.debug(f"Phase 2 시작: 처리 ({len(mails)}개)")
        processed_mails = await self.processing_service.process_mails(mails)
        
        # 처리된 메일에서 키워드 정보 확인 (디버깅용)
        total_keywords = 0
        for mail in processed_mails:
            if '_processed' in mail and 'keywords' in mail['_processed']:
                keywords = mail['_processed']['keywords']
                total_keywords += len(keywords)
                if keywords:
                    self.logger.debug(f"메일 {mail.get('id', 'unknown')}: 키워드 {len(keywords)}개 - {keywords}")
        
        self.logger.info(f"Phase 2 완료: {len(processed_mails)}개 메일에서 총 {total_keywords}개 키워드 추출")
        return processed_mails
    
    async def _phase3_persist(self, account_id: str, mails: List[Dict]) -> Dict:
        """Phase 3: 저장 및 이벤트 발행"""
        self.logger.debug(f"Phase 3 시작: 저장 ({len(mails)}개)")
        
        # 처리된 메일 데이터에 키워드 정보 포함
        for mail in mails:
            if '_processed' in mail:
                # _processed 정보를 메일 데이터에 병합
                processed_info = mail['_processed']
                mail['keywords'] = processed_info.get('keywords', [])
                mail['clean_content'] = processed_info.get('clean_content', '')
                mail['sent_time'] = processed_info.get('sent_time')
                mail['processing_status'] = 'SUCCESS'
        
        return await self.persistence_service.persist_mails(account_id, mails)
    
    async def _phase4_statistics(
        self, 
        account_id: str,
        total_count: int,
        filtered_count: int,
        saved_results: Dict,
        publish_batch_event: bool,
        processed_mails: List[Dict] = None  # 파라미터 추가
    ) -> Dict:
        """Phase 4: 통계 기록"""
        self.logger.debug("Phase 4 시작: 통계")
        return await self.statistics_service.record_statistics(
            account_id=account_id,
            total_count=total_count,
            filtered_count=filtered_count,
            saved_results=saved_results,
            publish_batch_event=publish_batch_event,
            processed_mails=processed_mails  # 전달 추가
        )
    
    async def _cleanup_resources(self):
        """리소스 정리"""
        try:
            await self.processing_service.close()
        except Exception as e:
            self.logger.error(f"리소스 정리 중 오류: {str(e)}")
    
    async def close(self):
        """명시적 리소스 정리"""
        await self._cleanup_resources()