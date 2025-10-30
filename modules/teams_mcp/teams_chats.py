"""
Teams Chats
Teams 채팅 목록 조회 기능
"""

import httpx
from typing import Optional, List, Dict, Any
from infra.core.logger import get_logger

logger = get_logger(__name__)


class TeamsChats:
    """Teams 채팅 목록 관리"""

    def __init__(self, graph_base_url: str = "https://graph.microsoft.com/v1.0"):
        self.graph_base_url = graph_base_url

    async def list_chats(
        self,
        access_token: str,
        sort_by: str = "recent",
        limit: Optional[int] = None,
        filter_by_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        사용자의 채팅 목록 조회 (1:1 및 그룹 채팅)

        Args:
            access_token: Graph API 액세스 토큰
            sort_by: 정렬 방식 ("recent", "name", "type") - 기본값: "recent"
            limit: 최대 조회 개수 (None이면 전체)
            filter_by_name: 이름 필터 (Optional)

        Returns:
            채팅 목록
        """
        try:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.graph_base_url}/me/chats",
                    headers=headers,
                    timeout=30.0
                )

                if response.status_code == 200:
                    data = response.json()
                    chats = data.get("value", [])
                    logger.info(f"✅ 채팅 {len(chats)}개 조회 성공")

                    # 필터링 (이름) - topic None 방어
                    if filter_by_name:
                        needle = (filter_by_name or "").lower()
                        filtered = []
                        for chat in chats:
                            topic_value = (chat.get("topic") or "").lower()
                            if needle in topic_value:
                                filtered.append(chat)
                        chats = filtered

                    # 정렬
                    if sort_by == "recent":
                        chats.sort(
                            key=lambda x: x.get("lastUpdatedDateTime", ""),
                            reverse=True
                        )
                    elif sort_by == "name":
                        chats.sort(
                            key=lambda x: (x.get("topic") or "").lower()
                        )
                    elif sort_by == "type":
                        chats.sort(
                            key=lambda x: x.get("chatType", "")
                        )

                    # 제한
                    if limit and limit > 0:
                        chats = chats[:limit]

                    return {
                        "success": True,
                        "chats": chats,
                        "count": len(chats),
                        "sort_by": sort_by,
                        "limit": limit,
                        "filter": filter_by_name
                    }
                else:
                    error_msg = f"채팅 목록 조회 실패: {response.status_code}"
                    logger.error(error_msg)
                    return {"success": False, "message": error_msg, "status_code": response.status_code}

        except Exception as e:
            logger.error(f"❌ 채팅 목록 조회 오류: {str(e)}", exc_info=True)
            return {"success": False, "message": f"오류 발생: {str(e)}"}

    async def get_chat_members(self, access_token: str, chat_id: str) -> Dict[str, Any]:
        """
        특정 채팅의 멤버 목록 조회

        Args:
            access_token: Graph API 액세스 토큰
            chat_id: 채팅 ID

        Returns:
            { success, members | message, status_code }
        """
        try:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.graph_base_url}/chats/{chat_id}/members",
                    headers=headers,
                    timeout=30.0
                )

                if response.status_code == 200:
                    data = response.json()
                    members = data.get("value", [])
                    return {"success": True, "members": members, "count": len(members)}
                else:
                    error_msg = f"멤버 조회 실패: {response.status_code}"
                    logger.error(error_msg)
                    return {"success": False, "message": error_msg, "status_code": response.status_code}

        except Exception as e:
            logger.error(f"❌ 멤버 조회 오류: {str(e)}", exc_info=True)
            return {"success": False, "message": f"오류 발생: {str(e)}"}
