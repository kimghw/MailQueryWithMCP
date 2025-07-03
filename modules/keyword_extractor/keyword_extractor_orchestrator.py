"""키워드 추출 오케스트레이터 - 순수 흐름 제어만 담당"""

from typing import Dict, List, Any, Optional
from infra.core.logger import get_logger
from .services import ExtractionService, PromptService
from .utilities import StructuredResponseSaver
from .keyword_extractor_schema import (
    KeywordExtractionRequest, 
    KeywordExtractionResponse,
    BatchExtractionRequest,
    BatchExtractionResponse
)

logger = get_logger(__name__)


class KeywordExtractorOrchestrator:
    """키워드 추출 흐름만 관리하는 오케스트레이터"""
    
    def __init__(self,
                 extraction_service: Optional[ExtractionService] = None,
                 prompt_service: Optional[PromptService] = None):
        """
        의존성 주입을 지원하는 초기화
        
        Args:
            extraction_service: 추출 서비스 (테스트 시 모킹 가능)
            prompt_service: 프롬프트 서비스 (테스트 시 모킹 가능)
        """
        self.logger = get_logger(__name__)
        
        # 서비스 초기화 (의존성 주입 지원)
        self.extraction_service = extraction_service or ExtractionService()
        self.prompt_service = prompt_service or PromptService()
        self.response_saver = StructuredResponseSaver()
    
    async def __aenter__(self):
        """컨텍스트 매니저 진입"""
        await self.extraction_service.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """컨텍스트 매니저 종료 - 자동 리소스 정리"""
        await self.close()
    
    async def extract_keywords(self, request: KeywordExtractionRequest) -> KeywordExtractionResponse:
        """
        단일 텍스트 키워드 추출 메인 플로우
        
        Args:
            request: 키워드 추출 요청
            
        Returns:
            키워드 추출 응답
        """
        self.logger.debug(f"키워드 추출 시작: text_length={len(request.text)}")
        
        try:
            # Phase 1: 텍스트 검증
            if not self._validate_text(request.text):
                return self._create_empty_response()
            
            # Phase 2: 프롬프트 준비
            prompt_data = await self._prepare_prompt(request)
            
            # Phase 3: 키워드 추출
            response = await self._extract_keywords(request, prompt_data)
            
            self.logger.debug(f"키워드 추출 완료: {len(response.keywords)}개")
            return response
            
        except Exception as e:
            self.logger.error(f"키워드 추출 중 예외 발생: {str(e)}", exc_info=True)
            return self._create_error_response(str(e))
    
    async def extract_keywords_batch(self, request: BatchExtractionRequest) -> BatchExtractionResponse:
        """
        배치 키워드 추출 메인 플로우
        
        Args:
            request: 배치 추출 요청
            
        Returns:
            배치 추출 응답
        """
        self.logger.info(f"배치 키워드 추출 시작: {len(request.items)}개 아이템")
        
        import time
        start_time = time.time()
        
        try:
            # Phase 1: 배치 준비 및 검증
            valid_items = self._prepare_batch_items(request.items)
            
            # Phase 2: 배치 추출 실행
            results = await self._execute_batch_extraction(
                valid_items, 
                request.batch_size,
                request.concurrent_requests
            )
            
            # Phase 3: 결과 정리
            response = self._compile_batch_results(
                request.items,
                results,
                start_time
            )
            
            self.logger.info(
                f"배치 키워드 추출 완료: "
                f"성공={response.successful_items}, "
                f"실패={response.failed_items}, "
                f"시간={response.total_execution_time_ms}ms"
            )
            return response
            
        except Exception as e:
            self.logger.error(f"배치 키워드 추출 중 예외 발생: {str(e)}", exc_info=True)
            # 실패 응답 생성
            return BatchExtractionResponse(
                results=[[] for _ in request.items],
                total_items=len(request.items),
                successful_items=0,
                failed_items=len(request.items),
                total_execution_time_ms=int((time.time() - start_time) * 1000)
            )
    
    def _validate_text(self, text: str) -> bool:
        """텍스트 유효성 검증"""
        return text and len(text.strip()) >= 10
    
    async def _prepare_prompt(self, request: KeywordExtractionRequest) -> Dict[str, Any]:
        """프롬프트 준비"""
        prompt_type = "structured" if request.use_structured_response else "simple"
        return await self.prompt_service.get_prompt_data(prompt_type)
    
    async def _extract_keywords(
        self, 
        request: KeywordExtractionRequest,
        prompt_data: Dict[str, Any]
    ) -> KeywordExtractionResponse:
        """실제 키워드 추출"""
        response = await self.extraction_service.extract(
            text=request.text,
            subject=request.subject,
            sent_time=request.sent_time,
            max_keywords=request.max_keywords,
            prompt_data=prompt_data,
            use_structured_response=request.use_structured_response
        )
        
        # 구조화된 응답이 있고 mail_type이 있는 경우 저장
        if (request.use_structured_response and 
            hasattr(response, 'mail_type') and 
            response.mail_type):
            
            # 구조화된 응답 데이터 구성
            structured_data = {
                'keywords': response.keywords,
                'summary': getattr(response, 'summary', None),
                'deadline': getattr(response, 'deadline', None),
                'has_deadline': getattr(response, 'has_deadline', None),
                'mail_type': getattr(response, 'mail_type', None),
                'decision_status': getattr(response, 'decision_status', None),
                'sender_type': getattr(response, 'sender_type', None),
                'sender_organization': getattr(response, 'sender_organization', None),
                'agenda_no': getattr(response, 'agenda_no', None),
                'agenda_info': getattr(response, 'agenda_info', None)
            }
            
            # 저장 실행
            self.response_saver.save_response(
                text=request.text,
                subject=request.subject or "",
                sent_time=request.sent_time,
                result=structured_data,
                model=response.model
            )
        
        return response
    
    def _prepare_batch_items(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """배치 아이템 준비 및 필터링"""
        valid_items = []
        
        for item in items:
            content = item.get('content', '') if isinstance(item, dict) else str(item)
            if content and len(content.strip()) >= 10:
                valid_items.append(item)
        
        return valid_items
    
    async def _execute_batch_extraction(
        self,
        items: List[Dict[str, Any]],
        batch_size: int,
        concurrent_requests: int
    ) -> List[List[str]]:
        """배치 추출 실행 (구조화된 응답 포함)"""
        # 구조화된 응답을 위한 프롬프트 데이터 준비
        prompt_data = await self.prompt_service.get_prompt_data("structured")
        
        return await self.extraction_service.extract_batch(
            items,
            batch_size,
            concurrent_requests,
            prompt_data
        )
    
    def _compile_batch_results(
        self,
        original_items: List[Dict[str, Any]],
        results: List[List[str]],
        start_time: float
    ) -> BatchExtractionResponse:
        """배치 결과 컴파일"""
        import time
        
        # 원본 아이템과 결과 매칭
        final_results = []
        successful = 0
        
        result_idx = 0
        for item in original_items:
            content = item.get('content', '') if isinstance(item, dict) else str(item)
            if content and len(content.strip()) >= 10:
                if result_idx < len(results):
                    keywords = results[result_idx]
                    final_results.append(keywords)
                    if keywords:
                        successful += 1
                    result_idx += 1
                else:
                    final_results.append([])
            else:
                final_results.append([])
        
        return BatchExtractionResponse(
            results=final_results,
            total_items=len(original_items),
            successful_items=successful,
            failed_items=len(original_items) - successful,
            total_execution_time_ms=int((time.time() - start_time) * 1000)
        )
    
    def _create_empty_response(self) -> KeywordExtractionResponse:
        """빈 텍스트용 응답 생성"""
        return KeywordExtractionResponse(
            keywords=[],
            method="empty_text",
            model="none",
            execution_time_ms=0
        )
    
    def _create_error_response(self, error: str) -> KeywordExtractionResponse:
        """에러 응답 생성"""
        return KeywordExtractionResponse(
            keywords=[],
            method="fallback_error",
            model="none",
            execution_time_ms=0,
            token_info={"error": error}
        )
    
    async def close(self):
        """리소스 정리"""
        try:
            await self.extraction_service.close()
        except Exception as e:
            self.logger.error(f"리소스 정리 중 오류: {str(e)}")
