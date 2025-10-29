"""
Teams Graph API Handler
Microsoft Graph API를 사용한 Teams 작업 처리 (통합 핸들러)
"""

from typing import Optional, Dict, Any
from infra.core.logger import get_logger
from infra.core.token_service import TokenService

# 서브 모듈 import
from .teams_db_manager import TeamsDBManager
from .teams_chats import TeamsChats
from .teams_messages import TeamsMessages
from .teams_search import TeamsSearch

logger = get_logger(__name__)

# 특별한 Teams Chat ID 상수
# 주의: 이 chat_id들은 teams_list_chats API에 나타나지 않지만 직접 사용 가능합니다
SPECIAL_CHAT_IDS = {
    "notes": "48:notes",  # Teams Notes 채팅 (개인 메모용)
}


class TeamsHandler:
    """Teams Graph API 작업 처리 핸들러 (메인)"""

    def __init__(self):
        self.token_service = TokenService()
        self.graph_base_url = "https://graph.microsoft.com/v1.0"

        # 서브 모듈 초기화
        self.db_manager = TeamsDBManager()
        self.chats_manager = TeamsChats(self.graph_base_url)
        self.messages_manager = TeamsMessages(self.graph_base_url)
        self.search_manager = TeamsSearch(self.graph_base_url)

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

    # ========================================================================
    # 채팅 목록 관련
    # ========================================================================

    async def list_chats(
        self,
        user_id: str,
        sort_by: str = "recent",
        limit: Optional[int] = None,
        filter_by_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        사용자의 채팅 목록 조회 (1:1 및 그룹 채팅)

        Args:
            user_id: 사용자 ID
            sort_by: 정렬 방식 ("recent", "name", "type") - 기본값: "recent"
            limit: 최대 조회 개수 (None이면 전체)
            filter_by_name: 이름 필터 (Optional)

        Returns:
            채팅 목록
        """
        try:
            access_token = await self._get_access_token(user_id)
            if not access_token:
                return {"success": False, "message": "액세스 토큰이 없습니다"}

            # 채팅 목록 조회
            result = await self.chats_manager.list_chats(
                access_token, sort_by, limit, filter_by_name
            )

            # 성공 시 DB 동기화
            if result.get("success") and result.get("chats"):
                await self.db_manager.sync_chats_to_db(user_id, result["chats"])

            return result

        except Exception as e:
            logger.error(f"❌ 채팅 목록 조회 오류: {str(e)}", exc_info=True)
            return {"success": False, "message": f"오류 발생: {str(e)}"}

    # ========================================================================
    # 메시지 조회/전송
    # ========================================================================

    async def get_chat_messages(
        self,
        user_id: str,
        chat_id: Optional[str] = None,
        recipient_name: Optional[str] = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        채팅의 메시지 목록 조회

        Args:
            user_id: 사용자 ID
            chat_id: 채팅 ID (Optional)
            recipient_name: 상대방 이름 (chat_id가 없을 때 사용)
            limit: 조회할 메시지 수 (기본 50)

        Returns:
            메시지 목록
        """
        try:
            # chat_id 결정
            if not chat_id:
                if recipient_name:
                    # 이름으로 검색
                    chat_id = await self.db_manager.find_chat_by_name(user_id, recipient_name)
                    if not chat_id:
                        return {"success": False, "message": f"'{recipient_name}' 사용자를 찾을 수 없습니다"}
                else:
                    # 최근 대화 사용
                    chat_id = await self.db_manager.get_recent_chat_id(user_id)
                    if not chat_id:
                        # 기본값으로 Notes 사용
                        chat_id = "48:notes"
                        logger.info("ℹ️ chat_id 없음, 기본값 48:notes 사용")

            access_token = await self._get_access_token(user_id)
            if not access_token:
                return {"success": False, "message": "액세스 토큰이 없습니다"}

            return await self.messages_manager.get_chat_messages(access_token, chat_id, limit)

        except Exception as e:
            logger.error(f"❌ 메시지 조회 오류: {str(e)}", exc_info=True)
            return {"success": False, "message": f"오류 발생: {str(e)}"}

    async def send_chat_message(
        self,
        user_id: str,
        content: str,
        chat_id: Optional[str] = None,
        recipient_name: Optional[str] = None,
        prefix: str = "[claude]"
    ) -> Dict[str, Any]:
        """
        채팅에 메시지 전송

        Args:
            user_id: 사용자 ID
            content: 메시지 내용
            chat_id: 채팅 ID (Optional)
            recipient_name: 상대방 이름 (chat_id가 없을 때 사용)
            prefix: 메시지 앞에 붙을 프리픽스 (기본값: '[claude]')

        Returns:
            전송 결과
        """
        try:
            # chat_id 결정
            if not chat_id:
                if recipient_name:
                    # 이름으로 검색
                    chat_id = await self.db_manager.find_chat_by_name(user_id, recipient_name)
                    if not chat_id:
                        return {"success": False, "message": f"'{recipient_name}' 사용자를 찾을 수 없습니다"}
                else:
                    # 최근 대화 사용
                    chat_id = await self.db_manager.get_recent_chat_id(user_id)
                    if not chat_id:
                        # 기본값으로 Notes 사용
                        chat_id = "48:notes"
                        logger.info("ℹ️ chat_id 없음, 기본값 48:notes 사용")

            access_token = await self._get_access_token(user_id)
            if not access_token:
                return {"success": False, "message": "액세스 토큰이 없습니다"}

            # 메시지 전송
            result = await self.messages_manager.send_chat_message(
                access_token, chat_id, content, prefix
            )

            # 성공 시 DB 업데이트
            if result.get("success"):
                await self.db_manager.update_last_sent_at(user_id, chat_id)

            return result

        except Exception as e:
            logger.error(f"❌ 메시지 전송 오류: {str(e)}", exc_info=True)
            return {"success": False, "message": f"오류 발생: {str(e)}"}

    # ========================================================================
    # 메시지 검색
    # ========================================================================

    async def search_messages(
        self,
        user_id: str,
        keyword: str,
        search_scope: str = "current_chat",
        chat_id: Optional[str] = None,
        page_size: int = 50,
        max_results: int = 500
    ) -> Dict[str, Any]:
        """
        메시지 키워드 검색

        Args:
            user_id: 사용자 ID
            keyword: 검색 키워드
            search_scope: 검색 범위 ("current_chat" 또는 "all_chats")
            chat_id: 채팅 ID (search_scope="current_chat"일 때 필수)
            page_size: 페이지 크기 (기본 50)
            max_results: 최대 결과 수 (기본 500)

        Returns:
            검색 결과
        """
        try:
            access_token = await self._get_access_token(user_id)
            if not access_token:
                return {"success": False, "message": "액세스 토큰이 없습니다"}

            return await self.search_manager.search_messages(
                access_token, keyword, search_scope, chat_id, page_size, max_results
            )

        except Exception as e:
            logger.error(f"❌ 메시지 검색 오류: {str(e)}", exc_info=True)
            return {"success": False, "message": f"오류 발생: {str(e)}"}
