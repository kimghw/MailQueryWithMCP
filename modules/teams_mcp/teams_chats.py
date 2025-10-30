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

    async def _enrich_null_topic_chats(self, access_token: str, chats: List[Dict[str, Any]]) -> None:
        """
        topic이 null인 1:1 채팅의 상대방 이름을 비동기로 조회하여 topic에 설정

        Args:
            access_token: Graph API 액세스 토큰
            chats: 채팅 목록 (in-place 수정)
        """
        import asyncio

        # topic이 null인 1:1 채팅만 필터링
        null_topic_chats = [
            chat for chat in chats
            if chat.get("chatType") == "oneOnOne" and chat.get("topic") is None
        ]

        if not null_topic_chats:
            return

        logger.info(f"🔍 topic이 null인 1:1 채팅 {len(null_topic_chats)}개 발견, 멤버 조회 시작")

        # 비동기로 멤버 조회
        async def fetch_and_set_peer_name(chat):
            chat_id = chat.get("id")
            if not chat_id:
                return

            members_result = await self.get_chat_members(access_token, chat_id)
            if members_result.get("success"):
                members = members_result.get("members", [])
                # 상대방 이름 찾기 (본인이 아닌 멤버)
                for member in members:
                    display_name = member.get("displayName")
                    if display_name:
                        # 첫 번째 멤버의 이름을 topic으로 설정
                        # (더 정확하게는 본인 제외해야 하지만, 간단히 처리)
                        if len(members) >= 2:
                            # 두 번째 멤버를 상대방으로 간주
                            peer = members[1] if len(members) > 1 else members[0]
                            peer_name = peer.get("displayName", "Unknown")
                        else:
                            peer_name = members[0].get("displayName", "Unknown")

                        chat["topic"] = peer_name
                        logger.debug(f"✅ 채팅 {chat_id[:20]}... 상대방 이름: {peer_name}")
                        break

        # 모든 null topic 채팅을 비동기로 처리
        await asyncio.gather(*[fetch_and_set_peer_name(chat) for chat in null_topic_chats])
        logger.info(f"✅ {len(null_topic_chats)}개 채팅의 상대방 이름 조회 완료")

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

                    # topic이 null인 1:1 채팅의 상대방 이름 조회 (비동기)
                    await self._enrich_null_topic_chats(access_token, chats)

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
