"""첨부파일 다운로드 및 저장 핸들러"""

import logging
import base64
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class AttachmentHandler:
    """첨부파일 다운로드 및 저장 핸들러"""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def download_and_save_attachments(
        self,
        graph_client,
        message_id: str,
        attachments: List[Dict[str, Any]],
        save_dir: Path
    ) -> List[Dict[str, Any]]:
        """
        첨부파일 다운로드 및 저장

        Returns:
            List of {
                'name': str,
                'path': Path,
                'size': int,
                'error': str or None
            }
        """
        save_dir.mkdir(parents=True, exist_ok=True)
        results = []

        for attachment in attachments:
            try:
                result = await self._process_single_attachment(
                    graph_client,
                    message_id,
                    attachment,
                    save_dir
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to process attachment: {str(e)}")
                results.append({
                    'name': attachment.get('name', 'unknown'),
                    'path': None,
                    'size': attachment.get('size', 0),
                    'error': str(e)
                })

        return results

    async def _process_single_attachment(
        self,
        graph_client,
        message_id: str,
        attachment: Dict[str, Any],
        save_dir: Path
    ) -> Dict[str, Any]:
        """단일 첨부파일 처리"""
        attachment_name = attachment.get('name', 'unnamed')
        attachment_id = attachment.get('id')

        # contentBytes가 직접 포함된 경우
        if 'contentBytes' in attachment:
            content = base64.b64decode(attachment['contentBytes'])
        else:
            # 별도 다운로드 필요
            if not attachment_id:
                raise ValueError("No attachment ID and no content")

            content = await self._download_attachment(
                graph_client,
                message_id,
                attachment_id
            )

        # 파일 저장
        file_path = self._save_file(save_dir, attachment_name, content)

        return {
            'name': attachment_name,
            'path': file_path,
            'size': len(content),
            'error': None
        }

    async def _download_attachment(
        self,
        graph_client,
        message_id: str,
        attachment_id: str
    ) -> bytes:
        """Graph API에서 첨부파일 다운로드"""
        try:
            url = f"/me/messages/{message_id}/attachments/{attachment_id}"

            # graph_client가 get_valid_access_token을 가지고 있다면
            if hasattr(graph_client, 'get'):
                response = await graph_client.get(url)
            else:
                # GraphAPIClient 사용 (access_token 필요)
                raise NotImplementedError("Graph client must have 'get' method")

            if response and 'contentBytes' in response:
                content = base64.b64decode(response['contentBytes'])
                logger.info(f"Downloaded attachment {attachment_id}")
                return content
            else:
                raise ValueError(f"No content for attachment {attachment_id}")

        except Exception as e:
            logger.error(f"Failed to download attachment: {str(e)}")
            raise

    def _save_file(self, save_dir: Path, filename: str, content: bytes) -> Path:
        """파일 저장 (중복 처리)"""
        from ...utils import sanitize_filename

        safe_filename = sanitize_filename(filename, max_length=200)
        file_path = save_dir / safe_filename

        # 중복 파일명 처리
        counter = 1
        while file_path.exists():
            name, ext = file_path.stem, file_path.suffix
            file_path = save_dir / f"{name}_{counter}{ext}"
            counter += 1

        file_path.write_bytes(content)
        logger.info(f"Saved file to {file_path}")
        return file_path
