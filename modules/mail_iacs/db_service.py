"""
IACS DB 서비스
패널 의장 및 멤버 정보 관리
"""

from typing import List, Optional
from infra.core.database import get_database_manager
from infra.core.logger import get_logger
from infra.core.config import get_config
from .schemas import PanelChairDB, DefaultValueDB

logger = get_logger(__name__)


class IACSDBService:
    """IACS DB 서비스"""

    def __init__(self):
        self.db = get_database_manager()
        self._ensure_schema()

    def _ensure_schema(self):
        """스키마 확인 및 생성"""
        try:
            # schema.sql 파일 실행
            import os
            schema_path = os.path.join(
                os.path.dirname(__file__), "schema.sql"
            )

            if os.path.exists(schema_path):
                with open(schema_path, "r", encoding="utf-8") as f:
                    schema_sql = f.read()

                # executescript 사용 (한 번에 실행)
                import sqlite3
                from pathlib import Path

                # DB 경로 (.env의 DATABASE_PATH 사용)
                config = get_config()
                db_path = Path(config.database_path)
                db_path.parent.mkdir(parents=True, exist_ok=True)

                conn = sqlite3.connect(str(db_path))
                conn.executescript(schema_sql)
                conn.commit()
                conn.close()

                logger.info("IACS 스키마 초기화 완료")
            else:
                logger.warning(f"스키마 파일을 찾을 수 없습니다: {schema_path}")

        except Exception as e:
            logger.error(f"스키마 초기화 실패: {str(e)}")
            raise

    # ========================================================================
    # Panel Info 관련 메서드
    # ========================================================================

    def insert_panel_info(
        self,
        chair_address: str,
        panel_name: str,
        kr_panel_member: str
    ) -> bool:
        """
        패널 정보 삽입

        Note:
            - panel_name과 chair_address가 중복되면 기존 데이터 삭제 후 삽입
        """
        try:
            # 기존 데이터 삭제
            self.db.execute_query(
                """
                DELETE FROM iacs_panel_info
                WHERE panel_name = ? AND chair_address = ?
                """,
                (panel_name, chair_address)
            )

            # 새 데이터 삽입
            self.db.insert(
                "iacs_panel_info",
                {
                    "chair_address": chair_address,
                    "panel_name": panel_name,
                    "kr_panel_member": kr_panel_member,
                }
            )

            logger.info(
                f"패널 정보 삽입 완료: "
                f"panel={panel_name}, chair={chair_address}"
            )
            return True

        except Exception as e:
            logger.error(f"패널 정보 삽입 실패: {str(e)}")
            raise

    def get_panel_info_by_name(self, panel_name: str) -> Optional[PanelChairDB]:
        """패널 이름으로 정보 조회"""
        try:
            row = self.db.fetch_one(
                """
                SELECT * FROM iacs_panel_info
                WHERE panel_name = ?
                LIMIT 1
                """,
                (panel_name,)
            )

            if row:
                # sqlite3.Row를 딕셔너리로 변환
                row_dict = dict(row)
                return PanelChairDB(**row_dict)
            return None

        except Exception as e:
            logger.error(f"패널 정보 조회 실패: {str(e)}")
            return None

    def get_all_panel_info(self) -> List[PanelChairDB]:
        """모든 패널 정보 조회"""
        try:
            rows = self.db.fetch_all(
                "SELECT * FROM iacs_panel_info ORDER BY panel_name"
            )

            return [PanelChairDB(**row) for row in rows]

        except Exception as e:
            logger.error(f"패널 정보 전체 조회 실패: {str(e)}")
            return []

    # ========================================================================
    # Default Value 관련 메서드
    # ========================================================================

    def insert_default_value(self, panel_name: str) -> bool:
        """기본 패널 이름 설정"""
        try:
            # 기존 데이터 삭제
            self.db.execute_query(
                "DELETE FROM iacs_default_value WHERE panel_name = ?",
                (panel_name,)
            )

            # 새 데이터 삽입
            self.db.insert(
                "iacs_default_value",
                {"panel_name": panel_name}
            )

            logger.info(f"기본 패널 이름 설정 완료: {panel_name}")
            return True

        except Exception as e:
            logger.error(f"기본 패널 이름 설정 실패: {str(e)}")
            raise

    def get_default_panel_name(self) -> Optional[str]:
        """기본 패널 이름 조회"""
        try:
            row = self.db.fetch_one(
                "SELECT panel_name FROM iacs_default_value LIMIT 1"
            )

            if row:
                # sqlite3.Row를 딕셔너리로 변환하거나 인덱스로 접근
                return dict(row)["panel_name"]
            return None

        except Exception as e:
            logger.error(f"기본 패널 이름 조회 실패: {str(e)}")
            return None

    def get_all_default_values(self) -> List[DefaultValueDB]:
        """모든 기본값 조회"""
        try:
            rows = self.db.fetch_all(
                "SELECT * FROM iacs_default_value"
            )

            return [DefaultValueDB(**row) for row in rows]

        except Exception as e:
            logger.error(f"기본값 전체 조회 실패: {str(e)}")
            return []

    # ========================================================================
    # 인증 관련 메서드
    # ========================================================================

    def get_kr_panel_member_by_default(self) -> Optional[str]:
        """
        기본 패널의 한국 멤버 user_id 조회

        Returns:
            한국 패널 멤버 user_id
        """
        try:
            # 1. 기본 패널 이름 조회
            default_panel = self.get_default_panel_name()
            if not default_panel:
                logger.warning("기본 패널 이름이 설정되지 않았습니다")
                return None

            # 2. 해당 패널의 멤버 조회
            panel_info = self.get_panel_info_by_name(default_panel)
            if not panel_info:
                logger.warning(f"패널 정보를 찾을 수 없습니다: {default_panel}")
                return None

            return panel_info.kr_panel_member

        except Exception as e:
            logger.error(f"한국 패널 멤버 조회 실패: {str(e)}")
            return None

    def get_panel_info_dict(self, panel_name: str) -> Optional[dict]:
        """
        패널 이름으로 전체 정보 조회 (dict 반환)

        Returns:
            {
                'chair_address': str,
                'panel_name': str,
                'kr_panel_member': str
            }
        """
        try:
            panel_info = self.get_panel_info_by_name(panel_name)
            if not panel_info:
                return None

            return {
                "chair_address": panel_info.chair_address,
                "panel_name": panel_info.panel_name,
                "kr_panel_member": panel_info.kr_panel_member,
            }

        except Exception as e:
            logger.error(f"패널 정보 조회 실패: {str(e)}")
            return None

    # ========================================================================
    # Tool Schema 관련 메서드 (새로운 per-tool 테이블 구조)
    # ========================================================================

    def get_tool_schema(self, tool_name: str) -> List[dict]:
        """
        도구의 스키마 정보 조회

        Args:
            tool_name: 도구 이름 (search_agenda, search_responses, insert_info, insert_default_value)

        Returns:
            [
                {
                    'parameter_name': str,
                    'parameter_type': str,
                    'is_required': str,  # 'required' or 'optional'
                    'default_value': str or None
                },
                ...
            ]
        """
        try:
            table_name = f"iacs_tool_{tool_name}"
            rows = self.db.fetch_all(
                f"""
                SELECT parameter_name, parameter_type, is_required, default_value
                FROM {table_name}
                """
            )

            return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"도구 스키마 조회 실패 ({tool_name}): {str(e)}")
            return []

    def update_tool_schema(self, tool_name: str, parameters: List[dict]) -> bool:
        """
        도구의 스키마 정보 업데이트

        Args:
            tool_name: 도구 이름
            parameters: [
                {
                    'parameter_name': str,
                    'parameter_type': str,
                    'is_required': str,
                    'default_value': str or None
                },
                ...
            ]

        Returns:
            성공 여부
        """
        try:
            table_name = f"iacs_tool_{tool_name}"

            # 각 파라미터 업데이트
            for param in parameters:
                self.db.execute_query(
                    f"""
                    UPDATE {table_name}
                    SET parameter_type = ?,
                        is_required = ?,
                        default_value = ?
                    WHERE parameter_name = ?
                    """,
                    (
                        param['parameter_type'],
                        param['is_required'],
                        param['default_value'],
                        param['parameter_name']
                    )
                )

            logger.info(f"도구 스키마 업데이트 완료: {tool_name}")
            return True

        except Exception as e:
            logger.error(f"도구 스키마 업데이트 실패 ({tool_name}): {str(e)}")
            return False

    def get_all_tool_schemas(self) -> dict:
        """
        모든 도구의 스키마 정보 조회

        Returns:
            {
                'search_agenda': [
                    {'parameter_name': 'start_date', 'parameter_type': 'string', 'is_required': 'optional', 'default_value': 'now'},
                    ...
                ],
                'search_responses': [...],
                'insert_info': [...],
                'insert_default_value': [...]
            }
        """
        try:
            tool_names = ['search_agenda', 'search_responses', 'insert_info', 'insert_default_value']
            result = {}

            for tool_name in tool_names:
                result[tool_name] = self.get_tool_schema(tool_name)

            return result

        except Exception as e:
            logger.error(f"모든 도구 스키마 조회 실패: {str(e)}")
            return {}
