#!/usr/bin/env python3
"""
replace 폴더의 파일들을 첫 부분의 경로 정보를 읽어서 해당 경로로 파일을 이동/복사하는 스크립트
하나의 파일에 여러 개의 파일이 포함된 경우도 처리 가능
"""

import os
import shutil
import re
import time
from pathlib import Path
from typing import List, Tuple, Optional, Dict


def extract_multiple_files_from_content(file_path: str) -> List[Tuple[str, str]]:
    """
    파일 내용에서 여러 파일의 경로와 내용을 추출합니다.

    Args:
        file_path: 읽을 파일 경로

    Returns:
        [(대상 경로, 파일 내용), ...] 형태의 리스트
    """
    files = []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # """ 또는 ''' 로 구분된 섹션 찾기
        pattern = r'"""[\s\S]*?"""'
        sections = list(re.finditer(pattern, content))

        for i, section_match in enumerate(sections):
            section = section_match.group(0)
            # 섹션 내에서 경로 추출
            lines = section.split("\n")
            target_path = None

            # 경로 패턴들
            path_patterns = [
                r"modules/[^\s]+\.py",  # modules/로 시작하는 경로
                r"scripts/[^\s]+\.py",  # scripts/로 시작하는 경로
                r"infra/[^\s]+\.py",  # infra/로 시작하는 경로
                r"[a-zA-Z0-9_/]+\.py",  # 일반적인 .py 경로
            ]

            # 처음 몇 줄에서 경로 찾기
            for line in lines[:10]:
                for pattern in path_patterns:
                    match = re.search(pattern, line)
                    if match:
                        target_path = match.group(0)
                        break
                if target_path:
                    break

            if target_path:
                # 현재 섹션의 끝 위치
                section_end = section_match.end()

                # 다음 섹션의 시작 위치 찾기
                if i + 1 < len(sections):
                    next_section_start = sections[i + 1].start()
                    section_content = content[section_end:next_section_start]
                else:
                    # 마지막 섹션인 경우 파일 끝까지
                    section_content = content[section_end:]

                # 앞뒤 공백 제거
                section_content = section_content.strip()

                if section_content:
                    files.append((target_path, section_content))
                    print(f"  📄 발견: {target_path} ({len(section_content)} bytes)")

        # 단일 파일인 경우 처리
        if not files:
            target_path = extract_file_path_from_content(file_path)
            if target_path:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                files.append((target_path, content))

    except Exception as e:
        print(f"파일 {file_path} 읽기 오류: {e}")

    return files


def extract_file_path_from_content(file_path: str) -> Optional[str]:
    """
    파일 내용의 첫 부분에서 경로 정보를 추출합니다.

    Args:
        file_path: 읽을 파일 경로

    Returns:
        추출된 경로 또는 None
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read(500)  # 첫 500자만 읽기

        # docstring 내부의 경로 찾기
        if content.startswith('"""') or content.startswith("'''"):
            # docstring 내용 추출
            docstring_pattern = r'^("""|\'\'\')\s*(.*?)\s*\1'
            match = re.search(docstring_pattern, content, re.DOTALL)
            if match:
                docstring_content = match.group(2)
                # docstring 내에서 경로 찾기
                path_patterns = [
                    r"modules/[^\s]+\.py",
                    r"scripts/[^\s]+\.py",
                    r"infra/[^\s]+\.py",
                    r"[a-zA-Z0-9_/]+\.py",
                ]
                for pattern in path_patterns:
                    path_match = re.search(pattern, docstring_content)
                    if path_match:
                        return path_match.group(0)

        # 기존 방식으로도 시도
        lines = content.split("\n")[:10]

        # 다양한 패턴으로 경로 찾기
        patterns = [
            r"^#\s*파일\s*경로\s*:\s*(.+)$",  # # 파일 경로: path/to/file
            r"^#\s*PATH\s*:\s*(.+)$",  # # PATH: path/to/file
            r"^#\s*File\s*:\s*(.+)$",  # # File: path/to/file
            r"^#\s*Target\s*:\s*(.+)$",  # # Target: path/to/file
            r"^#\s*Replace\s*:\s*(.+)$",  # # Replace: path/to/file
            r"^#\s*(.+\.py)$",  # # some/path/file.py
            r"^#\s*(.+\..+)$",  # # some/path/file.ext
            r"^\s*#\s*(.+/[^/]+\.[^/]+)$",  # # path/file.ext
            r"^\s*(.+/[^/]+\.[^/]+)$",  # path/file.ext (주석 없이)
            r"(modules/[^\s]+\.py)",  # modules/ 경로
            r"(scripts/[^\s]+\.py)",  # scripts/ 경로
            r"(infra/[^\s]+\.py)",  # infra/ 경로
        ]

        for line in lines:
            line = line.strip()
            if not line:
                continue

            for pattern in patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    target_path = match.group(1).strip()
                    # 상대 경로를 절대 경로로 변환
                    if not os.path.isabs(target_path):
                        target_path = os.path.join(os.getcwd(), target_path)
                    return target_path

    except Exception as e:
        print(f"파일 {file_path} 읽기 오류: {e}")

    return None


def find_replace_files(directory: str = ".") -> List[str]:
    """
    /home/kimghw/Downloads 폴더의 *.py, *.txt 파일들 중 최근 3분 안에 생성된 파일들을 찾습니다.

    Args:
        directory: 검색할 디렉토리 (사용되지 않음)

    Returns:
        교체할 파일들의 경로 리스트
    """
    replace_files = []

    # 현재 시간에서 3분 전 시간 계산
    three_minutes_ago = time.time() - (3 * 60)  # 3분 = 180초

    # /home/kimghw/Downloads 폴더의 파일들 찾기
    downloads_dir = "/home/kimghw/Downloads"
    allowed_extensions = (".py", ".txt", ".md")  # 원하는 확장자 추가 가능

    if os.path.exists(downloads_dir) and os.path.isdir(downloads_dir):
        for file in os.listdir(downloads_dir):
            if file.endswith(allowed_extensions) and not file.startswith("."):
                file_path = os.path.join(downloads_dir, file)
                if os.path.isfile(file_path):
                    # 파일 생성 시간 확인
                    file_creation_time = os.path.getctime(file_path)
                    if file_creation_time >= three_minutes_ago:
                        replace_files.append(file_path)
                        print(
                            f"  📅 최근 파일 발견: {file} (생성시간: {time.ctime(file_creation_time)})"
                        )

    return replace_files


def process_file_replacement(source_file: str, dry_run: bool = False) -> bool:
    """
    단일 파일을 처리하여 지정된 경로로 이동/복사합니다.

    Args:
        source_file: 원본 파일 경로
        dry_run: True면 실제 작업 없이 시뮬레이션만

    Returns:
        성공 여부
    """
    print(f"\n처리 중: {source_file}")

    # 파일에서 대상 경로 추출
    target_path = extract_file_path_from_content(source_file)

    if not target_path:
        print(f"  ❌ 대상 경로를 찾을 수 없습니다.")
        return False

    print(f"  📍 대상 경로: {target_path}")

    # 대상 디렉토리 생성
    target_dir = os.path.dirname(target_path)

    if dry_run:
        print(f"  🔍 [DRY RUN] 디렉토리 생성: {target_dir}")
        print(f"  🔍 [DRY RUN] 파일 복사: {source_file} -> {target_path}")
        return True

    try:
        # 디렉토리가 없으면 생성 (중첩 디렉토리도 모두 생성)
        if target_dir and not os.path.exists(target_dir):
            os.makedirs(target_dir, exist_ok=True)
            print(f"  📁 디렉토리 생성: {target_dir}")

        # 파일 복사
        shutil.copy2(source_file, target_path)
        print(f"  ✅ 파일 복사 완료: {target_path}")

        # 원본 파일 삭제
        os.remove(source_file)
        print(f"  🗑️ 원본 파일 삭제: {source_file}")

        return True

    except Exception as e:
        print(f"  ❌ 오류 발생: {e}")
        return False


def process_multi_file_replacement(source_file: str, dry_run: bool = False) -> int:
    """
    다중 파일이 포함된 파일을 처리합니다.

    Args:
        source_file: 원본 파일 경로
        dry_run: True면 실제 작업 없이 시뮬레이션만

    Returns:
        성공적으로 처리된 파일 수
    """
    print(f"\n🔍 파일 분석 중: {source_file}")

    # 파일에서 여러 파일 추출 시도
    files = extract_multiple_files_from_content(source_file)

    # 다중 파일이 없으면 단일 파일로 처리
    if not files or len(files) == 0:
        # 단일 파일로 처리 시도
        if process_file_replacement(source_file, dry_run):
            return 1
        else:
            return 0

    if len(files) > 1:
        print(f"  📦 {len(files)}개의 파일이 포함되어 있습니다.")

    success_count = 0

    for target_path, content in files:
        print(f"\n  📍 대상 경로: {target_path}")

        # 대상 디렉토리 생성
        target_dir = os.path.dirname(target_path)

        if dry_run:
            print(f"    🔍 [DRY RUN] 디렉토리 생성: {target_dir}")
            print(f"    🔍 [DRY RUN] 파일 생성: {target_path} ({len(content)} bytes)")
            success_count += 1
            continue

        try:
            # 디렉토리가 없으면 생성
            if target_dir and not os.path.exists(target_dir):
                os.makedirs(target_dir, exist_ok=True)
                print(f"    📁 디렉토리 생성: {target_dir}")

            # 파일 쓰기
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"    ✅ 파일 생성 완료: {target_path}")

            success_count += 1

        except Exception as e:
            print(f"    ❌ 오류 발생: {e}")

    # 모든 파일이 성공적으로 처리되면 원본 삭제
    if not dry_run and success_count == len(files) and len(files) > 0:
        try:
            os.remove(source_file)
            print(f"  🗑️ 원본 파일 삭제: {source_file}")
        except Exception as e:
            print(f"  ⚠️ 원본 파일 삭제 실패: {e}")

    return success_count


def main():
    """메인 함수"""
    print("🔄 파일 교체 스크립트 시작 (다중 파일 지원)")
    print("=" * 50)

    # 교체할 파일들 찾기
    replace_files = find_replace_files()

    if not replace_files:
        print("❌ 교체할 파일을 찾을 수 없습니다.")
        print("최근 3분 이내에 생성된 파일을 /home/kimghw/Downloads 폴더에서 찾습니다.")
        return

    print(f"📋 발견된 파일: {len(replace_files)}개")
    for file in replace_files:
        print(f"  - {file}")

    # 사용자 확인
    print("\n🔍 DRY RUN 모드로 먼저 확인합니다...")
    print("-" * 30)

    total_files = 0
    file_counts = {}

    for file in replace_files:
        count = process_multi_file_replacement(file, dry_run=True)
        file_counts[file] = count
        total_files += count

    print(f"\n📊 DRY RUN 결과: 총 {total_files}개 파일 처리 가능")
    for file, count in file_counts.items():
        if count > 0:
            print(f"  - {os.path.basename(file)}: {count}개 파일")

    if total_files == 0:
        print("❌ 처리 가능한 파일이 없습니다.")
        return

    # 실제 실행 확인
    response = (
        input(f"\n실제로 {total_files}개 파일을 처리하시겠습니까? (y/N): ")
        .strip()
        .lower()
    )

    if response not in ["y", "yes"]:
        print("❌ 작업이 취소되었습니다.")
        return

    print("\n🚀 실제 파일 처리 시작...")
    print("-" * 30)

    final_total = 0
    for file in replace_files:
        count = process_multi_file_replacement(file, dry_run=False)
        final_total += count

    print(f"\n🎉 작업 완료: {final_total}개 파일 처리됨")


if __name__ == "__main__":
    main()
