# modules/mail_dashboard/service.py
"""
Email Dashboard Service - email.received 이벤트 처리
"""

import asyncio
import threading
from typing import Any, Dict, Optional

from infra.core import get_config, get_database_manager, get_kafka_client, get_logger

from .event_processor import EmailDashboardEventProcessor
from .repository import EmailDashboardRepository
from .query import EmailDashboardQuery
from .orchestrator import EmailDashboardOrchestrator


class EmailDashboardService:
    """Email Dashboard 모듈 서비스"""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.config = get_config()
        self.db = get_database_manager()
        self.kafka_client = get_kafka_client()

        # 컴포넌트 초기화
        self.event_processor = EmailDashboardEventProcessor()
        self.repository = EmailDashboardRepository()
        self.query = EmailDashboardQuery()
        self.orchestrator = EmailDashboardOrchestrator()

        # 이벤트 구독 관련
        self._event_subscription_active = False
        self._event_thread: Optional[threading.Thread] = None

        self.logger.info("Email Dashboard Service 초기화 완료")

    def initialize(self) -> bool:
        """모듈 초기화"""
        try:
            self.logger.info("Email Dashboard 모듈 초기화 시작")

            # 1. 기존 테이블 삭제
            if not self._drop_old_tables():
                self.logger.error("기존 테이블 삭제 실패")
                return False

            # 2. 새 테이블 생성
            if not self._create_new_tables():
                self.logger.error("새 테이블 생성 실패")
                return False

            # 3. 환경설정 검증
            if not self._validate_configuration():
                self.logger.error("환경설정 검증 실패")
                return False

            self.logger.info("Email Dashboard 모듈 초기화 완료")
            return True

        except Exception as e:
            self.logger.error(f"모듈 초기화 실패: {str(e)}")
            return False

    def _drop_old_tables(self) -> bool:
        """기존 테이블 삭제"""
        try:
            self.logger.info("기존 테이블 삭제 시작")

            old_tables = [
                "email_events_unprocessed",
                "email_agenda_member_response_times",
                "email_agenda_member_responses",
                "email_agendas_chair",
            ]

            for table in old_tables:
                if self.db.table_exists(table):
                    self.db.execute_query(f"DROP TABLE IF EXISTS {table}")
                    self.logger.info(f"테이블 삭제: {table}")

            return True

        except Exception as e:
            self.logger.error(f"테이블 삭제 실패: {str(e)}")
            return False

    def _create_new_tables(self) -> bool:
        """새 테이블 생성"""
        try:
            self.logger.info("새 테이블 생성 시작")

            # create_table.sql 파일 읽기
            from pathlib import Path

            sql_file = Path(__file__).parent / "sql" / "migrations" / "create_table.sql"

            if not sql_file.exists():
                self.logger.error(f"SQL 파일을 찾을 수 없음: {sql_file}")
                return False

            with open(sql_file, "r", encoding="utf-8") as f:
                schema_sql = f.read()

            # SQL 문장별로 실행
            statements = [
                stmt.strip() for stmt in schema_sql.split(";") if stmt.strip()
            ]

            with self.db.transaction():
                for statement in statements:
                    if statement:
                        self.db.execute_query(statement)

            self.logger.info(f"새 테이블 생성 완료: {len(statements)}개 구문 실행")

            # 생성 확인
            required_tables = [
                "agenda_all",
                "agenda_chair",
                "agenda_responses_content",
                "agenda_responses_receivedtime",
                "agenda_pending",
            ]

            for table in required_tables:
                if not self.db.table_exists(table):
                    self.logger.error(f"테이블 생성 실패: {table}")
                    return False
                else:
                    self.logger.info(f"테이블 생성 확인: {table}")

            return True

        except Exception as e:
            self.logger.error(f"테이블 생성 실패: {str(e)}")
            return False

    def _validate_configuration(self) -> bool:
        """환경설정 검증"""
        try:
            # 필수 설정 확인
            required_settings = ["DATABASE_PATH", "ENCRYPTION_KEY"]

            for setting in required_settings:
                if not self.config.get_setting(setting):
                    self.logger.error(f"필수 설정 누락: {setting}")
                    return False

            # Dashboard 설정
            dashboard_settings = {
                "ENABLE_DASHBOARD_EVENTS": "true",
                "KAFKA_TOPIC_EMAIL_EVENTS": "email.received",  # 변경된 토픽
                "DASHBOARD_DATA_RETENTION_DAYS": "90",
            }

            for setting, default_value in dashboard_settings.items():
                value = self.config.get_setting(setting, default_value)
                self.logger.debug(f"{setting}: {value}")

            return True

        except Exception as e:
            self.logger.error(f"환경설정 검증 실패: {str(e)}")
            return False

    def start_event_subscription(self) -> bool:
        """이벤트 구독 시작"""
        try:
            if self._event_subscription_active:
                self.logger.warning("이벤트 구독이 이미 활성화됨")
                return True

            # Dashboard 이벤트 활성화 확인
            if self.config.get_setting(
                "ENABLE_DASHBOARD_EVENTS", "true"
            ).lower() not in ("true", "1", "yes", "on"):
                self.logger.info("Dashboard 이벤트가 비활성화됨")
                return True

            # 구독할 토픽
            topic = self.config.get_setting(
                "KAFKA_TOPIC_EMAIL_EVENTS", "email.received"
            )
            topics = [topic]

            self.logger.info(f"이벤트 구독 시작: {topics}")

            # 별도 스레드에서 구독 실행
            self._event_subscription_active = True
            self._event_thread = threading.Thread(
                target=self._event_subscription_worker, args=(topics,), daemon=True
            )
            self._event_thread.start()

            self.logger.info("이벤트 구독 시작됨")
            return True

        except Exception as e:
            self.logger.error(f"이벤트 구독 시작 실패: {str(e)}")
            self._event_subscription_active = False
            return False

    def stop_event_subscription(self) -> bool:
        """이벤트 구독 중지"""
        try:
            if not self._event_subscription_active:
                self.logger.info("이벤트 구독이 이미 비활성화됨")
                return True

            self.logger.info("이벤트 구독 중지 시작")
            self._event_subscription_active = False

            # 스레드 종료 대기
            if self._event_thread and self._event_thread.is_alive():
                self._event_thread.join(timeout=10)
                if self._event_thread.is_alive():
                    self.logger.warning("이벤트 구독 스레드가 정상 종료되지 않음")

            self.logger.info("이벤트 구독 중지 완료")
            return True

        except Exception as e:
            self.logger.error(f"이벤트 구독 중지 실패: {str(e)}")
            return False

    def _event_subscription_worker(self, topics: list):
        """이벤트 구독 워커"""
        try:
            self.logger.info(f"이벤트 구독 워커 시작: {topics}")

            def message_handler(topic: str, message: Dict[str, Any]):
                """메시지 처리 핸들러"""
                try:
                    # 이벤트 타입 확인
                    event_type = message.get("event_type")
                    if event_type == "email.received":
                        # Email Dashboard 이벤트 처리
                        result = self.event_processor.process_email_event(message)

                        if result.get("success"):
                            self.logger.debug(
                                f"이벤트 처리 성공: {result.get('action')}"
                            )
                        else:
                            self.logger.warning(
                                f"이벤트 처리 실패: {result.get('message')}"
                            )
                    else:
                        self.logger.debug(f"처리하지 않는 이벤트 타입: {event_type}")

                except Exception as e:
                    self.logger.error(f"메시지 처리 중 오류: {str(e)}")

            # Kafka 구독 시작
            consumer_group_id = f"{self.config.kafka_consumer_group_id}-dashboard"

            while self._event_subscription_active:
                try:
                    self.kafka_client.consume_events(
                        topics=topics,
                        message_handler=message_handler,
                        consumer_group_id=consumer_group_id,
                        max_messages=100,
                    )
                except Exception as e:
                    self.logger.error(f"Kafka 구독 오류: {str(e)}")
                    if self._event_subscription_active:
                        import time

                        time.sleep(5)  # 재시도 대기

            self.logger.info("이벤트 구독 워커 종료")

        except Exception as e:
            self.logger.error(f"이벤트 구독 워커 실행 실패: {str(e)}")
        finally:
            self._event_subscription_active = False

    def get_health_status(self) -> Dict[str, Any]:
        """모듈 상태 확인"""
        try:
            # 통계 조회
            stats = self.repository.get_dashboard_stats(7)

            # 테이블 확인
            required_tables = [
                "agenda_all",
                "agenda_chair",
                "agenda_responses_content",
                "agenda_responses_receivedtime",
                "agenda_pending",
            ]

            missing_tables = []
            for table in required_tables:
                if not self.db.table_exists(table):
                    missing_tables.append(table)

            return {
                "success": True,
                "module": "email_dashboard",
                "status": "healthy" if not missing_tables else "unhealthy",
                "event_subscription_active": self._event_subscription_active,
                "tables_ready": len(missing_tables) == 0,
                "missing_tables": missing_tables,
                "stats": stats,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"상태 확인 실패: {str(e)}")
            return {
                "success": False,
                "module": "email_dashboard",
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def shutdown(self) -> bool:
        """모듈 종료"""
        try:
            self.logger.info("Email Dashboard 모듈 종료 시작")

            # 이벤트 구독 중지
            self.stop_event_subscription()

            self.logger.info("Email Dashboard 모듈 종료 완료")
            return True

        except Exception as e:
            self.logger.error(f"모듈 종료 실패: {str(e)}")
            return False

    def process_pending_events(self) -> Dict[str, Any]:
        """미처리 이벤트 재처리"""
        try:
            # 미처리 이벤트 조회
            pending_events = self.repository.get_pending_events(limit=100)

            if not pending_events:
                return {
                    "success": True,
                    "message": "처리할 미처리 이벤트가 없습니다",
                    "processed_count": 0,
                }

            processed_count = 0
            success_count = 0

            for event in pending_events:
                try:
                    # 원본 이벤트 데이터 파싱
                    import json

                    raw_event = json.loads(event.raw_event_data)

                    # 재처리
                    result = self.event_processor.process_email_event(raw_event)

                    if result.get("success") and result.get("action") not in [
                        "saved_to_pending"
                    ]:
                        # 성공적으로 처리된 경우
                        self.repository.mark_pending_processed(event.event_id)
                        success_count += 1

                    processed_count += 1

                except Exception as e:
                    self.logger.error(
                        f"미처리 이벤트 재처리 실패: event_id={event.event_id}, error={str(e)}"
                    )

            return {
                "success": True,
                "total_events": len(pending_events),
                "processed_count": processed_count,
                "success_count": success_count,
                "message": f"{success_count}/{len(pending_events)}개 이벤트 재처리 성공",
            }

        except Exception as e:
            self.logger.error(f"미처리 이벤트 재처리 실패: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": f"미처리 이벤트 재처리 실패: {str(e)}",
            }
