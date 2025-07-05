"""프롬프트 관리 서비스"""

import re
from pathlib import Path
from typing import Any, Dict, Optional

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
        """개별 프롬프트 파일 로드 - Claude 최적화 버전"""
        content = file_path.read_text(encoding="utf-8")

        if prompt_type == "structured_extraction_prompt":
            # 1. SYSTEM_PROMPT 섹션 추출
            system_match = re.search(
                r"## SYSTEM_PROMPT\s*\n(.*?)(?=\n##)", content, re.DOTALL
            )
            base_system_prompt = system_match.group(1).strip() if system_match else ""

            # 2. OUTPUT_FORMAT 섹션 추출
            format_match = re.search(
                r"## OUTPUT_FORMAT\s*\n(.*?)(?=\n##)", content, re.DOTALL
            )
            output_format = format_match.group(1).strip() if format_match else ""

            # 3. RULES 섹션 추출
            rules_match = re.search(r"## RULES\s*\n(.*?)(?=$)", content, re.DOTALL)
            rules_content = rules_match.group(1).strip() if rules_match else ""

            # 4. USER_PROMPT_TEMPLATE 섹션 추출
            user_match = re.search(
                r"## USER_PROMPT_TEMPLATE\s*\n(.*?)(?=\n##)", content, re.DOTALL
            )
            user_prompt_template = user_match.group(1).strip() if user_match else ""

            # 5. Claude에 최적화된 System Prompt 구성
            # 시스템 프롬프트에 모든 규칙과 포맷을 포함
            enhanced_system_prompt = f"""{base_system_prompt}

    ## Expected Output Format:
    {output_format}

    ## Extraction Rules and Guidelines:
    {rules_content}

    ## CRITICAL: You must respond with ONLY valid JSON matching the format above. No explanations, no additional text, no markdown formatting - just the JSON object."""

            self.prompts_cache[prompt_type] = {
                "system_prompt": enhanced_system_prompt,
                "user_prompt_template": user_prompt_template,
                "output_format": output_format,  # 디버깅용
                "rules": rules_content,  # 디버깅용
            }

            # 디버깅 로그
            self.logger.debug(f"Loaded {prompt_type}:")
            self.logger.debug(f"- Base system prompt length: {len(base_system_prompt)}")
            self.logger.debug(f"- Output format length: {len(output_format)}")
            self.logger.debug(f"- Rules length: {len(rules_content)}")
            self.logger.debug(f"- User template length: {len(user_prompt_template)}")
            self.logger.debug(
                f"- Enhanced system prompt length: {len(enhanced_system_prompt)}"
            )

        else:
            # 일반 프롬프트 파일 처리
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
