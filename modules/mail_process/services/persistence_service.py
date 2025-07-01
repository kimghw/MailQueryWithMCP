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
        env_value = os.getenv("ENABLE_MAIL_DUPLICATE_CHECK", "true")
        # 주석 제거 (#로 시작하는 부분 제거)
        if '#' in env_value:
            env_value = env_value.split('#')[0].strip()
        
        self.duplicate_check_enabled = env_value.lower() == "true"
        self.logger.info(f"중복 체크 활성화: {self.duplicate_check_enabled}")
    
    def get_existing_mail_ids(self, mail_ids: List[str]) -> List[str]:
        """여러 메일 ID의 존재 여부를 한 번에 확인 (배치 조회)"""
        if not mail_ids or not self.duplicate_check_enabled:
            return []
        
        try:
            # IN 절을 사용한 배치 조회
            placeholders = ','.join(['?' for _ in mail_ids])
            query = f"""
                SELECT message_id 
                FROM mail_history 
                WHERE message_id IN ({placeholders})
            """
            
            results = self.db_service.db_manager.fetch_all(query, mail_ids)
            existing_ids = [row['message_id'] for row in results]
            
            self.logger.debug(f"배치 중복 체크: {len(mail_ids)}개 중 {len(existing_ids)}개 존재")
            return existing_ids
            
        except Exception as e:
            self.logger.error(f"배치 중복 체크 오류: {str(e)}")
            # 오류 시 모든 ID를 존재하는 것으로 간주 (안전하게)
            return mail_ids
    
    def is_duplicate_by_id(self, mail_id: str) -> bool:
        """메일 ID로만 간단히 중복 체크 (단일 체크)"""
        if not self.duplicate_check_enabled:
            return False
        
        try:
            existing_mail = self.db_service.get_mail_by_id(mail_id)
            return existing_mail is not None
        except Exception as e:
            self.logger.error(f"중복 체크 오류: {str(e)}")
            # 오류 시 중복으로 간주하여 안전하게 처리
            return True
    
    async def persist_mails(self, account_id: str, mails: List[Dict], mails_for_events: List[Dict] = None) -> Dict:
        """
        메일 데이터 저장
        
        ENABLE_MAIL_DUPLICATE_CHECK=false: DB 저장 없이 바로 이벤트 발행
        ENABLE_MAIL_DUPLICATE_CHECK=true: 신규 메일만 DB 저장 및 이벤트 발행
        
        Args:
            account_id: 계정 ID
            mails: 처리된 메일 리스트 (DB 저장용, 이미 중복 체크된 신규 메일만)
            mails_for_events: 이벤트 발행용 메일 리스트 (중복 필드 제거된 버전)
            
        Returns:
            저장 결과 통계
        """
        # 이벤트용 메일이 제공되지 않으면 기존 메일 사용
        if mails_for_events is None:
            mails_for_events = mails
            
        saved_count = 0
        failed_count = 0
        event_published_count = 0
        
        for i, mail in enumerate(mails):
            try:
                # 이벤트용 메일 가져오기
                event_mail = mails_for_events[i] if i < len(mails_for_events) else mail
                
                # 중복 체크가 비활성화된 경우
                if not self.duplicate_check_enabled:
                    # DB 저장 없이 바로 이벤트 발행
                    await self._publish_event(account_id, event_mail, mail)
                    event_published_count += 1
                    saved_count += 1  # 통계상 성공으로 처리
                    self.logger.debug(f"중복 체크 OFF - 이벤트만 발행: {mail.get('id')}")
                    continue
                
                # 중복 체크가 활성화된 경우 (이미 Phase 2에서 중복 확인됨)
                processed_mail = self._create_processed_mail_data(account_id, mail)
                
                # DB 저장
                success = self._save_to_database(processed_mail, mail.get('clean_content', ''))
                
                if success:
                    saved_count += 1
                    # DB 저장 성공 시 이벤트 발행
                    await self._publish_event(account_id, event_mail, mail)
                    event_published_count += 1
                    self.logger.debug(f"신규 메일 저장 및 이벤트 발행: {processed_mail.mail_id}")
                else:
                    failed_count += 1
                    
            except Exception as e:
                self.logger.error(f"메일 처리 실패: {str(e)}")
                failed_count += 1
        
        results = {
            'saved': saved_count,
            'duplicates': 0,  # Phase 2에서 이미 제외됨
            'failed': failed_count,
            'total': len(mails),
            'events_published': event_published_count,
            'duplicate_check_enabled': self.duplicate_check_enabled
        }
        
        self.logger.info(
            f"메일 처리 완료 - 저장: {saved_count}, "
            f"실패: {failed_count}, "
            f"이벤트 발행: {event_published_count}, "
            f"중복체크: {'ON' if self.duplicate_check_enabled else 'OFF'}"
        )
        
        return results
    
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
    
    async def _publish_event(self, account_id: str, event_mail: Dict, original_mail: Dict):
        """
        이벤트 발행
        
        Args:
            account_id: 계정 ID
            event_mail: 이벤트 발행용 메일 (중복 필드 제거됨)
            original_mail: 원본 메일 (키워드와 clean_content 정보 포함)
        """
        try:
            self.event_service.publish_mail_event(
                account_id=account_id,
                mail=event_mail,
                keywords=original_mail.get('keywords', []),
                clean_content=original_mail.get('clean_content', '')
            )
        except Exception as e:
            # 이벤트 발행 실패는 전체 프로세스를 중단시키지 않음
            self.logger.error(f"이벤트 발행 실패: {str(e)}")
            raise  # 통계를 위해 예외를 다시 발생시킴
    
    def get_duplicate_check_status(self) -> bool:
        """중복 체크 활성화 상태 반환"""
        return self.duplicate_check_enabled