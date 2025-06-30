"""Mail Processor 오케스트레이터 - 중복 검토 토글 추가 버전"""

import os
from datetime import datetime
from typing import Dict, List, Optional

from infra.core.logger import get_logger
from infra.core.config import get_config
from modules.mail_process.mail_processor_schema import ProcessedMailData, ProcessingStatus
from modules.mail_process.utilities.mail_filter import MailFilter
from modules.mail_process.utilities.text_cleaner import TextCleaner
from modules.mail_process.utilities.mail_parser import MailParser
from modules.mail_process.service.db_service import MailDatabaseService
from modules.mail_process.service.keyword_service import MailKeywordService
from modules.mail_process.service.event_service import MailEventService


class MailProcessorOrchestrator:
    """메일 처리 오케스트레이터 - 외부 호출용 간소화 버전"""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.config = get_config()

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

    async def process_mails(
        self, 
        account_id: str, 
        mails: List[Dict], 
        publish_batch_event: bool = True
    ) -> Dict[str, int]:
        """
        메일 목록을 처리하는 메인 메서드
        
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

        self.logger.info(f"메일 처리 시작: account_id={account_id}, 총 {len(mails)}개")
        
        try:
            async with self.keyword_service:
                for mail in mails:
                    try:
                        result = await self._process_single_mail(account_id, mail)
                        
                        if result.processing_status == ProcessingStatus.SUCCESS:
                            processed_count += 1
                        elif result.processing_status == ProcessingStatus.SKIPPED:
                            skipped_count += 1
                            self.logger.debug(f"메일 건너뜀: {result.mail_id} - {result.error_message}")
                        else:
                            failed_count += 1
                            
                    except Exception as e:
                        self.logger.error(f"메일 처리 중 오류: {str(e)}", exc_info=True)
                        failed_count += 1

            # 배치 완료 이벤트 발행
            if publish_batch_event and len(mails) > 1:  # 단일 메일은 배치 이벤트 불필요
                self.event_service.publish_batch_complete_event(
                    account_id, processed_count, skipped_count, failed_count
                )

            self.logger.info(
                f"메일 처리 완료: 성공={processed_count}, "
                f"건너뜀={skipped_count}, 실패={failed_count}"
            )

            return {
                "processed": processed_count,
                "skipped": skipped_count,
                "failed": failed_count,
                "total": len(mails)
            }
            
        finally:
            # 키워드 서비스 리소스 자동 정리
            await self.keyword_service.close()
            self.logger.debug("메일 처리 후 리소스 정리 완료")

    async def _process_single_mail(self, account_id: str, mail: Dict) -> ProcessedMailData:
        """
        개별 메일 처리 - 내부 전용 메서드 (private)
        
        Args:
            account_id: 계정 ID
            mail: 메일 데이터 딕셔너리
            
        Returns:
            ProcessedMailData: 처리 결과
        """
        try:
            # 1단계: 메일 데이터 파싱
            mail_id = self.mail_parser.extract_mail_id(mail)
            sender_address = self.mail_parser.extract_sender_address(mail)
            subject = self.mail_parser.extract_subject(mail)
            sent_time = self.mail_parser.extract_sent_time(mail)
            body_preview = self.mail_parser.extract_body_preview(mail)

            # 2단계: 발신자 필터링
            if not self.mail_filter.should_process(sender_address, subject):
                return self._create_processed_mail_data(
                    mail_id, account_id, sender_address, subject, body_preview,
                    sent_time, [], ProcessingStatus.SKIPPED, "발신자 필터링으로 제외"
                )

            # 3단계: 텍스트 정제
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
            is_duplicate = False
            existing_keywords = []
            
            if self.enable_duplicate_check:
                is_duplicate, existing_keywords = self.db_service.check_duplicate_by_content_hash(
                    mail_id, clean_content
                )

                if is_duplicate:
                    self.logger.debug(f"중복 메일 발견 (중복 검사 활성화): {mail_id}")
                    # 중복 검사가 활성화된 경우, 중복이면 저장도 안하고 이벤트도 발행 안함
                    return self._create_processed_mail_data(
                        mail_id, account_id, sender_address, subject, body_preview,
                        sent_time, existing_keywords, ProcessingStatus.SKIPPED, "중복 메일"
                    )
            else:
                self.logger.debug(f"중복 검토 건너뜀: {mail_id}")

            # 5단계: 키워드 추출
            keywords = await self.keyword_service.extract_keywords(clean_content)
            
            # 6단계: DB 저장 (ENABLE_MAIL_HISTORY가 true인 경우에만)
            saved_successfully = False
            if self.config.enable_mail_history:
                try:
                    self.db_service.save_mail_with_hash(
                        ProcessedMailData(
                            mail_id=mail_id,
                            account_id=account_id,
                            sender_address=sender_address,
                            subject=subject,
                            body_preview=body_preview,
                            sent_time=sent_time,
                            keywords=keywords,
                            processing_status=ProcessingStatus.SUCCESS
                        ),
                        clean_content
                    )
                    saved_successfully = True
                    self.logger.info(f"메일 저장 성공: {mail_id}")
                except Exception as e:
                    # UNIQUE 제약조건 위반 등의 저장 실패
                    if "UNIQUE constraint failed" in str(e) or "duplicate" in str(e).lower():
                        self.logger.warning(f"메일 저장 실패 (이미 존재): {mail_id}")
                        # 중복 검사가 비활성화된 경우, 저장 실패해도 이벤트는 발행
                        if not self.enable_duplicate_check:
                            saved_successfully = False  # 저장은 실패했지만 계속 진행
                        else:
                            # 중복 검사가 활성화된 상태에서 저장 실패는 오류
                            raise
                    else:
                        # 다른 종류의 에러는 재발생
                        raise
            else:
                self.logger.debug("메일 히스토리 저장 비활성화됨")

            # 7단계: 이벤트 발행
            # - 중복 검사 비활성화: 항상 발행 (저장 실패해도)
            # - 중복 검사 활성화: 중복이 아닌 경우만 발행 (여기까지 왔다면 중복 아님)
            self.event_service.publish_mail_event(account_id, mail, keywords, clean_content)
            
            # 8단계: 결과 반환
            return self._create_processed_mail_data(
                mail_id, account_id, sender_address, subject, body_preview,
                sent_time, keywords, ProcessingStatus.SUCCESS, None
            )

        except Exception as e:
            self.logger.error(f"메일 처리 실패: {mail_id}, 오류: {str(e)}")
            return self._create_processed_mail_data(
                mail_id, account_id, sender_address, subject, body_preview,
                sent_time, [], ProcessingStatus.FAILED, str(e)
            )

    def get_duplicate_check_status(self) -> bool:
        """현재 중복 검토 활성화 상태 반환"""
        return self.enable_duplicate_check

    def set_duplicate_check(self, enabled: bool):
        """중복 검토 활성화/비활성화 (런타임 중 변경)"""
        self.enable_duplicate_check = enabled
        status = "활성화" if enabled else "비활성화"
        self.logger.info(f"메일 중복 검토가 {status}되었습니다")

    def get_filter_stats(self) -> dict:
        """필터 통계 반환"""
        return self.mail_filter.get_filter_stats()

    def _create_processed_mail_data(
        self,
        mail_id: str,
        account_id: str,
        sender_address: str,
        subject: str,
        body_preview: str,
        sent_time: datetime,
        keywords: List[str],
        processing_status: ProcessingStatus,
        error_message: Optional[str] = None
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
            processing_status=processing_status,
            error_message=error_message,
            processed_at=datetime.now()
        )