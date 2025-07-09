#!/usr/bin/env python3
"""
replace 폴더의 파일들을 첫 부분의 경로 정보를 읽어서 해당 경로로 파일을 이동/복사하는 스크립트
"""

import os
import shutil
import re
import time
from pathlib import Path
from typing import List, Tuple, Optional


def extract_file_path_from_content(file_path: str) -> Optional[str]:
    """
    파일 내용의 첫 부분에서 경로 정보를 추출합니다.
    docstring 내부나 이후의 주석도 파싱 가능합니다.

    Args:
        file_path: 읽을 파일 경로

    Returns:
        추출된 경로 또는 None
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 줄 단위로 분리
        lines = content.split("\n")

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
        ]

        # 첫 30줄 정도만 확인 (docstring 고려)
        for i, line in enumerate(lines[:30]):
            # 일반 주석 패턴
            if line.strip().startswith("#"):
                for pattern in patterns:
                    match = re.match(pattern, line.strip(), re.IGNORECASE)
                    if match:
                        target_path = match.group(1).strip()
                        # 상대 경로를 절대 경로로 변환
                        if not os.path.isabs(target_path):
                            target_path = os.path.join(os.getcwd(), target_path)
                        return target_path

            # docstring 내부나 근처의 경로 찾기
            # modules/, src/, lib/ 등으로 시작하는 파이썬 파일 경로 패턴
            if any(
                keyword in line
                for keyword in ["modules/", "src/", "lib/", "app/", "tests/"]
            ):
                # 경로처럼 보이는 패턴 추출
                # 다양한 파일 확장자 지원
                path_patterns = [
                    r'((?:modules|src|lib|app|tests)/[^\s"""\']+\.(?:py|txt|json|yaml|yml|md))',
                    r'([a-zA-Z0-9_]+/[^\s"""\']+\.(?:py|txt|json|yaml|yml|md))',
                ]

                for path_pattern in path_patterns:
                    path_match = re.search(path_pattern, line)
                    if path_match:
                        target_path = path_match.group(1)
                        if not os.path.isabs(target_path):
                            target_path = os.path.join(os.getcwd(), target_path)
                        return target_path

        # 특별한 경우: docstring 바로 다음 줄에 경로가 있는 경우
        in_docstring = False
        docstring_end_line = -1

        for i, line in enumerate(lines[:30]):
            # docstring 시작/종료 감지
            if '"""' in line or "'''" in line:
                if not in_docstring:
                    in_docstring = True
                else:
                    in_docstring = False
                    docstring_end_line = i

            # docstring 종료 직후 몇 줄 내에서 경로 찾기
            if docstring_end_line != -1 and i - docstring_end_line <= 5:
                # 경로 패턴 매칭
                if any(
                    keyword in line
                    for keyword in ["modules/", "src/", "lib/", "app/", "tests/"]
                ):
                    path_match = re.search(r"([a-zA-Z0-9_/]+\.py)", line)
                    if path_match:
                        target_path = path_match.group(1)
                        if not os.path.isabs(target_path):
                            target_path = os.path.join(os.getcwd(), target_path)
                        return target_path

    except Exception as e:
        print(f"파일 {file_path} 읽기 오류: {e}")

    return None


def find_replace_files(directory: str = ".") -> List[str]:
    """
    /home/kimghw/Downloads 폴더의 *.py 파일들 중 최근 3분 안에 생성된 파일들을 찾습니다.

    Args:
        directory: 검색할 디렉토리 (사용되지 않음)

    Returns:
        교체할 파일들의 경로 리스트
    """
    replace_files = []

    # 현재 시간에서 3분 전 시간 계산
    three_minutes_ago = time.time() - (3 * 60)  # 3분 = 180초

    # /home/kimghw/Downloads 폴더의 *.py 파일들 찾기
    downloads_dir = "/home/kimghw/Downloads"
    allowed_extensions = (
        ".py",
        ".txt",
        ".json",
        ".yaml",
        ".yml",
        ".md",
    )  # 원하는 확장자 추가

    if os.path.exists(downloads_dir) and os.path.isdir(downloads_dir):
        for file in os.listdir(downloads_dir):
            if file.endswith(allowed_extensions) and not file.startswith("."):
                file_path = os.path.join(downloads_dir, file)
                if os.path.isfile(file_path):
                    # 파일 생성 시간 확인
                    file_creation_time = os.path.getctime(file_path)
                    if file_creation_time >= three_minutes_ago:
                        replace_files.append(file_path)
                        # 생성 시간을 더 읽기 쉽게 표시
                        time_diff = int(time.time() - file_creation_time)
                        if time_diff < 60:
                            time_str = f"{time_diff}초 전"
                        else:
                            time_str = f"{time_diff // 60}분 {time_diff % 60}초 전"
                        print(f"  📅 최근 파일 발견: {file} ({time_str} 생성)")

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
    print(f"\n처리 중: {os.path.basename(source_file)}")

    # 파일에서 대상 경로 추출
    target_path = extract_file_path_from_content(source_file)

    if not target_path:
        print(f"  ❌ 대상 경로를 찾을 수 없습니다.")
        # 파일 내용의 처음 몇 줄을 보여줘서 디버깅 도움
        try:
            with open(source_file, "r", encoding="utf-8") as f:
                lines = [f.readline().strip() for _ in range(5)]
            print(f"  📝 파일 시작 부분:")
            for i, line in enumerate(lines, 1):
                if line:
                    print(f"     {i}: {line[:60]}{'...' if len(line) > 60 else ''}")
        except:
            pass
        return False

    print(f"  📍 대상 경로: {target_path}")

    # 대상 디렉토리 생성
    target_dir = os.path.dirname(target_path)

    if dry_run:
        print(f"  🔍 [DRY RUN] 디렉토리 생성: {target_dir}")
        print(f"  🔍 [DRY RUN] 파일 복사: {source_file} -> {target_path}")

        # 파일이 이미 존재하는지 확인
        if os.path.exists(target_path):
            print(f"  ⚠️  [DRY RUN] 경고: 대상 파일이 이미 존재합니다!")
        return True

    try:
        # 디렉토리가 없으면 생성 (중첩 디렉토리도 모두 생성)
        if target_dir and not os.path.exists(target_dir):
            os.makedirs(target_dir, exist_ok=True)
            print(f"  📁 디렉토리 생성: {target_dir}")

        # 대상 파일이 이미 존재하는 경우 백업
        if os.path.exists(target_path):
            backup_path = f"{target_path}.backup_{int(time.time())}"
            shutil.copy2(target_path, backup_path)
            print(f"  💾 기존 파일 백업: {os.path.basename(backup_path)}")

        # 파일 복사
        shutil.copy2(source_file, target_path)
        print(f"  ✅ 파일 복사 완료: {target_path}")

        # 원본 파일 삭제
        os.remove(source_file)
        print(f"  🗑️  원본 파일 삭제: {source_file}")

        return True

    except Exception as e:
        print(f"  ❌ 오류 발생: {e}")
        return False


def main():
    """메인 함수"""
    print("🔄 파일 교체 스크립트 시작")
    print("=" * 50)

    # 교체할 파일들 찾기
    print(f"📂 검색 디렉토리: /home/kimghw/Downloads")
    print(f"⏰ 검색 조건: 최근 3분 이내 생성된 파일")
    print("-" * 30)

    replace_files = find_replace_files()

    if not replace_files:
        print("❌ 교체할 파일을 찾을 수 없습니다.")
        print(
            "   최근 3분 이내에 생성된 .py, .txt, .json, .yaml, .yml, .md 파일을 찾습니다."
        )
        return

    print(f"\n📋 발견된 교체 파일: {len(replace_files)}개")
    for file in replace_files:
        print(f"  - {os.path.basename(file)}")

    # 사용자 확인
    print("\n🔍 DRY RUN 모드로 먼저 확인합니다...")
    print("-" * 30)

    success_count = 0
    for file in replace_files:
        if process_file_replacement(file, dry_run=True):
            success_count += 1

    print(f"\n📊 DRY RUN 결과: {success_count}/{len(replace_files)} 파일 처리 가능")

    if success_count == 0:
        print("❌ 처리 가능한 파일이 없습니다.")
        print("   파일 내용에 경로 정보가 포함되어 있는지 확인하세요.")
        print("   예: # modules/path/to/file.py")
        return

    # 실제 실행 확인
    response = (
        input(f"\n실제로 {success_count}개 파일을 처리하시겠습니까? (Y/n): ")
        .strip()
        .lower()
    )

    if response in ["n", "no"]:
        print("❌ 작업이 취소되었습니다.")
        return

    print("\n🚀 실제 파일 처리 시작...")
    print("-" * 30)

    final_success = 0
    for file in replace_files:
        if process_file_replacement(file, dry_run=False):
            final_success += 1

    print(f"\n🎉 작업 완료: {final_success}/{len(replace_files)} 파일 처리됨")


if __name__ == "__main__":
    main()
