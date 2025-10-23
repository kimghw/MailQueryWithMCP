"""Attachment downloader module for Microsoft Graph API"""

import base64
import logging
import os
from typing import Optional, Dict, Any, Literal
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

# Storage mode type
StorageMode = Literal["local", "onedrive", "sharepoint"]


class AttachmentDownloader:
    """첨부파일 다운로드 클래스"""

    def __init__(
        self,
        output_dir: str = "./attachments",
        storage_mode: Optional[StorageMode] = None,
        onedrive_folder_path: str = "/EmailAttachments",
        sharepoint_folder_url: Optional[str] = None
    ):
        """
        Initialize attachment downloader

        Args:
            output_dir: Directory to save attachments locally
            storage_mode: Storage mode - local, onedrive, or sharepoint
                         If None, reads from ATTACHMENT_STORAGE_MODE env var (default: local)
            onedrive_folder_path: OneDrive folder path for uploads
            sharepoint_folder_url: SharePoint folder URL for uploads
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Determine storage mode from parameter or environment variable
        if storage_mode is None:
            storage_mode = os.getenv("ATTACHMENT_STORAGE_MODE", "local")

        self.storage_mode: StorageMode = storage_mode
        self.onedrive_folder_path = onedrive_folder_path
        self.sharepoint_folder_url = sharepoint_folder_url

        logger.info(f"AttachmentDownloader initialized with storage_mode={self.storage_mode}")

        # Initialize OneDrive uploader if needed
        if self.storage_mode == "onedrive":
            try:
                from .onedrive_uploader import OneDriveUploader
                self.onedrive_uploader = OneDriveUploader(folder_path=self.onedrive_folder_path)
                logger.info("OneDrive uploader initialized")
            except ImportError:
                logger.error("OneDrive uploader not available. Falling back to local storage.")
                self.storage_mode = "local"

        # Initialize SharePoint uploader if needed
        if self.storage_mode == "sharepoint":
            if not self.sharepoint_folder_url:
                logger.warning("SharePoint URL not provided. Falling back to local storage.")
                self.storage_mode = "local"
            else:
                try:
                    from .sharepoint_uploader import SharePointUploader
                    self.sharepoint_uploader = SharePointUploader(folder_url=self.sharepoint_folder_url)
                    logger.info("SharePoint uploader initialized")
                except ImportError:
                    logger.error("SharePoint uploader not available. Falling back to local storage.")
                    self.storage_mode = "local"
    
    async def download_attachment(
        self,
        graph_client,
        message_id: str,
        attachment_id: str,
        access_token: Optional[str] = None
    ) -> Optional[bytes]:
        """
        Download attachment from Microsoft Graph API

        Args:
            graph_client: Microsoft Graph client instance
            message_id: Email message ID
            attachment_id: Attachment ID
            access_token: Access token for Graph API

        Returns:
            Attachment content as bytes or None if failed
        """
        try:
            # Microsoft Graph API를 통한 첨부파일 다운로드
            url = f"/me/messages/{message_id}/attachments/{attachment_id}"
            response = await graph_client.get(url, access_token=access_token)

            if response and 'contentBytes' in response:
                # Base64로 인코딩된 컨텐츠 디코드
                content = base64.b64decode(response['contentBytes'])
                logger.info(f"Successfully downloaded attachment {attachment_id}")
                return content
            else:
                logger.warning(f"No content found for attachment {attachment_id}")
                return None

        except Exception as e:
            logger.error(f"Failed to download attachment {attachment_id}: {str(e)}")
            return None
    
    def save_attachment(
        self, 
        content: bytes, 
        filename: str, 
        user_id: str,
        folder_name: Optional[str] = None
    ) -> Path:
        """
        Save attachment to disk
        
        Args:
            content: File content as bytes
            filename: Original filename
            user_id: User ID for directory organization
            folder_name: Optional folder name for organizing files
            
        Returns:
            Path to saved file
        """
        # 사용자별 디렉토리 생성
        user_dir = self.output_dir / user_id
        
        # 폴더명이 지정된 경우 해당 폴더에 저장
        if folder_name:
            safe_folder = self._sanitize_filename(folder_name)
            user_dir = user_dir / safe_folder
            
        user_dir.mkdir(parents=True, exist_ok=True)
        
        # 안전한 파일명 생성
        safe_filename = self._sanitize_filename(filename)
        file_path = user_dir / safe_filename
        
        # 중복 파일명 처리
        counter = 1
        while file_path.exists():
            name, ext = file_path.stem, file_path.suffix
            file_path = user_dir / f"{name}_{counter}{ext}"
            counter += 1
        
        # 파일 저장
        try:
            with open(file_path, 'wb') as f:
                f.write(content)
            logger.info(f"Saved attachment to {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Failed to save attachment {filename}: {str(e)}")
            raise
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename for safe storage

        Args:
            filename: Original filename

        Returns:
            Sanitized filename
        """
        # Use common utility function
        try:
            from .utils import sanitize_filename
            return sanitize_filename(filename, max_length=200)
        except ImportError:
            # Fallback to inline implementation if import fails
            # 위험한 문자 제거
            dangerous_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
            safe_name = filename

            for char in dangerous_chars:
                safe_name = safe_name.replace(char, '_')

            # 공백을 언더스코어로
            safe_name = safe_name.replace(' ', '_')

            # 연속된 언더스코어 정리
            import re
            safe_name = re.sub(r'_+', '_', safe_name)

            # 양 끝의 언더스코어 제거
            safe_name = safe_name.strip('_')

            # 빈 파일명 방지
            if not safe_name or safe_name.strip() == '':
                safe_name = 'unnamed_file'

            # 길이 제한 (255자)
            max_length = 200  # 여유를 두고 200자로 제한
            if len(safe_name) > max_length:
                name, ext = Path(safe_name).stem, Path(safe_name).suffix
                safe_name = name[:max_length - len(ext)] + ext

            return safe_name
    
    async def download_and_save(
        self,
        graph_client,
        message_id: str,
        attachment: Dict[str, Any],
        user_id: str,
        upload_to_onedrive: bool = False,
        email_date: Optional[Any] = None,
        sender_email: Optional[str] = None,
        email_subject: Optional[str] = None,
        access_token: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Download and save attachment in one step
        
        Args:
            graph_client: Microsoft Graph client
            message_id: Email message ID
            attachment: Attachment metadata dictionary
            user_id: User ID
            upload_to_onedrive: Upload to OneDrive after saving
            email_date: Email received date for folder organization
            sender_email: Sender email for folder organization
            
        Returns:
            Dictionary with file path and OneDrive info, or None if failed
        """
        attachment_id = attachment.get('id')
        attachment_name = attachment.get('name', 'unnamed')
        
        # $expand=attachments를 사용한 경우 contentBytes가 직접 포함됨
        if 'contentBytes' in attachment:
            logger.info(f"Attachment content included directly in response for {attachment_name}")
            try:
                content = base64.b64decode(attachment['contentBytes'])
            except Exception as e:
                logger.error(f"Failed to decode base64 content: {str(e)}")
                return None
        else:
            # contentBytes가 없는 경우 별도로 다운로드
            if not attachment_id:
                logger.error("No attachment ID provided and no content in response")
                return None
            
            # 다운로드
            content = await self.download_attachment(
                graph_client,
                message_id,
                attachment_id,
                access_token=access_token
            )
            
            if not content:
                return None
        
        # 저장
        try:
            # 메일제목_날짜_보낸사람 형식의 폴더명 생성
            folder_name = None
            if email_date and sender_email:
                from datetime import datetime
                
                # 날짜 객체 확인
                if not isinstance(email_date, datetime):
                    email_date = datetime.now()
                
                date_str = email_date.strftime("%Y%m%d_%H%M%S")  # 시분초 추가
                # 전체 이메일 주소 사용
                safe_email = self._sanitize_filename(sender_email if sender_email else 'unknown')
                safe_subject = self._sanitize_filename((email_subject or "NoSubject")[:50])
                
                folder_name = f"{safe_subject}_{date_str}_{safe_email}"
            
            file_path = self.save_attachment(
                content,
                attachment_name,
                user_id,
                folder_name
            )
            
            result = {
                "file_path": str(file_path),
                "file_name": attachment_name,
                "size": len(content),
                "storage_mode": self.storage_mode,
                "onedrive": None,
                "sharepoint": None
            }

            # Storage mode에 따라 업로드 처리
            if self.storage_mode == "onedrive" and hasattr(self, 'onedrive_uploader') and email_date:
                from datetime import datetime
                
                # 날짜 객체 확인
                if not isinstance(email_date, datetime):
                    email_date = datetime.now()
                
                # OneDrive 경로 설정 - 메일제목_날짜_보낸사람 형식
                date_str = email_date.strftime("%Y%m%d")
                # OneDrive용 전체 이메일 주소 사용
                safe_email = self.onedrive_uploader._sanitize_for_path(sender_email or "unknown")
                safe_subject = self.onedrive_uploader._sanitize_for_path((email_subject or "NoSubject")[:50])
                
                folder_name = f"{safe_subject}_{date_str}_{safe_email}"
                onedrive_path = f"/EmailAttachments/{user_id}/{folder_name}/{attachment_name}"
                
                # 업로드 실행
                upload_result = await self.onedrive_uploader.upload_file(
                    graph_client,
                    file_path,
                    onedrive_path,
                    access_token=access_token
                )
                
                if upload_result:
                    result["onedrive"] = {
                        "path": onedrive_path,
                        "webUrl": upload_result.get("webUrl"),
                        "id": upload_result.get("id"),
                        "name": upload_result.get("name")
                    }
                    logger.info(f"Uploaded to OneDrive: {onedrive_path}")
                else:
                    logger.warning(f"Failed to upload to OneDrive: {attachment_name}")

            # SharePoint 업로드
            elif self.storage_mode == "sharepoint" and hasattr(self, 'sharepoint_uploader'):
                try:
                    upload_result = await self.sharepoint_uploader.upload_file(
                        file_path=file_path,
                        folder_name=folder_name,
                        user_id=user_id
                    )

                    if upload_result and upload_result.get("success"):
                        result["sharepoint"] = {
                            "uploaded": True,
                            "folder_url": self.sharepoint_folder_url,
                            "message": upload_result.get("message")
                        }
                        logger.info(f"Uploaded to SharePoint: {attachment_name}")
                    else:
                        logger.warning(f"Failed to upload to SharePoint: {attachment_name}")
                        result["sharepoint"] = {"uploaded": False, "error": upload_result.get("error")}
                except Exception as e:
                    logger.error(f"SharePoint upload error: {str(e)}")
                    result["sharepoint"] = {"uploaded": False, "error": str(e)}

            return result
            
        except Exception as e:
            logger.error(f"Failed to save attachment: {str(e)}")
            return None