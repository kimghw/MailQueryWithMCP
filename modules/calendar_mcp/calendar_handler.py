"""
Calendar Graph API Handler
Microsoft Graph API를 사용한 Calendar 작업 처리
"""

import httpx
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from infra.core.logger import get_logger
from infra.core.database import get_database_manager
from infra.core.token_service import TokenService

logger = get_logger(__name__)


class CalendarHandler:
    """Calendar Graph API 작업 처리 핸들러"""

    def __init__(self):
        self.db = get_database_manager()
        self.token_service = TokenService()
        self.graph_base_url = "https://graph.microsoft.com/v1.0"

    async def _get_access_token(self, user_id: str) -> Optional[str]:
        """
        사용자 ID로 유효한 액세스 토큰 조회 (자동 갱신 포함)

        Args:
            user_id: 사용자 ID

        Returns:
            유효한 액세스 토큰 또는 None
        """
        try:
            # TokenService를 사용하여 토큰 유효성 확인 및 자동 갱신
            return await self.token_service.get_valid_access_token(user_id)
        except Exception as e:
            logger.error(f"❌ 토큰 조회 실패: {str(e)}")
            return None

    def _build_filter_query(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> str:
        """
        OData 필터 쿼리 생성

        Args:
            start_date: 시작 날짜 (YYYY-MM-DD)
            end_date: 종료 날짜 (YYYY-MM-DD)

        Returns:
            OData 필터 문자열
        """
        filters = []

        if start_date:
            # 시작 날짜 이후의 이벤트
            filters.append(f"start/dateTime ge '{start_date}T00:00:00'")

        if end_date:
            # 종료 날짜 이전의 이벤트
            filters.append(f"end/dateTime le '{end_date}T23:59:59'")

        if filters:
            return "&$filter=" + " and ".join(filters)
        return ""

    async def list_events(
        self,
        user_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 50,
        search_query: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        사용자의 일정 목록 조회

        Args:
            user_id: 사용자 ID
            start_date: 시작 날짜 (YYYY-MM-DD)
            end_date: 종료 날짜 (YYYY-MM-DD)
            limit: 조회할 일정 수
            search_query: 검색어 (제목 검색)

        Returns:
            일정 목록
        """
        try:
            access_token = await self._get_access_token(user_id)
            if not access_token:
                return {"success": False, "message": "액세스 토큰이 없습니다"}

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }

            # 기본값: 오늘부터 30일 후까지
            if not start_date:
                start_date = datetime.now().strftime("%Y-%m-%d")
            if not end_date:
                end_dt = datetime.now() + timedelta(days=30)
                end_date = end_dt.strftime("%Y-%m-%d")

            # 필터 쿼리 생성
            filter_query = self._build_filter_query(start_date, end_date)

            # 검색어가 있으면 $search 사용
            search_param = ""
            if search_query:
                search_param = f"&$search=\"{search_query}\""

            # API 호출
            url = f"{self.graph_base_url}/me/calendar/events?$top={limit}&$orderby=start/dateTime{filter_query}{search_param}"

            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, timeout=30.0)

                if response.status_code == 200:
                    data = response.json()
                    events = data.get("value", [])
                    logger.info(f"✅ 일정 {len(events)}개 조회 성공")
                    return {
                        "success": True,
                        "events": events,
                        "count": len(events)
                    }
                else:
                    error_msg = f"일정 목록 조회 실패: {response.status_code}"
                    logger.error(error_msg)
                    return {
                        "success": False,
                        "message": error_msg,
                        "status_code": response.status_code
                    }

        except Exception as e:
            logger.error(f"❌ 일정 목록 조회 오류: {str(e)}", exc_info=True)
            return {"success": False, "message": f"오류 발생: {str(e)}"}

    async def create_event(
        self,
        user_id: str,
        subject: str,
        start: str,
        end: str,
        body: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[List[str]] = None,
        is_all_day: bool = False,
        is_online_meeting: bool = False
    ) -> Dict[str, Any]:
        """
        일정 생성

        Args:
            user_id: 사용자 ID
            subject: 일정 제목
            start: 시작 시간 (ISO 8601 format)
            end: 종료 시간 (ISO 8601 format)
            body: 일정 내용
            location: 위치
            attendees: 참석자 이메일 목록
            is_all_day: 종일 일정 여부
            is_online_meeting: 온라인 회의 여부

        Returns:
            생성된 일정 정보
        """
        try:
            access_token = await self._get_access_token(user_id)
            if not access_token:
                return {"success": False, "message": "액세스 토큰이 없습니다"}

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }

            # 이벤트 데이터 생성
            event_data = {
                "subject": subject,
                "start": {
                    "dateTime": start,
                    "timeZone": "Asia/Seoul"
                },
                "end": {
                    "dateTime": end,
                    "timeZone": "Asia/Seoul"
                },
                "isAllDay": is_all_day,
                "isOnlineMeeting": is_online_meeting,
            }

            if body:
                event_data["body"] = {
                    "contentType": "HTML",
                    "content": body
                }

            if location:
                event_data["location"] = {
                    "displayName": location
                }

            if attendees:
                event_data["attendees"] = [
                    {
                        "emailAddress": {"address": email},
                        "type": "required"
                    }
                    for email in attendees
                ]

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.graph_base_url}/me/calendar/events",
                    headers=headers,
                    json=event_data,
                    timeout=30.0
                )

                if response.status_code == 201:
                    event = response.json()
                    event_id = event.get("id")
                    logger.info(f"✅ 일정 생성 성공: {subject} (ID: {event_id})")
                    return {
                        "success": True,
                        "message": "일정이 생성되었습니다",
                        "event_id": event_id,
                        "event": event
                    }
                else:
                    error_msg = f"일정 생성 실패: {response.status_code}"
                    logger.error(f"{error_msg} - {response.text}")
                    return {
                        "success": False,
                        "message": error_msg,
                        "status_code": response.status_code
                    }

        except Exception as e:
            logger.error(f"❌ 일정 생성 오류: {str(e)}", exc_info=True)
            return {"success": False, "message": f"오류 발생: {str(e)}"}

    async def update_event(
        self,
        user_id: str,
        event_id: str,
        subject: Optional[str] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        body: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[List[str]] = None,
        is_online_meeting: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        일정 수정

        Args:
            user_id: 사용자 ID
            event_id: 일정 ID
            subject: 일정 제목
            start: 시작 시간 (ISO 8601 format)
            end: 종료 시간 (ISO 8601 format)
            body: 일정 내용
            location: 위치
            attendees: 참석자 이메일 목록
            is_online_meeting: 온라인 회의 여부

        Returns:
            수정된 일정 정보
        """
        try:
            access_token = await self._get_access_token(user_id)
            if not access_token:
                return {"success": False, "message": "액세스 토큰이 없습니다"}

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }

            # 수정할 데이터만 포함
            event_data = {}

            if subject is not None:
                event_data["subject"] = subject

            if start is not None:
                event_data["start"] = {
                    "dateTime": start,
                    "timeZone": "Asia/Seoul"
                }

            if end is not None:
                event_data["end"] = {
                    "dateTime": end,
                    "timeZone": "Asia/Seoul"
                }

            if body is not None:
                event_data["body"] = {
                    "contentType": "HTML",
                    "content": body
                }

            if location is not None:
                event_data["location"] = {
                    "displayName": location
                }

            if attendees is not None:
                event_data["attendees"] = [
                    {
                        "emailAddress": {"address": email},
                        "type": "required"
                    }
                    for email in attendees
                ]

            if is_online_meeting is not None:
                event_data["isOnlineMeeting"] = is_online_meeting

            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    f"{self.graph_base_url}/me/calendar/events/{event_id}",
                    headers=headers,
                    json=event_data,
                    timeout=30.0
                )

                if response.status_code == 200:
                    event = response.json()
                    logger.info(f"✅ 일정 수정 성공: {event_id}")
                    return {
                        "success": True,
                        "message": "일정이 수정되었습니다",
                        "event": event
                    }
                else:
                    error_msg = f"일정 수정 실패: {response.status_code}"
                    logger.error(f"{error_msg} - {response.text}")
                    return {
                        "success": False,
                        "message": error_msg,
                        "status_code": response.status_code
                    }

        except Exception as e:
            logger.error(f"❌ 일정 수정 오류: {str(e)}", exc_info=True)
            return {"success": False, "message": f"오류 발생: {str(e)}"}

    async def delete_event(self, user_id: str, event_id: str) -> Dict[str, Any]:
        """
        일정 삭제

        Args:
            user_id: 사용자 ID
            event_id: 일정 ID

        Returns:
            삭제 결과
        """
        try:
            access_token = await self._get_access_token(user_id)
            if not access_token:
                return {"success": False, "message": "액세스 토큰이 없습니다"}

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }

            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.graph_base_url}/me/calendar/events/{event_id}",
                    headers=headers,
                    timeout=30.0
                )

                if response.status_code == 204:
                    logger.info(f"✅ 일정 삭제 성공: {event_id}")
                    return {
                        "success": True,
                        "message": "일정이 삭제되었습니다"
                    }
                else:
                    error_msg = f"일정 삭제 실패: {response.status_code}"
                    logger.error(f"{error_msg} - {response.text}")
                    return {
                        "success": False,
                        "message": error_msg,
                        "status_code": response.status_code
                    }

        except Exception as e:
            logger.error(f"❌ 일정 삭제 오류: {str(e)}", exc_info=True)
            return {"success": False, "message": f"오류 발생: {str(e)}"}

    async def get_event(self, user_id: str, event_id: str) -> Dict[str, Any]:
        """
        특정 일정 상세 조회

        Args:
            user_id: 사용자 ID
            event_id: 일정 ID

        Returns:
            일정 상세 정보
        """
        try:
            access_token = await self._get_access_token(user_id)
            if not access_token:
                return {"success": False, "message": "액세스 토큰이 없습니다"}

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.graph_base_url}/me/calendar/events/{event_id}",
                    headers=headers,
                    timeout=30.0
                )

                if response.status_code == 200:
                    event = response.json()
                    logger.info(f"✅ 일정 조회 성공: {event_id}")
                    return {
                        "success": True,
                        "event": event
                    }
                else:
                    error_msg = f"일정 조회 실패: {response.status_code}"
                    logger.error(error_msg)
                    return {
                        "success": False,
                        "message": error_msg,
                        "status_code": response.status_code
                    }

        except Exception as e:
            logger.error(f"❌ 일정 조회 오류: {str(e)}", exc_info=True)
            return {"success": False, "message": f"오류 발생: {str(e)}"}
