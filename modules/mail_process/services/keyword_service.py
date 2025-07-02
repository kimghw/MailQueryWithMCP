"""키워드 추출 서비스 (배치 처리 및 구조화된 데이터 추출 지원)"""

import re
import time
import json
import asyncio
import aiohttp
import os
from collections import Counter
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime
from infra.core.config import get_config
from infra.core.logger import get_logger
from modules.mail_process.mail_processor_schema import KeywordExtractionResponse


class MailKeywordService:
    """메일 키워드 추출 서비스 (배치 처리 및 구조화된 데이터 추출 지원)"""

    def __init__(self):
        self.config = get_config()
        self.logger = get_logger(__name__)

        # OpenRouter 설정
        self.api_key = getattr(self.config, "openrouter_api_key", None)
        self.model = getattr(self.config, "openrouter_model", "openai/gpt-3.5-turbo")
        self.base_url = "https://openrouter.ai/api/v1"
        self.max_keywords = int(getattr(self.config, "max_keywords_per_mail", 5))

        # 배치 처리 설정
        self.batch_size = 50
        self.concurrent_requests = 5
        self.batch_timeout = 60
        
        # 구조화된 추출 모드
        self.structured_extraction = self.config.get_setting("ENABLE_STRUCTURED_EXTRACTION", "true").lower() == "true"
        
        # 재사용 가능한 세션
        self._session: Optional[aiohttp.ClientSession] = None
        
        self.logger.info(
            f"키워드 서비스 초기화: batch_size={self.batch_size}, "
            f"concurrent_requests={self.concurrent_requests}, "
            f"structured_extraction={self.structured_extraction}"
        )

    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
            self.logger.debug("키워드 서비스 세션 생성됨")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        await self.close()

    async def close(self):
        """세션 정리"""
        if self._session and not self._session.closed:
            await self._session.close()
            self.logger.debug("키워드 서비스 세션 정리됨")
            self._session = None

    async def extract_keywords_batch(self, contents: List[str]) -> List[List[str]]:
        """
        여러 텍스트의 키워드를 배치로 추출
        
        Args:
            contents: 텍스트 리스트
            
        Returns:
            각 텍스트별 키워드 리스트
        """
        if not contents:
            return []
        
        start_time = time.time()
        self.logger.info(f"키워드 배치 추출 시작: {len(contents)}개 텍스트")
        
        # 너무 짧은 텍스트 사전 필터링
        valid_indices = []
        valid_contents = []
        
        for i, content in enumerate(contents):
            if content and len(content.strip()) >= 10:
                valid_indices.append(i)
                valid_contents.append(content)
        
        # 모든 텍스트가 너무 짧은 경우
        if not valid_contents:
            self.logger.warning("모든 텍스트가 너무 짧음")
            return [[] for _ in contents]
        
        # 결과 초기화
        results = [[] for _ in contents]
        
        try:
            # OpenRouter API 사용 가능한 경우
            if self.api_key:
                # 배치를 더 작은 청크로 나누어 처리
                for chunk_start in range(0, len(valid_contents), self.batch_size):
                    chunk_end = min(chunk_start + self.batch_size, len(valid_contents))
                    chunk_contents = valid_contents[chunk_start:chunk_end]
                    chunk_indices = valid_indices[chunk_start:chunk_end]
                    
                    # 동시 처리
                    chunk_results = await self._process_chunk_concurrent(chunk_contents)
                    
                    # 결과 저장
                    for i, keywords in enumerate(chunk_results):
                        original_index = chunk_indices[i]
                        results[original_index] = keywords
                    
                    # API 속도 제한 고려
                    if chunk_end < len(valid_contents):
                        await asyncio.sleep(0.5)
                        
            else:
                # Fallback: 동기적 처리
                self.logger.warning("API 키 없음, fallback 사용")
                for i, content in zip(valid_indices, valid_contents):
                    results[i] = self._fallback_keyword_extraction(content)
            
        except Exception as e:
            self.logger.error(f"배치 키워드 추출 실패: {str(e)}")
            # 실패 시 모든 텍스트에 대해 fallback 사용
            for i, content in zip(valid_indices, valid_contents):
                if not results[i]:  # 아직 처리되지 않은 경우
                    results[i] = self._fallback_keyword_extraction(content)
        
        elapsed = time.time() - start_time
        self.logger.info(
            f"키워드 배치 추출 완료: {len(contents)}개 텍스트, "
            f"{elapsed:.2f}초 소요"
        )
        
        return results

    async def extract_structured_data(self, mail_content: str, subject: str = "") -> Dict[str, Any]:
        """
        메일에서 구조화된 데이터 추출
        
        Args:
            mail_content: 메일 본문
            subject: 메일 제목
            
        Returns:
            구조화된 데이터 딕셔너리
        """
        if not self.structured_extraction or not self.api_key:
            # 구조화된 추출이 비활성화되거나 API 키가 없는 경우 기본 키워드만 반환
            keywords = await self.extract_keywords(mail_content)
            return {
                "keywords": keywords,
                "structured_extraction": False
            }
        
        try:
            # OpenRouter API를 통한 구조화된 추출
            structured_data = await self._call_openrouter_structured_api(mail_content, subject)
            
            if structured_data:
                # 추출된 데이터 검증 및 정제
                validated_data = self._validate_structured_data(structured_data)
                validated_data["structured_extraction"] = True
                return validated_data
            else:
                # 실패 시 기본 키워드 추출로 폴백
                keywords = await self.extract_keywords(mail_content)
                return {
                    "keywords": keywords,
                    "structured_extraction": False
                }
                
        except Exception as e:
            self.logger.error(f"구조화된 데이터 추출 실패: {str(e)}")
            keywords = await self.extract_keywords(mail_content)
            return {
                "keywords": keywords,
                "structured_extraction": False,
                "error": str(e)
            }

    async def _call_openrouter_structured_api(self, content: str, subject: str) -> Optional[Dict]:
        """OpenRouter API를 통한 구조화된 데이터 추출"""
        if not self.api_key:
            return None

        # 텍스트 길이 제한
        limited_content = content[:2000] if len(content) > 2000 else content

        # 구조화된 추출을 위한 프롬프트 - f-string 포맷 문제 수정
        prompt = """
Analyze the following email and extract structured information in JSON format.

Subject: """ + subject + """
Content: """ + limited_content + """

Extract the following information and return ONLY valid JSON:
{
  "summary": "Brief summary of the email content (1-2 sentences)",
  "deadline": "YYYY-MM-DD HH:MM:SS format or null if no deadline",
  "has_deadline": true or false,
  "response_required": "MANDATORY" or "OPTIONAL" or "NONE",
  "mail_type": "REQUEST" or "RESPONSE" or "NOTIFICATION" or "COMPLETED" or "OTHER",
  "keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"],
  "pl_patterns": [
    {
      "full_pattern": "Complete pattern like PL25003_ILa",
      "panel_name": "Panel code (e.g., PL)",
      "year": "2-digit year (e.g., 25)",
      "agenda_number": "3-digit number (e.g., 003)",
      "round_version": "Round letter or null (e.g., null, a, b, c)",
      "organization_code": "Organization code (e.g., IL)",
      "sequence": "Sequence letter or null (e.g., a, b, c)",
      "organization_name": "Full organization name",
      "reply_version": "Reply version or null (e.g., null, a, b, c)"
    }
  ]
   "analysis_reasoning": {
    "mail_type_reason": "Explanation of why this mail type was chosen",
    "response_required_reason": "Explanation of response requirement classification",
    "deadline_reason": "Explanation of deadline extraction or absence",
    "key_phrases": ["phrase1", "phrase2"] // Key phrases that influenced the classification
  }
}

Rules:
1. Extract up to 5 most relevant keywords
2. For pl_patterns:
   - Look for patterns like: PL25003_ILa, MSC108/3/1, MEPC81/INF.23
   - Extract PL patterns from the email's Subject line
3. If no patterns found, return empty array for pl_patterns
4. Email chain handling:
   - ONLY analyze the MOST RECENT message (before any "From:", "Sent:", "Subject:" headers)
   - Ignore quoted or forwarded content below the main message
5. Parse deadlines carefully:
   - ONLY consider deadlines mentioned in the current sender's message
   - If email is addressed to "Chair" or "Panel Chair", do NOT treat dates as deadlines
   - Only extract deadlines directly requested by the current email sender
6. Determine response_required:
   - MANDATORY: Must respond (e.g., "please provide", "members shall", "response required")
   - OPTIONAL: Response is voluntary (e.g., "tacit acceptance applies", "if you have comments", "comments welcome", "no response means agreement")
   - NONE: No response expected (notifications, FYI emails)
7. Determine mail_type:
   - REQUEST: asking for action, response, or submission
   - RESPONSE: replying to a request (e.g., "I prefer option 2", "Here are my comments", "Dear Chair")
   - NOTIFICATION: informing about events, decisions, or updates
   - COMPLETED: summarizing/compiling multiple opinions AND may request final review (e.g., "consolidated responses", "summary received from members", "compilation of feedback")
   - OTHER: doesn't fit above categories
8. Return ONLY the JSON object, no additional text
"""

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 500,
            "temperature": 0.1,  # 낮은 temperature로 일관성 있는 JSON 출력
        }

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
                    return None

                data = await response.json()

                # 응답에서 컨텐츠 추출
                if "choices" in data and data["choices"]:
                    choice = data["choices"][0]
                    if "message" in choice and "content" in choice["message"]:
                        content = choice["message"]["content"]
                        if content and content.strip():
                            try:
                                # JSON 파싱 시도
                                # 때로는 ```json ... ``` 형태로 올 수 있으므로 정제
                                content = content.strip()
                                if content.startswith("```json"):
                                    content = content[7:]
                                if content.endswith("```"):
                                    content = content[:-3]
                                
                                structured_data = json.loads(content.strip())
                                return structured_data
                            except json.JSONDecodeError as e:
                                self.logger.error(f"JSON 파싱 실패: {str(e)}, 응답: {content[:200]}")
                                return None

                return None

        except Exception as e:
            self.logger.error(f"OpenRouter 구조화 API 호출 실패: {str(e)}")
            return None

    def _validate_structured_data(self, data: Dict) -> Dict:
        """추출된 구조화 데이터 검증 및 정제"""
        validated = {
            "summary": data.get("summary", ""),
            "deadline": None,
            "deadline_text": data.get("deadline_text"),
            "deadline_type": data.get("deadline_type"),
            "has_deadline": data.get("has_deadline", False),
            "response_required": data.get("response_required", "NONE"),
            "mail_type": data.get("mail_type", "OTHER"),
            "keywords": [],
            "pl_patterns": []
        }
        
        # 키워드 검증
        if isinstance(data.get("keywords"), list):
            validated["keywords"] = [
                str(k).strip() for k in data["keywords"][:self.max_keywords] 
                if k and str(k).strip()
            ]
        
        # 마감일 검증
        if data.get("deadline"):
            try:
                # 다양한 날짜 형식 파싱 시도
                deadline_str = str(data["deadline"])
                validated["deadline"] = self._parse_deadline(deadline_str)
            except:
                self.logger.warning(f"마감일 파싱 실패: {data.get('deadline')}")
        
        # 마감일 타입 검증
        valid_deadline_types = ["ACTION_REQUIRED", "SUBMISSION_DEADLINE", "INFORMATION_ONLY", "OTHER"]
        if validated["deadline_type"] not in valid_deadline_types:
            validated["deadline_type"] = None
        
        # 응답 필요 여부 검증
        valid_response_required = ["MANDATORY", "OPTIONAL", "NONE"]
        if validated["response_required"] not in valid_response_required:
            validated["response_required"] = "NONE"
        
        # PL 패턴 검증
        if isinstance(data.get("pl_patterns"), list):
            for pattern in data["pl_patterns"]:
                if isinstance(pattern, dict) and pattern.get("full_pattern"):
                    validated_pattern = self._validate_pl_pattern(pattern)
                    if validated_pattern:
                        validated["pl_patterns"].append(validated_pattern)
        
        # 메일 타입 검증
        valid_types = ["REQUEST", "RESPONSE", "NOTIFICATION", "COMPLETED", "OTHER"]
        if validated["mail_type"] not in valid_types:
            validated["mail_type"] = "OTHER"
        
        return validated

    def _parse_deadline(self, deadline_str: str) -> Optional[str]:
        """마감일 문자열 파싱"""
        try:
            # ISO 형식 시도
            dt = datetime.fromisoformat(deadline_str.replace('Z', '+00:00'))
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            try:
                # 다른 일반적인 형식들 시도
                from dateutil import parser
                dt = parser.parse(deadline_str)
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except:
                return None

    def _validate_pl_pattern(self, pattern: Dict) -> Optional[Dict]:
        """PL 패턴 검증"""
        try:
            return {
                "full_pattern": str(pattern.get("full_pattern", "")).strip(),
                "panel_name": str(pattern.get("panel_name", "")).strip(),
                "year": str(pattern.get("year", "")).strip(),
                "agenda_number": str(pattern.get("agenda_number", "")).strip(),
                "round_version": pattern.get("round_version"),
                "organization_code": str(pattern.get("organization_code", "")).strip(),
                "sequence": pattern.get("sequence"),
                "organization_name": str(pattern.get("organization_name", "")).strip(),
                "reply_version": pattern.get("reply_version")
            }
        except:
            return None

    async def _process_chunk_concurrent(self, contents: List[str]) -> List[List[str]]:
        """청크를 동시에 처리"""
        semaphore = asyncio.Semaphore(self.concurrent_requests)
        
        async def process_with_semaphore(content: str) -> List[str]:
            async with semaphore:
                try:
                    keywords, _ = await self._call_openrouter_api(content)
                    return keywords if keywords else self._fallback_keyword_extraction(content)
                except Exception as e:
                    self.logger.warning(f"개별 API 호출 실패: {str(e)}")
                    return self._fallback_keyword_extraction(content)
        
        tasks = [process_with_semaphore(content) for content in contents]
        
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=self.batch_timeout
            )
        except asyncio.TimeoutError:
            self.logger.error(f"배치 처리 타임아웃 ({self.batch_timeout}초)")
            results = [self._fallback_keyword_extraction(content) for content in contents]
        
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.warning(f"태스크 {i} 실패: {str(result)}")
                processed_results.append(self._fallback_keyword_extraction(contents[i]))
            else:
                processed_results.append(result)
        
        return processed_results

    async def extract_keywords(self, clean_content: str) -> List[str]:
        """단일 텍스트에서 키워드 추출 (기존 메서드 유지)"""
        start_time = time.time()

        try:
            if len(clean_content.strip()) < 10:
                return []

            if self.api_key:
                keywords, token_info = await self._call_openrouter_api(clean_content)
                if keywords:
                    self.logger.debug(f"키워드 추출 성공: {keywords}")
                    return keywords

            keywords = self._fallback_keyword_extraction(clean_content)
            return keywords

        except Exception as e:
            self.logger.warning(f"키워드 추출 실패, fallback 사용: {str(e)}")
            return self._fallback_keyword_extraction(clean_content)

    async def _get_session(self) -> aiohttp.ClientSession:
        """세션 가져오기 (필요시 생성)"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
            self.logger.debug("새로운 키워드 서비스 세션 생성")
        return self._session

    async def _call_openrouter_api(self, text: str) -> Tuple[List[str], dict]:
        """OpenRouter API 호출 (기본 키워드 추출)"""
        if not self.api_key:
            self.logger.error("OpenRouter API 키가 설정되지 않음")
            return [], {}

        limited_text = text[:1000] if len(text) > 1000 else text
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

                if "usage" in data:
                    usage = data["usage"]
                    token_info.update({
                        "prompt_tokens": usage.get("prompt_tokens", 0),
                        "completion_tokens": usage.get("completion_tokens", 0),
                        "total_tokens": usage.get("total_tokens", 0),
                    })

                if "choices" in data and data["choices"]:
                    choice = data["choices"][0]
                    if "message" in choice and "content" in choice["message"]:
                        content = choice["message"]["content"]
                        if content and content.strip():
                            keywords = self._parse_keywords(content)
                            return keywords[:self.max_keywords], token_info

                return [], token_info

        except aiohttp.ClientError as e:
            self.logger.error(f"OpenRouter API 네트워크 오류: {str(e)}")
            return [], token_info
        except Exception as e:
            self.logger.error(f"OpenRouter API 호출 실패: {str(e)}")
            return [], token_info

    def _fallback_keyword_extraction(self, text: str) -> List[str]:
        """Fallback 키워드 추출"""
        # PL 패턴 추출
        pl_patterns = re.findall(r'[A-Z]{2,}\d{2,}(?:/\d+)?(?:[/_][A-Z]+\d*)?', text)
        
        # 한국어 단어 추출 (2글자 이상)
        korean_words = re.findall(r"[가-힣]{2,}", text)

        # 영문 단어 추출 (3글자 이상)
        english_words = re.findall(r"[A-Za-z]{3,}", text)

        # 숫자 포함 식별자 추출
        identifiers = re.findall(r"[A-Z]{2,}\d+|[A-Z]+-\d+|\d{3,}", text)

        # 모든 단어 합치기
        all_words = korean_words + english_words + identifiers + pl_patterns

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

    def get_batch_statistics(self) -> Dict[str, Any]:
        """배치 처리 통계 반환"""
        return {
            "batch_size": self.batch_size,
            "concurrent_requests": self.concurrent_requests,
            "batch_timeout": self.batch_timeout,
            "api_enabled": bool(self.api_key),
            "model": self.model if self.api_key else "fallback",
            "structured_extraction": self.structured_extraction
        }

    def __del__(self):
        """소멸자 - 세션 정리 시도 (최후의 수단)"""
        if hasattr(self, '_session') and self._session and not self._session.closed:
            try:
                import asyncio
                import warnings
                
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    
                    try:
                        loop = asyncio.get_running_loop()
                        if loop and not loop.is_closed():
                            pass
                    except RuntimeError:
                        try:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            loop.run_until_complete(self._session.close())
                            loop.close()
                        except:
                            pass
            except:
                pass
