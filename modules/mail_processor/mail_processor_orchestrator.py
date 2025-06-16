"""Mail Processor 오케스트레이터 - 완전 독립적 구현"""
import time
from datetime import datetime
from typing import List, Dict

from infra.core.logger import get_logger
from .mail_processor_schema import (
    MailProcessingResult, ProcessedMailData, ProcessingStatus, GraphMailItem
)
from .keyword_extractor_service import MailProcessorKeywordExtractorService
from .mail_filter_service import MailProcessorFilterService
from ._mail_processor_helpers import (
    MailProcessorGraphApiHelper,
    MailProcessorDatabaseHelper,
    MailProcessorKafkaHelper,
    MailProcessorDataHelper
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
                    await self.db_helper.handle_account_error(account['user_id'], str(e))
            
            execution_time = int((time.time() - start_time) * 1000)
            
            return MailProcessingResult(
                account_id="ALL",
                total_fetched=total_processed + total_skipped,
                processed_count=total_processed,
                skipped_count=total_skipped,
                failed_count=total_failed,
                last_sync_time=datetime.now(),
                execution_time_ms=execution_time,
                errors=errors
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
                    processed_mail = await self._process_single_mail(account['user_id'], mail)
                    
                    if processed_mail.processing_status == ProcessingStatus.SUCCESS:
                        # DB 저장
                        await self.db_helper.save_mail_history(processed_mail)
                        # Kafka 이벤트 발행
                        await self.kafka_helper.publish_kafka_event(account['user_id'], mail)
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
            await self.db_helper.update_account_sync_time(account['user_id'], datetime.now())
            
            execution_time = int((time.time() - account_start_time) * 1000)
            
            self.logger.info(
                f"계정 {account['user_id']} 처리 완료: "
                f"처리={processed_count}, 건너뜀={skipped_count}, 실패={failed_count}"
            )
            
            return MailProcessingResult(
                account_id=account['user_id'],
                total_fetched=len(mails),
                processed_count=processed_count,
                skipped_count=skipped_count,
                failed_count=failed_count,
                last_sync_time=datetime.now(),
                execution_time_ms=execution_time,
                errors=errors
            )
            
        except Exception as e:
            self.logger.error(f"계정 {account['user_id']} 처리 실패: {str(e)}")
            raise
    
    async def _process_single_mail(self, account_id: str, mail: Dict) -> ProcessedMailData:
        """개별 메일 처리"""
        try:
            mail_id = mail.get('id', 'unknown')
            sender_info = mail.get('from', {}).get('emailAddress', {})
            sender_address = sender_info.get('address', '')
            subject = mail.get('subject', '')
            
            # 1. 발신자 필터링 (from_address 또는 from 필드 모두 지원)
            sender_info = mail.get('from_address', mail.get('from', {}))
            if isinstance(sender_info, dict):
                sender_info = sender_info.get('emailAddress', {})
                sender_address = sender_info.get('address', '')
            else:
                sender_address = ''
                
            if not self.filter_service.should_process(sender_address, subject):
                return MailProcessorDataHelper.create_processed_mail_data(
                    mail, account_id, [], ProcessingStatus.SKIPPED,
                    "발신자 필터링으로 제외"
                )
            
            # 2. 중복 검사
            if await self.db_helper.is_duplicate_mail(mail_id, sender_address):
                return MailProcessorDataHelper.create_processed_mail_data(
                    mail, account_id, [], ProcessingStatus.SKIPPED,
                    "중복 메일"
                )
            
            # 3. 키워드 추출
            body_content = MailProcessorDataHelper.extract_mail_content(mail)
            keyword_response = await self.keyword_service.extract_keywords(body_content)
            
            # 4. 처리된 메일 데이터 생성
            return MailProcessorDataHelper.create_processed_mail_data(
                mail, account_id, keyword_response.keywords, ProcessingStatus.SUCCESS
            )
            
        except Exception as e:
            self.logger.error(f"메일 처리 실패 - {mail.get('id', 'unknown')}: {str(e)}")
            return MailProcessorDataHelper.create_processed_mail_data(
                mail, account_id, [], ProcessingStatus.FAILED, str(e)
            )
    
    async def process_graph_mail_item(self, mail_item: GraphMailItem, account_id: str) -> ProcessedMailData:
        """GraphMailItem 객체를 받아서 처리하는 메서드"""
        try:
            # GraphMailItem을 Dict로 변환
            mail_dict = mail_item.model_dump()
            
            # 발신자 정보 추출
            sender_address = ""
            if mail_item.from_address and isinstance(mail_item.from_address, dict):
                email_address = mail_item.from_address.get('emailAddress', {})
                sender_address = email_address.get('address', '')
            elif mail_item.sender and isinstance(mail_item.sender, dict):
                email_address = mail_item.sender.get('emailAddress', {})
                sender_address = email_address.get('address', '')
            
            # 1. 발신자 필터링
            if not self.filter_service.should_process(sender_address, mail_item.subject or ''):
                return MailProcessorDataHelper.create_processed_mail_data(
                    mail_dict, account_id, [], ProcessingStatus.SKIPPED,
                    "발신자 필터링으로 제외"
                )
            
            # 2. 중복 검사
            if await self.db_helper.is_duplicate_mail(mail_item.id, sender_address):
                return MailProcessorDataHelper.create_processed_mail_data(
                    mail_dict, account_id, [], ProcessingStatus.SKIPPED,
                    "중복 메일"
                )
            
            # 3. 키워드 추출
            body_content = self._extract_content_from_graph_mail_item(mail_item)
            keyword_response = await self.keyword_service.extract_keywords(body_content)
            
            # 4. 처리된 메일 데이터 생성
            processed_mail = MailProcessorDataHelper.create_processed_mail_data(
                mail_dict, account_id, keyword_response.keywords, ProcessingStatus.SUCCESS
            )
            
            # 5. DB 저장
            await self.db_helper.save_mail_history(processed_mail)
            
            # 6. Kafka 이벤트 발행
            await self.kafka_helper.publish_kafka_event(account_id, mail_dict)
            
            self.logger.info(f"GraphMailItem 처리 완료: {mail_item.id}")
            return processed_mail
            
        except Exception as e:
            self.logger.error(f"GraphMailItem 처리 실패 - {mail_item.id}: {str(e)}")
            return MailProcessorDataHelper.create_processed_mail_data(
                mail_item.model_dump(), account_id, [], ProcessingStatus.FAILED, str(e)
            )
    
    def _extract_content_from_graph_mail_item(self, mail_item: GraphMailItem) -> str:
        """GraphMailItem에서 텍스트 내용 추출"""
        # 본문 내용 추출 우선순위: body.content > body_preview > subject
        body_content = ""
        
        # 1. body.content 확인
        if mail_item.body and isinstance(mail_item.body, dict) and mail_item.body.get('content'):
            body_content = mail_item.body['content']
        
        # 2. body_preview 확인
        elif mail_item.body_preview:
            body_content = mail_item.body_preview
        
        # 3. subject만 있는 경우
        elif mail_item.subject:
            body_content = mail_item.subject
        
        return body_content
    
    async def get_processing_stats(self) -> Dict:
        """처리 통계 조회"""
        try:
            # 최근 처리 통계
            query = """
                SELECT 
                    COUNT(*) as total_mails,
                    COUNT(CASE WHEN processed_at > datetime('now', '-1 hour') THEN 1 END) as recent_hour,
                    COUNT(CASE WHEN processed_at > datetime('now', '-1 day') THEN 1 END) as recent_day
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
                    "kafka": "active"
                }
            }
            
        except Exception as e:
            self.logger.error(f"통계 조회 실패: {str(e)}")
            return {"error": str(e)}
