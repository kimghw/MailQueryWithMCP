"""
Teams Messages
Teams 메시지 조회 및 전송 기능
"""

import re
import httpx
from typing import Optional, Dict, Any
from infra.core.logger import get_logger

logger = get_logger(__name__)


class TeamsMessages:
    """Teams 메시지 조회 및 전송"""

    def __init__(self, graph_base_url: str = "https://graph.microsoft.com/v1.0"):
        self.graph_base_url = graph_base_url

    async def get_chat_messages(
        self,
        access_token: str,
        chat_id: str,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        채팅의 메시지 목록 조회

        Args:
            access_token: Graph API 액세스 토큰
            chat_id: 채팅 ID
            limit: 조회할 메시지 수 (기본 50)

        Returns:
            메시지 목록
        """
        try:
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

    async def send_chat_message(
        self,
        access_token: str,
        chat_id: str,
        content: str,
        prefix: str = "[claude]"
    ) -> Dict[str, Any]:
        """
        채팅에 메시지 전송

        Args:
            access_token: Graph API 액세스 토큰
            chat_id: 채팅 ID
            content: 메시지 내용
            prefix: 메시지 앞에 붙을 프리픽스 (기본값: '[claude]')

        Returns:
            전송 결과
        """
        try:
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
                        "chat_id": chat_id,
                        "data": data
                    }
                else:
                    error_msg = f"메시지 전송 실패: {response.status_code}"
                    logger.error(f"{error_msg} - {response.text}")
                    return {"success": False, "message": error_msg, "status_code": response.status_code}

        except Exception as e:
            logger.error(f"❌ 메시지 전송 오류: {str(e)}", exc_info=True)
            return {"success": False, "message": f"오류 발생: {str(e)}"}
