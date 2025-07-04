"""프롬프트 관리 서비스"""

import re
from pathlib import Path
from typing import Dict, Any, Optional
from infra.core.logger import get_logger


class PromptService:
    """프롬프트 관리 서비스"""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.prompts_cache = {}
        self._load_prompts()

    def _load_prompts(self):
        """프롬프트 파일들 로드"""
        # 프롬프트 디렉토리 경로
        current_dir = Path(__file__).parent.parent
        prompts_dir = current_dir / "prompts"

        if not prompts_dir.exists():
            self.logger.warning(f"프롬프트 디렉토리를 찾을 수 없음: {prompts_dir}")
            return

        # 모든 프롬프트 파일 로드
        for prompt_file in prompts_dir.glob("*.txt"):
            prompt_type = prompt_file.stem  # 파일명에서 확장자 제거
            try:
                self._load_prompt_file(prompt_type, prompt_file)
                self.logger.info(f"프롬프트 로드 완료: {prompt_type}")
            except Exception as e:
                self.logger.error(f"프롬프트 로드 실패 ({prompt_type}): {str(e)}")

    def _load_prompt_file(self, prompt_type: str, file_path: Path):
        """개별 프롬프트 파일 로드"""
        content = file_path.read_text(encoding="utf-8")

        # structured_extraction_prompt.txt 형식 파싱
        if prompt_type == "structured_extraction_prompt":
            print(f"Loading structured_extraction_prompt from {file_path}")
            print(f"File content length: {len(content)}")
            print(f"First 500 chars: {content[:500]}")

            # SYSTEM_PROMPT 추출
            system_match = re.search(
                r"## SYSTEM_PROMPT\s*\n(.*?)(?=\n##|\n#|$)", content, re.DOTALL
            )
            system_prompt = system_match.group(1).strip() if system_match else ""

            # USER_PROMPT_TEMPLATE 추출 - # Rules 섹션 전까지
            user_match = re.search(
                r"## USER_PROMPT_TEMPLATE\s*\n(.*?)(?=\n# Rules)", content, re.DOTALL
            )
            user_prompt_template = user_match.group(1).strip() if user_match else ""

            print(f"Extracted system_prompt length: {len(system_prompt)}")
            print(f"Extracted user_prompt_template length: {len(user_prompt_template)}")
            print(f"user_prompt_template first 200 chars: {user_prompt_template[:200]}")

            self.prompts_cache[prompt_type] = {
                "system_prompt": system_prompt,
                "user_prompt_template": user_prompt_template,
            }
        else:
            # 일반 프롬프트 파일
            self.prompts_cache[prompt_type] = {
                "system_prompt": "You are a keyword extraction expert.",
                "user_prompt_template": content,
            }

    async def get_prompt_data(self, prompt_type: str) -> Dict[str, Any]:
        """프롬프트 데이터 가져오기"""
        print(f"get_prompt_data called with prompt_type: {prompt_type}")
        print(f"Available prompts in cache: {list(self.prompts_cache.keys())}")

        # 타입 매핑 처리
        actual_prompt_type = prompt_type
        if prompt_type == "structured":
            actual_prompt_type = "structured_extraction_prompt"
        elif prompt_type == "simple":
            actual_prompt_type = "simple_extraction_prompt"

        if actual_prompt_type in self.prompts_cache:
            data = self.prompts_cache[actual_prompt_type].copy()
            print(f"Returning cached data for {actual_prompt_type}")
            print(f"Cached system_prompt length: {len(data.get('system_prompt', ''))}")
            print(
                f"Cached user_prompt_template length: {len(data.get('user_prompt_template', ''))}"
            )
            return data

        print(f"Prompt type {prompt_type} not found in cache, returning default")
        # 기본 프롬프트
        return {
            "system_prompt": "You are a keyword extraction expert. Extract the most relevant keywords from the given text.",
            "user_prompt_template": "Extract {max_keywords} keywords from the following text:\n\n{text}\n\nKeywords:",
        }
