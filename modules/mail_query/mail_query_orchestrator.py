"""
Mail Query 오케스트레이터
메일 조회 비즈니스 로직 및 플로우 관리
"""

import time
from datetime import datetime
from typing import Any, Dict, Optional

from infra.core.database import get_database_manager
from infra.core.exceptions import AuthenticationError
from infra.core.logger import get_logger
from infra.core.token_service import get_token_service

from .graph_api_client import GraphAPIClient
from .mail_query_helpers import (
    format_query_summary,
    sanitize_filter_input,
    validate_pagination_params,
)
from .mail_query_schema import (
    MailQueryFilters,
    MailQueryRequest,
    MailQueryResponse,
    PaginationOptions,
)
from .odata_filter_builder import ODataFilterBuilder

logger = get_logger(__name__)


class MailQueryOrchestrator:
    """메일 조회 오케스트레이터"""

    def __init__(self):
        # infra 서비스 직접 사용
        self.token_service = get_token_service()
        self.db = get_database_manager()

        # 모듈 내부 구현
        self.graph_client = GraphAPIClient()
        self.filter_builder = ODataFilterBuilder()

    async def __aenter__(self):
        """컨텍스트 매니저 진입"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """컨텍스트 매니저 종료 시 리소스 정리"""
        await self.close()

    async def close(self):
        """리소스 정리"""
        await self.graph_client.close()
        logger.debug("MailQueryOrchestrator 리소스 정리 완료")

    async def search_user_emails(
        self, request: MailQueryRequest
    ) -> MailQueryResponse:
        """
        $search를 사용한 메일 검색 (발신자/키워드)

        Args:
            request: MailQueryRequest (filters.search_query 필수)

        Returns:
            MailQueryResponse
        """
        start_time = time.time()

        try:
            # 1. 검색어 확인
            if not request.filters or not request.filters.search_query:
                raise ValueError("search_query가 필요합니다")

            # 2. 토큰 확보
            access_token = await self.token_service.get_valid_access_token(
                request.user_id
            )
            if not access_token:
                raise AuthenticationError(f"유효한 토큰이 없습니다: {request.user_id}")

            # 3. search_query 생성
            search_query = self.filter_builder.build_search_query(
                request.filters.search_query
            )

            # 4. select_fields 처리
            select_fields = None
            if request.select_fields:
                select_fields = self.filter_builder.build_select_clause(
                    request.select_fields
                )

            # 5. 페이징 설정
            pagination = request.pagination or PaginationOptions()

            # 6. $search API 호출
            page_data = await self.graph_client.search_messages(
                access_token=access_token,
                search_query=search_query,
                select_fields=select_fields,
                top=min(pagination.top, 250),  # $search 최대 제한
            )

            messages = page_data.get("messages", [])

            # 7. 응답 생성
            execution_time = int((time.time() - start_time) * 1000)

            response = MailQueryResponse(
                user_id=request.user_id,
                total_fetched=len(messages),
                messages=messages,
                has_more=page_data.get("has_more", False),
                next_link=page_data.get("next_link"),
                execution_time_ms=execution_time,
                query_info={
                    "search_query": search_query,
                    "select_fields": select_fields,
                    "query_type": "$search",
                },
            )

            # 8. 로그 기록
            self._log_query_execution(
                request, response, None, select_fields, search_query
            )

            logger.info(
                f"$search 검색 완료: user_id={request.user_id}, "
                f"결과={len(messages)}개, 시간={execution_time}ms"
            )

            return response

        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            self._log_query_error(request, str(e), execution_time)
            logger.error(f"$search 검색 실패: {str(e)}")
            raise

    async def mail_query_user_emails(
        self, request: MailQueryRequest
    ) -> MailQueryResponse:
        """
        사용자 메일 조회 (메인 메서드)

        Note:
            - search_query가 있으면 자동으로 $search 방식 사용
            - 그 외에는 $filter 방식 사용
        """
        # search_query가 있으면 $search 방식으로 자동 전환
        if request.filters and request.filters.search_query:
            logger.info(f"search_query 감지, $search 방식으로 전환: {request.user_id}")
            return await self.search_user_emails(request)

        # 기존 $filter 방식
        start_time = time.time()

        try:
            # 1. 입력 검증
            await self._validate_request(request)

            # 2. infra.token_service를 통한 토큰 확보
            access_token = await self.token_service.get_valid_access_token(
                request.user_id
            )
            if not access_token:
                raise AuthenticationError(f"유효한 토큰이 없습니다: {request.user_id}")

            # 3. 모듈 내부: OData 필터 생성
            odata_filter = None
            select_fields = None

            if request.filters:
                # 필터 복잡성 검증
                if not self.filter_builder.validate_filter_complexity(request.filters):
                    logger.warning(f"복잡한 필터 조건 감지: user_id={request.user_id}")

                odata_filter = self.filter_builder.build_filter(request.filters)

            if request.select_fields:
                select_fields = self.filter_builder.build_select_clause(
                    request.select_fields
                )

            # 4. 페이징 설정
            pagination = request.pagination or PaginationOptions()

            # 5. 모듈 내부: Graph API 호출 (페이징 처리)
            messages = []
            total_pages = 0
            next_link = None
            current_skip = pagination.skip

            for page_num in range(pagination.max_pages):
                logger.debug(
                    f"페이지 {page_num + 1} 조회 시작: user_id={request.user_id}"
                )

                page_data = await self.graph_client.query_messages_single_page(
                    access_token=access_token,
                    odata_filter=odata_filter,
                    select_fields=select_fields,
                    top=pagination.top,
                    skip=current_skip,
                )

                if not page_data.get("messages"):
                    logger.debug(f"페이지 {page_num + 1}에서 메시지 없음")
                    break

                messages.extend(page_data["messages"])
                next_link = page_data.get("next_link")
                total_pages += 1

                logger.debug(
                    f"페이지 {page_num + 1} 완료: {len(page_data['messages'])}개 메시지"
                )

                if not page_data.get("has_more"):
                    break

                current_skip += pagination.top

            # 6. 응답 생성
            execution_time = int((time.time() - start_time) * 1000)

            response = MailQueryResponse(
                user_id=request.user_id,
                total_fetched=len(messages),
                messages=messages,
                has_more=bool(next_link),
                next_link=next_link,
                execution_time_ms=execution_time,
                query_info={
                    "odata_filter": odata_filter,
                    "select_fields": select_fields,
                    "pages_fetched": total_pages,
                    "pagination": pagination.model_dump(),
                    "performance_estimate": (
                        self.filter_builder.estimate_query_performance(
                            request.filters or MailQueryFilters(), pagination.top
                        )
                        if request.filters
                        else "FAST"
                    ),
                },
            )

            # 7. infra.database를 통한 로그 기록 (동기 함수이므로 await 제거)
            self._log_query_execution(
                request, response, odata_filter, select_fields, None
            )

            logger.info(
                format_query_summary(request.user_id, len(messages), execution_time)
            )

            return response

        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            self._log_query_error(request, str(e), execution_time)

            logger.error(
                format_query_summary(request.user_id, 0, execution_time, has_error=True)
            )
            raise

    async def _validate_request(self, request: MailQueryRequest):
        """요청 유효성 검사"""
        if not request.user_id:
            raise ValueError("user_id는 필수입니다")

        if request.pagination:
            if not validate_pagination_params(
                request.pagination.top,
                request.pagination.skip,
                request.pagination.max_pages,
            ):
                raise ValueError("잘못된 페이징 매개변수입니다")

        # 필터 입력값 정제
        if request.filters:
            if request.filters.sender_address:
                request.filters.sender_address = sanitize_filter_input(
                    request.filters.sender_address
                )
            if request.filters.subject_contains:
                request.filters.subject_contains = sanitize_filter_input(
                    request.filters.subject_contains
                )

    def _log_query_execution(
        self,
        request: MailQueryRequest,
        response: MailQueryResponse,
        odata_filter: Optional[str],
        select_fields: Optional[str],
        search_query: Optional[str] = None,
    ):
        """쿼리 실행 로그 기록 (infra.database 직접 사용)"""
        try:
            pagination = request.pagination or PaginationOptions()

            # query_type 결정
            query_type = "$search" if search_query else "mail_query"

            log_data = {
                "user_id": request.user_id,
                "query_type": query_type,
                "odata_filter": odata_filter,
                "select_fields": select_fields,
                "search_query": search_query,
                "top": pagination.top,
                "skip": pagination.skip,
                "result_count": response.total_fetched,
                "execution_time_ms": response.execution_time_ms,
                "has_error": False,
                "error_message": None,
                "created_at": datetime.utcnow(),
            }

            self.db.insert("query_logs", log_data)

        except Exception as e:
            logger.error(f"쿼리 로그 기록 실패: {str(e)}")

    def _log_query_error(
        self, request: MailQueryRequest, error_message: str, execution_time: int
    ):
        """쿼리 오류 로그 기록"""
        try:
            pagination = request.pagination or PaginationOptions()

            log_data = {
                "user_id": request.user_id,
                "query_type": "mail_query",
                "odata_filter": None,
                "select_fields": None,
                "top": pagination.top,
                "skip": pagination.skip,
                "result_count": 0,
                "execution_time_ms": execution_time,
                "has_error": True,
                "error_message": error_message[:500],  # 길이 제한
                "created_at": datetime.utcnow(),
            }

            self.db.insert("query_logs", log_data)

        except Exception as e:
            logger.error(f"오류 로그 기록 실패: {str(e)}")
