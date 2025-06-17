"""Mail Processor 오케스트레이터 - 개선된 버전"""

import time
from datetime import datetime
from typing import List, Dict, Optional

from infra.core.logger import get_logger
from .mail_processor_schema import (
    MailProcessingResult,
    ProcessedMailData,
    ProcessingStatus,
    GraphMailItem,
)
from .keyword_extractor_service import MailProcessorKeywordExtractorService
from .mail_filter_service import MailProcessorFilterService
from ._mail_processor_helpers import (
    MailProcessorGraphApiHelper,
    MailProcessorDatabaseHelper,
    MailProcessorKafkaHelper,
    MailProcessorDataHelper,
)


class MailProcessorOrchestrator:
    """메일 처리 오케스트레이터 - 완전 독립적 구현"""

    def __init__(self):
        self.logger = get_logger(__name__)

        # 서비스 초기화
        self.filter_service = MailProcessorFilterService()
        self.keyword_service = MailProcessorKeywordExtractorService()

        # 헬퍼 초기화
        self.graph_helper = MailProcessorGraphApiHelper()
        self.db_helper = MailProcessorDatabaseHelper()
        self.kafka_helper = MailProcessorKafkaHelper()

    async def process_new_mails(self) -> MailProcessingResult:
        """새 메일 처리 메인 함수"""
        start_time = time.time()
        total_processed = 0
        total_skipped = 0
        total_failed = 0
        errors = []

        try:
            # 1. 활성 계정 조회
            active_accounts = await self.db_helper.get_active_accounts()
            self.logger.info(f"활성 계정 {len(active_accounts)}개 처리 시작")

            for account in active_accounts:
                try:
                    # 2. 계정별 메일 처리
                    result = await self._process_account_mails(account)
                    total_processed += result.processed_count
                    total_skipped += result.skipped_count
                    total_failed += result.failed_count

                    if result.errors:
                        errors.extend(result.errors)

                except Exception as e:
                    error_msg = f"계정 {account['user_id']} 처리 실패: {str(e)}"
                    self.logger.error(error_msg, exc_info=True)
                    errors.append(error_msg)
                    total_failed += 1

                    # 계정별 에러 기록
                    await self.db_helper.handle_account_error(
                        account["user_id"], str(e)
                    )

            execution_time = int((time.time() - start_time) * 1000)

            return MailProcessingResult(
                account_id="ALL",
                total_fetched=total_processed + total_skipped,
                processed_count=total_processed,
                skipped_count=total_skipped,
                failed_count=total_failed,
                last_sync_time=datetime.now(),
                execution_time_ms=execution_time,
                errors=errors,
            )

        except Exception as e:
            self.logger.error(f"메일 처리 전체 실패: {str(e)}", exc_info=True)
            raise

    async def _process_account_mails(self, account: Dict) -> MailProcessingResult:
        """계정별 메일 처리"""
        account_start_time = time.time()
        processed_count = 0
        skipped_count = 0
        failed_count = 0
        errors = []

        try:
            # 1. Graph API에서 메일 조회
            mails = await self.graph_helper.fetch_mails_from_graph(account)
            self.logger.info(f"계정 {account['user_id']}: {len(mails)}개 메일 조회됨")

            # 2. 각 메일 처리
            for mail in mails:
                try:
                    processed_mail = await self._process_single_mail(
                        account["user_id"], mail
                    )

                    if processed_mail.processing_status == ProcessingStatus.SUCCESS:
                        processed_count += 1
                    elif processed_mail.processing_status == ProcessingStatus.SKIPPED:
                        skipped_count += 1
                    else:  # FAILED
                        failed_count += 1
                        if processed_mail.error_message:
                            errors.append(processed_mail.error_message)

                except Exception as e:
                    error_msg = f"메일 {mail.get('id', 'unknown')} 처리 실패: {str(e)}"
                    self.logger.error(error_msg)
                    errors.append(error_msg)
                    failed_count += 1

            # 3. 계정 동기화 시간 업데이트
            await self.db_helper.update_account_sync_time(
                account["user_id"], datetime.now()
            )

            execution_time = int((time.time() - account_start_time) * 1000)

            self.logger.info(
                f"계정 {account['user_id']} 처리 완료: "
                f"처리={processed_count}, 건너뜀={skipped_count}, 실패={failed_count}"
            )

            return MailProcessingResult(
                account_id=account["user_id"],
                total_fetched=len(mails),
                processed_count=processed_count,
                skipped_count=skipped_count,
                failed_count=failed_count,
                last_sync_time=datetime.now(),
                execution_time_ms=execution_time,
                errors=errors,
            )

        except Exception as e:
            self.logger.error(f"계정 {account['user_id']} 처리 실패: {str(e)}")
            raise

    async def _process_single_mail(
        self, account_id: str, mail: Dict
    ) -> ProcessedMailData:
        """개별 메일 처리 - 통합된 플로우"""
        try:
            # 1단계: 발신자 정보 추출
            sender_address = MailProcessorDataHelper._extract_sender_address(mail)
            subject = mail.get("subject", "")

            # 2단계: 발신자 필터링
            if not self.filter_service.should_process(sender_address, subject):
                self.logger.debug(
                    f"메일 필터링됨: {mail.get('id')} from {sender_address}"
                )
                return MailProcessorDataHelper.create_processed_mail_data(
                    mail,
                    account_id,
                    [],
                    ProcessingStatus.SKIPPED,
                    "발신자 필터링으로 제외",
                )

            # 3단계: 메일 내용 정리 (한 번만 수행)
            clean_content = self._prepare_mail_content(mail)

            # 4단계: 중복 검사 (정리된 내용의 해시로)
            is_duplicate, existing_keywords = (
                await self.db_helper.check_duplicate_by_content(
                    mail.get("id"), sender_address, clean_content
                )
            )

            if is_duplicate:
                self.logger.debug(f"중복 메일: {mail.get('id')}")
                # 기존 키워드가 있으면 그대로 사용
                return MailProcessorDataHelper.create_processed_mail_data(
                    mail,
                    account_id,
                    existing_keywords or [],
                    ProcessingStatus.SKIPPED,
                    "중복 메일",
                )

            # 5단계: 키워드 추출
            keyword_response = await self.keyword_service.extract_keywords(
                clean_content
            )

            # 6단계: DB 저장 및 이벤트 발행
            processed_mail = MailProcessorDataHelper.create_processed_mail_data(
                mail, account_id, keyword_response.keywords, ProcessingStatus.SUCCESS
            )

            # 컨텐츠 해시와 함께 저장
            await self.db_helper.save_mail_history_with_hash(
                processed_mail, clean_content
            )

            # Kafka 이벤트 발행
            await self.kafka_helper.publish_kafka_event(
                account_id, mail, processed_mail.keywords
            )

            return processed_mail

        except Exception as e:
            self.logger.error(f"메일 처리 실패 - {mail.get('id', 'unknown')}: {str(e)}")
            return MailProcessorDataHelper.create_processed_mail_data(
                mail, account_id, [], ProcessingStatus.FAILED, str(e)
            )

    def _prepare_mail_content(self, mail: Dict) -> str:
        """메일 내용을 추출하고 정리하는 통합 메서드"""
        # 1. 원본 내용 추출
        raw_content = MailProcessorDataHelper.extract_mail_content(mail)

        # 2. 텍스트 정제 (키워드 추출 서비스의 clean_text 활용)
        clean_content = self.keyword_service._clean_text(raw_content)

        # 3. 제목도 포함 (중요한 정보가 있을 수 있음)
        subject = mail.get("subject", "")
        if subject and subject not in clean_content:
            clean_content = f"{subject}\n{clean_content}"

        return clean_content

    async def process_graph_mail_item(
        self, mail_item: GraphMailItem, account_id: str
    ) -> ProcessedMailData:
        """GraphMailItem 객체를 받아서 처리하는 메서드"""
        try:
            # GraphMailItem을 Dict로 변환
            mail_dict = mail_item.model_dump()

            # 동일한 처리 플로우 사용
            return await self._process_single_mail(account_id, mail_dict)

        except Exception as e:
            self.logger.error(f"GraphMailItem 처리 실패 - {mail_item.id}: {str(e)}")
            return MailProcessorDataHelper.create_processed_mail_data(
                mail_item.model_dump(), account_id, [], ProcessingStatus.FAILED, str(e)
            )

    async def get_processing_stats(self) -> Dict:
        """처리 통계 조회"""
        try:
            # 최근 처리 통계
            query = """
                SELECT 
                    COUNT(*) as total_mails,
                    COUNT(CASE WHEN processed_at > datetime('now', '-1 hour') THEN 1 END) as recent_hour,
                    COUNT(CASE WHEN processed_at > datetime('now', '-1 day') THEN 1 END) as recent_day,
                    COUNT(DISTINCT content_hash) as unique_contents
                FROM mail_history
            """

            result = self.db_helper.db_manager.fetch_one(query)

            # 필터링 통계
            filter_stats = self.filter_service.get_filter_stats()

            return {
                "mail_stats": dict(result) if result else {},
                "filter_stats": filter_stats,
                "services_status": {
                    "keyword_extractor": "active",
                    "mail_filter": "active",
                    "graph_api": "active",
                    "database": "active",
                    "kafka": "active",
                },
            }

        except Exception as e:
            self.logger.error(f"통계 조회 실패: {str(e)}")
            return {"error": str(e)}
