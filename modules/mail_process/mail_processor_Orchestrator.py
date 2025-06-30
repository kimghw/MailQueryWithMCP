"""Mail Processor 오케스트레이터 - 중복 검토 토글 추가 버전"""

import os
from datetime import datetime
from typing import Dict, List, Optional

from infra.core.logger import get_logger

# ... 기존 import들 ...

class MailProcessorOrchestrator:
    """메일 처리 오케스트레이터 - 외부 호출용 간소화 버전"""

    def __init__(self):
        self.logger = get_logger(__name__)

        # 중복 검토 활성화 여부 (환경변수로 제어)
        self.enable_duplicate_check = os.getenv(
            "ENABLE_MAIL_DUPLICATE_CHECK", "true"
        ).lower() == "true"
        
        if not self.enable_duplicate_check:
            self.logger.warning("⚠️ 메일 중복 검토가 비활성화되었습니다")

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
            # 1-3단계: 기존과 동일 (파싱, 필터링, 정제)
            mail_id = self.mail_parser.extract_mail_id(mail)
            sender_address = self.mail_parser.extract_sender_address(mail)
            subject = self.mail_parser.extract_subject(mail)
            sent_time = self.mail_parser.extract_sent_time(mail)
            body_preview = self.mail_parser.extract_body_preview(mail)

            if not self.mail_filter.should_process(sender_address, subject):
                return self._create_processed_mail_data(
                    mail_id, account_id, sender_address, subject, body_preview,
                    sent_time, [], ProcessingStatus.SKIPPED, "발신자 필터링으로 제외"
                )

            refined_mail = self.text_cleaner.prepare_mail_content(mail)
            
            subject_for_keywords = refined_mail.get('subject', '')
            body_for_keywords = refined_mail.get('body', {}).get('content', '')
            clean_content = f"{subject_for_keywords} {body_for_keywords}".strip()
            
            if self.text_cleaner.is_content_too_short(clean_content):
                return self._create_processed_mail_data(
                    mail_id, account_id, sender_address, subject, body_preview,
                    sent_time, [], ProcessingStatus.SKIPPED, "내용 부족"
                )

            # 4단계: 중복 확인 (조건부 실행)
            if self.enable_duplicate_check:
                is_duplicate, existing_keywords = self.db_service.check_duplicate_by_content_hash(
                    mail_id, clean_content
                )

                if is_duplicate:
                    self.logger.debug(f"중복 메일 발견: {mail_id}")
                    return self._create_processed_mail_data(
                        mail_id, account_id, sender_address, subject, body_preview,
                        sent_time, existing_keywords, ProcessingStatus.SKIPPED, "중복 메일"
                    )
            else:
                self.logger.debug(f"중복 검토 건너뜀: {mail_id}")

            # 5-8단계: 기존과 동일 (키워드 추출, DB 저장, 이벤트 발행)
            # ... 나머지 코드는 동일 ...

    async def process_mail_batch(
        self, 
        account_id: str, 
        mails: List[Dict], 
        publish_batch_event: bool = True,
        skip_duplicate_check: bool = False  # 배치별 옵션 추가
    ) -> Dict[str, int]:
        """
        여러 메일을 한번에 처리하는 헬퍼 메서드
        
        Args:
            account_id: 계정 ID
            mails: 메일 리스트
            publish_batch_event: 배치 완료 이벤트 발행 여부
            skip_duplicate_check: 이 배치에서 중복 검토 건너뛰기
            
        Returns:
            처리 통계 딕셔너리
        """
        # 배치별로 중복 검토를 임시로 비활성화할 수 있음
        original_setting = self.enable_duplicate_check
        if skip_duplicate_check:
            self.enable_duplicate_check = False
            self.logger.info("이 배치에서 중복 검토가 비활성화됩니다")
        
        try:
            # 기존 배치 처리 로직
            processed_count = 0
            skipped_count = 0
            failed_count = 0

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
            
        finally:
            # 원래 설정으로 복원
            self.enable_duplicate_check = original_setting

    def get_duplicate_check_status(self) -> bool:
        """현재 중복 검토 활성화 상태 반환"""
        return self.enable_duplicate_check

    def set_duplicate_check(self, enabled: bool):
        """중복 검토 활성화/비활성화 (런타임 중 변경)"""
        self.enable_duplicate_check = enabled
        status = "활성화" if enabled else "비활성화"
        self.logger.info(f"메일 중복 검토가 {status}되었습니다")