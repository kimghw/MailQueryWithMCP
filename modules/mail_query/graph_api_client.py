"""
Microsoft Graph API 클라이언트
메일 데이터 조회를 위한 Graph API 호출 처리
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, Optional

import aiohttp

from infra.core.config import get_config
from infra.core.exceptions import APIConnectionError, TokenExpiredError
from infra.core.logger import get_logger

from .mail_query_helpers import (
    calculate_retry_delay,
    is_transient_error,
    parse_graph_error_response,
    parse_graph_mail_item,
)

logger = get_logger(__name__)


class GraphAPIClient:
    """Microsoft Graph API 클라이언트"""

    def __init__(self):
        self.config = get_config()
        self.base_url = "https://graph.microsoft.com/v1.0"
        self.max_retries = 3
        self.timeout = aiohttp.ClientTimeout(total=60)
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
            # 세션이 완전히 닫힐 때까지 잠시 대기
            await asyncio.sleep(0.1)
            logger.debug("aiohttp 세션 정리됨")
            self._session = None

    async def query_messages_single_page(
        self,
        access_token: str,
        odata_filter: Optional[str] = None,
        select_fields: Optional[str] = None,
        top: int = 50,
        skip: int = 0,
        orderby: str = "receivedDateTime desc",
    ) -> Dict[str, Any]:
        """단일 페이지 메시지 조회"""

        url = f"{self.base_url}/me/messages"
        params = {
            "$top": min(top, 1000),  # Graph API 최대 제한
            "$skip": skip,
            "$orderby": orderby,
        }

        if odata_filter:
            params["$filter"] = odata_filter
        if select_fields:
            params["$select"] = select_fields
            # attachments가 select 필드에 포함되면 expand도 추가
            # select_fields는 콤마로 구분된 문자열이므로 확인
            if "attachments" in select_fields:
                params["$expand"] = "attachments"
                logger.info(f"Attachments expand 추가됨: select_fields={select_fields}")

        # 디버그 로그 추가
        logger.info(f"Graph API 쿼리 파라미터: {params}")
        logger.info(f"Graph API URL: {url}")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Prefer": 'outlook.body-content-type="text"',  # 텍스트 형식 선호
        }

        try:
            response_data = await self._make_request_with_retry(
                method="GET", url=url, headers=headers, params=params
            )

            # GraphMailItem으로 변환
            messages = []
            for item in response_data.get("value", []):
                try:
                    graph_item = parse_graph_mail_item(item)
                    messages.append(graph_item)
                except Exception as e:
                    logger.warning(f"메일 아이템 파싱 실패: {str(e)}")
                    continue

            return {
                "messages": messages,
                "has_more": "@odata.nextLink" in response_data,
                "next_link": response_data.get("@odata.nextLink"),
                "total_count": len(messages),
            }

        except Exception as e:
            logger.error(f"Graph API 메시지 조회 실패: {str(e)}")
            raise

    async def _make_request_with_retry(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
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
                    json=json_data,
                ) as response:

                    # 성공 응답 처리
                    if response.status == 200:
                        data = await response.json()
                        # 첫 번째 메시지의 attachments 확인
                        if data.get("value") and len(data["value"]) > 0:
                            first_msg = data["value"][0]
                            logger.info(f"첫 번째 메시지 attachments 필드: {first_msg.get('attachments', 'NOT FOUND')}")
                        return data

                    # 인증 오류 처리
                    if response.status == 401:
                        raise TokenExpiredError("액세스 토큰이 만료되었습니다")

                    # 응답 본문 읽기 (오류 정보 포함)
                    try:
                        error_data = await response.json()
                        error_info = parse_graph_error_response(error_data)
                    except:
                        error_info = {
                            "code": f"HTTP_{response.status}",
                            "message": f"HTTP {response.status} 오류",
                        }

                    # 재시도 가능한 오류인지 확인
                    if is_transient_error(response.status, error_info.get("code")):
                        if attempt < self.max_retries:
                            # Retry-After 헤더 확인
                            retry_after = response.headers.get("Retry-After")
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
                        error_code=error_info.get("code"),
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
                        f"Graph API 네트워크 오류: {str(e)}", api_endpoint=url
                    ) from e

        # 여기에 도달하면 모든 재시도가 실패한 것
        raise APIConnectionError(
            f"Graph API 호출 실패: 최대 재시도 횟수 초과", api_endpoint=url
        )

    async def put(
        self,
        endpoint: str,
        data: bytes,
        headers: Optional[Dict[str, str]] = None,
        access_token: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        PUT 요청을 통해 파일 업로드
        
        Args:
            endpoint: API 엔드포인트 (예: /me/drive/root:/path/file.pdf:/content)
            data: 업로드할 파일 데이터
            headers: 추가 헤더
            access_token: 액세스 토큰
            
        Returns:
            업로드 결과 또는 None
        """
        if not access_token:
            logger.error("Access token is required for PUT requests")
            return None
            
        url = f"{self.base_url}{endpoint}"
        
        # 기본 헤더 설정
        request_headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/octet-stream"
        }
        
        # 추가 헤더 병합
        if headers:
            request_headers.update(headers)
        
        try:
            session = await self._get_session()
            async with session.put(
                url,
                data=data,
                headers=request_headers
            ) as response:
                if response.status in [200, 201]:
                    return await response.json()
                elif response.status == 409:
                    logger.warning(f"Conflict at {endpoint} - file may already exist")
                    return None
                else:
                    error_text = await response.text()
                    logger.error(f"PUT request failed: {response.status} - {error_text}")
                    return None
                    
        except Exception as e:
            logger.error(f"PUT request exception: {str(e)}")
            return None
    
    async def post(
        self,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        access_token: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        POST 요청
        
        Args:
            endpoint: API 엔드포인트
            json_data: JSON 데이터
            access_token: 액세스 토큰
            
        Returns:
            응답 데이터 또는 None
        """
        if not access_token:
            logger.error("Access token is required for POST requests")
            return None
            
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        try:
            return await self._make_request_with_retry(
                method="POST",
                url=url,
                headers=headers,
                json_data=json_data
            )
        except Exception as e:
            logger.error(f"POST request failed: {str(e)}")
            return None
