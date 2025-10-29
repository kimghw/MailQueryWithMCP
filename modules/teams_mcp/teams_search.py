"""
Teams Search
Teams 메시지 검색 기능
"""

import re
import httpx
from typing import Optional, Dict, Any
from infra.core.logger import get_logger

logger = get_logger(__name__)


class TeamsSearch:
    """Teams 메시지 검색"""

    def __init__(self, graph_base_url: str = "https://graph.microsoft.com/v1.0"):
        self.graph_base_url = graph_base_url

    async def search_messages(
        self,
        access_token: str,
        keyword: str,
        search_scope: str = "current_chat",
        chat_id: Optional[str] = None,
        page_size: int = 50,
        max_results: int = 500
    ) -> Dict[str, Any]:
        """
        메시지 키워드 검색

        Args:
            access_token: Graph API 액세스 토큰
            keyword: 검색 키워드
            search_scope: 검색 범위 ("current_chat" 또는 "all_chats")
            chat_id: 채팅 ID (search_scope="current_chat"일 때 필수)
            page_size: 페이지 크기 (기본 50)
            max_results: 최대 결과 수 (기본 500)

        Returns:
            검색 결과
        """
        try:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }

            search_results = []
            total_searched = 0

            async with httpx.AsyncClient() as client:
                if search_scope == "current_chat":
                    # 특정 채팅방 검색
                    if not chat_id:
                        return {"success": False, "message": "chat_id가 필요합니다"}

                    response = await client.get(
                        f"{self.graph_base_url}/chats/{chat_id}/messages?$top={page_size}",
                        headers=headers,
                        timeout=30.0
                    )

                    if response.status_code == 200:
                        data = response.json()
                        messages = data.get("value", [])

                        # 로컬에서 키워드 필터링
                        for msg in messages:
                            body = msg.get("body", {}).get("content", "")
                            # HTML 태그 제거
                            body_text = re.sub('<[^<]+?>', '', body)

                            if keyword.lower() in body_text.lower():
                                search_results.append({
                                    "chat_id": chat_id,
                                    "message_id": msg.get("id"),
                                    "from": msg.get("from", {}).get("user", {}).get("displayName", ""),
                                    "created": msg.get("createdDateTime", ""),
                                    "content": body_text[:200]  # 처음 200자만
                                })

                                if len(search_results) >= max_results:
                                    break

                        total_searched = len(messages)

                elif search_scope == "all_chats":
                    # 전체 채팅방 검색
                    # 먼저 채팅 목록 조회
                    chats_response = await client.get(
                        f"{self.graph_base_url}/me/chats",
                        headers=headers,
                        timeout=30.0
                    )

                    if chats_response.status_code != 200:
                        return {"success": False, "message": "채팅 목록 조회 실패"}

                    chats = chats_response.json().get("value", [])

                    # 각 채팅방의 메시지 검색
                    for chat in chats:
                        if len(search_results) >= max_results:
                            break

                        current_chat_id = chat.get("id")
                        messages_response = await client.get(
                            f"{self.graph_base_url}/chats/{current_chat_id}/messages?$top={page_size}",
                            headers=headers,
                            timeout=30.0
                        )

                        if messages_response.status_code == 200:
                            messages = messages_response.json().get("value", [])
                            total_searched += len(messages)

                            # 로컬에서 키워드 필터링
                            for msg in messages:
                                body = msg.get("body", {}).get("content", "")
                                body_text = re.sub('<[^<]+?>', '', body)

                                if keyword.lower() in body_text.lower():
                                    search_results.append({
                                        "chat_id": current_chat_id,
                                        "chat_topic": chat.get("topic", ""),
                                        "message_id": msg.get("id"),
                                        "from": msg.get("from", {}).get("user", {}).get("displayName", ""),
                                        "created": msg.get("createdDateTime", ""),
                                        "content": body_text[:200]
                                    })

                                    if len(search_results) >= max_results:
                                        break

            logger.info(f"✅ 키워드 '{keyword}' 검색 완료: {len(search_results)}개 결과")
            return {
                "success": True,
                "keyword": keyword,
                "search_scope": search_scope,
                "results": search_results,
                "count": len(search_results),
                "total_searched": total_searched,
                "max_results": max_results
            }

        except Exception as e:
            logger.error(f"❌ 메시지 검색 오류: {str(e)}", exc_info=True)
            return {"success": False, "message": f"오류 발생: {str(e)}"}
