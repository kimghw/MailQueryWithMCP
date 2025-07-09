# modules/mail_dashboard/query.py
"""
Email Dashboard Query Service - 새로운 테이블 구조
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from infra.core import get_database_manager, get_logger
from infra.core.exceptions import DatabaseError

from .schema import (
    ORGANIZATIONS,
    AgendaChair,
    AgendaResponsesContent,
    AgendaResponsesReceivedTime
)


class EmailDashboardQuery:
    """Email Dashboard 조회 서비스"""
    
    def __init__(self):
        self.db = get_database_manager()
        self.logger = get_logger(__name__)
    
    # =========================================================================
    # 아젠다 조회
    # =========================================================================
    
    def get_agendas(
        self,
        panel_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[AgendaChair]:
        """
        아젠다 목록 조회
        
        Args:
            panel_id: 패널 ID 필터
            status: 상태 필터
            limit: 조회 수 제한
            offset: 오프셋
            
        Returns:
            아젠다 목록
        """
        try:
            # WHERE 조건 구성
            where_conditions = []
            params = []
            
            if panel_id:
                where_conditions.append("agenda_panel = ?")
                params.append(panel_id)
                
            if status:
                where_conditions.append("decision_status = ?")
                params.append(status)
            
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
            
            query = f"""
                SELECT * FROM agenda_chair
                WHERE {where_clause}
                ORDER BY sent_time DESC
                LIMIT ? OFFSET ?
            """
            
            params.extend([limit, offset])
            
            rows = self.db.fetch_all(query, params)
            
            agendas = []
            for row in rows:
                agenda_dict = dict(row)
                # keywords JSON 파싱
                if agenda_dict.get("keywords"):
                    import json
                    try:
                        agenda_dict["keywords"] = json.loads(agenda_dict["keywords"])
                    except:
                        agenda_dict["keywords"] = []
                
                agenda = AgendaChair(**agenda_dict)
                agendas.append(agenda)
            
            return agendas
            
        except Exception as e:
            self.logger.error(f"아젠다 조회 실패: {str(e)}")
            raise DatabaseError(f"아젠다 조회 실패: {str(e)}")
    
    def get_agenda_detail(self, agenda_base_version: str) -> Optional[Dict[str, Any]]:
        """
        아젠다 상세 정보 조회
        
        Args:
            agenda_base_version: 아젠다 기본 버전
            
        Returns:
            아젠다 상세 정보
        """
        try:
            # 아젠다 기본 정보
            chair_query = "SELECT * FROM agenda_chair WHERE agenda_base_version = ?"
            chair_row = self.db.fetch_one(chair_query, (agenda_base_version,))
            
            if not chair_row:
                return None
            
            chair_dict = dict(chair_row)
            # keywords JSON 파싱
            if chair_dict.get("keywords"):
                import json
                try:
                    chair_dict["keywords"] = json.loads(chair_dict["keywords"])
                except:
                    chair_dict["keywords"] = []
            
            # 응답 정보
            responses = self._get_agenda_responses(agenda_base_version)
            
            # 결과 조합
            detail = {
                "agenda": chair_dict,
                "responses": responses,
                "response_summary": self._get_response_summary(responses),
                "timeline": self._get_agenda_timeline(agenda_base_version)
            }
            
            return detail
            
        except Exception as e:
            self.logger.error(f"아젠다 상세 조회 실패: {str(e)}")
            return None
    
    def _get_agenda_responses(self, agenda_base_version: str) -> Dict[str, Dict[str, Any]]:
        """아젠다 응답 정보 조회"""
        try:
            # 응답 내용
            content_query = "SELECT * FROM agenda_responses_content WHERE agenda_base_version = ?"
            content_row = self.db.fetch_one(content_query, (agenda_base_version,))
            
            # 응답 시간
            time_query = "SELECT * FROM agenda_responses_receivedtime WHERE agenda_base_version = ?"
            time_row = self.db.fetch_one(time_query, (agenda_base_version,))
            
            responses = {}
            
            for org in ORGANIZATIONS:
                response_content = content_row.get(org) if content_row else None
                response_time = time_row.get(org) if time_row else None
                
                responses[org] = {
                    "organization": org,
                    "has_responded": bool(response_content and response_content.strip()),
                    "response_content": response_content,
                    "response_time": response_time
                }
            
            return responses
            
        except Exception as e:
            self.logger.error(f"응답 정보 조회 실패: {str(e)}")
            return {}
    
    def _get_response_summary(self, responses: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """응답 요약 정보"""
        total_orgs = len(ORGANIZATIONS)
        responded_orgs = sum(1 for r in responses.values() if r["has_responded"])
        
        return {
            "total_organizations": total_orgs,
            "responded_count": responded_orgs,
            "pending_count": total_orgs - responded_orgs,
            "response_rate": responded_orgs / total_orgs if total_orgs > 0 else 0,
            "responded_organizations": [org for org, r in responses.items() if r["has_responded"]],
            "pending_organizations": [org for org, r in responses.items() if not r["has_responded"]]
        }
    
    def _get_agenda_timeline(self, agenda_base_version: str) -> List[Dict[str, Any]]:
        """아젠다 타임라인"""
        try:
            timeline = []
            
            # 발송 이벤트
            chair_query = "SELECT sent_time, sender_organization FROM agenda_chair WHERE agenda_base_version = ?"
            chair = self.db.fetch_one(chair_query, (agenda_base_version,))
            
            if chair:
                timeline.append({
                    "timestamp": chair["sent_time"],
                    "event_type": "sent",
                    "organization": chair["sender_organization"],
                    "description": f"아젠다 발송 - {chair['sender_organization']}"
                })
            
            # 응답 이벤트들
            time_query = f"""
                SELECT {', '.join(ORGANIZATIONS)} 
                FROM agenda_responses_receivedtime 
                WHERE agenda_base_version = ?
            """
            time_row = self.db.fetch_one(time_query, (agenda_base_version,))
            
            if time_row:
                for org in ORGANIZATIONS:
                    if time_row.get(org):
                        timeline.append({
                            "timestamp": time_row[org],
                            "event_type": "response",
                            "organization": org,
                            "description": f"{org} 응답"
                        })
            
            # 시간순 정렬
            timeline.sort(key=lambda x: x["timestamp"])
            
            return timeline
            
        except Exception as e:
            self.logger.error(f"타임라인 조회 실패: {str(e)}")
            return []
    
    # =========================================================================
    # 조직별 통계
    # =========================================================================
    
    def get_organization_summary(self, organization: str) -> Dict[str, Any]:
        """
        특정 조직의 요약 정보
        
        Args:
            organization: 조직 코드
            
        Returns:
            조직 요약 정보
        """
        try:
            if organization not in ORGANIZATIONS:
                raise ValueError(f"유효하지 않은 조직 코드: {organization}")
            
            # Chair로 활동한 수
            chair_count_query = """
                SELECT COUNT(*) as count 
                FROM agenda_chair 
                WHERE sender_organization = ?
            """
            chair_result = self.db.fetch_one(chair_count_query, (organization,))
            chair_count = chair_result["count"] if chair_result else 0
            
            # 응답한 아젠다 수
            response_count_query = f"""
                SELECT COUNT(*) as count 
                FROM agenda_responses_content 
                WHERE {organization} IS NOT NULL AND {organization} != ''
            """
            response_result = self.db.fetch_one(response_count_query)
            response_count = response_result["count"] if response_result else 0
            
            # 평균 응답 시간
            avg_response_time = self._get_avg_response_time(organization)
            
            # 최근 활동
            recent_activities = self._get_recent_activities(organization, limit=10)
            
            return {
                "organization": organization,
                "as_chair_count": chair_count,
                "response_count": response_count,
                "avg_response_time_hours": avg_response_time,
                "recent_activities": recent_activities
            }
            
        except Exception as e:
            self.logger.error(f"조직 요약 조회 실패: {str(e)}")
            return {}
    
    def _get_avg_response_time(self, organization: str) -> Optional[float]:
        """평균 응답 시간 계산"""
        try:
            # 응답한 아젠다들의 발송 시간과 응답 시간 조회
            query = f"""
                SELECT 
                    c.sent_time,
                    rt.{organization} as response_time
                FROM agenda_chair c
                JOIN agenda_responses_receivedtime rt ON c.agenda_base_version = rt.agenda_base_version
                WHERE rt.{organization} IS NOT NULL
            """
            
            rows = self.db.fetch_all(query)
            
            if not rows:
                return None
            
            total_hours = 0
            count = 0
            
            for row in rows:
                sent_time = datetime.fromisoformat(row["sent_time"])
                response_time = datetime.fromisoformat(row["response_time"])
                
                diff = response_time - sent_time
                hours = diff.total_seconds() / 3600
                
                total_hours += hours
                count += 1
            
            return round(total_hours / count, 2) if count > 0 else None
            
        except Exception as e:
            self.logger.error(f"평균 응답 시간 계산 실패: {str(e)}")
            return None
    
    def _get_recent_activities(self, organization: str, limit: int = 10) -> List[Dict[str, Any]]:
        """최근 활동 내역"""
        try:
            activities = []
            
            # Chair 활동
            chair_query = """
                SELECT 
                    agenda_base_version,
                    agenda_code,
                    sent_time,
                    'chair' as activity_type
                FROM agenda_chair
                WHERE sender_organization = ?
                ORDER BY sent_time DESC
                LIMIT ?
            """
            
            chair_rows = self.db.fetch_all(chair_query, (organization, limit))
            
            for row in chair_rows:
                activities.append({
                    "timestamp": row["sent_time"],
                    "type": "chair",
                    "agenda": row["agenda_code"],
                    "description": f"아젠다 발송: {row['agenda_code']}"
                })
            
            # 응답 활동
            response_query = f"""
                SELECT 
                    c.agenda_code,
                    rt.{organization} as response_time
                FROM agenda_chair c
                JOIN agenda_responses_receivedtime rt ON c.agenda_base_version = rt.agenda_base_version
                WHERE rt.{organization} IS NOT NULL
                ORDER BY rt.{organization} DESC
                LIMIT ?
            """
            
            response_rows = self.db.fetch_all(response_query, (limit,))
            
            for row in response_rows:
                activities.append({
                    "timestamp": row["response_time"],
                    "type": "response",
                    "agenda": row["agenda_code"],
                    "description": f"아젠다 응답: {row['agenda_code']}"
                })
            
            # 시간순 정렬 및 제한
            activities.sort(key=lambda x: x["timestamp"], reverse=True)
            return activities[:limit]
            
        except Exception as e:
            self.logger.error(f"최근 활동 조회 실패: {str(e)}")
            return []
    
    # =========================================================================
    # 대시보드 분석
    # =========================================================================
    
    def get_response_rate_by_panel(self, days: int = 30) -> Dict[str, float]:
        """패널별 응답률"""
        try:
            start_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            # 패널별 아젠다 수와 응답 수
            query = """
                SELECT 
                    c.agenda_panel,
                    COUNT(DISTINCT c.agenda_base_version) as total_agendas
                FROM agenda_chair c
                WHERE c.sent_time >= ?
                GROUP BY c.agenda_panel
            """
            
            rows = self.db.fetch_all(query, (start_date.isoformat(),))
            
            panel_stats = {}
            
            for row in rows:
                panel = row["agenda_panel"]
                total = row["total_agendas"]
                
                # 해당 패널의 응답률 계산
                response_rate = self._calculate_panel_response_rate(panel, start_date)
                
                panel_stats[panel] = response_rate
            
            return panel_stats
            
        except Exception as e:
            self.logger.error(f"패널별 응답률 조회 실패: {str(e)}")
            return {}
    
    def _calculate_panel_response_rate(self, panel: str, start_date: datetime) -> float:
        """특정 패널의 응답률 계산"""
        try:
            # 패널의 아젠다 목록
            agenda_query = """
                SELECT agenda_base_version 
                FROM agenda_chair 
                WHERE agenda_panel = ? AND sent_time >= ?
            """
            
            agenda_rows = self.db.fetch_all(agenda_query, (panel, start_date.isoformat()))
            
            if not agenda_rows:
                return 0.0
            
            total_possible = len(agenda_rows) * len(ORGANIZATIONS)
            total_actual = 0
            
            for agenda_row in agenda_rows:
                response_count = self._get_response_count_for_agenda(agenda_row["agenda_base_version"])
                total_actual += response_count
            
            return total_actual / total_possible if total_possible > 0 else 0.0
            
        except Exception as e:
            self.logger.error(f"패널 응답률 계산 실패: {str(e)}")
            return 0.0
    
    def _get_response_count_for_agenda(self, agenda_base_version: str) -> int:
        """특정 아젠다의 응답 수"""
        try:
            org_columns = ", ".join(ORGANIZATIONS)
            query = f"SELECT {org_columns} FROM agenda_responses_content WHERE agenda_base_version = ?"
            
            row = self.db.fetch_one(query, (agenda_base_version,))
            
            if not row:
                return 0
            
            count = 0
            for org in ORGANIZATIONS:
                if row.get(org) and row[org].strip():
                    count += 1
            
            return count
            
        except Exception as e:
            self.logger.error(f"응답 수 계산 실패: {str(e)}")
            return 0
    
    def get_overdue_agendas(self) -> List[Dict[str, Any]]:
        """마감일이 지난 아젠다 목록"""
        try:
            current_time = datetime.now(timezone.utc)
            
            query = """
                SELECT 
                    c.*,
                    (SELECT COUNT(*) FROM agenda_responses_content r 
                     WHERE r.agenda_base_version = c.agenda_base_version 
                     AND (r.ABS IS NOT NULL OR r.BV IS NOT NULL OR r.CCS IS NOT NULL 
                          OR r.CRS IS NOT NULL OR r.DNV IS NOT NULL OR r.IRS IS NOT NULL 
                          OR r.KR IS NOT NULL OR r.NK IS NOT NULL OR r.PRS IS NOT NULL 
                          OR r.RINA IS NOT NULL OR r.IL IS NOT NULL OR r.TL IS NOT NULL)
                    ) as response_count
                FROM agenda_chair c
                WHERE c.deadline < ? 
                AND c.decision_status IN ('created', 'comment')
                ORDER BY c.deadline ASC
            """
            
            rows = self.db.fetch_all(query, (current_time.isoformat(),))
            
            overdue_list = []
            for row in rows:
                agenda_dict = dict(row)
                
                # 응답률 계산
                response_count = self._get_response_count_for_agenda(row["agenda_base_version"])
                response_rate = response_count / len(ORGANIZATIONS) if len(ORGANIZATIONS) > 0 else 0
                
                # 경과 일수
                deadline = datetime.fromisoformat(row["deadline"])
                days_overdue = (current_time - deadline).days
                
                overdue_list.append({
                    "agenda": agenda_dict,
                    "response_count": response_count,
                    "response_rate": response_rate,
                    "days_overdue": days_overdue
                })
            
            return overdue_list
            
        except Exception as e:
            self.logger.error(f"마감 지난 아젠다 조회 실패: {str(e)}")
            return []