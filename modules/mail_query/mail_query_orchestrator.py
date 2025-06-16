"""
Mail Query 오케스트레이터
메일 조회 비즈니스 로직 및 플로우 관리
"""
import time
from typing import Optional, Dict, Any
from datetime import datetime

from infra.core.token_service import get_token_service
from infra.core.database import get_database_manager
from infra.core.logger import get_logger
from infra.core.exceptions import AuthenticationError, DatabaseError
from .mail_query_schema import (
    MailQueryRequest, MailQueryResponse, PaginationOptions,
    MailboxInfo, MailQueryLog, MailQueryFilters, GraphMailItem
)
from .graph_api_client import GraphAPIClient
from .odata_filter_builder import ODataFilterBuilder
from ._mail_query_helpers import (
    format_query_summary, 
    validate_pagination_params,
    sanitize_filter_input
)

logger = get_logger(__name__)


class MailQueryOrchestrator:
    """메일 조회 오케스트레이터 (완전 독립적)"""
    
    def __init__(self):
        # infra 서비스 직접 사용
        self.token_service = get_token_service()
        self.db = get_database_manager()
        
        # 모듈 내부 구현
        self.graph_client = GraphAPIClient()
        self.filter_builder = ODataFilterBuilder()
    
    async def mail_query_user_emails(self, request: MailQueryRequest) -> MailQueryResponse:
        """사용자 메일 조회 (독립적 구현)"""
        start_time = time.time()
        
        try:
            # 1. 입력 검증
            await self._validate_request(request)
            
            # 2. 토큰 상태 사전 확인 및 갱신
            token_status = await self.token_service.validate_and_refresh_token(request.user_id)
            
            if token_status["status"] not in ["valid", "refreshed"]:
                raise AuthenticationError(
                    f"토큰 인증 실패: {token_status['message']}",
                    details={"user_id": request.user_id, "status": token_status["status"]}
                )
            
            access_token = token_status["access_token"]
            logger.info(f"토큰 검증 완료: user_id={request.user_id}, status={token_status['status']}")
            
            # 3. 모듈 내부: OData 필터 생성
            odata_filter = None
            select_fields = None
            
            if request.filters:
                # 필터 복잡성 검증
                if not self.filter_builder.validate_filter_complexity(request.filters):
                    logger.warning(f"복잡한 필터 조건 감지: user_id={request.user_id}")
                
                odata_filter = self.filter_builder.build_filter(request.filters)
            
            if request.select_fields:
                select_fields = self.filter_builder.build_select_clause(request.select_fields)
            
            # 4. 페이징 설정
            pagination = request.pagination or PaginationOptions()
            
            # 5. 모듈 내부: Graph API 호출 (페이징 처리)
            messages = []
            total_pages = 0
            next_link = None
            current_skip = pagination.skip
            
            for page_num in range(pagination.max_pages):
                logger.debug(f"페이지 {page_num + 1} 조회 시작: user_id={request.user_id}")
                
                page_data = await self.graph_client.query_messages_single_page(
                    access_token=access_token,
                    odata_filter=odata_filter,
                    select_fields=select_fields,
                    top=pagination.top,
                    skip=current_skip
                )
                
                if not page_data.get('messages'):
                    logger.debug(f"페이지 {page_num + 1}에서 메시지 없음")
                    break
                
                messages.extend(page_data['messages'])
                next_link = page_data.get('next_link')
                total_pages += 1
                
                logger.debug(f"페이지 {page_num + 1} 완료: {len(page_data['messages'])}개 메시지")
                
                if not page_data.get('has_more'):
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
                    "performance_estimate": self.filter_builder.estimate_query_performance(
                        request.filters or MailQueryFilters(), pagination.top
                    ) if request.filters else "FAST"
                }
            )
            
            # 7. infra.database를 통한 로그 기록
            await self._log_query_execution(request, response, odata_filter, select_fields)
            
            logger.info(format_query_summary(
                request.user_id, len(messages), execution_time
            ))
            
            return response
            
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            await self._log_query_error(request, str(e), execution_time)
            
            logger.error(format_query_summary(
                request.user_id, 0, execution_time, has_error=True
            ))
            raise
    
    async def mail_query_search_messages(
        self, 
        user_id: str, 
        search_term: str,
        select_fields: Optional[list] = None,
        top: int = 50
    ) -> MailQueryResponse:
        """메시지 검색 ($search 사용)"""
        start_time = time.time()
        
        try:
            # 검색어 정제
            sanitized_term = sanitize_filter_input(search_term)
            if not sanitized_term:
                raise ValueError("유효한 검색어가 필요합니다")
            
            # 토큰 상태 사전 확인 및 갱신
            token_status = await self.token_service.validate_and_refresh_token(user_id)
            
            if token_status["status"] not in ["valid", "refreshed"]:
                raise AuthenticationError(
                    f"토큰 인증 실패: {token_status['message']}",
                    details={"user_id": user_id, "status": token_status["status"]}
                )
            
            access_token = token_status["access_token"]
            logger.info(f"토큰 검증 완료 (검색): user_id={user_id}, status={token_status['status']}")
            
            # 선택 필드 처리
            select_clause = None
            if select_fields:
                select_clause = self.filter_builder.build_select_clause(select_fields)
            
            # 검색 실행
            search_data = await self.graph_client.search_messages(
                access_token=access_token,
                search_query=sanitized_term,
                select_fields=select_clause,
                top=min(top, 250)  # $search 제한
            )
            
            execution_time = int((time.time() - start_time) * 1000)
            
            response = MailQueryResponse(
                user_id=user_id,
                total_fetched=len(search_data['messages']),
                messages=search_data['messages'],
                has_more=False,  # $search는 페이징 제한
                next_link=None,
                execution_time_ms=execution_time,
                query_info={
                    "search_term": sanitized_term,
                    "select_fields": select_clause,
                    "search_limit": min(top, 250)
                }
            )
            
            # 검색 로그 기록
            await self._log_search_execution(user_id, sanitized_term, response)
            
            logger.info(f"메시지 검색 완료: user_id={user_id}, "
                       f"term='{sanitized_term}', count={len(search_data['messages'])}, "
                       f"time={execution_time}ms")
            
            return response
            
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            logger.error(f"메시지 검색 실패: user_id={user_id}, "
                        f"term='{search_term}', error={str(e)}")
            raise
    
    async def mail_query_get_mailbox_info(self, user_id: str) -> MailboxInfo:
        """사용자 메일박스 정보 조회"""
        try:
            # 토큰 상태 사전 확인 및 갱신
            token_status = await self.token_service.validate_and_refresh_token(user_id)
            
            if token_status["status"] not in ["valid", "refreshed"]:
                raise AuthenticationError(
                    f"토큰 인증 실패: {token_status['message']}",
                    details={"user_id": user_id, "status": token_status["status"]}
                )
            
            access_token = token_status["access_token"]
            logger.info(f"토큰 검증 완료 (메일박스 정보): user_id={user_id}, status={token_status['status']}")
            
            mailbox_info = await self.graph_client.get_mailbox_info(access_token)
            
            logger.info(f"메일박스 정보 조회 완료: user_id={user_id}")
            return mailbox_info
            
        except Exception as e:
            logger.error(f"메일박스 정보 조회 실패: user_id={user_id}, error={str(e)}")
            raise
    
    async def mail_query_get_message_by_id(
        self, 
        user_id: str, 
        message_id: str,
        select_fields: Optional[list] = None
    ) -> GraphMailItem:
        """특정 메시지 조회"""
        try:
            # 토큰 상태 사전 확인 및 갱신
            token_status = await self.token_service.validate_and_refresh_token(user_id)
            
            if token_status["status"] not in ["valid", "refreshed"]:
                raise AuthenticationError(
                    f"토큰 인증 실패: {token_status['message']}",
                    details={"user_id": user_id, "status": token_status["status"]}
                )
            
            access_token = token_status["access_token"]
            logger.info(f"토큰 검증 완료 (메시지 조회): user_id={user_id}, status={token_status['status']}")
            
            select_clause = None
            if select_fields:
                select_clause = self.filter_builder.build_select_clause(select_fields)
            
            message = await self.graph_client.get_message_by_id(
                access_token=access_token,
                message_id=message_id,
                select_fields=select_clause
            )
            
            logger.info(f"메시지 조회 완료: user_id={user_id}, message_id={message_id}")
            return message
            
        except Exception as e:
            logger.error(f"메시지 조회 실패: user_id={user_id}, "
                        f"message_id={message_id}, error={str(e)}")
            raise
    
    async def _validate_request(self, request: MailQueryRequest):
        """요청 유효성 검사"""
        if not request.user_id:
            raise ValueError("user_id는 필수입니다")
        
        if request.pagination:
            if not validate_pagination_params(
                request.pagination.top, 
                request.pagination.skip, 
                request.pagination.max_pages
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
    
    async def _log_query_execution(
        self, 
        request: MailQueryRequest, 
        response: MailQueryResponse,
        odata_filter: Optional[str],
        select_fields: Optional[str]
    ):
        """쿼리 실행 로그 기록 (infra.database 직접 사용)"""
        try:
            pagination = request.pagination or PaginationOptions()
            
            log_data = {
                "user_id": request.user_id,
                "query_type": "mail_query",
                "odata_filter": odata_filter,
                "select_fields": select_fields,
                "top": pagination.top,
                "skip": pagination.skip,
                "result_count": response.total_fetched,
                "execution_time_ms": response.execution_time_ms,
                "has_error": False,
                "error_message": None,
                "created_at": datetime.utcnow()
            }
            
            self.db.insert("query_logs", log_data)
            
        except Exception as e:
            logger.error(f"쿼리 로그 기록 실패: {str(e)}")
    
    async def _log_search_execution(
        self, 
        user_id: str, 
        search_term: str, 
        response: MailQueryResponse
    ):
        """검색 실행 로그 기록"""
        try:
            log_data = {
                "user_id": user_id,
                "query_type": "mail_search",
                "odata_filter": f"search:{search_term}",
                "select_fields": None,
                "top": 250,  # $search 기본 제한
                "skip": 0,
                "result_count": response.total_fetched,
                "execution_time_ms": response.execution_time_ms,
                "has_error": False,
                "error_message": None,
                "created_at": datetime.utcnow()
            }
            
            self.db.insert("query_logs", log_data)
            
        except Exception as e:
            logger.error(f"검색 로그 기록 실패: {str(e)}")
    
    async def _log_query_error(
        self, 
        request: MailQueryRequest, 
        error_message: str, 
        execution_time: int
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
                "created_at": datetime.utcnow()
            }
            
            self.db.insert("query_logs", log_data)
            
        except Exception as e:
            logger.error(f"오류 로그 기록 실패: {str(e)}")
