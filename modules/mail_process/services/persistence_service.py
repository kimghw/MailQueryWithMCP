"""지속성 서비스 - 중복 체크 및 저장"""

import os
import json
from typing import Dict, List, Tuple
from datetime import datetime
from infra.core import get_logger
from modules.mail_process.services.db_service import MailDatabaseService
from modules.mail_process.services.event_service import MailEventService
from modules.mail_process.mail_processor_schema import ProcessedMailData


class PersistenceService:
    """지속성 관리 서비스"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.db_service = MailDatabaseService()
        self.event_service = MailEventService()
        
        # 중복 체크 활성화 여부 (환경변수에서 읽기)
        self.duplicate_check_enabled = (
            os.getenv("ENABLE_MAIL_DUPLICATE_CHECK", "true").lower() == "true"
        )
        self.logger.info(f"중복 체크 활성화: {self.duplicate_check_enabled}")
    
    async def persist_mails(self, account_id: str, mails: List[Dict]) -> Dict:
        """
        메일 데이터 저장
        
        ENABLE_MAIL_DUPLICATE_CHECK=false: DB 저장 없이 바로 이벤트 발행
        ENABLE_MAIL_DUPLICATE_CHECK=true: 중복 체크 → 신규만 DB 저장 및 이벤트 발행
        
        Args:
            account_id: 계정 ID
            mails: 처리된 메일 리스트
            
        Returns:
            저장 결과 통계
        """
        saved_count = 0
        duplicate_count = 0
        failed_count = 0
        event_published_count = 0
        
        for mail in mails:
            try:
                # 중복 체크가 비활성화된 경우
                if not self.duplicate_check_enabled:
                    # DB 저장 없이 바로 이벤트 발행
                    await self._publish_event(account_id, mail)
                    event_published_count += 1
                    saved_count += 1  # 통계상 성공으로 처리
                    self.logger.debug(f"중복 체크 OFF - 이벤트만 발행: {mail.get('id')}")
                    continue
                
                # 중복 체크가 활성화된 경우
                processed_mail = self._create_processed_mail_data(account_id, mail)
                
                # 중복 체크
                is_duplicate = self._check_duplicate(processed_mail, mail.get('clean_content', ''))
                
                if is_duplicate:
                    # 중복인 경우: 저장도 안하고 이벤트도 안보냄
                    self.logger.debug(f"중복 메일 건너뜀: {processed_mail.mail_id}")
                    duplicate_count += 1
                    continue
                
                # 신규 메일인 경우: DB 저장
                success = self._save_to_database(processed_mail, mail.get('clean_content', ''))
                
                if success:
                    saved_count += 1
                    # DB 저장 성공 시 이벤트 발행
                    await self._publish_event(account_id, mail)
                    event_published_count += 1
                    self.logger.debug(f"신규 메일 저장 및 이벤트 발행: {processed_mail.mail_id}")
                else:
                    failed_count += 1
                    
            except Exception as e:
                self.logger.error(f"메일 처리 실패: {str(e)}")
                failed_count += 1
        
        results = {
            'saved': saved_count,
            'duplicates': duplicate_count,
            'failed': failed_count,
            'total': len(mails),
            'events_published': event_published_count,
            'duplicate_check_enabled': self.duplicate_check_enabled
        }
        
        self.logger.info(
            f"메일 처리 완료 - 저장: {saved_count}, "
            f"중복: {duplicate_count}, 실패: {failed_count}, "
            f"이벤트 발행: {event_published_count}, "
            f"중복체크: {'ON' if self.duplicate_check_enabled else 'OFF'}"
        )
        
        return results
    
    def _check_duplicate(self, processed_mail: ProcessedMailData, clean_content: str) -> bool:
        """
        중복 체크 (중복 체크가 활성화된 경우에만 호출됨)
        
        Args:
            processed_mail: 처리된 메일 데이터
            clean_content: 정제된 메일 내용
            
        Returns:
            중복 여부 (True: 중복, False: 신규)
        """
        try:
            # 메일 ID로 먼저 체크
            existing_mail = self.db_service.get_mail_by_id(processed_mail.mail_id)
            if existing_mail:
                self.logger.debug(f"메일 ID 중복: {processed_mail.mail_id}")
                return True
            
            # 컨텐츠 해시로 체크 (내용 기반 중복 체크)
            if clean_content:
                is_duplicate, _ = self.db_service.check_duplicate_by_content_hash(
                    processed_mail.mail_id,
                    clean_content
                )
                if is_duplicate:
                    self.logger.debug(f"내용 해시 중복: {processed_mail.mail_id}")
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"중복 체크 오류: {str(e)}")
            # 오류 시 중복으로 간주하여 안전하게 처리
            return True
    
    def _save_to_database(self, processed_mail: ProcessedMailData, clean_content: str) -> bool:
        """
        데이터베이스에 저장 (중복 체크가 활성화된 경우에만 호출됨)
        
        Args:
            processed_mail: 처리된 메일 데이터
            clean_content: 정제된 메일 내용
            
        Returns:
            저장 성공 여부
        """
        try:
            return self.db_service.save_mail_with_hash(processed_mail, clean_content)
        except Exception as e:
            if "UNIQUE constraint failed" in str(e):
                # 동시성으로 인한 중복 저장 시도
                self.logger.warning(f"동시성 중복 발생: {processed_mail.mail_id}")
                return False
            else:
                self.logger.error(f"DB 저장 오류: {str(e)}")
                raise
    
    def _create_processed_mail_data(self, account_id: str, mail: Dict) -> ProcessedMailData:
        """ProcessedMailData 객체 생성"""
        return ProcessedMailData(
            mail_id=mail.get('id', 'unknown'),
            account_id=account_id,
            sender_address=mail.get('sender_address', ''),
            subject=mail.get('subject', ''),
            body_preview=mail.get('bodyPreview', ''),
            sent_time=mail.get('sent_time', datetime.now()),
            keywords=mail.get('keywords', []),
            processing_status=mail.get('processing_status', 'SUCCESS'),
            error_message=mail.get('error_message'),
            processed_at=datetime.now()
        )
    
    async def _publish_event(self, account_id: str, mail: Dict):
        """이벤트 발행"""
        try:
            self.event_service.publish_mail_event(
                account_id=account_id,
                mail=mail,
                keywords=mail.get('keywords', []),
                clean_content=mail.get('clean_content', '')
            )
        except Exception as e:
            # 이벤트 발행 실패는 전체 프로세스를 중단시키지 않음
            self.logger.error(f"이벤트 발행 실패: {str(e)}")
            raise  # 통계를 위해 예외를 다시 발생시킴
    
    def get_duplicate_check_status(self) -> bool:
        """중복 체크 활성화 상태 반환"""
        return self.duplicate_check_enabled