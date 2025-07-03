"""키워드 추출 서비스 (구조화된 응답 및 개선된 프롬프트)"""

import re
import time
import json
import asyncio
import aiohttp
from collections import Counter
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime
from pathlib import Path
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
        
        # 프롬프트 로드
        self._load_prompts()
        
        self.logger.info(
            f"키워드 서비스 초기화: batch_size={self.batch_size}, "
            f"concurrent_requests={self.concurrent_requests}, "
            f"structured_response={self.use_structured_response}"
        )

    def _load_prompts(self):
        """프롬프트 파일 로드 - Rules를 USER_PROMPT에 포함"""
        try:
            # 현재 파일의 디렉토리를 기준으로 프롬프트 파일 경로 찾기
            current_dir = Path(__file__).parent.parent
            prompt_file = current_dir / "prompts" / "structured_extraction_prompt.txt"
            
            if prompt_file.exists():
                content = prompt_file.read_text(encoding='utf-8')
                
                # 1. SYSTEM_PROMPT 추출
                system_match = re.search(r'## SYSTEM_PROMPT\s*\n(.*?)(?=\n##|\n#|$)', content, re.DOTALL)
                if system_match:
                    self.system_prompt = system_match.group(1).strip()
                else:
                    self.system_prompt = "You are an email analysis expert. Extract information from emails and return ONLY valid JSON."
                
                # 2. USER_PROMPT_TEMPLATE 추출 (Email Subject: 부분까지 포함)
                user_match = re.search(r'## USER_PROMPT_TEMPLATE\s*\n(.*?)$', content, re.DOTALL)
                if user_match:
                    user_template_content = user_match.group(1).strip()
                else:
                    user_template_content = ""
                
                # 3. Rules 섹션 추출 (# Rules부터 ## USER_PROMPT_TEMPLATE 전까지)
                rules_match = re.search(r'# Rules\s*\n(.*?)(?=## USER_PROMPT_TEMPLATE)', content, re.DOTALL)
                if rules_match:
                    rules_content = rules_match.group(1).strip()
                else:
                    rules_content = ""
                
                # 4. Rules와 USER_PROMPT_TEMPLATE을 결합
                # 프롬프트 파일에 이미 플레이스홀더가 있는지 확인
                if '{subject}' in user_template_content and '{content}' in user_template_content:
                    # 이미 플레이스홀더가 있으면 Rules만 추가
                    if rules_content:
                        self.user_prompt_template = f"""Follow these rules to analyze the email:

{rules_content}

{user_template_content}"""
                    else:
                        self.user_prompt_template = user_template_content
                else:
                    # 플레이스홀더가 없으면 추가
                    if rules_content:
                        self.user_prompt_template = f"""Follow these rules to analyze the email:

{rules_content}

{user_template_content}

Email Subject: {{subject}}
Email Sent Time: {{sent_time}}
Email Content:
{{content}}"""
                    else:
                        self.user_prompt_template = f"""{user_template_content}

Email Subject: {{subject}}
Email Sent Time: {{sent_time}}
Email Content:
{{content}}"""
                
                self.logger.info("프롬프트 파일 로드 완료")
                self.logger.debug(f"System prompt 길이: {len(self.system_prompt)}자")
                self.logger.debug(f"User prompt template 길이: {len(self.user_prompt_template)}자")
                self.logger.debug(f"Rules 포함 여부: {'예' if rules_content else '아니오'}")
                
            else:
                self.logger.warning(f"프롬프트 파일을 찾을 수 없음: {prompt_file}")
                self._use_default_prompts()
                
        except Exception as e:
            self.logger.error(f"프롬프트 파일 로드 실패: {str(e)}")
            self._use_default_prompts()
    
    def _use_default_prompts(self):
        """기본 프롬프트 사용 (파일 로드 실패 시)"""
        self.system_prompt = "You are an email analysis expert. Extract information from emails and return ONLY valid JSON."
        self.user_prompt_template = """Extract the following information and return ONLY valid JSON:
{{
  "summary": "Brief summary of the email content (1-2 sentences)",
  "deadline": "YYYY-MM-DD HH:MM:SS format or null if no deadline",
  "has_deadline": true or false,
  "mail_type": "REQUEST" or "RESPONSE" or "NOTIFICATION" or "COMPLETED" or "OTHER",
  "keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"]
}}

Email Subject: {subject}
Email Sent Time: {sent_time}
Email Content:
{content}"""

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
                            sent_time = mail_data.get('sent_time')
                        else:
                            content = str(mail_data)
                            subject = ''
                            sent_time = None
                        
                        result = await self._call_openrouter_structured_api(
                            content, 
                            subject, 
                            sent_time
                        )
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

    async def extract_keywords(self, clean_content: str, subject: str = "", sent_time: datetime = None) -> List[str]:
        """
        단일 텍스트에서 키워드 추출 (기존 메서드 유지)
        
        Args:
            clean_content: 이미 정제된 메일 내용
            subject: 메일 제목 (선택사항)
            sent_time: 메일 발송 시간 (선택사항)
            
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
                result = await self._call_openrouter_structured_api(clean_content, subject, sent_time)
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

    async def _call_openrouter_structured_api(self, content: str, subject: str = "", sent_time: datetime = None) -> Optional[Dict]:
        """
        OpenRouter API 호출 (구조화된 응답)
        
        Args:
            content: 메일 본문
            subject: 메일 제목 (선택사항)
            sent_time: 메일 발송 시간 (선택사항)
            
        Returns:
            {'keywords': [...], 'mail_type': ..., 'has_deadline': ..., 'prompt_used': ...}
        """
        if not self.api_key:
            self.logger.error("OpenRouter API 키가 설정되지 않음")
            return None

        # 텍스트 길이 제한
        limited_content = content[:2000] if len(content) > 2000 else content
        
        # 발송 시간 포맷팅
        sent_time_str = sent_time.isoformat() if sent_time else "Unknown"
        original_content = content  # 전체 내용 보존
        
        # 프롬프트 템플릿에 값 채우기 - format() 대신 replace() 사용
        try:
            user_prompt = self.user_prompt_template
            user_prompt = user_prompt.replace('{subject}', subject if subject else "No subject")
            user_prompt = user_prompt.replace('{content}', limited_content)
            user_prompt = user_prompt.replace('{sent_time}', sent_time_str)
        except Exception as e:
            self.logger.error(f"프롬프트 템플릿 처리 오류: {str(e)}")
            # 기본 프롬프트 사용
            user_prompt = f"""Extract keywords from this email and return JSON:
Subject: {subject}
Sent: {sent_time_str}
Content: {limited_content}"""

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.system_prompt},
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
            
            # 프롬프트 로깅 (디버그 레벨로 변경)
            full_prompt = f"{self.system_prompt}\n\n{user_prompt}"
            self.logger.debug(f"구조화된 API 호출 - 프롬프트 길이: {len(full_prompt)} 문자")
            
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
                    self.logger.error(f"API 오류: Status {response.status}, Response: {response_text}")
                    return None

                data = await response.json()
                
                # OpenRouter API 원본 응답 로깅 (디버그 레벨로 변경)
                self.logger.debug("=== OpenRouter API 원본 응답 ===")
                self.logger.debug(json.dumps(data, ensure_ascii=False, indent=2))
                self.logger.debug("=================================")

                # 응답에서 컨텐츠 추출
                if "choices" in data and data["choices"]:
                    choice = data["choices"][0]
                    if "message" in choice and "content" in choice["message"]:
                        content_response = choice["message"]["content"]
                        
                        # content_response가 None이거나 빈 문자열인지 확인
                        if not content_response:
                            self.logger.error("API 응답의 content가 비어있음")
                            return None
                        
                        # API가 반환한 content 내용 로깅 (디버그 레벨로 변경)
                        self.logger.debug("=== OpenRouter API content 응답 ===")
                        self.logger.debug(content_response)
                        self.logger.debug("===================================")
                        
                        # JSON 파싱 시도
                        try:
                            result = self._parse_json_response(content_response)
                            
                            # 응답 검증 및 필드 보정
                            validated_result = self._validate_and_fix_response(result, subject, sent_time_str)
                            
                            # 응답받은 JSON 전체를 로그로 출력 (디버그 레벨로 변경)
                            self.logger.debug("=== 검증된 API 응답 JSON ===")
                            self.logger.debug(json.dumps(validated_result, ensure_ascii=False, indent=2))
                            self.logger.debug("================================")
                            
                            # 각 필드별 상세 로깅
                            self.logger.debug(f"요약: {validated_result.get('summary', 'N/A')}")
                            self.logger.debug(f"마감일: {validated_result.get('deadline', 'N/A')}")
                            self.logger.debug(f"마감일 존재: {validated_result.get('has_deadline', False)}")
                            self.logger.debug(f"메일 타입: {validated_result.get('mail_type', 'N/A')}")
                            
                            # 키워드 검증 및 정제
                            keywords = validated_result.get('keywords', [])
                            if isinstance(keywords, list):
                                # 키워드 개수 제한
                                keywords = keywords[:self.max_keywords]
                                # 빈 문자열 제거
                                keywords = [k.strip() for k in keywords if k and k.strip()]
                                validated_result['keywords'] = keywords
                                self.logger.debug(f"추출된 키워드: {keywords}")
                            else:
                                validated_result['keywords'] = []
                                self.logger.warning("키워드가 리스트 형식이 아님")
                            
                            # 사용된 프롬프트 추가 (전체 대신 길이만)
                            validated_result['prompt_used'] = full_prompt
                            
                            # 토큰 사용량 정보 추가
                            if "usage" in data:
                                validated_result['token_usage'] = data["usage"]
                                self.logger.debug(
                                    f"토큰 사용량 - "
                                    f"입력: {data['usage'].get('prompt_tokens', 0)}, "
                                    f"출력: {data['usage'].get('completion_tokens', 0)}, "
                                    f"총합: {data['usage'].get('total_tokens', 0)}"
                                )
                            
                            # 결과를 파일로 저장
                            self._save_analysis_result(validated_result, subject, original_content)
                            
                            return validated_result
                            
                        except json.JSONDecodeError as e:
                            self.logger.warning(f"JSON 파싱 실패: {str(e)}")
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

    def _parse_json_response(self, content_response: str) -> Dict:
        """JSON 응답 파싱 (코드 블록 처리 포함)"""
        if not content_response:
            raise json.JSONDecodeError("Empty response", "", 0)
        
        # 첫 번째 시도: 직접 파싱
        try:
            return json.loads(content_response)
        except json.JSONDecodeError:
            pass
        
        # 두 번째 시도: 코드 블록 제거
        if content_response.strip().startswith('```'):
            lines = content_response.strip().split('\n')
            if lines[0].strip() in ['```json', '```']:
                lines = lines[1:]
            if lines and lines[-1].strip() == '```':
                lines = lines[:-1]
            clean_json = '\n'.join(lines)
            
            if clean_json.strip():
                return json.loads(clean_json)
        
        raise json.JSONDecodeError("Failed to parse JSON", content_response, 0)

    def _validate_and_fix_response(self, result: Dict, subject: str, sent_time_str: str) -> Dict:
        """응답 검증 및 누락된 필드 추가/수정"""
        
        # 필수 필드 목록
        required_fields = {
            'summary': '',
            'deadline': None,
            'has_deadline': False,
            'mail_type': 'OTHER',
            'decision_status': 'comment',
            'keywords': [],
            'sender_type': 'MEMBER',
            'sender_organization': None,
            'send_time': sent_time_str,
            'agenda_no': None,
            'agenda_info': {
                'full_pattern': None,
                'panel_name': None,
                'year': None,
                'round_no': None,
                'round_version': None,
                'organization_code': None,
                'sequence': None,
                'reply_version': None
            }
        }
        
        # 검증된 결과 초기화
        validated_result = {}
        
        # 1. 필수 필드 확인 및 기본값 설정
        for field, default_value in required_fields.items():
            if field in result:
                validated_result[field] = result[field]
            else:
                validated_result[field] = default_value
                self.logger.debug(f"누락된 필드 '{field}' 추가 (기본값: {default_value})")
        
        # 2. agenda_id를 agenda_no로 변환 (API가 잘못된 필드명 반환 시)
        if 'agenda_id' in result and 'agenda_no' not in result:
            # agenda_id가 리스트인 경우 첫 번째 요소 사용
            if isinstance(result['agenda_id'], list) and result['agenda_id']:
                validated_result['agenda_no'] = result['agenda_id'][0]
            elif isinstance(result['agenda_id'], str):
                validated_result['agenda_no'] = result['agenda_id']
        
        # 3. 제목에서 정보 추출하여 누락된 필드 보완
        if subject:
            # agenda 패턴 추출 (예: PL25015_ABa)
            agenda_pattern = self._extract_agenda_pattern(subject)
            if agenda_pattern:
                # agenda_no가 없으면 패턴에서 추출
                if not validated_result['agenda_no']:
                    validated_result['agenda_no'] = agenda_pattern['base_pattern']
                
                # agenda_info가 비어있으면 패턴에서 추출
                if not validated_result['agenda_info']['full_pattern']:
                    validated_result['agenda_info'] = agenda_pattern
                
                # sender_organization이 없으면 패턴에서 추출
                if not validated_result['sender_organization'] and agenda_pattern.get('organization_code'):
                    validated_result['sender_organization'] = agenda_pattern['organization_code']
        
        # 4. mail_type 검증 (유효한 값인지 확인)
        valid_mail_types = ['REQUEST', 'RESPONSE', 'NOTIFICATION', 'COMPLETED', 'OTHER']
        if validated_result['mail_type'] not in valid_mail_types:
            validated_result['mail_type'] = 'OTHER'
        
        # 5. decision_status 검증
        valid_decision_statuses = ['created', 'comment', 'consolidated', 'review', 'decision']
        if validated_result['decision_status'] not in valid_decision_statuses:
            validated_result['decision_status'] = 'comment'
        
        # 6. sender_type 검증
        valid_sender_types = ['CHAIR', 'MEMBER']
        if validated_result['sender_type'] not in valid_sender_types:
            validated_result['sender_type'] = 'MEMBER'
        
        # 7. send_time이 "Unknown"인 경우 sent_time_str로 대체
        if validated_result['send_time'] == 'Unknown':
            validated_result['send_time'] = sent_time_str
        
        # 8. 불필요한 필드 제거 (프롬프트에 없는 필드들)
        fields_to_remove = ['keywords_count', 'agenda_id_count']
        for field in fields_to_remove:
            if field in result:
                self.logger.debug(f"불필요한 필드 '{field}' 제거")
        
        self.logger.debug(f"응답 검증 완료 - 누락된 필드 {len(required_fields) - len([f for f in required_fields if f in result])}개 추가됨")
        
        return validated_result

    def _extract_agenda_pattern(self, text: str) -> Optional[Dict]:
        """텍스트에서 agenda 패턴 추출"""
        import re
        
        # 패턴: PL25015_ABa 형식
        pattern = r'(PL|JWG-\w+)(\d{2})(\d{3})([a-z]?)(?:_([A-Z]{2,3})([a-z]?)([a-z]?))?'
        match = re.search(pattern, text)
        
        if match:
            groups = match.groups()
            base_pattern = f"{groups[0]}{groups[1]}{groups[2]}"
            if groups[3]:  # round_version이 있으면 추가
                base_pattern += groups[3]
            
            return {
                'full_pattern': match.group(0),
                'panel_name': groups[0],
                'year': groups[1],
                'round_no': groups[2],
                'round_version': groups[3] if groups[3] else None,
                'organization_code': groups[4] if groups[4] else None,
                'sequence': groups[5] if groups[5] else None,
                'reply_version': groups[6] if groups[6] else None,
                'base_pattern': base_pattern  # agenda_no로 사용할 기본 패턴
            }
        
        return None

    def _save_analysis_result(self, result: Dict, subject: str, content: str):
        """분석 결과를 파일로 저장"""
        try:
            from datetime import datetime
            import fcntl  # 파일 잠금을 위해 추가
            
            # 저장 디렉토리 생성 (변경된 경로)
            save_dir = Path("data/mail_analysis_results")
            save_dir.mkdir(parents=True, exist_ok=True)
            
            # 타임스탬프 생성
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            
            # 저장할 데이터 구성
            save_data = {
                "timestamp": datetime.now().isoformat(),
                "subject": subject,
                "body_content": content,
                "analysis_result": {
                    "summary": result.get('summary', ''),
                    "deadline": result.get('deadline'),
                    "has_deadline": result.get('has_deadline', False),
                    "mail_type": result.get('mail_type', 'UNKNOWN'),
                    "decision_status": result.get('decision_status', 'unknown'),
                    "keywords": result.get('keywords', []),
                    "keywords_count": len(result.get('keywords', [])),
                    "sender_type": result.get('sender_type', 'UNKNOWN'),
                    "sender_organization": result.get('sender_organization'),
                    "send_time": result.get('send_time'),
                    "agenda_no": result.get('agenda_no'),
                    "agenda_info": result.get('agenda_info', {})
                }
            }
            
            # 토큰 사용량 정보 추가 (있는 경우)
            if 'token_usage' in result:
                save_data['token_usage'] = result['token_usage']
            
            # 오늘 날짜로 파일명 생성 (하나의 파일에 누적)
            today = datetime.now().strftime("%Y%m%d")
            filename = f"mail_analysis_results_{today}.jsonl"
            filepath = save_dir / filename
            
            # JSONL 파일에 추가 (파일 잠금 사용)
            with open(filepath, 'a', encoding='utf-8') as f:
                try:
                    # 파일 잠금 획득
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                    
                    # JSONL 형식으로 저장 (한 줄에 하나의 JSON)
                    json.dump(save_data, f, ensure_ascii=False)
                    f.write('\n')
                    
                finally:
                    # 파일 잠금 해제
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            
            self.logger.debug(f"분석 결과 저장됨: {filepath}")
            
        except Exception as e:
            self.logger.error(f"분석 결과 저장 실패: {str(e)}")

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