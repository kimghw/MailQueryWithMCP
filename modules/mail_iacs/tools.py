"""
IACS MCP Tools
아젠다 및 응답 메일 검색 도구
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pathlib import Path
from infra.core.logger import get_logger
from infra.core.config import get_config
from modules.mail_query import (
    MailQueryOrchestrator,
    MailQueryRequest,
    MailQueryFilters,
)
from modules.mail_process import AttachmentDownloader, EmailSaver

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
from .format_utils import IACSResultFormatter

logger = get_logger(__name__)


class IACSTools:
    """IACS MCP Tools"""

    def __init__(self):
        self.db_service = IACSDBService()
        config = get_config()
        # mail_process 헬퍼 초기화
        # 데이터베이스 경로를 기준으로 저장 디렉토리 설정
        db_path = Path(config.database_path)
        base_dir = db_path.parent  # database가 있는 디렉토리

        self.attachment_downloader = AttachmentDownloader(
            output_dir=str(base_dir / "iacs_attachments")
        )
        self.email_saver = EmailSaver(
            output_dir=str(base_dir / "iacs_emails")
        )
        # 결과 포맷터 초기화
        self.formatter = IACSResultFormatter()

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
            1. sender_address, kr_panel_member 직접 지정 우선
            2. 없으면 panel_name으로 DB 조회
            3. panel_name도 없으면 기본 패널 사용
            4. $filter 방식 사용 (sender_address로 필터링)
            5. agenda_code가 있으면 subject_contains로 추가 필터링
        """
        try:
            logger.info("=" * 80)
            logger.info("search_agenda 시작")
            logger.info(f"요청 파라미터: panel_name={request.panel_name}, "
                       f"sender_address={request.sender_address}, "
                       f"kr_panel_member={request.kr_panel_member}, "
                       f"agenda_code={request.agenda_code}, "
                       f"start_date={request.start_date}, "
                       f"end_date={request.end_date}")

            # 1. sender_address와 kr_panel_member 결정
            chair_address = request.sender_address
            kr_panel_member = request.kr_panel_member
            panel_name = request.panel_name

            logger.info(f"초기값 - chair_address={chair_address}, "
                       f"kr_panel_member={kr_panel_member}, "
                       f"panel_name={panel_name}")

            # 직접 지정되지 않은 경우 패널 정보에서 조회
            if not chair_address or not kr_panel_member:
                logger.info("패널 정보 조회 필요 (chair_address 또는 kr_panel_member 미지정)")

                # 패널 이름 결정
                if not panel_name:
                    logger.info("panel_name 미지정, 기본 패널 조회")
                    panel_name = self.db_service.get_default_panel_name()
                    logger.info(f"기본 패널: {panel_name}")

                if not panel_name:
                    logger.error("패널 정보를 찾을 수 없음 (기본 패널 없음)")
                    return SearchAgendaResponse(
                        success=False,
                        message="패널 정보 또는 sender_address/kr_panel_member를 지정해주세요",
                        total_count=0,
                        mails=[],
                    )

                # 패널 정보 조회
                logger.info(f"DB에서 패널 정보 조회: {panel_name}")
                panel_info = self.db_service.get_panel_info_by_name(panel_name)
                if not panel_info:
                    logger.error(f"패널 정보 조회 실패: {panel_name}")
                    return SearchAgendaResponse(
                        success=False,
                        message=f"패널 정보를 찾을 수 없습니다: {panel_name}",
                        total_count=0,
                        mails=[],
                    )

                logger.info(f"패널 정보 조회 성공: {panel_info}")

                # 패널 정보에서 가져오기 (직접 지정되지 않은 경우만)
                if not chair_address:
                    chair_address = panel_info["chair_address"]
                    logger.info(f"패널에서 chair_address 가져옴: {chair_address}")
                if not kr_panel_member:
                    kr_panel_member = panel_info["kr_panel_member"]
                    logger.info(f"패널에서 kr_panel_member 가져옴: {kr_panel_member}")

            # 2. 날짜 범위 설정
            start_date = request.start_date or get_default_start_date()
            end_date = request.end_date or get_default_end_date()
            logger.info(f"날짜 범위 설정: start_date={start_date}, end_date={end_date}")

            # 3. MailQuery 필터 생성
            filters = MailQueryFilters(
                sender_address=chair_address,  # 의장 이메일로 필터링
                date_from=start_date,  # 시작 날짜 (과거)
                date_to=end_date,  # 종료 날짜 (현재)
            )

            # agenda_code가 있으면 제목 필터 추가
            if request.agenda_code:
                filters.subject_contains = request.agenda_code
                logger.info(f"agenda_code 필터 추가: {request.agenda_code}")

            logger.info(f"MailQuery 필터: sender_address={filters.sender_address}, "
                       f"date_from={filters.date_from}, "
                       f"date_to={filters.date_to}, "
                       f"subject_contains={filters.subject_contains}")

            # 4. 메일 조회 (kr_panel_member로 인증)
            logger.info(f"MailQueryOrchestrator 시작 - user_id: {kr_panel_member}")
            # 항상 본문 포함
            select_fields = ["subject", "body", "from", "receivedDateTime", "id", "attachments"]
            async with MailQueryOrchestrator() as orchestrator:
                mail_request = MailQueryRequest(
                    user_id=kr_panel_member,  # 한국 패널 멤버로 조회
                    filters=filters,
                    select_fields=select_fields,
                )

                logger.info(f"메일 조회 요청: user_id={mail_request.user_id}, "
                           f"select_fields={mail_request.select_fields}")

                response = await orchestrator.mail_query_user_emails(mail_request)

                logger.info(f"메일 조회 완료: total_fetched={response.total_fetched}, "
                           f"messages_count={len(response.messages)}")

                # 5. 첨부파일 다운로드 및 메일 저장 처리
                mails = []
                for mail in response.messages:
                    mail_dict = mail.model_dump()

                    # 메일 저장
                    if request.save_email:
                        try:
                            email_dict = {
                                'id': mail.id,
                                'subject': mail.subject,
                                'received_date_time': mail.received_date_time,
                                'from': mail.from_address,
                                'body': mail.body if hasattr(mail, 'body') else None,
                                'to_recipients': getattr(mail, 'to_recipients', []),
                                'cc_recipients': getattr(mail, 'cc_recipients', []),
                            }
                            saved_info = await self.email_saver.save_email_as_text(
                                email_dict, user_id=kr_panel_member
                            )
                            mail_dict['saved_email_path'] = saved_info.get('email_path')
                            logger.info(f"메일 저장 완료: {saved_info.get('email_path')}")
                        except Exception as e:
                            logger.error(f"메일 저장 실패: {str(e)}")

                    # 첨부파일 다운로드
                    if request.download_attachments and mail.has_attachments:
                        try:
                            if hasattr(mail, 'attachments') and mail.attachments:
                                downloaded_attachments = []
                                for attachment in mail.attachments:
                                    att_result = await self.attachment_downloader.download_and_save(
                                        graph_client=orchestrator.graph_client,
                                        user_id=kr_panel_member,
                                        message_id=mail.id,
                                        attachment=attachment
                                    )
                                    if att_result:
                                        downloaded_attachments.append(att_result)
                                        logger.info(f"첨부파일 다운로드 완료: {att_result.get('file_path')}")
                                mail_dict['downloaded_attachments'] = downloaded_attachments
                        except Exception as e:
                            logger.error(f"첨부파일 다운로드 실패: {str(e)}")

                    mails.append(mail_dict)

                logger.info(f"search_agenda 성공: {len(mails)}개 아젠다 반환")
                logger.info("=" * 80)

                # 포맷팅된 텍스트 생성 (항상 본문 포함)
                formatted_text = self.formatter.format_search_results(
                    mails=mails,
                    user_id=kr_panel_member,
                    panel_name=panel_name,
                    chair_address=chair_address,
                    start_date=request.start_date,
                    end_date=request.end_date,
                    mail_type="agenda",
                    include_body=True,  # 항상 본문 포함
                    download_attachments=request.download_attachments,
                    save_email=request.save_email
                )

                return SearchAgendaResponse(
                    success=True,
                    message=formatted_text,  # 포맷팅된 텍스트를 message에 포함
                    total_count=response.total_fetched,
                    panel_name=panel_name,
                    chair_address=chair_address,
                    kr_panel_member=kr_panel_member,
                    mails=mails,
                )

        except Exception as e:
            logger.error(f"search_agenda 실패: {str(e)}", exc_info=True)
            logger.error("=" * 80)
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
            logger.info("=" * 80)
            logger.info("search_responses 시작")
            logger.info(f"요청 파라미터: agenda_code={request.agenda_code}, "
                       f"send_address={request.send_address}")

            # 1. 기본 패널의 kr_panel_member로 인증
            logger.info("기본 패널의 kr_panel_member 조회")
            kr_panel_member = self.db_service.get_kr_panel_member_by_default()
            if not kr_panel_member:
                logger.error("인증 정보를 찾을 수 없음 (기본 패널 없음)")
                return SearchResponsesResponse(
                    success=False,
                    message="인증 정보를 찾을 수 없습니다. 기본 패널을 설정해주세요",
                    total_count=0,
                    agenda_code=request.agenda_code,
                    mails=[],
                )

            logger.info(f"kr_panel_member: {kr_panel_member}")

            # 2. $search 쿼리 생성
            # agenda_code 앞 7자 검색
            search_keyword = request.agenda_code[:7]
            search_query = f"subject:{search_keyword}"
            logger.info(f"검색 쿼리 생성: search_keyword={search_keyword}, "
                       f"search_query={search_query}")

            # 3. 메일 조회
            logger.info(f"MailQueryOrchestrator 시작 - user_id: {kr_panel_member}")
            # 항상 본문 포함
            select_fields = ["subject", "body", "from", "receivedDateTime", "id", "attachments"]
            async with MailQueryOrchestrator() as orchestrator:
                mail_request = MailQueryRequest(
                    user_id=kr_panel_member,
                    filters=MailQueryFilters(search_query=search_query),
                    select_fields=select_fields,
                )

                logger.info(f"메일 조회 요청: user_id={mail_request.user_id}, "
                           f"search_query={search_query}, "
                           f"select_fields={mail_request.select_fields}")

                response = await orchestrator.mail_query_user_emails(mail_request)

                logger.info(f"메일 조회 완료: total_fetched={response.total_fetched}, "
                           f"messages_count={len(response.messages)}")

                # 4. 클라이언트 측 필터링 및 첨부파일 처리
                logger.info("클라이언트 측 필터링 시작")
                filtered_mails = []
                filtered_count = 0
                for mail in response.messages:
                    # 제목에 키워드 포함 확인 (어디든 포함되면 매칭)
                    subject = mail.subject or ""
                    if search_keyword not in subject:
                        filtered_count += 1
                        continue

                    # send_address 필터링
                    if request.send_address:
                        from_addr = mail.from_address or {}
                        email_addr = from_addr.get("emailAddress", {}).get(
                            "address", ""
                        )
                        if email_addr not in request.send_address:
                            logger.debug(f"send_address 필터링으로 제외: {email_addr}")
                            filtered_count += 1
                            continue

                    # 필터링 통과한 메일 처리
                    mail_dict = mail.model_dump()

                    # 메일 저장
                    if request.save_email:
                        try:
                            email_dict = {
                                'id': mail.id,
                                'subject': mail.subject,
                                'received_date_time': mail.received_date_time,
                                'from': mail.from_address,
                                'body': mail.body if hasattr(mail, 'body') else None,
                                'to_recipients': getattr(mail, 'to_recipients', []),
                                'cc_recipients': getattr(mail, 'cc_recipients', []),
                            }
                            saved_info = await self.email_saver.save_email_as_text(
                                email_dict, user_id=kr_panel_member
                            )
                            mail_dict['saved_email_path'] = saved_info.get('email_path')
                            logger.info(f"메일 저장 완료: {saved_info.get('email_path')}")
                        except Exception as e:
                            logger.error(f"메일 저장 실패: {str(e)}")

                    # 첨부파일 다운로드
                    if request.download_attachments and mail.has_attachments:
                        try:
                            if hasattr(mail, 'attachments') and mail.attachments:
                                downloaded_attachments = []
                                for attachment in mail.attachments:
                                    att_result = await self.attachment_downloader.download_and_save(
                                        graph_client=orchestrator.graph_client,
                                        user_id=kr_panel_member,
                                        message_id=mail.id,
                                        attachment=attachment
                                    )
                                    if att_result:
                                        downloaded_attachments.append(att_result)
                                        logger.info(f"첨부파일 다운로드 완료: {att_result.get('file_path')}")
                                mail_dict['downloaded_attachments'] = downloaded_attachments
                        except Exception as e:
                            logger.error(f"첨부파일 다운로드 실패: {str(e)}")

                    filtered_mails.append(mail_dict)

                logger.info(f"클라이언트 측 필터링 완료: {filtered_count}개 제외, "
                           f"{len(filtered_mails)}개 포함")
                logger.info(f"search_responses 성공: {len(filtered_mails)}개 응답 반환")
                logger.info("=" * 80)

                # 포맷팅된 텍스트 생성 (항상 본문 포함)
                # search_responses는 날짜 필터가 없으므로 임의값 사용
                from datetime import datetime, timezone
                now = datetime.now(timezone.utc)
                three_months_ago = now - timedelta(days=90)

                formatted_text = self.formatter.format_search_results(
                    mails=filtered_mails,
                    user_id=kr_panel_member,
                    panel_name="default",  # responses는 패널명이 없음
                    chair_address="",
                    start_date=three_months_ago,
                    end_date=now,
                    mail_type="responses",
                    include_body=True,  # 항상 본문 포함
                    download_attachments=request.download_attachments,
                    save_email=request.save_email
                )

                return SearchResponsesResponse(
                    success=True,
                    message=formatted_text,  # 포맷팅된 텍스트를 message에 포함
                    total_count=len(filtered_mails),
                    agenda_code=request.agenda_code,
                    mails=filtered_mails,
                )

        except Exception as e:
            logger.error(f"search_responses 실패: {str(e)}", exc_info=True)
            logger.error("=" * 80)
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
