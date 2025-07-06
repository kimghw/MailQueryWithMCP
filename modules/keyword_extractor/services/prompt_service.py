"""프롬프트 관리 서비스 - 캐싱 문제 해결 버전"""

import re
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime
import os

from infra.core.logger import get_logger
from infra.core.config import get_config


class PromptService:
    """프롬프트 관리 서비스"""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.config = get_config()
        self.prompts_cache = {}
        self.file_timestamps = {}  # 파일 수정 시간 추적

        # 개발 모드 설정 (환경 변수로 제어)
        self.dev_mode = (
            self.config.get_setting("PROMPT_DEV_MODE", "false").lower() == "true"
        )
        self.cache_ttl = int(
            self.config.get_setting("PROMPT_CACHE_TTL", "300")
        )  # 기본 5분

        self._load_prompts()

        if self.dev_mode:
            self.logger.info("프롬프트 개발 모드 활성화 - 캐싱 비활성화")

    def _load_prompts(self):
        """프롬프트 파일들 로드"""
        current_dir = Path(__file__).parent.parent
        prompts_dir = current_dir / "prompts"

        if not prompts_dir.exists():
            self.logger.warning(f"프롬프트 디렉토리를 찾을 수 없음: {prompts_dir}")
            return

        for prompt_file in prompts_dir.glob("*.txt"):
            prompt_type = prompt_file.stem
            try:
                self._load_prompt_file(prompt_type, prompt_file)
                self.logger.info(f"프롬프트 로드 완료: {prompt_type}")
            except Exception as e:
                self.logger.error(f"프롬프트 로드 실패 ({prompt_type}): {str(e)}")

    def _check_file_updated(self, file_path: Path) -> bool:
        """파일이 업데이트되었는지 확인"""
        current_mtime = file_path.stat().st_mtime
        cached_mtime = self.file_timestamps.get(str(file_path), 0)

        if current_mtime > cached_mtime:
            self.file_timestamps[str(file_path)] = current_mtime
            return True
        return False

    def _load_prompt_file(self, prompt_type: str, file_path: Path):
        """개별 프롬프트 파일 로드"""
        content = file_path.read_text(encoding="utf-8")

        # 파일 수정 시간 저장
        self.file_timestamps[str(file_path)] = file_path.stat().st_mtime

        if prompt_type == "structured_extraction_prompt":
            # 기존 파싱 로직 유지
            system_match = re.search(
                r"## SYSTEM_PROMPT\s*\n(.*?)(?=\n##)", content, re.DOTALL
            )
            base_system_prompt = system_match.group(1).strip() if system_match else ""

            format_match = re.search(
                r"## OUTPUT_FORMAT\s*\n(.*?)(?=\n##)", content, re.DOTALL
            )
            output_format = format_match.group(1).strip() if format_match else ""

            rules_match = re.search(r"## RULES\s*\n(.*?)(?=$)", content, re.DOTALL)
            rules_content = rules_match.group(1).strip() if rules_match else ""

            user_match = re.search(
                r"## USER_PROMPT_TEMPLATE\s*\n(.*?)(?=\n##)", content, re.DOTALL
            )
            user_prompt_template = user_match.group(1).strip() if user_match else ""

            enhanced_system_prompt = f"""{base_system_prompt}

## Expected Output Format:
{output_format}

## Extraction Rules and Guidelines:
{rules_content}

## CRITICAL: You must respond with ONLY valid JSON matching the format above. No explanations, no additional text, no markdown formatting - just the JSON object."""

            self.prompts_cache[prompt_type] = {
                "system_prompt": enhanced_system_prompt,
                "user_prompt_template": user_prompt_template,
                "output_format": output_format,
                "rules": rules_content,
                "loaded_at": datetime.now(),  # 로드 시간 추가
            }
        else:
            self.prompts_cache[prompt_type] = {
                "system_prompt": "You are a keyword extraction expert.",
                "user_prompt_template": content,
                "loaded_at": datetime.now(),
            }

    def reload_prompt(self, prompt_type: str) -> bool:
        """특정 프롬프트 리로드"""
        current_dir = Path(__file__).parent.parent
        prompts_dir = current_dir / "prompts"

        # 타입 매핑 처리
        actual_prompt_type = prompt_type
        if prompt_type == "structured":
            actual_prompt_type = "structured_extraction_prompt"
        elif prompt_type == "simple":
            actual_prompt_type = "simple_extraction_prompt"

        prompt_file = prompts_dir / f"{actual_prompt_type}.txt"

        if prompt_file.exists():
            try:
                self._load_prompt_file(actual_prompt_type, prompt_file)
                self.logger.info(f"프롬프트 리로드 완료: {actual_prompt_type}")
                return True
            except Exception as e:
                self.logger.error(f"프롬프트 리로드 실패: {str(e)}")
                return False
        return False

    def clear_cache(self):
        """전체 캐시 클리어"""
        self.prompts_cache.clear()
        self.file_timestamps.clear()
        self.logger.info("프롬프트 캐시 전체 클리어됨")
        self._load_prompts()

    async def get_prompt_data(self, prompt_type: str) -> Dict[str, Any]:
        """프롬프트 데이터 가져오기"""
        # 타입 매핑 처리
        actual_prompt_type = prompt_type
        if prompt_type == "structured":
            actual_prompt_type = "structured_extraction_prompt"
        elif prompt_type == "simple":
            actual_prompt_type = "simple_extraction_prompt"

        # 개발 모드에서는 항상 리로드
        if self.dev_mode:
            self.reload_prompt(prompt_type)
        else:
            # 파일 변경 체크 (프로덕션 모드)
            current_dir = Path(__file__).parent.parent
            prompt_file = current_dir / "prompts" / f"{actual_prompt_type}.txt"

            if prompt_file.exists() and self._check_file_updated(prompt_file):
                self.logger.info(
                    f"프롬프트 파일 변경 감지, 리로드: {actual_prompt_type}"
                )
                self.reload_prompt(prompt_type)

        if actual_prompt_type in self.prompts_cache:
            data = self.prompts_cache[actual_prompt_type].copy()
            # 로드 시간 정보 제거 (반환 데이터에서)
            data.pop("loaded_at", None)
            return data

        # 기본 프롬프트
        return {
            "system_prompt": "You are a keyword extraction expert. Extract the most relevant keywords from the given text.",
            "user_prompt_template": "Extract {max_keywords} keywords from the following text:\n\n{text}\n\nKeywords:",
        }


# 추가: 프롬프트 관리용 CLI 유틸리티 (선택사항)
if __name__ == "__main__":
    import asyncio
    import sys

    async def test_prompt_service():
        service = PromptService()

        if len(sys.argv) > 1:
            command = sys.argv[1]

            if command == "reload":
                if len(sys.argv) > 2:
                    prompt_type = sys.argv[2]
                    success = service.reload_prompt(prompt_type)
                    print(f"Reload {prompt_type}: {'Success' if success else 'Failed'}")
                else:
                    service.clear_cache()
                    print("All prompts reloaded")

            elif command == "show":
                for name, data in service.prompts_cache.items():
                    print(f"\n=== {name} ===")
                    print(f"Loaded at: {data.get('loaded_at', 'Unknown')}")
                    print(f"System prompt length: {len(data.get('system_prompt', ''))}")

        else:
            # 기본 테스트
            data = await service.get_prompt_data("structured")
            print("Structured prompt loaded successfully")
            print(f"System prompt starts with: {data['system_prompt'][:100]}...")

    asyncio.run(test_prompt_service())
