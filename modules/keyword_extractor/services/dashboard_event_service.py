"""대시보드 이벤트 발행 서비스 - 간단 버전"""

import uuid
from datetime import datetime
from typing import Dict, Optional, Any
from infra.core.logger import get_logger
from infra.core.kafka_client import get_kafka_client
from infra.core.config import get_config


class DashboardEventService:
    """구조화된 이메일 분석 결과를 즉시 이벤트로 발행하는 서비스"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.kafka_client = get_kafka_client()
        self.config = get_config()
        
        # 설정값
        self.dashboard_events_enabled = self.config.get_setting(
            "ENABLE_DASHBOARD_EVENTS", "true"
        ).lower() == "true"
        
        self.dashboard_topic = self.config.get_setting(
            "KAFKA_TOPIC_DASHBOARD_EVENTS", "email.api.response"
        )
        
        self.logger.info(
            f"대시보드 이벤트 서비스 초기화: "
            f"enabled={self.dashboard_events_enabled}, "
            f"topic={self.dashboard_topic}"
        )
    
    async def publish_extraction_result(
        self, 
        mail_id: str, 
        structured_result: Dict[str, Any], 
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        구조화된 추출 결과 즉시 이벤트 발행
        
        Args:
            mail_id: 메일 ID
            structured_result: 구조화된 분석 결과 (send_time 포함)
            metadata: 추출 메타데이터 (모델명, 토큰 사용량 등)
            
        Returns:
            발행 성공 여부
        """
        if not self.dashboard_events_enabled:
            self.logger.debug("대시보드 이벤트 비활성화 - 발행 건너뜀")
            return True
        
        if not self._is_dashboard_worthy(structured_result):
            self.logger.debug(f"대시보드 이벤트 조건 불충족 - mail_id: {mail_id}")
            return True  # 조건 불충족은 성공으로 간주
        
        try:
            # 기본 메타데이터 설정
            default_metadata = {
                'success': True,
                'extraction_time_ms': 0,
                'model_used': 'unknown'
            }
            
            if metadata:
                default_metadata.update(metadata)
            
            # 이벤트 데이터 생성
            event_data = self._create_single_event(mail_id, structured_result, default_metadata)
            
            # Kafka 이벤트 발행
            success = self.kafka_client.produce_event(
                topic=self.dashboard_topic,
                event_data=event_data,
                key=f"dashboard_{mail_id}"
            )
            
            if success:
                self.logger.info(
                    f"대시보드 이벤트 발행 완료: "
                    f"mail_id={mail_id}, "
                    f"agenda_no={structured_result.get('agenda_no', 'N/A')}, "
                    f"mail_type={structured_result.get('mail_type', 'N/A')}"
                )
                return True
            else:
                self.logger.error(f"Kafka 이벤트 발행 실패: mail_id={mail_id}")
                return False
            
        except Exception as e:
            self.logger.error(f"대시보드 이벤트 발행 중 예외: mail_id={mail_id}, error={str(e)}", exc_info=True)
            return False
    
    def _is_dashboard_worthy(self, structured_result: Dict[str, Any]) -> bool:
        """
        대시보드 이벤트 발행 조건 확인
        
        Args:
            structured_result: 구조화된 분석 결과
            
        Returns:
            발행 조건 충족 여부
        """
        # 필수 필드 확인
        if not isinstance(structured_result, dict):
            return False
        
        # 아젠다 번호가 있는 경우
        if structured_result.get('agenda_no'):
            return True
        
        # 특정 메일 타입인 경우
        mail_type = structured_result.get('mail_type')
        if mail_type in ['REQUEST', 'RESPONSE', 'NOTIFICATION', 'COMPLETED']:
            return True
        
        # 발신자 조직이 IACS 멤버인 경우
        sender_org = structured_result.get('sender_organization')
        iacs_members = ['ABS', 'BV', 'CCS', 'CRS', 'DNV', 'IRS', 'KR', 'NK', 'PRS', 'RINA', 'IL', 'TL']
        if sender_org in iacs_members:
            return True
        
        # 마감일이 있는 경우
        if structured_result.get('has_deadline') and structured_result.get('deadline'):
            return True
        
        return False
    
    def _create_single_event(self, mail_id: str, structured_result: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        단일 이벤트 데이터 생성
        
        Args:
            mail_id: 메일 ID
            structured_result: 구조화된 분석 결과
            metadata: 추출 메타데이터
            
        Returns:
            이벤트 데이터
        """
        current_time = datetime.utcnow().isoformat() + 'Z'
        
        return {
            "event_type": "email-dashboard",
            "event_id": str(uuid.uuid4()),
            "occurred_at": current_time,
            "source": "iacsgraph-keyword-extractor",
            "version": "1.0",
            "correlation_id": str(uuid.uuid4()),
            "data": {
                "mail_id": mail_id,
                "extraction_result": structured_result,  # send_time이 이미 포함됨
                "extraction_metadata": metadata,
                "processing_timestamp": current_time
            }
        }