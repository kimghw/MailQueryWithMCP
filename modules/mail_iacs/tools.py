"""
IACS MCP Tools
아젠다 및 응답 메일 검색 도구
"""

from datetime import datetime, timedelta
from typing import List, Optional
from infra.core.logger import get_logger
from modules.mail_query import (
    MailQueryOrchestrator,
    MailQueryRequest,
    MailQueryFilters,
)

from .db_service import IACSDBService
from .schemas import (
    InsertInfoRequest,
    InsertInfoResponse,
    SearchAgendaRequest,
    SearchAgendaResponse,
    SearchResponsesRequest,
    SearchResponsesResponse,
    InsertDefaultValueRequest,
    InsertDefaultValueResponse,
    get_default_start_date,
    get_default_end_date,
)

logger = get_logger(__name__)


class IACSTools:
    """IACS MCP Tools"""

    def __init__(self):
        self.db_service = IACSDBService()

    # ========================================================================
    # Tool 1: insert_info
    # ========================================================================

    async def insert_info(self, request: InsertInfoRequest) -> InsertInfoResponse:
        """
        패널 의장 및 멤버 정보 삽입

        Args:
            request: InsertInfoRequest

        Returns:
            InsertInfoResponse
        """
        try:
            success = self.db_service.insert_panel_chair(
                chair_address=request.chair_address,
                panel_name=request.panel_name,
                kr_panel_member=request.kr_panel_member,
            )

            return InsertInfoResponse(
                success=success,
                message=f"패널 정보가 성공적으로 저장되었습니다: {request.panel_name}",
                panel_name=request.panel_name,
                chair_address=request.chair_address,
                kr_panel_member=request.kr_panel_member,
            )

        except Exception as e:
            logger.error(f"insert_info 실패: {str(e)}")
            return InsertInfoResponse(
                success=False,
                message=f"패널 정보 저장 실패: {str(e)}",
                panel_name=request.panel_name,
                chair_address=request.chair_address,
                kr_panel_member=request.kr_panel_member,
            )

    # ========================================================================
    # Tool 2: search_agenda
    # ========================================================================

    async def search_agenda(
        self, request: SearchAgendaRequest
    ) -> SearchAgendaResponse:
        """
        아젠다 메일 검색 (의장이 보낸 메일)

        Flow:
            1. panel_name이 있으면 DB에서 chair_address 조회
            2. kr_panel_member로 인증하여 메일 조회
            3. $filter 방식 사용 (sender_address로 필터링)
            4. agenda_code가 있으면 subject_contains로 추가 필터링
        """
        try:
            # 1. 패널 정보 조회
            panel_name = request.panel_name
            if not panel_name:
                # 기본 패널 사용
                panel_name = self.db_service.get_default_panel_name()

            if not panel_name:
                return SearchAgendaResponse(
                    success=False,
                    message="패널 이름이 지정되지 않았고 기본 패널도 설정되지 않았습니다",
                    total_count=0,
                    mails=[],
                )

            panel_info = self.db_service.get_panel_info_by_name(panel_name)
            if not panel_info:
                return SearchAgendaResponse(
                    success=False,
                    message=f"패널 정보를 찾을 수 없습니다: {panel_name}",
                    total_count=0,
                    mails=[],
                )

            chair_address = panel_info["chair_address"]
            kr_panel_member = panel_info["kr_panel_member"]

            # 2. 날짜 범위 설정
            start_date = request.start_date or get_default_start_date()
            end_date = request.end_date or get_default_end_date()

            # 3. MailQuery 필터 생성
            filters = MailQueryFilters(
                sender_address=chair_address,  # 의장 이메일로 필터링
                date_from=end_date,  # 과거 날짜
                date_to=start_date,  # 현재 날짜
            )

            # agenda_code가 있으면 제목 필터 추가
            if request.agenda_code:
                filters.subject_contains = request.agenda_code

            # 4. 메일 조회 (kr_panel_member로 인증)
            async with MailQueryOrchestrator() as orchestrator:
                mail_request = MailQueryRequest(
                    user_id=kr_panel_member,  # 한국 패널 멤버로 조회
                    filters=filters,
                    select_fields=request.content_field,
                )

                response = await orchestrator.mail_query_user_emails(mail_request)

                # 5. 응답 생성
                mails = [mail.model_dump() for mail in response.messages]

                return SearchAgendaResponse(
                    success=True,
                    message=f"{response.total_fetched}개의 아젠다를 찾았습니다",
                    total_count=response.total_fetched,
                    panel_name=panel_name,
                    chair_address=chair_address,
                    kr_panel_member=kr_panel_member,
                    mails=mails,
                )

        except Exception as e:
            logger.error(f"search_agenda 실패: {str(e)}")
            return SearchAgendaResponse(
                success=False,
                message=f"아젠다 검색 실패: {str(e)}",
                total_count=0,
                mails=[],
            )

    # ========================================================================
    # Tool 3: search_responses
    # ========================================================================

    async def search_responses(
        self, request: SearchResponsesRequest
    ) -> SearchResponsesResponse:
        """
        응답 메일 검색 (멤버들이 보낸 메일)

        Flow:
            1. $search 방식 사용 (agenda_code 키워드 검색)
            2. send_address가 있으면 클라이언트 측에서 필터링
            3. 제목 앞 7자로 agenda_code 매칭 (클라이언트 측)
        """
        try:
            # 1. 기본 패널의 kr_panel_member로 인증
            kr_panel_member = self.db_service.get_kr_panel_member_by_default()
            if not kr_panel_member:
                return SearchResponsesResponse(
                    success=False,
                    message="인증 정보를 찾을 수 없습니다. 기본 패널을 설정해주세요",
                    total_count=0,
                    agenda_code=request.agenda_code,
                    mails=[],
                )

            # 2. $search 쿼리 생성
            # agenda_code 앞 7자 검색
            search_keyword = request.agenda_code[:7]
            search_query = f"subject:{search_keyword}"

            # 3. 메일 조회
            async with MailQueryOrchestrator() as orchestrator:
                mail_request = MailQueryRequest(
                    user_id=kr_panel_member,
                    filters=MailQueryFilters(search_query=search_query),
                    select_fields=request.content_field,
                )

                response = await orchestrator.mail_query_user_emails(mail_request)

                # 4. 클라이언트 측 필터링
                filtered_mails = []
                for mail in response.messages:
                    # 제목에 키워드 포함 확인 (어디든 포함되면 매칭)
                    subject = mail.subject or ""
                    if search_keyword not in subject:
                        continue

                    # send_address 필터링
                    if request.send_address:
                        from_addr = mail.from_address or {}
                        email_addr = from_addr.get("emailAddress", {}).get(
                            "address", ""
                        )
                        if email_addr not in request.send_address:
                            continue

                    filtered_mails.append(mail.model_dump())

                return SearchResponsesResponse(
                    success=True,
                    message=f"{len(filtered_mails)}개의 응답을 찾았습니다",
                    total_count=len(filtered_mails),
                    agenda_code=request.agenda_code,
                    mails=filtered_mails,
                )

        except Exception as e:
            logger.error(f"search_responses 실패: {str(e)}")
            return SearchResponsesResponse(
                success=False,
                message=f"응답 검색 실패: {str(e)}",
                total_count=0,
                agenda_code=request.agenda_code,
                mails=[],
            )

    # ========================================================================
    # Tool 4: insert_default_value
    # ========================================================================

    async def insert_default_value(
        self, request: InsertDefaultValueRequest
    ) -> InsertDefaultValueResponse:
        """
        기본 패널 이름 설정

        Args:
            request: InsertDefaultValueRequest

        Returns:
            InsertDefaultValueResponse
        """
        try:
            success = self.db_service.insert_default_value(
                panel_name=request.panel_name
            )

            return InsertDefaultValueResponse(
                success=success,
                message=f"기본 패널이 설정되었습니다: {request.panel_name}",
                panel_name=request.panel_name,
            )

        except Exception as e:
            logger.error(f"insert_default_value 실패: {str(e)}")
            return InsertDefaultValueResponse(
                success=False,
                message=f"기본 패널 설정 실패: {str(e)}",
                panel_name=request.panel_name,
            )
