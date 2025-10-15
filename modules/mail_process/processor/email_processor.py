"""메일 처리 파이프라인 메인 클래스"""

import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

from .process_options import ProcessOptions
from .result import EmailProcessResult, AttachmentResult, BatchProcessResult
from .handlers.email_saver import EmailSaver
from .handlers.attachment_handler import AttachmentHandler
from .handlers.text_converter import TextConverter
from ..utils import sanitize_filename

logger = logging.getLogger(__name__)


class EmailProcessor:
    """메일 처리 파이프라인"""

    def __init__(self, options: ProcessOptions):
        """
        Args:
            options: 처리 옵션
        """
        options.validate()
        self.options = options

        # 핸들러 초기화
        self.email_saver = EmailSaver(options.output_dir) if options.save_email else None
        self.attachment_handler = AttachmentHandler(options.output_dir) if options.save_attachments else None
        self.text_converter = TextConverter() if options.convert_to_text else None

    async def process_email(
        self,
        graph_client,
        email_data: Dict[str, Any]
    ) -> EmailProcessResult:
        """
        단일 메일 처리

        Args:
            graph_client: Microsoft Graph client
            email_data: 메일 데이터

        Returns:
            처리 결과
        """
        # 기본 정보 추출
        email_id = self._get_field(email_data, 'id', 'unknown')
        subject = self._get_field(email_data, 'subject', 'No Subject')
        sender_info = self._extract_sender_info(email_data)
        received_time = self._get_field(email_data, 'received_date_time', datetime.now())

        # 결과 객체 초기화
        result = EmailProcessResult(
            email_id=email_id,
            subject=subject,
            sender=sender_info['email'],
            received_datetime=received_time.isoformat() if isinstance(received_time, datetime) else str(received_time)
        )

        try:
            # 메일별 디렉토리 생성
            email_dir = self._create_email_directory(
                email_data,
                sender_info,
                received_time
            )
            result.email_dir = email_dir

            # 1. 메일 본문 저장
            if self.options.save_email:
                await self._save_email_content(email_data, email_dir, result)

            # 2. 첨부파일 처리
            if self.options.save_attachments and self._get_field(email_data, 'has_attachments', False):
                await self._process_attachments(
                    graph_client,
                    email_data,
                    email_dir,
                    result
                )

            logger.info(f"✅ Successfully processed email: {subject[:50]}")

        except Exception as e:
            error_msg = f"Error processing email {email_id}: {str(e)}"
            logger.error(error_msg)
            result.errors.append(error_msg)

        return result

    async def process_emails_batch(
        self,
        graph_client,
        emails: List[Dict[str, Any]]
    ) -> BatchProcessResult:
        """
        여러 메일 일괄 처리

        Args:
            graph_client: Microsoft Graph client
            emails: 메일 데이터 리스트

        Returns:
            일괄 처리 결과
        """
        total = len(emails)
        results = []
        successful = 0
        failed = 0

        logger.info(f"📧 Processing {total} emails...")

        for idx, email_data in enumerate(emails, 1):
            logger.info(f"Processing {idx}/{total}: {self._get_field(email_data, 'subject', 'No Subject')[:50]}")

            result = await self.process_email(graph_client, email_data)
            results.append(result)

            if result.has_errors():
                failed += 1
            else:
                successful += 1

        batch_result = BatchProcessResult(
            total_emails=total,
            successful=successful,
            failed=failed,
            results=results
        )

        logger.info(f"✅ Batch processing complete: {successful}/{total} successful")
        return batch_result

    def _create_email_directory(
        self,
        email_data: Dict[str, Any],
        sender_info: Dict[str, str],
        received_time
    ) -> Path:
        """메일별 디렉토리 생성"""
        user_dir = self.options.output_dir / self.options.user_id

        if not self.options.create_subfolder_per_email:
            user_dir.mkdir(parents=True, exist_ok=True)
            return user_dir

        # 폴더명 생성
        if not isinstance(received_time, datetime):
            received_time = datetime.now()

        folder_name = self.options.subfolder_format.format(
            subject=sanitize_filename(self._get_field(email_data, 'subject', 'NoSubject')[:50]),
            date=received_time.strftime('%Y%m%d_%H%M%S'),
            sender=sanitize_filename(sender_info['email'])
        )

        email_dir = user_dir / folder_name
        email_dir.mkdir(parents=True, exist_ok=True)

        return email_dir

    async def _save_email_content(
        self,
        email_data: Dict[str, Any],
        email_dir: Path,
        result: EmailProcessResult
    ):
        """메일 본문 저장"""
        try:
            save_result = await self.email_saver.save_email(
                email_data,
                email_dir,
                include_headers=self.options.include_email_headers,
                save_html=self.options.save_html_version
            )

            result.email_saved = True
            result.email_text_path = save_result['text_path']
            result.email_html_path = save_result['html_path']

        except Exception as e:
            error_msg = f"Failed to save email content: {str(e)}"
            logger.error(error_msg)
            result.errors.append(error_msg)

    async def _process_attachments(
        self,
        graph_client,
        email_data: Dict[str, Any],
        email_dir: Path,
        result: EmailProcessResult
    ):
        """첨부파일 처리"""
        attachments = self._get_field(email_data, 'attachments', [])
        if not attachments:
            return

        try:
            # 첨부파일 다운로드 및 저장
            saved_files = await self.attachment_handler.download_and_save_attachments(
                graph_client,
                self._get_field(email_data, 'id'),
                attachments,
                email_dir
            )

            # 텍스트 변환 (옵션)
            for saved_file in saved_files:
                att_result = AttachmentResult(
                    original_name=saved_file['name'],
                    saved_path=saved_file['path'],
                    size=saved_file['size']
                )

                if saved_file['error']:
                    result.errors.append(f"Attachment error: {saved_file['error']}")

                # 텍스트 변환
                if self.options.convert_to_text and saved_file['path']:
                    self._convert_attachment_to_text(saved_file['path'], att_result)

                result.attachments.append(att_result)

        except Exception as e:
            error_msg = f"Failed to process attachments: {str(e)}"
            logger.error(error_msg)
            result.errors.append(error_msg)

    def _convert_attachment_to_text(
        self,
        file_path: Path,
        att_result: AttachmentResult
    ):
        """첨부파일을 텍스트로 변환"""
        try:
            convert_result = self.text_converter.convert_file_to_text(
                file_path,
                save_text=self.options.save_converted_text,
                delete_original=self.options.delete_original_after_convert
            )

            if convert_result['success']:
                att_result.converted = True
                att_result.converted_text_path = convert_result['text_path']

                if self.options.return_text_content:
                    att_result.converted_text_content = convert_result['text_content']

                logger.info(f"✅ Converted {file_path.name} to text")
            else:
                att_result.conversion_error = convert_result['error']
                logger.warning(f"⚠️ Failed to convert {file_path.name}: {convert_result['error']}")

        except Exception as e:
            error_msg = f"Error converting {file_path.name}: {str(e)}"
            logger.error(error_msg)
            att_result.conversion_error = error_msg

    def _extract_sender_info(self, email_data: Dict[str, Any]) -> Dict[str, str]:
        """발신자 정보 추출"""
        sender_info = {
            'name': 'Unknown',
            'email': 'unknown@email.com'
        }

        if hasattr(email_data, 'from_address'):
            if email_data.from_address and isinstance(email_data.from_address, dict):
                email_addr = email_data.from_address.get('emailAddress', {})
                sender_info['email'] = email_addr.get('address', '')
                sender_info['name'] = email_addr.get('name', '')
            return sender_info

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

    def _get_field(self, email_data: Dict[str, Any], field_name: str, default: Any = None) -> Any:
        """필드 값 추출"""
        if hasattr(email_data, field_name):
            return getattr(email_data, field_name, default)

        if isinstance(email_data, dict):
            if field_name in email_data:
                return email_data.get(field_name, default)

            camel_case = ''.join(word.capitalize() if i > 0 else word for i, word in enumerate(field_name.split('_')))
            if camel_case in email_data:
                return email_data.get(camel_case, default)

        return default
