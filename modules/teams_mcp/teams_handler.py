"""
Teams Graph API Handler
Microsoft Graph API를 사용한 Teams 작업 처리
"""

import httpx
from typing import Optional, List, Dict, Any
from infra.core.logger import get_logger
from infra.core.database import get_database_manager
from infra.core.token_service import TokenService

logger = get_logger(__name__)

# 특별한 Teams Chat ID 상수
# 주의: 이 chat_id들은 teams_list_chats API에 나타나지 않지만 직접 사용 가능합니다
SPECIAL_CHAT_IDS = {
    "notes": "48:notes",  # Teams Notes 채팅 (개인 메모용)
}


class TeamsHandler:
    """Teams Graph API 작업 처리 핸들러"""

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

    async def list_chats(self, user_id: str) -> Dict[str, Any]:
        """
        사용자의 채팅 목록 조회 (1:1 및 그룹 채팅)

        Args:
            user_id: 사용자 ID

        Returns:
            채팅 목록
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
                    f"{self.graph_base_url}/me/chats",
                    headers=headers,
                    timeout=30.0
                )

                if response.status_code == 200:
                    data = response.json()
                    chats = data.get("value", [])
                    logger.info(f"✅ 채팅 {len(chats)}개 조회 성공")
                    return {
                        "success": True,
                        "chats": chats,
                        "count": len(chats)
                    }
                else:
                    error_msg = f"채팅 목록 조회 실패: {response.status_code}"
                    logger.error(error_msg)
                    return {"success": False, "message": error_msg, "status_code": response.status_code}

        except Exception as e:
            logger.error(f"❌ 채팅 목록 조회 오류: {str(e)}", exc_info=True)
            return {"success": False, "message": f"오류 발생: {str(e)}"}

    async def get_chat_messages(self, user_id: str, chat_id: str, limit: int = 50) -> Dict[str, Any]:
        """
        채팅의 메시지 목록 조회

        Args:
            user_id: 사용자 ID
            chat_id: 채팅 ID
            limit: 조회할 메시지 수 (기본 50)

        Returns:
            메시지 목록
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
                    f"{self.graph_base_url}/chats/{chat_id}/messages?$top={limit}",
                    headers=headers,
                    timeout=30.0
                )

                if response.status_code == 200:
                    data = response.json()
                    messages = data.get("value", [])
                    logger.info(f"✅ 메시지 {len(messages)}개 조회 성공")
                    return {
                        "success": True,
                        "messages": messages,
                        "count": len(messages)
                    }
                else:
                    error_msg = f"메시지 조회 실패: {response.status_code}"
                    logger.error(error_msg)
                    return {"success": False, "message": error_msg, "status_code": response.status_code}

        except Exception as e:
            logger.error(f"❌ 메시지 조회 오류: {str(e)}", exc_info=True)
            return {"success": False, "message": f"오류 발생: {str(e)}"}

    async def send_chat_message(self, user_id: str, chat_id: str, content: str, prefix: str = "[claude]") -> Dict[str, Any]:
        """
        채팅에 메시지 전송

        Args:
            user_id: 사용자 ID
            chat_id: 채팅 ID
            content: 메시지 내용
            prefix: 메시지 앞에 붙을 프리픽스 (기본값: '[claude]')

        Returns:
            전송 결과
        """
        try:
            access_token = await self._get_access_token(user_id)
            if not access_token:
                return {"success": False, "message": "액세스 토큰이 없습니다"}

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }

            # 메시지 페이로드 (프리픽스 추가)
            payload = {
                "body": {
                    "content": f"{prefix} {content}" if prefix else content
                }
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.graph_base_url}/chats/{chat_id}/messages",
                    headers=headers,
                    json=payload,
                    timeout=30.0
                )

                if response.status_code == 201:
                    data = response.json()
                    message_id = data.get("id")
                    logger.info(f"✅ 메시지 전송 성공: {message_id}")
                    return {
                        "success": True,
                        "message_id": message_id,
                        "data": data
                    }
                else:
                    error_msg = f"메시지 전송 실패: {response.status_code}"
                    logger.error(f"{error_msg} - {response.text}")
                    return {"success": False, "message": error_msg, "status_code": response.status_code}

        except Exception as e:
            logger.error(f"❌ 메시지 전송 오류: {str(e)}", exc_info=True)
            return {"success": False, "message": f"오류 발생: {str(e)}"}



