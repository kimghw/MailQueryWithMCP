"""Mail Processor 오케스트레이터 - 외부 호출용 간소화 버전"""

from datetime import datetime
from typing import Dict, List, Optional

from infra.core.logger import get_logger

# 스키마
from .mail_processor_schema import (
    ProcessedMailData,
    ProcessingStatus,
    GraphMailItem,
)

# 유틸리티
from .utilities.mail_filter import MailFilter
from .utilities.text_cleaner import TextCleaner
from .utilities.mail_parser import MailParser

# 서비스
from .service.db_service import MailDatabaseService
from .service.keyword_service import MailKeywordService
from .service.event_service import MailEventService


class MailProcessorOrchestrator:
    """메일 처리 오케스트레이터 - 외부 호출용 간소화 버전"""

    def __init__(self):
        self.logger = get_logger(__name__)

        # 유틸리티 초기화
        self.mail_filter = MailFilter()
        self.text_cleaner = TextCleaner()
        self.mail_parser = MailParser()

        # 서비스 초기화
        self.db_service = MailDatabaseService()
        self.keyword_service = MailKeywordService()
        self.event_service = MailEventService()

    async def process_single_mail(self, account_id: str, mail: Dict) -> ProcessedMailData:
        """
        개별 메일 처리 - 외부에서 직접 호출하는 메인 메서드
        
        Args:
            account_id: 계정 ID
            mail: 메일 데이터 딕셔너리
            
        Returns:
            ProcessedMailData: 처리 결과
        """
        try:
            # 1단계: 메일 파싱 (유틸리티)
            mail_id = self.mail_parser.extract_mail_id(mail)
            sender_address = self.mail_parser.extract_sender_address(mail)
            subject = self.mail_parser.extract_subject(mail)
            sent_time = self.mail_parser.extract_sent_time(mail)
            body_preview = self.mail_parser.extract_body_preview(mail)

            # 2단계: 발신자 필터링 (유틸리티)
            if not self.mail_filter.should_process(sender_address, subject):
                return self._create_processed_mail_data(
                    mail_id, account_id, sender_address, subject, body_preview,
                    sent_time, [], ProcessingStatus.SKIPPED, "발신자 필터링으로 제외"
                )

            # 3단계: 텍스트 정제 (유틸리티)
            refined_mail, clean_content = self.text_cleaner.prepare_mail_content(mail)
            
            # 내용이 너무 짧은지 확인 (유틸리티)
            if self.text_cleaner.is_content_too_short(clean_content):
                return self._create_processed_mail_data(
                    mail_id, account_id, sender_address, subject, body_preview,
                    sent_time, [], ProcessingStatus.SKIPPED, "내용 부족"
                )

            # 4단계: 중복 확인 (서비스)
            is_duplicate, existing_keywords = self.db_service.check_duplicate_by_content_hash(
                mail_id, clean_content
            )

            if is_duplicate:
                return self._create_processed_mail_data(
                    mail_id, account_id, sender_address, subject, body_preview,
                    sent_time, existing_keywords, ProcessingStatus.SKIPPED, "중복 메일"
                )

            # 5단계: 키워드 추출 (서비스)
            # 키워드 서비스가 이미 초기화되어 있지 않으면 컨텍스트 매니저 사용
            if self.keyword_service._session is None:
                async with self.keyword_service:
                    keywords = await self.keyword_service.extract_keywords(clean_content)
            else:
                keywords = await self.keyword_service.extract_keywords(clean_content)
            # 5.1단계
            refined_mail['extracted_keywords'] = keywords

            # 6단계: 처리된 메일 데이터 생성, 데이터베이스 저장
            processed_mail = self._create_processed_mail_data(
                mail_id, account_id, sender_address, subject, body_preview,
                sent_time, keywords, ProcessingStatus.SUCCESS
            )
            

            # 7단계: DB 저장 (서비스)
            self.db_service.save_mail_with_hash(processed_mail, clean_content)

            # 8단계: 이벤트 발행 (서비스)
            self.event_service.publish_mail_event(account_id, refined_mail, keywords)

            self.logger.info(
                f"메일 처리 완료 - ID: {mail_id}, 키워드: {len(keywords)}개"
            )

            return processed_mail

        except Exception as e:
            self.logger.error(f"메일 처리 실패 - {mail.get('id', 'unknown')}: {str(e)}")
            return self._create_processed_mail_data(
                mail.get('id', 'unknown'), account_id, 
                mail.get('from', {}).get('emailAddress', {}).get('address', ''),
                mail.get('subject', ''), mail.get('bodyPreview', ''),
                datetime.now(), [], ProcessingStatus.FAILED, str(e)
            )

    async def process_graph_mail_item(
        self, mail_item: GraphMailItem, account_id: str
    ) -> ProcessedMailData:
        """
        GraphMailItem 객체 처리 - 타입 안전한 버전
        
        Args:
            mail_item: GraphMailItem 객체
            account_id: 계정 ID
            
        Returns:
            ProcessedMailData: 처리 결과
        """
        try:
            # GraphMailItem을 Dict로 변환
            mail_dict = mail_item.model_dump()

            # 동일한 처리 플로우 사용
            return await self.process_single_mail(account_id, mail_dict)

        except Exception as e:
            self.logger.error(f"GraphMailItem 처리 실패 - {mail_item.id}: {str(e)}")
            return self._create_processed_mail_data(
                mail_item.id, account_id, 
                self.mail_parser.extract_sender_address(mail_item.model_dump()),
                mail_item.subject or '', mail_item.body_preview or '',
                mail_item.received_date_time, [],
                ProcessingStatus.FAILED, str(e)
            )

    async def process_mail_batch(
        self, account_id: str, mails: List[Dict], 
        publish_batch_event: bool = True
    ) -> Dict[str, int]:
        """
        여러 메일을 한번에 처리하는 헬퍼 메서드
        
        Args:
            account_id: 계정 ID
            mails: 메일 리스트
            publish_batch_event: 배치 완료 이벤트 발행 여부
            
        Returns:
            처리 통계 딕셔너리
        """
        processed_count = 0
        skipped_count = 0
        failed_count = 0

        # 키워드 서비스 컨텍스트 관리
        async with self.keyword_service:
            for mail in mails:
                try:
                    result = await self.process_single_mail(account_id, mail)
                    
                    if result.processing_status == ProcessingStatus.SUCCESS:
                        processed_count += 1
                    elif result.processing_status == ProcessingStatus.SKIPPED:
                        skipped_count += 1
                    else:
                        failed_count += 1
                        
                except Exception as e:
                    self.logger.error(f"메일 처리 중 오류: {str(e)}")
                    failed_count += 1

        # 배치 완료 이벤트 발행 (선택적)
        if publish_batch_event:
            self.event_service.publish_batch_complete_event(
                account_id, processed_count, skipped_count, failed_count
            )

        return {
            "processed": processed_count,
            "skipped": skipped_count,
            "failed": failed_count,
            "total": len(mails)
        }

    def _create_processed_mail_data(
        self, mail_id: str, account_id: str, sender_address: str,
        subject: str, body_preview: str, sent_time: datetime,
        keywords: List[str], status: ProcessingStatus,
        error_message: str = None
    ) -> ProcessedMailData:
        """ProcessedMailData 객체 생성 헬퍼"""
        return ProcessedMailData(
            mail_id=mail_id,
            account_id=account_id,
            sender_address=sender_address,
            subject=subject,
            body_preview=body_preview,
            sent_time=sent_time,
            keywords=keywords,
            processing_status=status,
            error_message=error_message
        )

    def get_filter_stats(self) -> Dict:
        """
        필터링 통계 조회 - 간단한 버전
        
        Returns:
            필터 통계 정보
        """
        return self.mail_filter.get_filter_stats()

    async def close(self):
        """
        리소스 정리 - 외부에서 사용 후 호출
        """
        if self.keyword_service._session:
            await self.keyword_service.close()
        self.logger.info("Mail Processor 리소스 정리 완료")
