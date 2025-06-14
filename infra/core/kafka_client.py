"""
IACSGraph 프로젝트의 Kafka 클라이언트 시스템

Kafka Producer와 Consumer를 관리하여 이벤트 기반 아키텍처를 지원합니다.
레이지 싱글톤 패턴으로 구현되어 전역에서 동일한 클라이언트를 사용합니다.
"""

import json
import threading
from functools import lru_cache
from typing import Optional, Dict, Any, List, Callable
from uuid import uuid4
from datetime import datetime

from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError as KafkaLibError, KafkaTimeoutError

from .config import get_config
from .exceptions import KafkaError, KafkaConnectionError, KafkaProducerError, KafkaConsumerError
from .logger import get_logger

logger = get_logger(__name__)


class KafkaClient:
    """Kafka Producer와 Consumer를 관리하는 클라이언트 클래스"""

    def __init__(self):
        """Kafka 클라이언트 초기화"""
        self.config = get_config()
        self._producer: Optional[KafkaProducer] = None
        self._consumers: Dict[str, KafkaConsumer] = {}
        self._lock = threading.Lock()

    def _get_producer(self) -> KafkaProducer:
        """Kafka Producer를 반환 (레이지 초기화)"""
        if self._producer is None:
            with self._lock:
                if self._producer is None:
                    try:
                        self._producer = KafkaProducer(
                            bootstrap_servers=self.config.kafka_bootstrap_servers,
                            # JSON 직렬화
                            value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode('utf-8'),
                            key_serializer=lambda k: str(k).encode('utf-8') if k else None,
                            # 안정성 설정
                            acks='all',  # 모든 인싱크 리플리카에 쓰기 완료 확인
                            retries=3,   # 실패 시 재시도
                            max_in_flight_requests_per_connection=1,  # 순서 보장
                            # 성능 최적화
                            compression_type='gzip',  # 메시지 압축
                            batch_size=16384,  # 배치 크기 (16KB)
                            linger_ms=10,      # 배치 대기 시간
                            # 타임아웃 설정
                            request_timeout_ms=self.config.kafka_timeout * 1000,
                        )
                        logger.info(f"Kafka Producer 초기화 완료: {self.config.kafka_bootstrap_servers}")
                        
                    except Exception as e:
                        raise KafkaConnectionError(
                            f"Kafka Producer 연결 실패: {str(e)}",
                            details={"servers": self.config.kafka_bootstrap_servers}
                        ) from e
        
        return self._producer

    def create_consumer(
        self, 
        topics: List[str], 
        consumer_group_id: Optional[str] = None,
        auto_offset_reset: str = 'earliest'
    ) -> KafkaConsumer:
        """
        Kafka Consumer를 생성합니다.
        
        Args:
            topics: 구독할 토픽 목록
            consumer_group_id: 컨슈머 그룹 ID
            auto_offset_reset: 오프셋 리셋 정책
            
        Returns:
            KafkaConsumer 인스턴스
        """
        group_id = consumer_group_id or self.config.kafka_consumer_group_id
        consumer_key = f"{group_id}:{':'.join(sorted(topics))}"
        
        if consumer_key not in self._consumers:
            try:
                consumer = KafkaConsumer(
                    *topics,
                    bootstrap_servers=self.config.kafka_bootstrap_servers,
                    group_id=group_id,
                    # 역직렬화
                    value_deserializer=lambda m: json.loads(m.decode('utf-8')) if m else None,
                    key_deserializer=lambda k: k.decode('utf-8') if k else None,
                    # 오프셋 관리
                    auto_offset_reset=auto_offset_reset,
                    enable_auto_commit=True,
                    auto_commit_interval_ms=5000,  # 5초마다 오프셋 커밋
                    # 세션 관리
                    session_timeout_ms=10000,     # 10초 세션 타임아웃
                    max_poll_interval_ms=300000,  # 5분 폴링 간격
                    # 성능 설정
                    fetch_min_bytes=1,
                    fetch_max_wait_ms=500,
                    max_partition_fetch_bytes=1048576,  # 1MB
                    # 타임아웃 설정
                    consumer_timeout_ms=self.config.kafka_timeout * 1000,
                )
                
                self._consumers[consumer_key] = consumer
                logger.info(f"Kafka Consumer 생성: 그룹={group_id}, 토픽={topics}")
                
            except Exception as e:
                raise KafkaConnectionError(
                    f"Kafka Consumer 생성 실패: {str(e)}",
                    details={"topics": topics, "group_id": group_id}
                ) from e
        
        return self._consumers[consumer_key]

    def produce_event(
        self, 
        topic: str, 
        event_data: Dict[str, Any], 
        key: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        이벤트를 Kafka 토픽에 발행합니다.
        
        Args:
            topic: 대상 토픽
            event_data: 이벤트 데이터
            key: 메시지 키 (파티셔닝용)
            headers: 메시지 헤더
            
        Returns:
            발행 성공 여부
        """
        try:
            producer = self._get_producer()
            
            # 헤더 준비
            kafka_headers = []
            if headers:
                kafka_headers = [(k, v.encode('utf-8')) for k, v in headers.items()]
            
            # 메시지 발행
            future = producer.send(
                topic=topic,
                value=event_data,
                key=key,
                headers=kafka_headers
            )
            
            # 전송 완료 대기
            record_metadata = future.get(timeout=self.config.kafka_timeout)
            
            logger.debug(
                f"이벤트 발행 성공: topic={topic}, partition={record_metadata.partition}, "
                f"offset={record_metadata.offset}"
            )
            return True
            
        except KafkaTimeoutError as e:
            raise KafkaProducerError(
                f"이벤트 발행 타임아웃: {str(e)}",
                topic=topic,
                details={"timeout": self.config.kafka_timeout}
            ) from e
        except Exception as e:
            raise KafkaProducerError(
                f"이벤트 발행 실패: {str(e)}",
                topic=topic,
                details={"event_type": event_data.get("event_type")}
            ) from e

    def create_standard_event(self, event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        표준 IACSGraph 이벤트 구조를 생성합니다.
        
        Args:
            event_type: 이벤트 타입
            data: 이벤트 데이터
            
        Returns:
            표준 이벤트 구조
        """
        return {
            "event_type": event_type,
            "source": "iacsgraph",
            "correlation_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat(timespec='milliseconds') + 'Z',
            "version": "1.0",
            "data": data
        }

    def create_mail_raw_data_event(
        self,
        account_id: str,
        email_data: Dict[str, Any],
        api_endpoint: str,
        response_status: int,
        request_params: Dict[str, Any],
        response_timestamp: str
    ) -> Dict[str, Any]:
        """
        메일 원시 데이터 이벤트를 생성합니다.
        
        Args:
            account_id: 계정 ID
            email_data: 이메일 데이터
            api_endpoint: API 엔드포인트
            response_status: 응답 상태 코드
            request_params: 요청 매개변수
            response_timestamp: 응답 타임스탬프
            
        Returns:
            메일 원시 데이터 이벤트
        """
        event_id = str(uuid4())
        occurred_at = datetime.utcnow().isoformat(timespec='milliseconds') + 'Z'

        return {
            "event_type": "email.raw_data_received",
            "event_id": event_id,
            "account_id": account_id,
            "occurred_at": occurred_at,
            "api_endpoint": api_endpoint,
            "response_status": response_status,
            "request_params": request_params,
            "response_data": {
                "value": [email_data] if not isinstance(email_data, list) else email_data,
                "@odata.context": f"https://graph.microsoft.com/v1.0/$metadata#users('{account_id}')/messages",
                "@odata.nextLink": "https://graph.microsoft.com/v1.0/me/messages?$skip=50"
            },
            "response_timestamp": response_timestamp
        }

    def consume_events(
        self,
        topics: List[str],
        message_handler: Callable[[str, Dict[str, Any]], None],
        consumer_group_id: Optional[str] = None,
        max_messages: Optional[int] = None
    ) -> None:
        """
        이벤트를 소비합니다.
        
        Args:
            topics: 구독할 토픽 목록
            message_handler: 메시지 처리 함수
            consumer_group_id: 컨슈머 그룹 ID
            max_messages: 최대 처리 메시지 수
        """
        consumer = self.create_consumer(topics, consumer_group_id)
        processed_count = 0
        
        try:
            logger.info(f"이벤트 소비 시작: topics={topics}, group={consumer_group_id}")
            
            for message in consumer:
                try:
                    # 메시지 처리
                    topic = message.topic
                    value = message.value
                    
                    logger.debug(
                        f"메시지 수신: topic={topic}, partition={message.partition}, "
                        f"offset={message.offset}"
                    )
                    
                    # 핸들러 호출
                    message_handler(topic, value)
                    
                    processed_count += 1
                    
                    # 최대 메시지 수 확인
                    if max_messages and processed_count >= max_messages:
                        logger.info(f"최대 메시지 수 도달: {max_messages}")
                        break
                        
                except Exception as e:
                    logger.error(f"메시지 처리 실패: {str(e)}")
                    # 계속 진행 (메시지 하나 실패해도 전체 중단하지 않음)
                    
        except KeyboardInterrupt:
            logger.info("사용자 중단 요청으로 이벤트 소비 중단")
        except Exception as e:
            raise KafkaConsumerError(
                f"이벤트 소비 실패: {str(e)}",
                details={"topics": topics}
            ) from e
        finally:
            consumer.close()
            logger.info(f"이벤트 소비 완료: {processed_count}개 메시지 처리")

    def publish_email_event(
        self,
        account_id: str,
        emails: List[Dict[str, Any]],
        api_endpoint: str = "/v1.0/me/messages"
    ) -> bool:
        """
        이메일 관련 이벤트를 발행합니다.
        
        Args:
            account_id: 계정 ID
            emails: 이메일 데이터 목록
            api_endpoint: API 엔드포인트
            
        Returns:
            발행 성공 여부
        """
        try:
            for email_data in emails:
                event = self.create_mail_raw_data_event(
                    account_id=account_id,
                    email_data=email_data,
                    api_endpoint=api_endpoint,
                    response_status=200,
                    request_params={"$select": "id,subject,from", "$top": 50, "$skip": 0},
                    response_timestamp=datetime.utcnow().isoformat(timespec='milliseconds') + 'Z'
                )
                
                self.produce_event(
                    topic=self.config.kafka_topic_email_events,
                    event_data=event,
                    key=event["event_id"]
                )
            
            logger.info(f"이메일 이벤트 발행 완료: {len(emails)}개 이메일")
            return True
            
        except Exception as e:
            logger.error(f"이메일 이벤트 발행 실패: {str(e)}")
            return False

    def flush(self, timeout: Optional[int] = None) -> None:
        """
        Producer의 버퍼를 플러시합니다.
        
        Args:
            timeout: 타임아웃 (초)
        """
        if self._producer:
            try:
                self._producer.flush(timeout=timeout or self.config.kafka_timeout)
                logger.debug("Producer 버퍼 플러시 완료")
            except Exception as e:
                logger.error(f"Producer 버퍼 플러시 실패: {str(e)}")

    def close(self) -> None:
        """모든 Kafka 연결을 종료합니다."""
        with self._lock:
            # Producer 종료
            if self._producer:
                try:
                    self._producer.close()
                    self._producer = None
                    logger.info("Kafka Producer 종료됨")
                except Exception as e:
                    logger.error(f"Producer 종료 실패: {str(e)}")
            
            # Consumer들 종료
            for consumer_key, consumer in self._consumers.items():
                try:
                    consumer.close()
                    logger.info(f"Kafka Consumer 종료됨: {consumer_key}")
                except Exception as e:
                    logger.error(f"Consumer 종료 실패: {str(e)}")
            
            self._consumers.clear()

    def get_topic_metadata(self, topic: str) -> Dict[str, Any]:
        """
        토픽 메타데이터를 조회합니다.
        
        Args:
            topic: 토픽명
            
        Returns:
            토픽 메타데이터
        """
        try:
            producer = self._get_producer()
            metadata = producer.partitions_for(topic)
            
            if metadata is None:
                raise KafkaError(f"토픽을 찾을 수 없습니다: {topic}")
            
            return {
                "topic": topic,
                "partitions": len(metadata),
                "partition_ids": list(metadata)
            }
            
        except Exception as e:
            raise KafkaError(
                f"토픽 메타데이터 조회 실패: {str(e)}",
                topic=topic
            ) from e

    def health_check(self) -> bool:
        """
        Kafka 클러스터 연결 상태를 확인합니다.
        
        Returns:
            연결 상태 (True: 정상, False: 비정상)
        """
        try:
            producer = self._get_producer()
            # 클러스터 메타데이터 조회로 연결 확인
            metadata = producer.cluster
            if metadata.brokers():
                logger.debug("Kafka 클러스터 연결 상태 정상")
                return True
            else:
                logger.warning("Kafka 브로커를 찾을 수 없음")
                return False
                
        except Exception as e:
            logger.error(f"Kafka 연결 상태 확인 실패: {str(e)}")
            return False


@lru_cache(maxsize=1)
def get_kafka_client() -> KafkaClient:
    """
    Kafka 클라이언트 인스턴스를 반환하는 레이지 싱글톤 함수
    
    Returns:
        KafkaClient: Kafka 클라이언트 인스턴스
    """
    return KafkaClient()


# 편의를 위한 전역 Kafka 클라이언트 인스턴스
kafka_client = get_kafka_client()
