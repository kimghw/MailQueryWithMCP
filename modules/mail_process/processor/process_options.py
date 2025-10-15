"""메일 처리 옵션 정의"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class ProcessOptions:
    """메일 처리 옵션"""

    # 기본 설정
    user_id: str
    output_dir: Path = Path("./mail_data")

    # 처리 옵션
    save_email: bool = True  # 메일 본문 저장
    save_attachments: bool = True  # 첨부파일 저장
    convert_to_text: bool = False  # 첨부파일 → 텍스트 변환

    # 메일 저장 옵션
    include_email_headers: bool = True  # 메일 헤더 포함
    save_html_version: bool = False  # HTML 버전도 저장

    # 첨부파일 저장 옵션
    create_subfolder_per_email: bool = True  # 메일별 하위 폴더 생성
    subfolder_format: str = "{subject}_{date}_{sender}"  # 폴더명 형식

    # 텍스트 변환 옵션
    save_converted_text: bool = True  # 변환된 텍스트 저장
    delete_original_after_convert: bool = False  # 변환 후 원본 삭제

    # 응답 옵션
    return_text_content: bool = False  # 텍스트 내용을 응답에 포함
    return_file_paths: bool = True  # 파일 경로를 응답에 포함

    def validate(self):
        """옵션 유효성 검사"""
        if self.convert_to_text and not self.save_attachments:
            raise ValueError("convert_to_text requires save_attachments=True")

        if self.delete_original_after_convert and not self.convert_to_text:
            raise ValueError("delete_original_after_convert requires convert_to_text=True")

        if not self.user_id:
            raise ValueError("user_id is required")

    def __post_init__(self):
        """초기화 후 자동 검증"""
        # Path 타입 변환
        if isinstance(self.output_dir, str):
            self.output_dir = Path(self.output_dir)

        self.validate()
