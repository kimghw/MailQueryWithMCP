"""Email content saver module for saving emails as text files"""

import re
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime
from html.parser import HTMLParser
from io import StringIO
try:
    from .onedrive_uploader import OneDriveUploader
except ImportError:
    OneDriveUploader = None

logger = logging.getLogger(__name__)


class HTMLTextExtractor(HTMLParser):
    """HTML을 텍스트로 변환하는 파서"""
    
    def __init__(self):
        super().__init__()
        self.text = StringIO()
        self.skip = False
        self.skip_tags = ['script', 'style', 'meta', 'link']
    
    def handle_starttag(self, tag, attrs):
        if tag in self.skip_tags:
            self.skip = True
        elif tag in ['p', 'div', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            self.text.write('\n')
    
    def handle_endtag(self, tag):
        if tag in self.skip_tags:
            self.skip = False
    
    def handle_data(self, data):
        if not self.skip:
            text = data.strip()
            if text:
                self.text.write(text + ' ')
    
    def get_text(self):
        raw_text = self.text.getvalue()
        # 중복 공백 및 줄바꿈 정리
        lines = [line.strip() for line in raw_text.split('\n')]
        lines = [line for line in lines if line]
        return '\n'.join(lines)


class EmailSaver:
    """이메일 내용을 텍스트 파일로 저장하는 클래스"""
    
    def __init__(self, output_dir: str = "./emails", enable_onedrive: bool = False):
        """
        Initialize email saver
        
        Args:
            output_dir: Directory to save email text files
            enable_onedrive: Enable OneDrive upload functionality
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.enable_onedrive = enable_onedrive
        if enable_onedrive:
            self.onedrive_uploader = OneDriveUploader()
    
    def html_to_text(self, html_content: str) -> str:
        """
        Convert HTML content to plain text
        
        Args:
            html_content: HTML string
            
        Returns:
            Plain text extracted from HTML
        """
        if not html_content:
            return ""
        
        # HTML 파서 사용
        parser = HTMLTextExtractor()
        parser.feed(html_content)
        text = parser.get_text()
        
        # 추가 정리
        # URL 패턴 간소화
        text = re.sub(r'https?://\S+', '[URL]', text)
        
        # 이메일 주소 패턴 보존
        # text = re.sub(r'\S+@\S+\.\S+', '[EMAIL]', text)
        
        return text
    
    async def save_email_as_text(
        self,
        email_data: Dict[str, Any],
        user_id: str,
        include_headers: bool = True,
        save_html: bool = False,
        upload_to_onedrive: bool = False,
        graph_client: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Save email content as text file
        
        Args:
            email_data: Email data dictionary from Graph API
            user_id: User ID for directory organization
            include_headers: Include email headers in the file
            save_html: Also save HTML version
            upload_to_onedrive: Upload to OneDrive after saving
            graph_client: Microsoft Graph client for OneDrive upload
            
        Returns:
            Dictionary with file paths and OneDrive info
        """
        # 사용자별 디렉토리 생성
        user_dir = self.output_dir / user_id
        user_dir.mkdir(exist_ok=True)
        
        # 메일 정보 추출
        email_id = email_data.get('id', 'unknown')
        subject = email_data.get('subject', 'No Subject')
        received_time = email_data.get('received_date_time', datetime.now())
        
        # 발신자 정보
        sender_info = self._extract_sender_info(email_data)
        
        # 파일명 생성 (안전한 파일명) - 메일제목_날짜시간_보낸사람 형식
        safe_subject = self._sanitize_filename(subject[:50])
        date_str = received_time.strftime('%Y%m%d_%H%M%S')  # 시분초 추가
        # 전체 이메일 주소 사용
        safe_email = self._sanitize_filename(sender_info['email'] if sender_info['email'] else 'unknown')
        
        folder_name = f"{safe_subject}_{date_str}_{safe_email}"
        
        # 메일별 디렉토리 생성
        email_dir = user_dir / folder_name
        email_dir.mkdir(exist_ok=True)
        
        # 본문 추출
        body_content = self._extract_body_content(email_data)
        
        # 텍스트 파일 내용 구성
        text_content = self._compose_email_text(
            email_data,
            sender_info,
            body_content,
            include_headers,
            None  # attachment_paths는 나중에 추가
        )
        
        # 텍스트 파일 저장 (중복 시 순번 추가)
        text_file = email_dir / "email_content.txt"
        counter = 1
        while text_file.exists():
            text_file = email_dir / f"email_content_{counter}.txt"
            counter += 1
            
        try:
            with open(text_file, 'w', encoding='utf-8') as f:
                f.write(text_content)
            logger.info(f"Saved email content to {text_file}")
            
            # HTML 버전도 저장 (선택사항)
            if save_html and email_data.get('body', {}).get('content'):
                html_file = email_dir / "email_content.html"
                counter = 1
                while html_file.exists():
                    html_file = email_dir / f"email_content_{counter}.html"
                    counter += 1
                    
                with open(html_file, 'w', encoding='utf-8') as f:
                    f.write(email_data['body']['content'])
                logger.info(f"Saved HTML version to {html_file}")
            
            # 메타데이터 저장
            self._save_metadata(email_dir, email_data, email_id)
            
            result = {
                "text_file": text_file,
                "html_file": html_file if save_html and email_data.get('body', {}).get('content') else None,
                "email_dir": email_dir,
                "onedrive": None
            }
            
            # OneDrive 업로드
            if upload_to_onedrive and self.enable_onedrive and graph_client:
                import asyncio
                
                # 메일 파일들 수집
                files_to_upload = [text_file]
                if result["html_file"]:
                    files_to_upload.append(result["html_file"])
                
                # 날짜와 발신자 정보
                email_date = email_data.get('received_date_time', datetime.now())
                sender_email = sender_info['email']
                
                # 비동기 함수 호출을 위한 태스크 생성
                try:
                    # 비동기 컨텍스트에서 실행
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # 이미 루프가 실행 중이면 태스크 생성
                        upload_task = asyncio.create_task(
                            self.onedrive_uploader.upload_email_with_attachments(
                                graph_client,
                                text_file,
                                [],  # 첨부파일은 별도 처리
                                user_id,
                                email_date,
                                sender_email,
                                subject,  # 메일 제목 추가
                                access_token
                            )
                        )
                        upload_result = await upload_task
                    else:
                        # 루프가 실행 중이 아니면 run_until_complete 사용
                        upload_result = loop.run_until_complete(
                            self.onedrive_uploader.upload_email_with_attachments(
                                graph_client,
                                text_file,
                                [],
                                user_id,
                                email_date,
                                sender_email,
                                subject
                            )
                        )
                except RuntimeError as e:
                    logger.warning(f"Failed to upload to OneDrive (async issue): {str(e)}")
                    upload_result = None
                
                result["onedrive"] = upload_result
                
                if upload_result and upload_result.get("email"):
                    logger.info(f"Uploaded email to OneDrive: {upload_result['email']['path']}")
                else:
                    logger.warning("Failed to upload email to OneDrive")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to save email: {str(e)}")
            raise
    
    def _extract_sender_info(self, email_data: Dict[str, Any]) -> Dict[str, str]:
        """발신자 정보 추출"""
        sender_info = {
            'name': 'Unknown',
            'email': 'unknown@email.com'
        }
        
        # from 필드 우선
        if email_data.get('from_address'):
            sender_info['email'] = email_data['from_address'].get('emailAddress', {}).get('address', '')
            sender_info['name'] = email_data['from_address'].get('emailAddress', {}).get('name', '')
        # sender 필드 확인
        elif email_data.get('sender'):
            sender_info['email'] = email_data['sender'].get('emailAddress', {}).get('address', '')
            sender_info['name'] = email_data['sender'].get('emailAddress', {}).get('name', '')
        
        return sender_info
    
    def _extract_body_content(self, email_data: Dict[str, Any]) -> str:
        """본문 내용 추출 및 변환"""
        # body 필드가 있는 경우
        if email_data.get('body') and email_data['body'].get('content'):
            content_type = email_data['body'].get('contentType', 'text')
            content = email_data['body']['content']
            
            if content_type.lower() == 'html':
                return self.html_to_text(content)
            else:
                return content
        
        # bodyPreview만 있는 경우
        elif email_data.get('body_preview'):
            return email_data['body_preview']
        
        return "No body content available"
    
    def _compose_email_text(
        self,
        email_data: Dict[str, Any],
        sender_info: Dict[str, str],
        body_content: str,
        include_headers: bool,
        attachment_paths: Optional[Dict[str, str]] = None
    ) -> str:
        """이메일 텍스트 내용 구성"""
        lines = []
        
        if include_headers:
            lines.append("=" * 80)
            lines.append(f"제목: {email_data.get('subject', 'No Subject')}")
            lines.append(f"발신자: {sender_info['name']} <{sender_info['email']}>")
            
            # 수신자 정보
            recipients = []
            for recipient in email_data.get('to_recipients', []):
                email_addr = recipient.get('emailAddress', {})
                recipients.append(f"{email_addr.get('name', '')} <{email_addr.get('address', '')}>")
            if recipients:
                lines.append(f"수신자: {', '.join(recipients)}")
            
            # 시간 정보
            received_time = email_data.get('received_date_time', datetime.now())
            lines.append(f"받은 시간: {received_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # 추가 정보
            lines.append(f"읽음 상태: {'읽음' if email_data.get('is_read', False) else '안읽음'}")
            lines.append(f"중요도: {email_data.get('importance', 'normal')}")
            lines.append(f"첨부파일: {'있음' if email_data.get('has_attachments', False) else '없음'}")
            
            if email_data.get('web_link'):
                lines.append(f"웹 링크: {email_data['web_link']}")
            
            lines.append("=" * 80)
            lines.append("")  # 빈 줄
        
        # 첨부파일 정보 추가
        if email_data.get('has_attachments') and email_data.get('attachments'):
            lines.append("첨부파일:")
            lines.append("-" * 40)
            for idx, attachment in enumerate(email_data.get('attachments', []), 1):
                att_name = attachment.get('name', f'attachment_{idx}')
                att_size = attachment.get('size', 0)
                att_id = attachment.get('id', '')
                lines.append(f"{idx}. {att_name} ({att_size:,} bytes)")
                
                # 로컬 파일 경로가 있으면 추가
                if attachment_paths and att_name in attachment_paths:
                    lines.append(f"   로컬 경로: {attachment_paths[att_name]}")
                
                # Graph API 접근 정보
                lines.append(f"   Graph API ID: {att_id}")
            lines.append("")  # 빈 줄
        
        # 본문 추가
        lines.append("본문:")
        lines.append("-" * 40)
        lines.append(body_content)
        
        return '\n'.join(lines)
    
    def _save_metadata(self, email_dir: Path, email_data: Dict[str, Any], email_id: str):
        """메타데이터를 별도 파일로 저장"""
        metadata = {
            'email_id': email_id,
            'subject': email_data.get('subject', ''),
            'received_time': str(email_data.get('received_date_time', '')),
            'has_attachments': email_data.get('has_attachments', False),
            'attachment_count': len(email_data.get('attachments', [])),
            'importance': email_data.get('importance', 'normal'),
            'is_read': email_data.get('is_read', False),
            'saved_at': datetime.now().isoformat()
        }
        
        metadata_file = email_dir / "metadata.txt"
        try:
            with open(metadata_file, 'w', encoding='utf-8') as f:
                for key, value in metadata.items():
                    f.write(f"{key}: {value}\n")
            logger.debug(f"Saved metadata to {metadata_file}")
        except Exception as e:
            logger.warning(f"Failed to save metadata: {str(e)}")
    
    def _sanitize_filename(self, filename: str) -> str:
        """안전한 파일명 생성"""
        # 위험한 문자 제거
        dangerous_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        safe_name = filename
        
        for char in dangerous_chars:
            safe_name = safe_name.replace(char, '_')
        
        # 공백을 언더스코어로
        safe_name = safe_name.replace(' ', '_')
        
        # 연속된 언더스코어 정리
        safe_name = re.sub(r'_+', '_', safe_name)
        
        # 양 끝의 언더스코어 제거
        safe_name = safe_name.strip('_')
        
        # 빈 파일명 방지
        if not safe_name or safe_name.strip() == '':
            safe_name = 'unnamed_email'
        
        return safe_name
    
    def create_email_summary(self, emails: list[Dict[str, Any]], user_id: str) -> Path:
        """여러 이메일의 요약 파일 생성"""
        user_dir = self.output_dir / user_id
        user_dir.mkdir(exist_ok=True)
        
        summary_file = user_dir / f"email_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        try:
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(f"Email Summary for {user_id}\n")
                f.write(f"Generated at: {datetime.now()}\n")
                f.write(f"Total emails: {len(emails)}\n")
                f.write("=" * 80 + "\n\n")
                
                for idx, email in enumerate(emails, 1):
                    f.write(f"{idx}. {email.get('subject', 'No Subject')}\n")
                    f.write(f"   From: {self._extract_sender_info(email)['email']}\n")
                    f.write(f"   Date: {email.get('received_date_time', 'Unknown')}\n")
                    f.write(f"   Attachments: {'Yes' if email.get('has_attachments') else 'No'}\n")
                    f.write("\n")
            
            logger.info(f"Created email summary: {summary_file}")
            return summary_file
            
        except Exception as e:
            logger.error(f"Failed to create summary: {str(e)}")
            raise