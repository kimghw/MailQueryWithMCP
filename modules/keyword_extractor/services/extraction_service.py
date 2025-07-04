"""키워드 추출 서비스 - 대시보드 이벤트 통합된 완전한 파일"""

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
from modules.keyword_extractor.keyword_extractor_schema import (
    KeywordExtractionResponse,
    ExtractionMethod,
)
from .dashboard_event_service import DashboardEventService


class ExtractionService:
    """키워드 추출 서비스"""

    def __init__(self):
        self.config = get_config()
        self.logger = get_logger(__name__)

        # OpenRouter 설정
        self.api_key = getattr(self.config, "openrouter_api_key", None)
        self.model = getattr(self.config, "openrouter_model", "openai/gpt-3.5-turbo")
        self.base_url = "https://openrouter.ai/api/v1"

        # 배치 처리 설정
        self.batch_size = int(
            self.config.get_setting("KEYWORD_EXTRACTION_BATCH_SIZE", "50")
        )
        self.concurrent_requests = int(
            self.config.get_setting("KEYWORD_EXTRACTION_CONCURRENT_REQUESTS", "5")
        )
        self.batch_timeout = int(
            self.config.get_setting("KEYWORD_EXTRACTION_BATCH_TIMEOUT", "60")
        )

        # 구조화된 응답 사용 여부
        self.use_structured_response = (
            self.config.get_setting("ENABLE_STRUCTURED_EXTRACTION", "true").lower()
            == "true"
        )

        # 구조화된 데이터 저장 여부
        self.save_structured_data = (
            self.config.get_setting("SAVE_STRUCTURED_DATA", "true").lower() == "true"
        )

        # 재사용 가능한 세션
        self._session: Optional[aiohttp.ClientSession] = None

        # 대시보드 이벤트 서비스 추가
        self.dashboard_service = DashboardEventService()

        # 현재 처리 중인 메일 정보
        self._current_mail_id = None

        self.logger.info(
            f"추출 서비스 초기화: "
            f"model={self.model}, "
            f"save_structured_data={self.save_structured_data}"
        )

    async def __aenter__(self):
        """컨텍스트 매니저 진입"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """컨텍스트 매니저 종료 - 자동 리소스 정리"""
        await self.close()

    async def extract(
        self,
        text: str,
        subject: str = "",
        sent_time: Optional[datetime] = None,
        max_keywords: int = 5,
        prompt_data: Optional[Dict[str, Any]] = None,
        use_structured_response: bool = True,
    ) -> KeywordExtractionResponse:
        """
        텍스트에서 키워드 추출

        Args:
            text: 추출할 텍스트
            subject: 제목
            sent_time: 발송 시간
            max_keywords: 최대 키워드 수
            prompt_data: 프롬프트 데이터
            use_structured_response: 구조화된 응답 사용 여부

        Returns:
            키워드 추출 응답
        """
        start_time = time.time()

        try:
            if use_structured_response and self.use_structured_response:
                # 구조화된 응답 API 호출
                result = await self._call_openrouter_structured_api(
                    content=text,
                    subject=subject,
                    sent_time=sent_time,
                    max_keywords=max_keywords,
                    prompt_data=prompt_data or {},
                )

                if result:
                    execution_time = int((time.time() - start_time) * 1000)
                    return KeywordExtractionResponse(
                        keywords=result.get("keywords", [])[:max_keywords],
                        method=ExtractionMethod.OPENROUTER,
                        model=self.model,
                        execution_time_ms=execution_time,
                        token_info=result.get("token_usage", {}),
                        # 구조화된 응답 추가 필드들
                        summary=result.get("summary"),
                        deadline=result.get("deadline"),
                        has_deadline=result.get("has_deadline"),
                        mail_type=result.get("mail_type"),
                        decision_status=result.get("decision_status"),
                        sender_type=result.get("sender_type"),
                        sender_organization=result.get("sender_organization"),
                        agenda_no=result.get("agenda_no"),
                        agenda_info=result.get("agenda_info"),
                    )

            # 폴백: 기본 키워드 추출
            keywords = self._extract_keywords_fallback(text, max_keywords)
            execution_time = int((time.time() - start_time) * 1000)

            return KeywordExtractionResponse(
                keywords=keywords,
                method=ExtractionMethod.FALLBACK,
                model="rule_based",
                execution_time_ms=execution_time,
            )

        except Exception as e:
            self.logger.error(f"키워드 추출 실패: {str(e)}")
            execution_time = int((time.time() - start_time) * 1000)

            return KeywordExtractionResponse(
                keywords=[],
                method=ExtractionMethod.FALLBACK_ERROR,
                model="error",
                execution_time_ms=execution_time,
                token_info={"error": str(e)},
            )

    async def extract_batch(
        self,
        items: List[Dict[str, Any]],
        batch_size: int,
        concurrent_requests: int,
        prompt_data: Dict[str, Any],
    ) -> List[List[str]]:
        """배치 키워드 추출"""
        results = []

        for i in range(0, len(items), batch_size):
            batch_items = items[i : i + batch_size]
            batch_results = await self._process_batch_chunk(batch_items, prompt_data)
            results.extend(batch_results)

        return results

    async def _process_batch_chunk(
        self, batch_items: List[Dict], prompt_data: Dict
    ) -> List[List[str]]:
        """배치 청크 처리"""
        tasks = []

        for item in batch_items:
            mail_id = item.get("mail_id", f"item_{id(item)}")
            task = self._process_single_item(item, mail_id, prompt_data)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 예외가 발생한 경우 빈 리스트로 처리
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                self.logger.error(f"배치 아이템 처리 중 예외: {result}")
                processed_results.append([])
            else:
                processed_results.append(result)

        return processed_results

    async def _process_single_item(
        self, item: Dict, mail_id: str, prompt_data: Dict
    ) -> List[str]:
        """단일 아이템 처리 (대시보드 이벤트 포함)"""
        try:
            # 메일 ID 설정 (대시보드 이벤트용)
            self.set_current_mail_id(mail_id)

            content = item.get("content", "")
            subject = item.get("subject", "")
            sent_time = item.get("sent_time")

            # 구조화된 API 호출 (대시보드 이벤트 자동 발행됨)
            result = await self._call_openrouter_structured_api(
                content=content,
                subject=subject,
                sent_time=sent_time,
                max_keywords=5,
                prompt_data=prompt_data,
            )

            if result:
                # 키워드만 반환 (기존 로직 유지)
                return result.get("keywords", [])
            else:
                return []

        except Exception as e:
            self.logger.error(f"아이템 처리 실패: mail_id={mail_id}, error={str(e)}")
            return []

    async def _call_openrouter_structured_api(
        self,
        content: str,
        subject: str,
        sent_time: Optional[datetime],
        max_keywords: int,
        prompt_data: Dict[str, Any],
    ) -> Optional[Dict]:
        """OpenRouter API 호출 (구조화된 응답) - 대시보드 이벤트 통합"""

        if not self.api_key:
            return None

        # 텍스트 길이 제한
        limited_content = content[:2000] if len(content) > 2000 else content

        # 발송 시간 포맷팅
        sent_time_str = sent_time.isoformat() if sent_time else "Unknown"

        # 프롬프트 준비
        try:
            system_prompt = prompt_data.get("system_prompt", "")
            user_prompt_template = prompt_data.get("user_prompt_template", "")

            # 플레이스홀더 치환
            user_prompt = user_prompt_template.replace(
                "{subject}", subject if subject else "No subject"
            )
            user_prompt = user_prompt.replace("{content}", limited_content)
            user_prompt = user_prompt.replace("{sent_time}", sent_time_str)

        except Exception as e:
            self.logger.error(f"프롬프트 템플릿 처리 오류: {str(e)}")
            return None

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": 500,
            "temperature": 0.1,
        }

        # response_format이 지원되는 모델인 경우 추가
        if (
            "gpt-4" in self.model or "gpt-3.5-turbo" in self.model
        ) and "anthropic" not in self.model:
            payload["response_format"] = {"type": "json_object"}

        start_time = time.time()

        try:
            session = await self._get_session()

            async with session.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:

                extraction_time_ms = int((time.time() - start_time) * 1000)

                if response.status != 200:
                    response_text = await response.text()
                    self.logger.error(
                        f"API 오류: Status {response.status}, Response: {response_text}"
                    )
                    return None

                data = await response.json()

                # 응답에서 컨텐츠 추출
                if "choices" in data and data["choices"]:
                    choice = data["choices"][0]
                    if "message" in choice and "content" in choice["message"]:
                        content_response = choice["message"]["content"]

                        if not content_response:
                            self.logger.warning("응답 컨텐츠가 비어있음")
                            return None

                        # JSON 파싱 시도
                        try:
                            result = self._parse_json_response(content_response)

                            if result:
                                # 토큰 사용량 정보 추가
                                if "usage" in data:
                                    result["token_usage"] = data["usage"]

                                # 파일 저장 (기존 설정에 따라)
                                if self.save_structured_data:
                                    self._save_structured_response(
                                        content, subject, sent_time, result
                                    )
                                    self.logger.debug("구조화된 응답 저장 완료")

                                # 🎯 대시보드 이벤트 즉시 발행
                                await self._publish_dashboard_event(
                                    result, extraction_time_ms, data.get("usage", {})
                                )

                            return result

                        except json.JSONDecodeError as e:
                            self.logger.error(f"JSON 파싱 실패: {str(e)}")
                            # JSON 파싱 실패 시 기존 방식으로 파싱
                            keywords = self._parse_keywords(content_response)
                            return {
                                "keywords": keywords[:max_keywords],
                                "token_usage": data.get("usage", {}),
                            }
                else:
                    self.logger.warning("API 응답에 choices가 없음")

                return None

        except Exception as e:
            self.logger.error(
                f"OpenRouter 구조화된 API 호출 실패: {str(e)}", exc_info=True
            )
            return None

    async def _publish_dashboard_event(
        self,
        structured_result: Dict[str, Any],
        extraction_time_ms: int,
        token_usage: Dict[str, Any],
    ):
        """대시보드 이벤트 발행"""
        try:
            # 메일 ID 결정
            mail_id = (
                getattr(self, "_current_mail_id", None)
                or f"extraction_{int(time.time() * 1000)}"
            )

            # 메타데이터 구성
            metadata = {
                "model_used": self.model,
                "extraction_time_ms": extraction_time_ms,
                "success": True,
                "token_usage": token_usage,
            }

            # 즉시 이벤트 발행
            success = await self.dashboard_service.publish_extraction_result(
                mail_id=mail_id, structured_result=structured_result, metadata=metadata
            )

            if not success:
                self.logger.warning(f"대시보드 이벤트 발행 실패: mail_id={mail_id}")

        except Exception as e:
            self.logger.error(f"대시보드 이벤트 발행 중 오류: {str(e)}")

    def set_current_mail_id(self, mail_id: str):
        """현재 처리 중인 메일 ID 설정 (외부에서 호출)"""
        self._current_mail_id = mail_id

    async def _get_session(self) -> aiohttp.ClientSession:
        """HTTP 세션을 반환 (레이지 초기화)"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.config.http_timeout)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers={"User-Agent": "IACSGraph/1.0", "Accept": "application/json"},
            )
        return self._session

    def _parse_json_response(self, content_response: str) -> Optional[Dict]:
        """JSON 응답 파싱"""
        try:
            # JSON 블록 추출 시도
            json_match = re.search(
                r"```json\s*(\{.*?\})\s*```", content_response, re.DOTALL
            )
            if json_match:
                json_str = json_match.group(1)
            else:
                # 중괄호로 둘러싸인 JSON 찾기
                brace_match = re.search(r"\{.*\}", content_response, re.DOTALL)
                if brace_match:
                    json_str = brace_match.group(0)
                else:
                    json_str = content_response

            # JSON 파싱
            parsed = json.loads(json_str)
            return parsed if isinstance(parsed, dict) else None

        except json.JSONDecodeError:
            return None

    def _parse_keywords(self, text: str) -> List[str]:
        """텍스트에서 키워드 파싱 (폴백용)"""
        # 간단한 키워드 추출 로직
        words = re.findall(r"\b[가-힣a-zA-Z]{2,}\b", text)
        word_counts = Counter(words)
        return [word for word, _ in word_counts.most_common(5)]

    def _extract_keywords_fallback(self, text: str, max_keywords: int) -> List[str]:
        """폴백 키워드 추출"""
        # 간단한 규칙 기반 키워드 추출
        words = re.findall(r"\b[가-힣a-zA-Z]{3,}\b", text)
        word_counts = Counter(words)
        return [word for word, _ in word_counts.most_common(max_keywords)]

    def _save_structured_response(
        self,
        text: str,
        subject: str,
        sent_time: Optional[datetime],
        result: Dict[str, Any],
    ) -> None:
        """구조화된 응답을 파일로 저장 (설정에 따라 호출됨)"""
        try:
            self.logger.info(f"구조화된 응답 저장 시작 - subject: {subject}")

            # 프로젝트 루트 기준 상대 경로 사용
            from pathlib import Path

            # config에서 DATABASE_PATH를 참고하여 data 디렉토리 찾기
            db_path = self.config.database_path  # ./data/iacsgraph.db
            data_dir = Path(db_path).parent  # ./data
            base_dir = data_dir / "mail_analysis_results"

            base_dir.mkdir(parents=True, exist_ok=True)

            # 파일명 생성 (날짜 기반)
            date_str = datetime.now().strftime("%Y%m%d")
            filename = f"mail_analysis_results_{date_str}.jsonl"
            filepath = base_dir / filename

            # 저장할 데이터 구성
            analysis_data = {
                "timestamp": datetime.now().isoformat(),
                "subject": subject,
                "sent_time": (
                    sent_time.isoformat()
                    if sent_time and hasattr(sent_time, "isoformat")
                    else str(sent_time)
                ),
                "body_content": text[:2000],  # 처음 2000자만
                "model": self.model,
                "analysis_result": result,
            }

            # JSONL 파일에 추가 모드로 저장
            with open(filepath, "a", encoding="utf-8") as f:
                json.dump(analysis_data, f, ensure_ascii=False)
                f.write("\n")

            self.logger.info(f"구조화된 응답 저장 완료: {filepath.absolute()}")

        except Exception as e:
            self.logger.error(f"구조화된 응답 저장 실패: {str(e)}", exc_info=True)

    async def close(self):
        """리소스 정리"""
        try:
            if self._session and not self._session.closed:
                await self._session.close()
                self.logger.debug("HTTP 세션 종료됨")
        except Exception as e:
            self.logger.error(f"리소스 정리 중 오류: {str(e)}")
