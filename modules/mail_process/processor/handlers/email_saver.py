"""이메일 본문 저장 핸들러"""

import logging
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from html.parser import HTMLParser
from io import StringIO

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
        lines = [line.strip() for line in raw_text.split('\n')]
        lines = [line for line in lines if line]
        return '\n'.join(lines)


class EmailSaver:
    """이메일 본문 저장 핸들러"""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def save_email(
        self,
        email_data: Dict[str, Any],
        email_dir: Path,
        include_headers: bool = True,
        save_html: bool = False
    ) -> Dict[str, Optional[Path]]:
        """
        이메일 저장

        Returns:
            {
                'text_path': Path,
                'html_path': Path or None,
                'metadata_path': Path
            }
        """
        email_dir.mkdir(parents=True, exist_ok=True)

        result = {
            'text_path': None,
            'html_path': None,
            'metadata_path': None
        }

        try:
            # 발신자 정보
            sender_info = self._extract_sender_info(email_data)

            # 본문 내용
            body_content = self._extract_body_content(email_data)

            # 텍스트 파일 내용 구성
            text_content = self._compose_email_text(
                email_data,
                sender_info,
                body_content,
                include_headers
            )

            # 텍스트 파일 저장
            text_file = email_dir / "email_content.txt"
            text_file = self._get_unique_path(text_file)
            text_file.write_text(text_content, encoding='utf-8')
            result['text_path'] = text_file
            logger.info(f"Saved email text to {text_file}")

            # HTML 버전 저장 (옵션)
            if save_html and email_data.get('body', {}).get('content'):
                html_file = email_dir / "email_content.html"
                html_file = self._get_unique_path(html_file)
                html_file.write_text(
                    email_data['body']['content'],
                    encoding='utf-8'
                )
                result['html_path'] = html_file
                logger.info(f"Saved HTML version to {html_file}")

            # 메타데이터 저장
            metadata_path = self._save_metadata(email_dir, email_data)
            result['metadata_path'] = metadata_path

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

        # GraphMailItem 형식
        if hasattr(email_data, 'from_address'):
            if email_data.from_address and isinstance(email_data.from_address, dict):
                email_addr = email_data.from_address.get('emailAddress', {})
                sender_info['email'] = email_addr.get('address', '')
                sender_info['name'] = email_addr.get('name', '')
            return sender_info

        # Dict 형식
        if 'from_address' in email_data:
            from_addr = email_data['from_address']
            if isinstance(from_addr, dict):
                email_addr = from_addr.get('emailAddress', {})
                sender_info['email'] = email_addr.get('address', '')
                sender_info['name'] = email_addr.get('name', '')
        elif 'sender' in email_data:
            sender = email_data['sender']
            if isinstance(sender, dict):
                email_addr = sender.get('emailAddress', {})
                sender_info['email'] = email_addr.get('address', '')
                sender_info['name'] = email_addr.get('name', '')

        return sender_info

    def _extract_body_content(self, email_data: Dict[str, Any]) -> str:
        """본문 내용 추출"""
        # GraphMailItem 형식
        if hasattr(email_data, 'body'):
            body = email_data.body
            if isinstance(body, dict):
                content_type = body.get('contentType', 'text')
                content = body.get('content', '')

                if content_type == 'html':
                    return self._html_to_text(content)
                return content
            return ''

        # Dict 형식
        if 'body' in email_data:
            body = email_data['body']
            if isinstance(body, dict):
                content_type = body.get('contentType', 'text')
                content = body.get('content', '')

                if content_type == 'html':
                    return self._html_to_text(content)
                return content

        # body_preview fallback
        if hasattr(email_data, 'body_preview'):
            return email_data.body_preview or ''

        if 'body_preview' in email_data or 'bodyPreview' in email_data:
            return email_data.get('body_preview') or email_data.get('bodyPreview', '')

        return ''

    def _compose_email_text(
        self,
        email_data: Dict[str, Any],
        sender_info: Dict[str, str],
        body_content: str,
        include_headers: bool
    ) -> str:
        """텍스트 파일 내용 구성"""
        lines = []

        if include_headers:
            lines.append("=" * 70)
            lines.append("EMAIL CONTENT")
            lines.append("=" * 70)
            lines.append("")

            # 기본 정보
            subject = self._get_field(email_data, 'subject', 'No Subject')
            received_time = self._get_field(email_data, 'received_date_time', datetime.now())

            lines.append(f"Subject: {subject}")
            lines.append(f"From: {sender_info['name']} <{sender_info['email']}>")
            lines.append(f"Date: {received_time}")
            lines.append("")
            lines.append("-" * 70)
            lines.append("")

        # 본문
        lines.append(body_content)

        return '\n'.join(lines)

    def _save_metadata(self, email_dir: Path, email_data: Dict[str, Any]) -> Path:
        """메타데이터 JSON 저장"""
        metadata = {
            'id': self._get_field(email_data, 'id'),
            'subject': self._get_field(email_data, 'subject'),
            'from': self._extract_sender_info(email_data),
            'received_date_time': str(self._get_field(email_data, 'received_date_time')),
            'has_attachments': self._get_field(email_data, 'has_attachments', False),
        }

        metadata_file = email_dir / "metadata.json"
        metadata_file.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding='utf-8')

        return metadata_file

    def _html_to_text(self, html_content: str) -> str:
        """HTML을 텍스트로 변환"""
        if not html_content:
            return ""

        parser = HTMLTextExtractor()
        parser.feed(html_content)
        return parser.get_text()

    def _get_field(self, email_data: Dict[str, Any], field_name: str, default: Any = None) -> Any:
        """필드 값 추출 (GraphMailItem 또는 Dict 대응)"""
        # GraphMailItem 형식
        if hasattr(email_data, field_name):
            return getattr(email_data, field_name, default)

        # Dict 형식
        if isinstance(email_data, dict):
            # snake_case
            if field_name in email_data:
                return email_data.get(field_name, default)

            # camelCase 변환
            camel_case = ''.join(word.capitalize() if i > 0 else word for i, word in enumerate(field_name.split('_')))
            if camel_case in email_data:
                return email_data.get(camel_case, default)

        return default

    def _get_unique_path(self, file_path: Path) -> Path:
        """중복 파일명 처리"""
        if not file_path.exists():
            return file_path

        counter = 1
        while True:
            new_path = file_path.parent / f"{file_path.stem}_{counter}{file_path.suffix}"
            if not new_path.exists():
                return new_path
            counter += 1
