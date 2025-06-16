"""
Microsoft Graph API 클라이언트
메일 데이터 조회를 위한 Graph API 호출 처리
"""
import aiohttp
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime

from infra.core.config import get_config
from infra.core.logger import get_logger
from infra.core.exceptions import APIConnectionError, TokenExpiredError
from .mail_query_schema import GraphMailItem, MailboxInfo
from ._mail_query_helpers import (
    parse_graph_mail_item, 
    parse_graph_error_response,
    calculate_retry_delay,
    is_transient_error
)

logger = get_logger(__name__)


class GraphAPIClient:
    """Microsoft Graph API 클라이언트 (모듈 내부)"""
    
    def __init__(self):
        self.config = get_config()
        self.base_url = "https://graph.microsoft.com/v1.0"
        self.max_retries = 3
        self.timeout = aiohttp.ClientTimeout(total=30)
        self._session: Optional[aiohttp.ClientSession] = None
        self._session_lock = asyncio.Lock()
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """세션 생성 또는 반환 (재사용)"""
        if self._session is None or self._session.closed:
            async with self._session_lock:
                if self._session is None or self._session.closed:
                    self._session = aiohttp.ClientSession(timeout=self.timeout)
                    logger.debug("새로운 aiohttp 세션 생성됨")
        return self._session
    
    async def close(self):
        """세션 정리"""
        if self._session and not self._session.closed:
            await self._session.close()
            logger.debug("aiohttp 세션 정리됨")
            self._session = None
    
    async def __aenter__(self):
        """컨텍스트 매니저 진입"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """컨텍스트 매니저 종료 시 세션 정리"""
        await self.close()
    
    async def query_messages_single_page(
        self,
        access_token: str,
        odata_filter: Optional[str] = None,
        select_fields: Optional[str] = None,
        top: int = 50,
        skip: int = 0,
        orderby: str = "receivedDateTime desc"
    ) -> Dict[str, Any]:
        """단일 페이지 메시지 조회"""
        
        url = f"{self.base_url}/me/messages"
        params = {
            "$top": min(top, 1000),  # Graph API 최대 제한
            "$skip": skip,
            "$orderby": orderby
        }
        
        if odata_filter:
            params["$filter"] = odata_filter
        if select_fields:
            params["$select"] = select_fields
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Prefer": "outlook.body-content-type=\"text\""  # 텍스트 형식 선호
        }
        
        try:
            response_data = await self._make_request_with_retry(
                method="GET",
                url=url,
                headers=headers,
                params=params
            )
            
            # GraphMailItem으로 변환
            messages = []
            for item in response_data.get('value', []):
                try:
                    graph_item = parse_graph_mail_item(item)
                    messages.append(graph_item)
                except Exception as e:
                    logger.warning(f"메일 아이템 파싱 실패: {str(e)}")
                    continue
            
            return {
                'messages': messages,
                'has_more': '@odata.nextLink' in response_data,
                'next_link': response_data.get('@odata.nextLink'),
                'total_count': len(messages)
            }
            
        except Exception as e:
            logger.error(f"Graph API 메시지 조회 실패: {str(e)}")
            raise
    
    async def get_mailbox_info(self, access_token: str) -> MailboxInfo:
        """메일박스 정보 조회"""
        url = f"{self.base_url}/me/mailboxSettings"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }
        
        try:
            response_data = await self._make_request_with_retry(
                method="GET",
                url=url,
                headers=headers
            )
            
            return MailboxInfo(
                display_name=response_data.get('displayName'),
                user_principal_name=response_data.get('userPrincipalName'),
                automatic_replies_setting=response_data.get('automaticRepliesSetting'),
                archive_folder=response_data.get('archiveFolder'),
                time_zone=response_data.get('timeZone'),
                language=response_data.get('language')
            )
            
        except Exception as e:
            logger.error(f"메일박스 정보 조회 실패: {str(e)}")
            raise APIConnectionError(
                f"메일박스 정보 조회 실패: {str(e)}",
                api_endpoint=url
            ) from e
    
    async def search_messages(
        self,
        access_token: str,
        search_query: str,
        select_fields: Optional[str] = None,
        top: int = 50
    ) -> Dict[str, Any]:
        """메시지 검색 ($search 사용)"""
        url = f"{self.base_url}/me/messages"
        params = {
            "$search": f'"{search_query}"',
            "$top": min(top, 250)  # $search는 250개 제한
        }
        
        if select_fields:
            params["$select"] = select_fields
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "ConsistencyLevel": "eventual"  # 검색을 위한 일관성 레벨
        }
        
        try:
            response_data = await self._make_request_with_retry(
                method="GET",
                url=url,
                headers=headers,
                params=params
            )
            
            # 검색 결과 파싱
            messages = []
            for item in response_data.get('value', []):
                try:
                    graph_item = parse_graph_mail_item(item)
                    messages.append(graph_item)
                except Exception as e:
                    logger.warning(f"검색 결과 파싱 실패: {str(e)}")
                    continue
            
            return {
                'messages': messages,
                'has_more': False,  # $search는 페이징 제한
                'next_link': None,
                'total_count': len(messages)
            }
            
        except Exception as e:
            logger.error(f"메시지 검색 실패: {str(e)}")
            raise
    
    async def get_message_by_id(
        self,
        access_token: str,
        message_id: str,
        select_fields: Optional[str] = None
    ) -> GraphMailItem:
        """특정 메시지 조회"""
        url = f"{self.base_url}/me/messages/{message_id}"
        params = {}
        
        if select_fields:
            params["$select"] = select_fields
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }
        
        try:
            response_data = await self._make_request_with_retry(
                method="GET",
                url=url,
                headers=headers,
                params=params
            )
            
            return parse_graph_mail_item(response_data)
            
        except Exception as e:
            logger.error(f"메시지 조회 실패 (ID: {message_id}): {str(e)}")
            raise
    
    async def _make_request_with_retry(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """재시도 로직이 포함된 HTTP 요청"""
        
        session = await self._get_session()
        
        for attempt in range(self.max_retries + 1):
            try:
                async with session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    json=json_data
                ) as response:
                    
                    # 성공 응답 처리
                    if response.status == 200:
                        return await response.json()
                    
                    # 인증 오류 처리
                    if response.status == 401:
                        raise TokenExpiredError("액세스 토큰이 만료되었습니다")
                    
                    # 응답 본문 읽기 (오류 정보 포함)
                    try:
                        error_data = await response.json()
                        error_info = parse_graph_error_response(error_data)
                    except:
                        error_info = {
                            'code': f'HTTP_{response.status}',
                            'message': f'HTTP {response.status} 오류'
                        }
                    
                    # 재시도 가능한 오류인지 확인
                    if is_transient_error(response.status, error_info.get('code')):
                        if attempt < self.max_retries:
                            # Retry-After 헤더 확인
                            retry_after = response.headers.get('Retry-After')
                            if retry_after:
                                delay = float(retry_after)
                            else:
                                delay = calculate_retry_delay(attempt)
                            
                            logger.warning(
                                f"일시적 오류 발생 (시도 {attempt + 1}/{self.max_retries + 1}), "
                                f"{delay}초 후 재시도: {error_info['message']}"
                            )
                            await asyncio.sleep(delay)
                            continue
                    
                    # 재시도 불가능한 오류 또는 최대 재시도 횟수 초과
                    raise APIConnectionError(
                        f"Graph API 호출 실패: {error_info['message']}",
                        api_endpoint=url,
                        status_code=response.status,
                        error_code=error_info.get('code')
                    )
                    
            except aiohttp.ClientError as e:
                if attempt < self.max_retries:
                    delay = calculate_retry_delay(attempt)
                    logger.warning(
                        f"네트워크 오류 발생 (시도 {attempt + 1}/{self.max_retries + 1}), "
                        f"{delay}초 후 재시도: {str(e)}"
                    )
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise APIConnectionError(
                        f"Graph API 네트워크 오류: {str(e)}",
                        api_endpoint=url
                    ) from e
        
        # 여기에 도달하면 모든 재시도가 실패한 것
        raise APIConnectionError(
            f"Graph API 호출 실패: 최대 재시도 횟수 초과",
            api_endpoint=url
        )
    
    async def get_raw_message(
        self,
        access_token: str,
        message_id: str
    ) -> Dict[str, Any]:
        """메시지 원본 데이터 조회 (전체 필드 포함)"""
        url = f"{self.base_url}/me/messages/{message_id}"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Prefer": "outlook.body-content-type=\"text\""  # 텍스트 형식 선호
        }
        
        try:
            # 전체 필드를 포함한 원본 데이터 조회
            response_data = await self._make_request_with_retry(
                method="GET",
                url=url,
                headers=headers
            )
            
            logger.debug(f"메시지 원본 데이터 조회 완료: message_id={message_id}")
            return response_data
            
        except Exception as e:
            logger.error(f"메시지 원본 조회 실패 (ID: {message_id}): {str(e)}")
            raise
