"""키워드 추출 서비스"""

import re
import time
import json
import aiohttp
from collections import Counter
from typing import List, Optional, Tuple
from infra.core.config import get_config
from infra.core.logger import get_logger
from modules.mail_processor.mail_processor_schema import KeywordExtractionResponse


class MailKeywordService:
    """메일 키워드 추출 서비스"""

    def __init__(self):
        self.config = get_config()
        self.logger = get_logger(__name__)

        # OpenRouter 설정
        self.api_key = getattr(self.config, "openrouter_api_key", None)
        self.model = getattr(self.config, "openrouter_model", "openai/gpt-3.5-turbo")
        self.base_url = "https://openrouter.ai/api/v1"
        self.max_keywords = int(getattr(self.config, "max_keywords_per_mail", 5))

        # 재사용 가능한 세션
        self._session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        self._session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        if self._session:
            await self._session.close()
            self._session = None

    async def extract_keywords(self, clean_content: str) -> List[str]:
        """
        정제된 내용에서 키워드 추출
        
        Args:
            clean_content: 이미 정제된 메일 내용
            
        Returns:
            추출된 키워드 리스트
        """
        start_time = time.time()

        try:
            # 너무 짧은 텍스트는 빈 리스트 반환
            if len(clean_content.strip()) < 10:
                return []

            # OpenRouter API 호출
            if self.api_key:
                keywords, token_info = await self._call_openrouter_api(clean_content)
                if keywords:
                    self.logger.debug(f"키워드 추출 성공: {keywords}")
                    return keywords

            # Fallback 키워드 추출
            keywords = self._fallback_keyword_extraction(clean_content)
            return keywords

        except Exception as e:
            self.logger.warning(f"키워드 추출 실패, fallback 사용: {str(e)}")
            return self._fallback_keyword_extraction(clean_content)

    async def _get_session(self) -> aiohttp.ClientSession:
        """세션 가져오기 (필요시 생성)"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def _call_openrouter_api(self, text: str) -> Tuple[List[str], dict]:
        """OpenRouter API 호출"""
        if not self.api_key:
            self.logger.error("OpenRouter API 키가 설정되지 않음")
            return [], {}

        # 텍스트 길이 제한
        limited_text = text[:1000] if len(text) > 1000 else text

        # 간단한 프롬프트
        prompt = f"Extract {self.max_keywords} keywords from this email: {limited_text}\n\nKeywords:"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 100,
            "temperature": 0.3,
        }

        token_info = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "cost_usd": 0.0,
        }

        session = None
        try:
            session = await self._get_session()

            async with session.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:

                if response.status != 200:
                    response_text = await response.text()
                    self.logger.error(f"API 오류: {response_text}")
                    return [], token_info

                data = await response.json()

                # 토큰 사용량 정보 추출
                if "usage" in data:
                    usage = data["usage"]
                    token_info.update({
                        "prompt_tokens": usage.get("prompt_tokens", 0),
                        "completion_tokens": usage.get("completion_tokens", 0),
                        "total_tokens": usage.get("total_tokens", 0),
                    })

                # 응답에서 컨텐츠 추출
                if "choices" in data and data["choices"]:
                    choice = data["choices"][0]
                    if "message" in choice and "content" in choice["message"]:
                        content = choice["message"]["content"]
                        if content and content.strip():
                            keywords = self._parse_keywords(content)
                            return keywords[:self.max_keywords], token_info

                return [], token_info

        except Exception as e:
            self.logger.error(f"OpenRouter API 호출 실패: {str(e)}")
            return [], token_info

    def _fallback_keyword_extraction(self, text: str) -> List[str]:
        """Fallback 키워드 추출"""
        # 한국어 단어 추출 (2글자 이상)
        korean_words = re.findall(r"[가-힣]{2,}", text)

        # 영문 단어 추출 (3글자 이상)
        english_words = re.findall(r"[A-Za-z]{3,}", text)

        # 숫자 포함 식별자 추출
        identifiers = re.findall(r"[A-Z]{2,}\d+|[A-Z]+-\d+|\d{3,}", text)

        # 모든 단어 합치기
        all_words = korean_words + english_words + identifiers

        # 빈도수 기반 상위 키워드 선택
        word_counts = Counter(all_words)
        top_keywords = [word for word, count in word_counts.most_common(self.max_keywords)]

        return top_keywords

    def _parse_keywords(self, content: str) -> List[str]:
        """키워드 응답 파싱"""
        keywords = []

        # 1. 번호 매김 형식
        if re.search(r"\d+\.\s*", content):
            lines = content.split("\n")
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                match = re.match(r"\d+\.\s*(.+)", line)
                if match:
                    keyword = match.group(1).strip()
                    if keyword:
                        keywords.append(keyword)

        # 2. 콤마로 구분된 형식
        elif "," in content:
            keywords = [kw.strip() for kw in content.split(",") if kw.strip()]

        # 3. 줄바꿈으로 구분된 형식
        elif "\n" in content:
            keywords = [line.strip() for line in content.split("\n") if line.strip()]

        # 4. 공백으로 구분된 형식
        else:
            keywords = content.split()

        # 키워드 정제
        cleaned_keywords = []
        for kw in keywords:
            kw = re.sub(r"^[^\w가-힣]+|[^\w가-힣]+$", "", kw)
            if kw and len(kw) >= 2:
                cleaned_keywords.append(kw)

        return cleaned_keywords
