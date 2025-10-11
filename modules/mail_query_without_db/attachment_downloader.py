"""Attachment downloader module for Microsoft Graph API"""

import base64
import logging
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime
# OneDrive functionality removed - not implemented

logger = logging.getLogger(__name__)


class AttachmentDownloader:
    """첨부파일 다운로드 클래스"""
    
    def __init__(self, output_dir: str = "./attachments", enable_onedrive: bool = False):
        """
        Initialize attachment downloader
        
        Args:
            output_dir: Directory to save attachments
            enable_onedrive: Enable OneDrive upload functionality
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.enable_onedrive = enable_onedrive
        if enable_onedrive:
            self.onedrive_uploader = OneDriveUploader()
    
    async def download_attachment(
        self, 
        graph_client, 
        message_id: str, 
        attachment_id: str
    ) -> Optional[bytes]:
        """
        Download attachment from Microsoft Graph API
        
        Args:
            graph_client: Microsoft Graph client instance
            message_id: Email message ID
            attachment_id: Attachment ID
            
        Returns:
            Attachment content as bytes or None if failed
        """
        try:
            # Microsoft Graph API를 통한 첨부파일 다운로드
            url = f"/me/messages/{message_id}/attachments/{attachment_id}"
            response = await graph_client.get(url)
            
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
            from .core.utils import sanitize_filename
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
                attachment_id
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
                "file_path": file_path,
                "file_name": attachment_name,
                "size": len(content),
                "onedrive": None
            }
            
            # OneDrive 업로드 (옵션)
            if upload_to_onedrive and self.enable_onedrive and email_date:
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
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to save attachment: {str(e)}")
            return None