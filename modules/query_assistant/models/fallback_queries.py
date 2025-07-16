"""
Fallback Queries Model
LLM 폴백 처리된 쿼리 로그 및 학습 데이터 관리
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
import json
import hashlib
from dataclasses import dataclass, field, asdict


@dataclass
class FallbackQuery:
    """폴백 쿼리 데이터 모델"""
    
    # 기본 식별자
    id: Optional[int] = None
    session_id: Optional[str] = None
    
    # 사용자 입력 정보
    original_query: str = ""
    normalized_query: Optional[str] = None
    query_category: Optional[str] = None
    
    # 매칭 시도 정보
    best_template_id: Optional[str] = None
    match_score: Optional[float] = None
    vector_score: Optional[float] = None
    keyword_score: Optional[float] = None
    
    # 파라미터 추출 정보
    extracted_params: Dict[str, Any] = field(default_factory=dict)
    missing_params: List[str] = field(default_factory=list)
    
    # 폴백 처리 정보
    fallback_type: Optional[str] = None  # 'llm_generation', 'user_interaction', 'parameter_completion'
    llm_prompt: Optional[str] = None
    llm_response: Optional[str] = None
    
    # 생성된 SQL 정보
    generated_sql: Optional[str] = None
    sql_validation_status: Optional[str] = None  # 'valid', 'syntax_error', 'execution_error'
    execution_error: Optional[str] = None
    
    # 결과 및 피드백
    result_count: Optional[int] = None
    execution_time_ms: Optional[int] = None
    user_feedback: Optional[str] = None  # 'satisfied', 'unsatisfied', NULL
    user_comment: Optional[str] = None
    
    # 템플릿 후보 정보
    is_template_candidate: bool = False
    template_created: bool = False
    new_template_id: Optional[str] = None
    
    # 메타데이터
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    
    # 인덱스를 위한 추가 컬럼
    frequency_count: int = 1
    pattern_hash: Optional[str] = None
    
    def __post_init__(self):
        """초기화 후 처리"""
        # 패턴 해시 생성
        if self.original_query and not self.pattern_hash:
            self.pattern_hash = self._generate_pattern_hash()
        
        # 시간 필드 초기화
        if not self.created_at:
            self.created_at = datetime.now()
        if not self.updated_at:
            self.updated_at = datetime.now()
    
    def _generate_pattern_hash(self) -> str:
        """쿼리 패턴의 해시 생성"""
        # 숫자, 날짜, 특정 엔티티를 일반화하여 패턴 생성
        pattern = self.original_query.lower()
        # 숫자를 {NUM}으로 치환
        import re
        pattern = re.sub(r'\d+', '{NUM}', pattern)
        # 날짜 형식을 {DATE}로 치환
        pattern = re.sub(r'\d{4}-\d{2}-\d{2}', '{DATE}', pattern)
        # 이메일을 {EMAIL}로 치환
        pattern = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '{EMAIL}', pattern)
        
        return hashlib.md5(pattern.encode()).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        data = asdict(self)
        
        # JSON 필드 직렬화
        if self.extracted_params:
            data['extracted_params'] = json.dumps(self.extracted_params, ensure_ascii=False)
        if self.missing_params:
            data['missing_params'] = json.dumps(self.missing_params, ensure_ascii=False)
        
        # datetime 필드 직렬화
        for field_name in ['created_at', 'updated_at', 'processed_at']:
            if data.get(field_name):
                data[field_name] = data[field_name].isoformat()
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FallbackQuery':
        """딕셔너리에서 객체 생성"""
        # JSON 필드 역직렬화
        if isinstance(data.get('extracted_params'), str):
            data['extracted_params'] = json.loads(data['extracted_params'])
        if isinstance(data.get('missing_params'), str):
            data['missing_params'] = json.loads(data['missing_params'])
        
        # datetime 필드 역직렬화
        for field_name in ['created_at', 'updated_at', 'processed_at']:
            if data.get(field_name):
                if isinstance(data[field_name], str):
                    data[field_name] = datetime.fromisoformat(data[field_name])
        
        return cls(**data)
    
    def mark_as_template_candidate(self):
        """템플릿 후보로 표시"""
        self.is_template_candidate = True
        self.updated_at = datetime.now()
    
    def set_user_feedback(self, feedback: str, comment: Optional[str] = None):
        """사용자 피드백 설정"""
        if feedback not in ['satisfied', 'unsatisfied']:
            raise ValueError(f"Invalid feedback value: {feedback}")
        
        self.user_feedback = feedback
        self.user_comment = comment
        self.updated_at = datetime.now()
    
    def is_successful(self) -> bool:
        """쿼리 실행이 성공적이었는지 확인"""
        return (
            self.sql_validation_status == 'valid' and
            self.execution_error is None and
            self.result_count is not None and
            self.result_count >= 0
        )