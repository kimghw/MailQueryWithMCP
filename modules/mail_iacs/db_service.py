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
    # Panel Chair 관련 메서드
    # ========================================================================

    def insert_panel_chair(
        self,
        chair_address: str,
        panel_name: str,
        kr_panel_member: str
    ) -> bool:
        """
        패널 의장 정보 삽입

        Note:
            - panel_name과 chair_address가 중복되면 기존 데이터 삭제 후 삽입
        """
        try:
            # 기존 데이터 삭제
            self.db.execute_query(
                """
                DELETE FROM iacs_panel_chair
                WHERE panel_name = ? AND chair_address = ?
                """,
                (panel_name, chair_address)
            )

            # 새 데이터 삽입
            self.db.insert(
                "iacs_panel_chair",
                {
                    "chair_address": chair_address,
                    "panel_name": panel_name,
                    "kr_panel_member": kr_panel_member,
                }
            )

            logger.info(
                f"패널 의장 정보 삽입 완료: "
                f"panel={panel_name}, chair={chair_address}"
            )
            return True

        except Exception as e:
            logger.error(f"패널 의장 정보 삽입 실패: {str(e)}")
            raise

    def get_panel_chair_by_name(self, panel_name: str) -> Optional[PanelChairDB]:
        """패널 이름으로 의장 정보 조회"""
        try:
            row = self.db.fetch_one(
                """
                SELECT * FROM iacs_panel_chair
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
            logger.error(f"패널 의장 정보 조회 실패: {str(e)}")
            return None

    def get_all_panel_chairs(self) -> List[PanelChairDB]:
        """모든 패널 의장 정보 조회"""
        try:
            rows = self.db.fetch_all(
                "SELECT * FROM iacs_panel_chair ORDER BY panel_name"
            )

            return [PanelChairDB(**row) for row in rows]

        except Exception as e:
            logger.error(f"패널 의장 정보 전체 조회 실패: {str(e)}")
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
                return row.get("panel_name")
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
        기본 패널의 한국 멤버 이메일 조회

        Returns:
            한국 패널 멤버 이메일 주소
        """
        try:
            # 1. 기본 패널 이름 조회
            default_panel = self.get_default_panel_name()
            if not default_panel:
                logger.warning("기본 패널 이름이 설정되지 않았습니다")
                return None

            # 2. 해당 패널의 멤버 조회
            panel_chair = self.get_panel_chair_by_name(default_panel)
            if not panel_chair:
                logger.warning(f"패널 정보를 찾을 수 없습니다: {default_panel}")
                return None

            return panel_chair.kr_panel_member

        except Exception as e:
            logger.error(f"한국 패널 멤버 조회 실패: {str(e)}")
            return None

    def get_panel_info_by_name(self, panel_name: str) -> Optional[dict]:
        """
        패널 이름으로 전체 정보 조회

        Returns:
            {
                'chair_address': str,
                'panel_name': str,
                'kr_panel_member': str
            }
        """
        try:
            panel_chair = self.get_panel_chair_by_name(panel_name)
            if not panel_chair:
                return None

            return {
                "chair_address": panel_chair.chair_address,
                "panel_name": panel_chair.panel_name,
                "kr_panel_member": panel_chair.kr_panel_member,
            }

        except Exception as e:
            logger.error(f"패널 정보 조회 실패: {str(e)}")
            return None
