"""
OneDrive Graph API Handler
Microsoft Graph API를 사용한 OneDrive 작업 처리
"""

import httpx
import base64
from typing import Optional, List, Dict, Any
from infra.core.logger import get_logger
from infra.core.database import get_database_manager
from infra.core.token_service import TokenService

logger = get_logger(__name__)


class OneDriveHandler:
    """OneDrive Graph API 작업 처리 핸들러"""

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

    async def list_files(
        self, user_id: str, folder_path: Optional[str] = None, search: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        OneDrive 파일 목록 조회

        Args:
            user_id: 사용자 ID
            folder_path: 폴더 경로 (기본값: 루트)
            search: 검색어

        Returns:
            파일 목록
        """
        try:
            access_token = await self._get_access_token(user_id)
            if not access_token:
                return {"success": False, "message": "액세스 토큰이 없습니다"}

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }

            # URL 구성
            if search:
                # 검색
                url = f"{self.graph_base_url}/me/drive/root/search(q='{search}')"
            elif folder_path:
                # 특정 폴더
                url = f"{self.graph_base_url}/me/drive/root:/{folder_path}:/children"
            else:
                # 루트 폴더
                url = f"{self.graph_base_url}/me/drive/root/children"

            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, timeout=30.0)

                if response.status_code == 200:
                    data = response.json()
                    files = data.get("value", [])
                    logger.info(f"✅ 파일 {len(files)}개 조회 성공")
                    return {"success": True, "files": files}
                else:
                    error_msg = f"파일 목록 조회 실패: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    return {"success": False, "message": error_msg}

        except Exception as e:
            error_msg = f"파일 목록 조회 오류: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "message": error_msg}

    async def read_file(self, user_id: str, file_path: str) -> Dict[str, Any]:
        """
        OneDrive 파일 읽기

        Args:
            user_id: 사용자 ID
            file_path: 파일 경로 또는 파일 ID

        Returns:
            파일 내용
        """
        try:
            access_token = await self._get_access_token(user_id)
            if not access_token:
                return {"success": False, "message": "액세스 토큰이 없습니다"}

            headers = {
                "Authorization": f"Bearer {access_token}",
            }

            # file_path가 ID인지 경로인지 확인
            if "/" in file_path or file_path.startswith("root"):
                # 경로
                download_url = f"{self.graph_base_url}/me/drive/root:/{file_path}:/content"
                metadata_url = f"{self.graph_base_url}/me/drive/root:/{file_path}"
            else:
                # ID
                download_url = f"{self.graph_base_url}/me/drive/items/{file_path}/content"
                metadata_url = f"{self.graph_base_url}/me/drive/items/{file_path}"

            async with httpx.AsyncClient() as client:
                # 메타데이터 조회
                meta_response = await client.get(metadata_url, headers=headers, timeout=30.0)
                if meta_response.status_code != 200:
                    error_msg = f"파일 메타데이터 조회 실패: {meta_response.status_code}"
                    logger.error(error_msg)
                    return {"success": False, "message": error_msg}

                meta_data = meta_response.json()
                file_name = meta_data.get("name", "unknown")
                file_size = meta_data.get("size", 0)
                mime_type = meta_data.get("file", {}).get("mimeType", "application/octet-stream")

                # 파일 다운로드
                content_response = await client.get(download_url, headers=headers, timeout=60.0)

                if content_response.status_code == 200:
                    # 텍스트 파일인 경우
                    if mime_type.startswith("text/") or mime_type in [
                        "application/json",
                        "application/xml",
                        "application/javascript",
                    ]:
                        content = content_response.text
                    else:
                        # 바이너리 파일은 base64 인코딩
                        content = base64.b64encode(content_response.content).decode("utf-8")
                        content = f"[Base64 Encoded]\n{content}"

                    logger.info(f"✅ 파일 읽기 성공: {file_name}")
                    return {
                        "success": True,
                        "content": content,
                        "file_name": file_name,
                        "file_size": file_size,
                        "mime_type": mime_type,
                    }
                else:
                    error_msg = f"파일 다운로드 실패: {content_response.status_code}"
                    logger.error(error_msg)
                    return {"success": False, "message": error_msg}

        except Exception as e:
            error_msg = f"파일 읽기 오류: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "message": error_msg}

    async def write_file(
        self, user_id: str, file_path: str, content: str, overwrite: bool = True,
        content_type: Optional[str] = None, is_binary: bool = False
    ) -> Dict[str, Any]:
        """
        OneDrive 파일 쓰기

        Args:
            user_id: 사용자 ID
            file_path: 파일 경로
            content: 파일 내용 (텍스트 또는 base64 인코딩된 바이너리)
            overwrite: 덮어쓰기 여부
            content_type: MIME 타입 (자동 감지 시 None)
            is_binary: 바이너리 파일 여부

        Returns:
            파일 쓰기 결과
        """
        try:
            access_token = await self._get_access_token(user_id)
            if not access_token:
                return {"success": False, "message": "액세스 토큰이 없습니다"}

            # Content-Type 자동 감지
            if not content_type:
                import mimetypes
                content_type, _ = mimetypes.guess_type(file_path)
                if not content_type:
                    content_type = "application/octet-stream"

            # 바이너리 파일 처리
            if is_binary:
                # base64 디코딩
                import base64
                try:
                    file_content = base64.b64decode(content)
                except Exception as e:
                    logger.error(f"Base64 디코딩 실패: {e}")
                    return {"success": False, "message": f"Base64 디코딩 실패: {e}"}
            else:
                # 텍스트 파일
                file_content = content.encode("utf-8")

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": content_type
            }

            # URL 구성
            url = f"{self.graph_base_url}/me/drive/root:/{file_path}:/content"
            if not overwrite:
                url += "?@microsoft.graph.conflictBehavior=fail"

            async with httpx.AsyncClient() as client:
                response = await client.put(
                    url, headers=headers, content=file_content, timeout=120.0
                )

                if response.status_code in [200, 201]:
                    data = response.json()
                    file_id = data.get("id")
                    file_name = data.get("name")
                    web_url = data.get("webUrl")
                    logger.info(f"✅ 파일 쓰기 성공: {file_name} ({content_type})")
                    return {
                        "success": True,
                        "file_id": file_id,
                        "file_name": file_name,
                        "web_url": web_url,
                        "size": len(file_content)
                    }
                else:
                    error_msg = f"파일 쓰기 실패: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    return {"success": False, "message": error_msg}

        except Exception as e:
            error_msg = f"파일 쓰기 오류: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "message": error_msg}

    async def delete_file(self, user_id: str, file_path: str) -> Dict[str, Any]:
        """
        OneDrive 파일 삭제

        Args:
            user_id: 사용자 ID
            file_path: 파일 경로 또는 파일 ID

        Returns:
            삭제 결과
        """
        try:
            access_token = await self._get_access_token(user_id)
            if not access_token:
                return {"success": False, "message": "액세스 토큰이 없습니다"}

            headers = {
                "Authorization": f"Bearer {access_token}",
            }

            # file_path가 ID인지 경로인지 확인
            if "/" in file_path or file_path.startswith("root"):
                # 경로
                url = f"{self.graph_base_url}/me/drive/root:/{file_path}"
            else:
                # ID
                url = f"{self.graph_base_url}/me/drive/items/{file_path}"

            async with httpx.AsyncClient() as client:
                response = await client.delete(url, headers=headers, timeout=30.0)

                if response.status_code == 204:
                    logger.info(f"✅ 파일 삭제 성공: {file_path}")
                    return {"success": True, "message": "파일이 성공적으로 삭제되었습니다"}
                else:
                    error_msg = f"파일 삭제 실패: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    return {"success": False, "message": error_msg}

        except Exception as e:
            error_msg = f"파일 삭제 오류: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "message": error_msg}

    async def create_folder(
        self, user_id: str, folder_path: str, parent_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        OneDrive 폴더 생성

        Args:
            user_id: 사용자 ID
            folder_path: 폴더 이름
            parent_path: 부모 폴더 경로 (기본값: 루트)

        Returns:
            폴더 생성 결과
        """
        try:
            access_token = await self._get_access_token(user_id)
            if not access_token:
                return {"success": False, "message": "액세스 토큰이 없습니다"}

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }

            # URL 구성
            if parent_path:
                url = f"{self.graph_base_url}/me/drive/root:/{parent_path}:/children"
            else:
                url = f"{self.graph_base_url}/me/drive/root/children"

            body = {"name": folder_path, "folder": {}, "@microsoft.graph.conflictBehavior": "fail"}

            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=body, timeout=30.0)

                if response.status_code == 201:
                    data = response.json()
                    folder_id = data.get("id")
                    folder_name = data.get("name")
                    logger.info(f"✅ 폴더 생성 성공: {folder_name}")
                    return {"success": True, "folder_id": folder_id, "folder_name": folder_name}
                else:
                    error_msg = f"폴더 생성 실패: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    return {"success": False, "message": error_msg}

        except Exception as e:
            error_msg = f"폴더 생성 오류: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "message": error_msg}
