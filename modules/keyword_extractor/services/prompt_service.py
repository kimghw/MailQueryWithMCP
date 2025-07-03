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
        content = file_path.read_text(encoding='utf-8')
        
        # structured_extraction_prompt.txt 형식 파싱
        if prompt_type == "structured_extraction_prompt":
            # SYSTEM_PROMPT 추출
            system_match = re.search(r'## SYSTEM_PROMPT\s*\n(.*?)(?=\n##|\n#|$)', content, re.DOTALL)
            system_prompt = system_match.group(1).strip() if system_match else ""
            
            # USER_PROMPT_TEMPLATE 추출
            user_match = re.search(r'## USER_PROMPT_TEMPLATE\s*\n(.*?)$', content, re.DOTALL)
            user_template_content = user_match.group(1).strip() if user_match else ""
            
            # Rules 섹션 추출
            rules_match = re.search(r'# Rules\s*\n(.*?)(?=## USER_PROMPT_TEMPLATE)', content, re.DOTALL)
            rules_content = rules_match.group(1).strip() if rules_match else ""
            
            # 프롬프트 조합
            if rules_content and user_template_content:
                user_prompt_template = f"""Follow these rules to analyze the text:

{rules_content}

{user_template_content}"""
            else:
                user_prompt_template = user_template_content or ""
            
            self.prompts_cache[prompt_type] = {
                'system_prompt': system_prompt,
                'user_prompt_template': user_prompt_template
            }
        else:
            # 일반 프롬프트 파일
            self.prompts_cache[prompt_type] = {
                'system_prompt': "You are a keyword extraction expert.",
                'user_prompt_template': content
            }
    
    async def get_prompt_data(self, prompt_type: str) -> Dict[str, Any]:
        """프롬프트 데이터 가져오기"""
        if prompt_type in self.prompts_cache:
            return self.prompts_cache[prompt_type].copy()
        
        # 기본 프롬프트
        return {
            'system_prompt': "You are a keyword extraction expert. Extract the most relevant keywords from the given text.",
            'user_prompt_template': "Extract {max_keywords} keywords from the following text:\n\n{text}\n\nKeywords:"
        }