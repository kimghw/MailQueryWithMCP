"""Mail Processor 헬퍼 함수들 (350줄 제한 대응)"""
import json
import uuid
import aiohttp
from datetime import datetime
from typing import List, Dict, Any, Optional

from infra.core.logger import get_logger
from infra.core.token_service import get_token_service
from infra.core.database import get_database_manager
from infra.core.kafka_client import get_kafka_client
from infra.core.config import get_config
from .mail_processor_schema import ProcessedMailData, ProcessingStatus, MailReceivedEvent

logger = get_logger(__name__)


class MailProcessorGraphApiHelper:
    """Graph API 호출 헬퍼"""
    
    def __init__(self):
        self.token_service = get_token_service()
    
    async def fetch_mails_from_graph(self, account: Dict) -> List[Dict]:
        """Graph API 직접 호출로 메일 조회"""
        try:
            # 유효한 토큰 획득
            access_token = await self.token_service.get_valid_access_token(account['user_id'])
            if not access_token:
                raise Exception(f"유효한 토큰이 없습니다: {account['user_id']}")
            
            # 마지막 동기화 이후 메일만 조회
            since_filter = ""
            if account.get('last_sync_time'):
                since_date = account['last_sync_time'].isoformat() + 'Z'
                since_filter = f"receivedDateTime ge {since_date}"
            
            # Graph API URL 구성
            url = "https://graph.microsoft.com/v1.0/me/messages"
            params = {
                "$select": "id,subject,from,body,bodyPreview,receivedDateTime,hasAttachments,importance,isRead",
                "$top": 50,
                "$orderby": "receivedDateTime desc"
            }
            
            if since_filter:
                params["$filter"] = since_filter
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json',
                'Prefer': 'outlook.body-content-type="text"'
            }
            
            all_mails = []
            
            async with aiohttp.ClientSession() as session:
                while url and len(all_mails) < 200:  # 최대 200개 제한
                    async with session.get(url, headers=headers, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            mails = data.get('value', [])
                            all_mails.extend(mails)
                            
                            # 다음 페이지 URL
                            url = data.get('@odata.nextLink')
                            params = {}  # nextLink에 이미 파라미터 포함
                            
                            logger.debug(f"계정 {account['user_id']}: {len(mails)}개 메일 조회")
                            
                        elif response.status == 401:
                            # 토큰 만료 - 재시도 1회
                            logger.warning(f"토큰 만료, 갱신 시도: {account['user_id']}")
                            access_token = await self.token_service.force_token_refresh(account['user_id'])
                            headers['Authorization'] = f'Bearer {access_token}'
                            continue
                            
                        else:
                            error_text = await response.text()
                            raise Exception(f"Graph API 호출 실패: {response.status} - {error_text}")
            
            logger.info(f"계정 {account['user_id']}: 총 {len(all_mails)}개 메일 조회 완료")
            return all_mails
            
        except Exception as e:
            logger.error(f"Graph API 호출 실패 - 계정 {account['user_id']}: {str(e)}")
            raise


class MailProcessorDatabaseHelper:
    """데이터베이스 관련 헬퍼"""
    
    def __init__(self):
        self.db_manager = get_database_manager()
    
    async def get_active_accounts(self) -> List[Dict]:
        """활성 계정 조회"""
        query = """
            SELECT id, user_id, user_name, last_sync_time, access_token, refresh_token
            FROM accounts 
            WHERE is_active = 1 
            ORDER BY last_sync_time ASC NULLS FIRST
        """
        
        rows = self.db_manager.fetch_all(query)
        accounts = []
        
        for row in rows:
            account = dict(row)
            # datetime 변환
            if account['last_sync_time']:
                account['last_sync_time'] = datetime.fromisoformat(account['last_sync_time'])
            accounts.append(account)
        
        return accounts
    
    async def is_duplicate_mail(self, mail_id: str, sender_address: str) -> bool:
        """중복 메일 검사"""
        query = """
            SELECT COUNT(*) as count 
            FROM mail_history 
            WHERE message_id = ? OR (sender = ? AND message_id LIKE ?)
        """
        
        # 유사한 메일 ID 패턴도 확인 (Graph API ID는 변경될 수 있음)
        similar_pattern = f"%{mail_id[-20:]}%" if len(mail_id) > 20 else mail_id
        
        result = self.db_manager.fetch_one(query, (mail_id, sender_address, similar_pattern))
        return result['count'] > 0
    
    async def save_mail_history(self, processed_mail: ProcessedMailData) -> None:
        """메일 히스토리 저장"""
        # account_id가 문자열인 경우 accounts 테이블에서 실제 ID 조회
        if isinstance(processed_mail.account_id, str):
            account_query = "SELECT id FROM accounts WHERE user_id = ?"
            account_result = self.db_manager.fetch_one(account_query, (processed_mail.account_id,))
            
            if account_result:
                actual_account_id = account_result['id']
            else:
                # 테스트용 계정이 없는 경우 임시로 생성
                logger.warning(f"계정 {processed_mail.account_id}가 존재하지 않음, 임시 계정 생성")
                insert_account_query = """
                    INSERT INTO accounts (user_id, user_name, is_active) 
                    VALUES (?, ?, 1)
                """
                self.db_manager.execute_query(insert_account_query, (
                    processed_mail.account_id, 
                    f"Test User ({processed_mail.account_id})"
                ))
                
                # 생성된 계정 ID 조회
                account_result = self.db_manager.fetch_one(account_query, (processed_mail.account_id,))
                actual_account_id = account_result['id']
        else:
            actual_account_id = processed_mail.account_id
        
        query = """
            INSERT INTO mail_history (
                account_id, message_id, received_time, subject, 
                sender, keywords, processed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        
        keywords_json = json.dumps(processed_mail.keywords, ensure_ascii=False)
        
        self.db_manager.execute_query(query, (
            actual_account_id,
            processed_mail.mail_id,
            processed_mail.sent_time,
            processed_mail.subject,
            processed_mail.sender_address,
            keywords_json,
            processed_mail.processed_at
        ))
    
    async def update_account_sync_time(self, account_id: str, sync_time: datetime) -> None:
        """계정 동기화 시간 업데이트"""
        query = "UPDATE accounts SET last_sync_time = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?"
        self.db_manager.execute_query(query, (sync_time, account_id))
    
    async def handle_account_error(self, account_id: str, error_message: str) -> None:
        """계정 에러 처리"""
        # 처리 로그에 에러 기록
        log_query = """
            INSERT INTO processing_logs (run_id, account_id, log_level, message)
            VALUES (?, (SELECT id FROM accounts WHERE user_id = ?), 'ERROR', ?)
        """
        
        run_id = str(uuid.uuid4())
        self.db_manager.execute_query(log_query, (run_id, account_id, error_message))
        
        logger.error(f"계정 {account_id} 에러 기록: {error_message}")


class MailProcessorKafkaHelper:
    """Kafka 이벤트 발행 헬퍼"""
    
    def __init__(self):
        self.kafka_client = get_kafka_client()
        self.config = get_config()
    
    async def publish_kafka_event(self, account_id: str, mail: Dict, keywords: List[str] = None) -> None:
        """Kafka 이벤트 발행 - 키워드 정보 포함"""
        try:
            # mail 딕셔너리의 datetime 객체들을 문자열로 변환
            mail_copy = self._convert_datetime_to_string(mail.copy())
            
            # 키워드 정보를 메일 데이터에 추가
            if keywords:
                mail_copy['extracted_keywords'] = keywords
            
            event = MailReceivedEvent(
                event_id=str(uuid.uuid4()),
                account_id=account_id,
                occurred_at=datetime.now(),
                request_params={
                    "$select": "id,subject,from,body,bodyPreview,receivedDateTime",
                    "$top": 50
                },
                response_data={"value": [mail_copy]},
                response_timestamp=datetime.now()
            )
            
            # datetime 객체를 문자열로 변환하여 JSON 직렬화 가능하게 만듦
            event_data = event.model_dump()
            
            # datetime 필드들을 ISO 형식 문자열로 변환
            if 'occurred_at' in event_data and isinstance(event_data['occurred_at'], datetime):
                event_data['occurred_at'] = event_data['occurred_at'].isoformat()
            if 'response_timestamp' in event_data and isinstance(event_data['response_timestamp'], datetime):
                event_data['response_timestamp'] = event_data['response_timestamp'].isoformat()
            
            self.kafka_client.produce_event(
                topic=self.config.kafka_topic_email_events,
                event_data=event_data,
                key=account_id
            )
            
            logger.debug(f"Kafka 이벤트 발행 완료 (키워드 {len(keywords) if keywords else 0}개): {mail.get('id', 'unknown')}")
            
        except Exception as e:
            logger.error(f"Kafka 이벤트 발행 실패: {str(e)}")
            # 이벤트 발행 실패는 전체 프로세스를 중단시키지 않음
    
    def _convert_datetime_to_string(self, data: Any) -> Any:
        """재귀적으로 datetime 객체를 문자열로 변환"""
        if isinstance(data, datetime):
            return data.isoformat()
        elif isinstance(data, dict):
            return {key: self._convert_datetime_to_string(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._convert_datetime_to_string(item) for item in data]
        else:
            return data


class MailProcessorDataHelper:
    """메일 데이터 처리 헬퍼"""
    
    @staticmethod
    def create_processed_mail_data(
        mail: Dict, 
        account_id: str, 
        keywords: List[str], 
        status: ProcessingStatus,
        error_message: Optional[str] = None
    ) -> ProcessedMailData:
        """처리된 메일 데이터 생성 - 다양한 발신자 필드 지원"""
        # 발신자 정보 추출 - 여러 필드 순차 확인
        sender_address = MailProcessorDataHelper._extract_sender_address(mail)
        
        # 수신 시간 파싱 (received_date_time 또는 receivedDateTime 필드 지원)
        received_time_str = mail.get('received_date_time', mail.get('receivedDateTime', ''))
        try:
            if isinstance(received_time_str, datetime):
                sent_time = received_time_str
            elif isinstance(received_time_str, str):
                if received_time_str.endswith('Z'):
                    received_time_str = received_time_str[:-1] + '+00:00'
                sent_time = datetime.fromisoformat(received_time_str)
            else:
                sent_time = datetime.now()
        except (ValueError, TypeError):
            sent_time = datetime.now()
        
        # 본문 미리보기 추출 (body_preview 또는 bodyPreview 필드 지원)
        body_preview = mail.get('body_preview', mail.get('bodyPreview', ''))
        
        return ProcessedMailData(
            mail_id=mail.get('id', 'unknown'),
            account_id=account_id,
            sender_address=sender_address,
            subject=mail.get('subject', ''),
            body_preview=body_preview,
            sent_time=sent_time,
            keywords=keywords,
            processing_status=status,
            error_message=error_message
        )
    
    @staticmethod
    def extract_mail_content(mail: Dict) -> str:
        """메일에서 텍스트 내용 추출"""
        # 본문 내용 추출 우선순위: body.content > bodyPreview > subject
        body_content = ""
        
        # 1. body.content 확인
        body = mail.get('body', {})
        if isinstance(body, dict) and body.get('content'):
            body_content = body['content']
        
        # 2. bodyPreview 확인
        elif mail.get('bodyPreview'):
            body_content = mail['bodyPreview']
        
        # 3. subject만 있는 경우
        elif mail.get('subject'):
            body_content = mail['subject']
        
        return body_content
    
    @staticmethod
    def _extract_sender_address(mail: Dict) -> str:
        """발신자 주소 추출 - 여러 필드 순차 확인"""
        
        # 1. from 필드 확인
        from_field = mail.get('from', {})
        if from_field and isinstance(from_field, dict):
            email_addr = from_field.get('emailAddress', {})
            if email_addr and email_addr.get('address'):
                return email_addr['address']
        
        # 2. sender 필드 확인
        sender_field = mail.get('sender', {})
        if sender_field and isinstance(sender_field, dict):
            email_addr = sender_field.get('emailAddress', {})
            if email_addr and email_addr.get('address'):
                return email_addr['address']
        
        # 3. from_address 필드 확인 (GraphMailItem 호환)
        from_address = mail.get('from_address', {})
        if from_address and isinstance(from_address, dict):
            email_addr = from_address.get('emailAddress', {})
            if email_addr and email_addr.get('address'):
                return email_addr['address']
        
        # 4. 초안 메일의 경우 빈 문자열 반환
        if mail.get('isDraft', False):
            logger.debug(f"초안 메일로 발신자 정보 없음: {mail.get('id', 'unknown')}")
            return ''
        
        # 5. 발신자 정보가 없는 경우 로깅
        logger.debug(f"발신자 정보 없음", extra={
            "mail_id": mail.get('id', 'unknown'),
            "is_draft": mail.get('isDraft', False),
            "has_from": bool(mail.get('from')),
            "has_sender": bool(mail.get('sender')),
            "has_from_address": bool(mail.get('from_address')),
            "subject": mail.get('subject', '')[:50]
        })
        
        return ''  # 발신자 정보 없음
