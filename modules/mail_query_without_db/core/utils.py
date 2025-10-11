"""Common utility functions for mail query module"""

import re
from pathlib import Path
from typing import Optional


def sanitize_filename(filename: str, max_length: int = 100) -> str:
    """
    안전한 파일명 생성

    Args:
        filename: 원본 파일명
        max_length: 최대 파일명 길이 (기본값: 100)

    Returns:
        안전한 파일명
    """
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
        safe_name = 'unnamed_file'

    # 길이 제한
    if len(safe_name) > max_length:
        # 확장자 보존
        name_parts = safe_name.rsplit('.', 1)
        if len(name_parts) == 2:
            name, ext = name_parts
            name = name[:max_length - len(ext) - 1]
            safe_name = f"{name}.{ext}"
        else:
            safe_name = safe_name[:max_length]

    return safe_name


def ensure_directory_exists(path: Path) -> Path:
    """
    디렉토리가 존재하는지 확인하고 없으면 생성

    Args:
        path: 확인할 디렉토리 경로

    Returns:
        생성된 또는 기존 디렉토리 경로
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def truncate_text(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """
    텍스트를 지정된 길이로 자르기

    Args:
        text: 원본 텍스트
        max_length: 최대 길이
        suffix: 잘린 경우 추가할 접미사

    Returns:
        잘린 텍스트
    """
    if len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix


def format_file_size(size_bytes: int) -> str:
    """
    파일 크기를 사람이 읽기 쉬운 형식으로 변환

    Args:
        size_bytes: 바이트 단위 크기

    Returns:
        포맷된 크기 문자열
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def is_valid_email(email: str) -> bool:
    """
    이메일 주소 유효성 검사

    Args:
        email: 검사할 이메일 주소

    Returns:
        유효한 이메일인지 여부
    """
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None