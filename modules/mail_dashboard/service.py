"""
Email Dashboard Service - 업데이트 버전

모듈의 전체 생명주기를 관리하는 서비스 클래스입니다.
- 모듈 내부 SQL 스크립트 사용
- 데이터베이스 테이블 초기화
- 이벤트 구독 관리
- 모듈 상태 관리
"""

import asyncio
import threading
from pathlib import Path
from typing import Any, Dict, Optional

from infra.core import get_config, get_database_manager, get_kafka_client, get_logger
from infra.core.exceptions import DatabaseError, KafkaError

from .orchestrator import EmailDashboardOrchestrator
from .repository import EmailDashboardRepository
from .sql import get_create_tables_sql, get_required_tables


class EmailDashboardService:
    """Email Dashboard 모듈 서비스 관리"""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.config = get_config()
        self.db = get_database_manager()
        self.kafka_client = get_kafka_client()

        # 컴포넌트 초기화
        self.orchestrator = EmailDashboardOrchestrator()
        self.repository = EmailDashboardRepository()

        # 이벤트 구독 관련
        self._event_subscription_active = False
        self._event_thread: Optional[threading.Thread] = None

        self.logger.info("Email Dashboard Service 초기화 완료")

    def initialize(self) -> bool:
        """
        모듈 전체를 초기화합니다.

        Returns:
            초기화 성공 여부
        """
        try:
            self.logger.info("Email Dashboard 모듈 초기화 시작")

            # 1. 데이터베이스 테이블 초기화
            if not self._initialize_database_tables():
                self.logger.error("데이터베이스 테이블 초기화 실패")
                return False

            # 2. 환경설정 검증
            if not self._validate_configuration():
                self.logger.error("환경설정 검증 실패")
                return False

            # 3. Kafka 연결 확인 (이벤트 발행이 활성화된 경우)
            enable_dashboard_events = self.config.get_setting(
                "ENABLE_DASHBOARD_EVENTS", "true"
            ).lower() in ("true", "1", "yes", "on")
            if enable_dashboard_events:
                if not self._validate_kafka_connection():
                    self.logger.warning(
                        "Kafka 연결 확인 실패 - 이벤트 기능이 제한될 수 있습니다"
                    )

            self.logger.info("Email Dashboard 모듈 초기화 완료")
            return True

        except Exception as e:
            self.logger.error(f"Email Dashboard 모듈 초기화 중 오류: {str(e)}")
            return False

    def _initialize_database_tables(self) -> bool:
        """데이터베이스 테이블을 초기화합니다 (모듈 내부 SQL 사용)"""
        try:
            self.logger.info("Email Dashboard 테이블 초기화 시작")

            # 필요한 테이블 목록 가져오기
            required_tables = get_required_tables()

            # 테이블 존재 확인
            missing_tables = []
            for table in required_tables:
                if not self.db.table_exists(table):
                    missing_tables.append(table)

            if missing_tables:
                self.logger.info(f"누락된 테이블 발견: {missing_tables}")

                # 모듈 내부 SQL 스크립트 가져오기
                try:
                    schema_sql = get_create_tables_sql()
                except FileNotFoundError as e:
                    self.logger.error(f"모듈 SQL 파일을 찾을 수 없음: {str(e)}")
                    return False

                # SQL 문장별로 분리하여 실행
                statements = [
                    stmt.strip() for stmt in schema_sql.split(";") if stmt.strip()
                ]

                with self.db.transaction():
                    for statement in statements:
                        if statement:
                            self.db.execute_query(statement)

                self.logger.info(
                    f"Email Dashboard 테이블 생성 완료: {len(statements)}개 구문 실행"
                )

                # 생성된 테이블 재확인
                still_missing = []
                for table in required_tables:
                    if not self.db.table_exists(table):
                        still_missing.append(table)

                if still_missing:
                    self.logger.error(
                        f"테이블 생성 후에도 누락된 테이블: {still_missing}"
                    )
                    return False

            else:
                self.logger.info("Email Dashboard 테이블이 이미 존재합니다")

            # 스키마 버전 기록 (schema_versions 테이블이 있는 경우)
            self._record_schema_version()

            return True

        except Exception as e:
            self.logger.error(f"테이블 초기화 실패: {str(e)}")
            return False

    def _record_schema_version(self):
        """스키마 버전을 기록합니다"""
        try:
            # schema_versions 테이블이 있는지 확인
            if self.db.table_exists("schema_versions"):
                # 버전 정보 삽입/업데이트
                self.db.execute_query(
                    """
                    INSERT OR REPLACE INTO schema_versions (module_name, version, applied_at) 
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                    """,
                    ("email_dashboard", "1.0.0"),
                )
                self.logger.debug("스키마 버전 기록 완료: email_dashboard v1.0.0")
            else:
                self.logger.debug(
                    "schema_versions 테이블이 없어 버전 기록을 건너뜁니다"
                )

        except Exception as e:
            self.logger.warning(f"스키마 버전 기록 실패 (무시됨): {str(e)}")

    def _validate_configuration(self) -> bool:
        """환경설정을 검증합니다"""
        try:
            # 필수 설정 확인
            required_settings = ["DATABASE_PATH", "ENCRYPTION_KEY"]

            missing_settings = []
            for setting in required_settings:
                if not self.config.get_setting(setting):
                    missing_settings.append(setting)

            if missing_settings:
                self.logger.error(f"필수 환경설정 누락: {missing_settings}")
                return False

            # Dashboard 관련 설정 확인 및 기본값 설정
            dashboard_settings = {
                "ENABLE_DASHBOARD_EVENTS": "true",
                "KAFKA_TOPIC_DASHBOARD_EVENTS": "email.api.response",
                "DASHBOARD_DATA_RETENTION_DAYS": "90",
                "DASHBOARD_DEFAULT_STATS_PERIOD_DAYS": "30",
                "DASHBOARD_QUERY_TIMEOUT": "30",
                "DASHBOARD_MAX_AGENDA_LIMIT": "1000",
            }

            for setting, default_value in dashboard_settings.items():
                value = self.config.get_setting(setting, default_value)
                self.logger.debug(f"{setting}: {value}")

            return True

        except Exception as e:
            self.logger.error(f"환경설정 검증 실패: {str(e)}")
            return False

    def _validate_kafka_connection(self) -> bool:
        """Kafka 연결을 검증합니다"""
        try:
            return self.kafka_client.health_check()
        except Exception as e:
            self.logger.error(f"Kafka 연결 검증 실패: {str(e)}")
            return False

    def start_event_subscription(self) -> bool:
        """
        이벤트 구독을 시작합니다.

        Returns:
            구독 시작 성공 여부
        """
        try:
            if self._event_subscription_active:
                self.logger.warning("이벤트 구독이 이미 활성화되어 있습니다")
                return True

            # Dashboard 이벤트 활성화 확인
            enable_dashboard_events = self.config.get_setting(
                "ENABLE_DASHBOARD_EVENTS", "true"
            ).lower() in ("true", "1", "yes", "on")
            if not enable_dashboard_events:
                self.logger.info("Dashboard 이벤트가 비활성화되어 있습니다")
                return True

            # 구독할 토픽 설정
            dashboard_topic = self.config.get_setting(
                "KAFKA_TOPIC_DASHBOARD_EVENTS", "email.api.response"
            )
            topics = [dashboard_topic]

            self.logger.info(f"이벤트 구독 시작: 토픽 {topics}")

            # 별도 스레드에서 이벤트 구독 실행
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
        """
        이벤트 구독을 중지합니다.

        Returns:
            구독 중지 성공 여부
        """
        try:
            if not self._event_subscription_active:
                self.logger.info("이벤트 구독이 이미 비활성화되어 있습니다")
                return True

            self.logger.info("이벤트 구독 중지 시작")
            self._event_subscription_active = False

            # 스레드 종료 대기 (최대 10초)
            if self._event_thread and self._event_thread.is_alive():
                self._event_thread.join(timeout=10)
                if self._event_thread.is_alive():
                    self.logger.warning(
                        "이벤트 구독 스레드가 정상적으로 종료되지 않았습니다"
                    )

            self.logger.info("이벤트 구독 중지 완료")
            return True

        except Exception as e:
            self.logger.error(f"이벤트 구독 중지 실패: {str(e)}")
            return False

    def _event_subscription_worker(self, topics: list):
        """이벤트 구독 워커 (별도 스레드에서 실행)"""
        try:
            self.logger.info(f"이벤트 구독 워커 시작: {topics}")

            def message_handler(topic: str, message: Dict[str, Any]):
                """메시지 처리 핸들러"""
                try:
                    self.logger.debug(f"이벤트 수신: topic={topic}")

                    # 이벤트 타입 확인
                    event_type = message.get("event_type")
                    if event_type == "email-dashboard":
                        # Email Dashboard 이벤트 처리
                        result = self.orchestrator.email_dashboard_handle_email_event(
                            message
                        )
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

            # Kafka 이벤트 구독 시작
            consumer_group_id = f"{self.config.kafka_consumer_group_id}-dashboard"

            while self._event_subscription_active:
                try:
                    self.kafka_client.consume_events(
                        topics=topics,
                        message_handler=message_handler,
                        consumer_group_id=consumer_group_id,
                        max_messages=100,  # 배치 단위로 처리
                    )
                except KafkaError as e:
                    self.logger.error(f"Kafka 구독 오류: {str(e)}")
                    if self._event_subscription_active:
                        import time

                        time.sleep(5)  # 5초 후 재시도
                except KeyboardInterrupt:
                    self.logger.info("사용자 요청으로 이벤트 구독 중지")
                    break
                except Exception as e:
                    self.logger.error(f"이벤트 구독 워커 오류: {str(e)}")
                    if self._event_subscription_active:
                        import time

                        time.sleep(5)  # 5초 후 재시도

            self.logger.info("이벤트 구독 워커 종료")

        except Exception as e:
            self.logger.error(f"이벤트 구독 워커 실행 실패: {str(e)}")
        finally:
            self._event_subscription_active = False

    def get_health_status(self) -> Dict[str, Any]:
        """모듈 상태를 확인합니다"""
        try:
            # 오케스트레이터를 통한 상태 확인
            health_status = self.orchestrator.email_dashboard_get_health_status()

            # 이벤트 구독 상태 추가
            health_status["event_subscription_active"] = self._event_subscription_active

            # 테이블 상태 확인
            required_tables = get_required_tables()
            missing_tables = []
            for table in required_tables:
                if not self.db.table_exists(table):
                    missing_tables.append(table)

            health_status["required_tables"] = required_tables
            health_status["missing_tables"] = missing_tables
            health_status["tables_ready"] = len(missing_tables) == 0

            return health_status

        except Exception as e:
            self.logger.error(f"상태 확인 실패: {str(e)}")
            return {
                "success": False,
                "module": "email_dashboard",
                "status": "unhealthy",
                "error": str(e),
                "event_subscription_active": self._event_subscription_active,
                "tables_ready": False,
            }

    def shutdown(self) -> bool:
        """모듈을 종료합니다"""
        try:
            self.logger.info("Email Dashboard 모듈 종료 시작")

            # 이벤트 구독 중지
            self.stop_event_subscription()

            self.logger.info("Email Dashboard 모듈 종료 완료")
            return True

        except Exception as e:
            self.logger.error(f"모듈 종료 실패: {str(e)}")
            return False
