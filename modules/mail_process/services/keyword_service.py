"""키워드 추출 서비스 (구조화된 응답 및 개선된 프롬프트)"""

import re
import time
import json
import asyncio
import aiohttp
from collections import Counter
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime
from infra.core.config import get_config
from infra.core.logger import get_logger
from modules.mail_process.mail_processor_schema import KeywordExtractionResponse


class MailKeywordService:
    """메일 키워드 추출 서비스 (배치 처리 지원)"""

    def __init__(self):
        self.config = get_config()
        self.logger = get_logger(__name__)

        # OpenRouter 설정
        self.api_key = getattr(self.config, "openrouter_api_key", None)
        self.model = getattr(self.config, "openrouter_model", "openai/gpt-3.5-turbo")
        self.base_url = "https://openrouter.ai/api/v1"
        self.max_keywords = int(getattr(self.config, "max_keywords_per_mail", 5))

        # 배치 처리 설정
        self.batch_size = int(self.config.get_setting("KEYWORD_EXTRACTION_BATCH_SIZE", "50"))
        self.concurrent_requests = int(self.config.get_setting("KEYWORD_EXTRACTION_CONCURRENT_REQUESTS", "5"))
        self.batch_timeout = int(self.config.get_setting("KEYWORD_EXTRACTION_BATCH_TIMEOUT", "60"))
        
        # 구조화된 응답 사용 여부
        self.use_structured_response = self.config.get_setting("USE_STRUCTURED_KEYWORD_RESPONSE", "true").lower() == "true"
        
        # 재사용 가능한 세션
        self._session: Optional[aiohttp.ClientSession] = None
        
        self.logger.info(
            f"키워드 서비스 초기화: batch_size={self.batch_size}, "
            f"concurrent_requests={self.concurrent_requests}, "
            f"structured_response={self.use_structured_response}"
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

    async def extract_keywords_batch(self, mail_contents: List[Dict[str, str]]) -> List[List[str]]:
        """
        여러 메일의 키워드를 배치로 추출
        
        Args:
            mail_contents: [{"content": "본문", "subject": "제목"}, ...] 형식의 리스트
            
        Returns:
            각 메일별 키워드 리스트
        """
        if not mail_contents:
            return []
        
        start_time = time.time()
        self.logger.info(f"키워드 배치 추출 시작: {len(mail_contents)}개 메일")
        
        # 너무 짧은 텍스트 사전 필터링
        valid_indices = []
        valid_mails = []
        
        for i, mail_data in enumerate(mail_contents):
            content = mail_data.get('content', '') if isinstance(mail_data, dict) else str(mail_data)
            if content and len(content.strip()) >= 10:
                valid_indices.append(i)
                valid_mails.append(mail_data)
        
        # 모든 텍스트가 너무 짧은 경우
        if not valid_mails:
            self.logger.warning("모든 메일 내용이 너무 짧음")
            return [[] for _ in mail_contents]
        
        # 결과 초기화
        results = [[] for _ in mail_contents]
        
        try:
            # OpenRouter API 사용 가능한 경우
            if self.api_key:
                # 배치를 더 작은 청크로 나누어 처리
                for chunk_start in range(0, len(valid_mails), self.batch_size):
                    chunk_end = min(chunk_start + self.batch_size, len(valid_mails))
                    chunk_mails = valid_mails[chunk_start:chunk_end]
                    chunk_indices = valid_indices[chunk_start:chunk_end]
                    
                    # 동시 처리
                    chunk_results = await self._process_chunk_concurrent(chunk_mails)
                    
                    # 결과 저장
                    for i, keywords in enumerate(chunk_results):
                        original_index = chunk_indices[i]
                        results[original_index] = keywords
                    
                    # API 속도 제한 고려
                    if chunk_end < len(valid_mails):
                        await asyncio.sleep(0.5)
                        
            else:
                # Fallback: 동기적 처리
                self.logger.warning("API 키 없음, fallback 사용")
                for i, mail_data in zip(valid_indices, valid_mails):
                    content = mail_data.get('content', '') if isinstance(mail_data, dict) else str(mail_data)
                    results[i] = self._fallback_keyword_extraction(content)
            
        except Exception as e:
            self.logger.error(f"배치 키워드 추출 실패: {str(e)}")
            # 실패 시 모든 텍스트에 대해 fallback 사용
            for i, mail_data in zip(valid_indices, valid_mails):
                if not results[i]:  # 아직 처리되지 않은 경우
                    content = mail_data.get('content', '') if isinstance(mail_data, dict) else str(mail_data)
                    results[i] = self._fallback_keyword_extraction(content)
        
        elapsed = time.time() - start_time
        self.logger.info(
            f"키워드 배치 추출 완료: {len(mail_contents)}개 메일, "
            f"{elapsed:.2f}초 소요"
        )
        
        return results

    async def _process_chunk_concurrent(self, mail_contents: List[Any]) -> List[List[str]]:
        """
        청크를 동시에 처리
        
        Args:
            mail_contents: 처리할 메일 청크
            
        Returns:
            각 메일의 키워드 리스트
        """
        # 세마포어로 동시 요청 수 제한
        semaphore = asyncio.Semaphore(self.concurrent_requests)
        
        async def process_with_semaphore(mail_data: Any) -> List[str]:
            async with semaphore:
                try:
                    # 구조화된 응답 사용 여부에 따라 다른 함수 호출
                    if self.use_structured_response:
                        if isinstance(mail_data, dict):
                            content = mail_data.get('content', '')
                            subject = mail_data.get('subject', '')
                        else:
                            content = str(mail_data)
                            subject = ''
                        
                        result = await self._call_openrouter_structured_api(content, subject)
                        if result and 'keywords' in result:
                            keywords = result['keywords']
                            # 프롬프트 로깅
                            if 'prompt_used' in result:
                                self.logger.debug(f"사용된 프롬프트 길이: {len(result['prompt_used'])} 문자")
                            return keywords
                    else:
                        content = mail_data.get('content', '') if isinstance(mail_data, dict) else str(mail_data)
                        keywords, _ = await self._call_openrouter_api(content)
                        if keywords:
                            return keywords
                    
                    content = mail_data.get('content', '') if isinstance(mail_data, dict) else str(mail_data)
                    return self._fallback_keyword_extraction(content)
                except Exception as e:
                    self.logger.warning(f"개별 API 호출 실패: {str(e)}")
                    content = mail_data.get('content', '') if isinstance(mail_data, dict) else str(mail_data)
                    return self._fallback_keyword_extraction(content)
        
        # 모든 태스크를 동시에 실행
        tasks = [process_with_semaphore(mail_data) for mail_data in mail_contents]
        
        # 타임아웃 설정
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=self.batch_timeout
            )
        except asyncio.TimeoutError:
            self.logger.error(f"배치 처리 타임아웃 ({self.batch_timeout}초)")
            # 타임아웃 시 fallback 사용
            results = []
            for mail_data in mail_contents:
                content = mail_data.get('content', '') if isinstance(mail_data, dict) else str(mail_data)
                results.append(self._fallback_keyword_extraction(content))
        
        # 예외 처리
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.warning(f"태스크 {i} 실패: {str(result)}")
                content = mail_contents[i].get('content', '') if isinstance(mail_contents[i], dict) else str(mail_contents[i])
                processed_results.append(self._fallback_keyword_extraction(content))
            else:
                processed_results.append(result)
        
        return processed_results

    async def extract_keywords(self, clean_content: str, subject: str = "") -> List[str]:
        """
        단일 텍스트에서 키워드 추출 (기존 메서드 유지)
        
        Args:
            clean_content: 이미 정제된 메일 내용
            subject: 메일 제목 (선택사항)
            
        Returns:
            추출된 키워드 리스트
        """
        start_time = time.time()

        try:
            # 너무 짧은 텍스트는 빈 리스트 반환
            if len(clean_content.strip()) < 10:
                return []

            # 구조화된 응답 사용
            if self.use_structured_response and self.api_key:
                result = await self._call_openrouter_structured_api(clean_content, subject)
                if result and 'keywords' in result:
                    keywords = result['keywords']
                    # 프롬프트 로깅
                    if 'prompt_used' in result:
                        self.logger.debug(f"사용된 프롬프트 길이: {len(result['prompt_used'])} 문자")
                    self.logger.debug(f"키워드 추출 성공: {keywords}")
                    
                    # 추가 정보도 로깅
                    if 'mail_type' in result:
                        self.logger.debug(f"메일 타입: {result['mail_type']}")
                    if 'has_deadline' in result:
                        self.logger.debug(f"마감일 여부: {result['has_deadline']}")
                    
                    return keywords

            # 기존 API 호출
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
            self.logger.debug("새로운 키워드 서비스 세션 생성")
        return self._session

    async def _call_openrouter_structured_api(self, content: str, subject: str = "") -> Optional[Dict]:
        """
        OpenRouter API 호출 (구조화된 응답)
        
        Args:
            content: 메일 본문
            subject: 메일 제목 (선택사항)
            
        Returns:
            {'keywords': [...], 'mail_type': ..., 'has_deadline': ..., 'prompt_used': ...}
        """
        if not self.api_key:
            self.logger.error("OpenRouter API 키가 설정되지 않음")
            return None

        # 텍스트 길이 제한
        limited_content = content[:2000] if len(content) > 2000 else content
        
        # 제공된 프롬프트 사용
        system_prompt = """You are an email analysis expert. Extract information from emails and return ONLY valid JSON."""

        user_prompt = f"""Extract the following information and return ONLY valid JSON:
{{
  "summary": "Brief summary of the email content (1-2 sentences)",
  "deadline": "YYYY-MM-DD HH:MM:SS format or null if no deadline",
  "has_deadline": true or false,
  "mail_type": "REQUEST" or "RESPONSE" or "NOTIFICATION" or "COMPLETED" or "OTHER",
  "keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"],
  "pl_patterns": [
    {{
      "full_pattern": "Complete pattern like PL25003_ILa",
      "panel_name": "Panel code (e.g., PL)",
      "year": "2-digit year (e.g., 25)",
      "agenda_number": "3-digit number (e.g., 003)",
      "round_version": "Round letter or null (e.g., null, a, b, c)",
      "organization_code": "Organization code (e.g., IL)",
      "sequence": "Sequence letter or null (e.g., a, b, c)",
      "organization_name": "Full organization name",
      "reply_version": "Reply version or null (e.g., null, a, b, c)"
    }}
  ]
}}
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
6. Determine mail_type:
   - REQUEST: asking for action, response, or submission
   - RESPONSE: replying to a request (e.g., "I prefer option 2", "Here are my comments", "Dear Chair")
   - NOTIFICATION: informing about events, decisions, or updates
   - COMPLETED: summarizing or compiling multiple opinions/responses from different parties (e.g., "Following are the compiled comments from members", "Summary of responses received", "Consolidated feedback from all parties")
   - OTHER: doesn't fit above categories
7. Return ONLY the JSON object, no additional text

Email Subject: {subject if subject else "No subject"}
Email Content:
{limited_content}"""

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "max_tokens": 500,
            "temperature": 0.1,
        }

        # response_format이 지원되는 모델인 경우 추가
        if "gpt-4" in self.model or "gpt-3.5-turbo" in self.model:
            payload["response_format"] = {"type": "json_object"}

        try:
            session = await self._get_session()
            
            # 프롬프트 로깅
            full_prompt = f"{system_prompt}\n\n{user_prompt}"
            self.logger.info(f"구조화된 API 호출 - 프롬프트 길이: {len(full_prompt)} 문자")
            
            # 프롬프트의 일부만 로깅 (전체가 너무 길 수 있음)
            self.logger.debug(f"프롬프트 시작 부분 (500자):\n{full_prompt[:500]}...")

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
                
                # OpenRouter API 원본 응답 로깅
                self.logger.info("=== OpenRouter API 원본 응답 ===")
                self.logger.info(json.dumps(data, ensure_ascii=False, indent=2))
                self.logger.info("=================================")

                # 응답에서 컨텐츠 추출
                if "choices" in data and data["choices"]:
                    choice = data["choices"][0]
                    if "message" in choice and "content" in choice["message"]:
                        content_response = choice["message"]["content"]
                        
                        # API가 반환한 content 내용 로깅
                        self.logger.info("=== OpenRouter API content 응답 ===")
                        self.logger.info(content_response)
                        self.logger.info("===================================")
                        
                        # JSON 파싱 시도
                        try:
                            result = json.loads(content_response)
                            
                            # 응답받은 JSON 전체를 로그로 출력
                            self.logger.info("=== OpenRouter API 응답 JSON ===")
                            self.logger.info(json.dumps(result, ensure_ascii=False, indent=2))
                            self.logger.info("================================")
                            
                            # 각 필드별 상세 로깅
                            self.logger.debug(f"요약: {result.get('summary', 'N/A')}")
                            self.logger.debug(f"마감일: {result.get('deadline', 'N/A')}")
                            self.logger.debug(f"마감일 존재: {result.get('has_deadline', False)}")
                            self.logger.debug(f"메일 타입: {result.get('mail_type', 'N/A')}")
                            
                            # PL 패턴 로깅
                            pl_patterns = result.get('pl_patterns', [])
                            if pl_patterns:
                                self.logger.debug(f"PL 패턴 수: {len(pl_patterns)}")
                                for idx, pattern in enumerate(pl_patterns):
                                    self.logger.debug(f"  패턴 {idx+1}: {pattern.get('full_pattern', 'N/A')}")
                            
                            # 키워드 검증 및 정제
                            keywords = result.get('keywords', [])
                            if isinstance(keywords, list):
                                # 키워드 개수 제한
                                keywords = keywords[:self.max_keywords]
                                # 빈 문자열 제거
                                keywords = [k.strip() for k in keywords if k and k.strip()]
                                result['keywords'] = keywords
                                self.logger.debug(f"추출된 키워드: {keywords}")
                            else:
                                result['keywords'] = []
                                self.logger.warning("키워드가 리스트 형식이 아님")
                            
                            # 사용된 프롬프트 추가 (전체 대신 길이만)
                            result['prompt_used'] = full_prompt
                            
                            # 토큰 사용량 정보 추가
                            if "usage" in data:
                                result['token_usage'] = data["usage"]
                                self.logger.info(
                                    f"토큰 사용량 - "
                                    f"입력: {data['usage'].get('prompt_tokens', 0)}, "
                                    f"출력: {data['usage'].get('completion_tokens', 0)}, "
                                    f"총합: {data['usage'].get('total_tokens', 0)}"
                                )
                            
                            self.logger.info(
                                f"구조화된 응답 처리 완료: "
                                f"키워드 {len(keywords)}개, "
                                f"메일타입: {result.get('mail_type', 'UNKNOWN')}, "
                                f"마감일: {result.get('has_deadline', False)}"
                            )
                            
                            return result
                            
                        except json.JSONDecodeError as e:
                            self.logger.warning(f"JSON 파싱 실패: {str(e)}")
                            self.logger.debug(f"응답 내용: {content_response[:200]}...")
                            # JSON 파싱 실패 시 기존 방식으로 파싱
                            keywords = self._parse_keywords(content_response)
                            return {
                                'keywords': keywords[:self.max_keywords],
                                'prompt_used': full_prompt
                            }

                return None

        except aiohttp.ClientError as e:
            self.logger.error(f"OpenRouter API 네트워크 오류: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"OpenRouter 구조화된 API 호출 실패: {str(e)}")
            return None

    async def _call_openrouter_api(self, text: str) -> Tuple[List[str], dict]:
        """OpenRouter API 호출 (기존 방식)"""
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

        except aiohttp.ClientError as e:
            self.logger.error(f"OpenRouter API 네트워크 오류: {str(e)}")
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

    def get_batch_statistics(self) -> Dict[str, Any]:
        """배치 처리 통계 반환"""
        return {
            "batch_size": self.batch_size,
            "concurrent_requests": self.concurrent_requests,
            "batch_timeout": self.batch_timeout,
            "api_enabled": bool(self.api_key),
            "model": self.model if self.api_key else "fallback",
            "use_structured_response": self.use_structured_response
        }

    def __del__(self):
        """소멸자 - 세션 정리 시도 (최후의 수단)"""
        if hasattr(self, '_session') and self._session and not self._session.closed:
            try:
                # 동기적으로 세션 정리 시도
                import asyncio
                import warnings
                
                # 경고 무시 (Python 종료 시 발생하는 경고들)
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    
                    # 이벤트 루프가 실행 중인지 확인
                    try:
                        loop = asyncio.get_running_loop()
                        if loop and not loop.is_closed():
                            # 이미 실행 중인 루프에서는 새 태스크 생성하지 않음
                            pass
                    except RuntimeError:
                        # 실행 중인 루프가 없는 경우
                        try:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            loop.run_until_complete(self._session.close())
                            loop.close()
                        except:
                            pass
            except:
                pass  # 소멸자에서는 모든 예외를 무시