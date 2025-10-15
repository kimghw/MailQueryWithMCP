"""메일 처리 옵션 정의"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List
from enum import Enum


class TempFileCleanupPolicy(Enum):
    """임시 파일 정리 정책"""
    KEEP = "keep"  # 임시 파일 유지
    DELETE_ON_RETURN = "delete_on_return"  # 함수 반환 시 즉시 삭제
    DELETE_ON_NEW_QUERY = "delete_on_new_query"  # 다음 쿼리 시작 시 삭제


class AttachmentPathMode(Enum):
    """첨부파일 저장 경로 모드"""
    WITH_EMAIL = "with_email"  # 메일과 같은 디렉토리 (기본값)
    SEPARATE_ATTACHMENTS = "separate_attachments"  # 별도 attachments 디렉토리
    CUSTOM = "custom"  # 사용자 지정 경로


@dataclass
class ProcessOptions:
    """메일 처리 옵션"""

    # ===== 1. 기본 설정 =====
    user_id: str
    output_dir: Path = Path("./mail_data")

    # ===== 2. 메일 처리 옵션 =====
    save_email: bool = True  # 메일 본문 저장
    save_attachments: bool = True  # 첨부파일 저장
    convert_to_text: bool = False  # 첨부파일 → 텍스트 변환

    # ===== 3. 메일 저장 옵션 =====
    include_email_headers: bool = True  # 메일 헤더 포함
    save_html_version: bool = False  # HTML 버전도 저장

    # ===== 4. 첨부파일 저장 옵션 =====
    create_subfolder_per_email: bool = True  # 메일별 하위 폴더 생성
    subfolder_format: str = "{subject}_{date}_{sender}"  # 폴더명 형식

    # ===== 5. 첨부파일 경로 옵션 (새로 추가) =====
    attachment_path_mode: AttachmentPathMode = AttachmentPathMode.WITH_EMAIL
    # SEPARATE_ATTACHMENTS 모드일 때 사용할 경로
    separate_attachments_dir: Optional[Path] = None
    # CUSTOM 모드일 때 사용할 경로
    custom_attachment_dir: Optional[Path] = None

    # ===== 6. 텍스트 변환 옵션 =====
    save_converted_text: bool = True  # 변환된 텍스트 저장
    delete_original_after_convert: bool = False  # 변환 후 원본 삭제

    # ===== 7. 임시 파일 관리 옵션 (새로 추가) =====
    use_temp_storage: bool = False  # 임시 저장소 사용 여부
    temp_dir: Optional[Path] = None  # 임시 디렉토리 경로
    temp_cleanup_policy: TempFileCleanupPolicy = TempFileCleanupPolicy.KEEP

    # ===== 8. 응답 옵션 =====
    return_text_content: bool = False  # 텍스트 내용을 응답에 포함
    return_file_paths: bool = True  # 파일 경로를 응답에 포함

    def validate(self):
        """옵션 유효성 검사"""
        # 기존 검증 로직
        if self.convert_to_text and not self.save_attachments:
            raise ValueError("convert_to_text requires save_attachments=True")

        if self.delete_original_after_convert and not self.convert_to_text:
            raise ValueError("delete_original_after_convert requires convert_to_text=True")

        if not self.user_id:
            raise ValueError("user_id is required")

        # 첨부파일 경로 모드 검증
        if self.attachment_path_mode == AttachmentPathMode.SEPARATE_ATTACHMENTS:
            if not self.separate_attachments_dir:
                raise ValueError("separate_attachments_dir is required when using SEPARATE_ATTACHMENTS mode")

        if self.attachment_path_mode == AttachmentPathMode.CUSTOM:
            if not self.custom_attachment_dir:
                raise ValueError("custom_attachment_dir is required when using CUSTOM mode")

        # 임시 파일 관리 검증
        if self.use_temp_storage and not self.temp_dir:
            raise ValueError("temp_dir is required when use_temp_storage=True")

    def __post_init__(self):
        """초기화 후 자동 검증"""
        # Path 타입 변환
        if isinstance(self.output_dir, str):
            self.output_dir = Path(self.output_dir)

        if self.separate_attachments_dir and isinstance(self.separate_attachments_dir, str):
            self.separate_attachments_dir = Path(self.separate_attachments_dir)

        if self.custom_attachment_dir and isinstance(self.custom_attachment_dir, str):
            self.custom_attachment_dir = Path(self.custom_attachment_dir)

        if self.temp_dir and isinstance(self.temp_dir, str):
            self.temp_dir = Path(self.temp_dir)

        self.validate()

    # ===== 헬퍼 메서드 =====
    def get_attachment_base_dir(self, email_dir: Path) -> Path:
        """첨부파일 저장 경로 결정

        Args:
            email_dir: 메일이 저장된 디렉토리

        Returns:
            첨부파일 저장 경로
        """
        if self.attachment_path_mode == AttachmentPathMode.WITH_EMAIL:
            return email_dir / "attachments"
        elif self.attachment_path_mode == AttachmentPathMode.SEPARATE_ATTACHMENTS:
            return self.separate_attachments_dir
        elif self.attachment_path_mode == AttachmentPathMode.CUSTOM:
            return self.custom_attachment_dir
        else:
            return email_dir / "attachments"

    def get_temp_dir(self) -> Optional[Path]:
        """임시 디렉토리 경로 반환"""
        return self.temp_dir if self.use_temp_storage else None

    def should_use_temp_storage(self) -> bool:
        """임시 저장소 사용 여부 확인"""
        return self.use_temp_storage and self.temp_dir is not None
