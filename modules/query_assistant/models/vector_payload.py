"""Vector Database Payload Schema for Query Templates"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
import json

# ========================================
# 1. 페이로드 스키마 정의
# ========================================

class VectorPayloadSchema(BaseModel):
    """Qdrant 벡터 데이터베이스 페이로드 구조"""
    
    # 기본 식별 정보
    template_id: str = Field(
        description="템플릿 고유 식별자 (예: 'org_response_rate_v1')"
    )
    version: str = Field(
        default="1.0",
        description="템플릿 버전 (업데이트 추적용)"
    )
    
    # 자연어 질의 정보
    natural_questions: List[str] = Field(
        description="자연어 질의 패턴 목록",
        example=[
            "{organization} 기관의 응답률은 어떻게 되나요?",
            "{organization}의 응답률 통계를 보여주세요",
            "{organization} 응답 현황은?"
        ]
    )
    
    # SQL 쿼리 정보
    sql_query: str = Field(
        description="실제 실행될 SQL 쿼리 (파라미터 치환 후)"
    )
    sql_query_with_parameters: str = Field(
        description="파라미터 플레이스홀더가 포함된 SQL 템플릿"
    )
    
    # 매칭 정보
    keywords: List[str] = Field(
        description="매칭용 키워드 목록",
        example=["응답률", "기관", "organization", "response", "rate", "통계"]
    )
    category: str = Field(
        description="템플릿 분류",
        example="statistics"
    )
    
    # 파라미터 정보
    required_params: List[str] = Field(
        description="필수 파라미터 목록",
        example=["organization"]
    )
    optional_params: List[str] = Field(
        description="선택적 파라미터 목록",  # query_filter 대신 명확한 이름 사용
        example=["days", "limit"]
    )
    default_params: Dict[str, Any] = Field(
        description="파라미터 기본값 매핑",
        example={
            "organization": "KR",
            "days": 30,
            "limit": 20
        }
    )
    
    # 파라미터 메타데이터
    param_metadata: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="각 파라미터의 상세 정보",
        example={
            "organization": {
                "type": "string",
                "allowed_values": ["KR", "BV", "CCS", "DNV", "LR", "ABS"],
                "description": "기관 코드",
                "validation_regex": "^[A-Z]{2,4}$"
            },
            "days": {
                "type": "integer",
                "min": 1,
                "max": 365,
                "description": "조회 기간 (일)"
            }
        }
    )
    
    # 데이터베이스 정보
    related_tables: List[str] = Field(
        description="관련 테이블 목록",
        example=["agenda_chair", "agenda_responses_content"]
    )
    
    # 사용 통계
    usage_count: int = Field(
        default=0,
        description="사용 횟수"
    )
    success_count: int = Field(
        default=0,
        description="성공적 실행 횟수"
    )
    avg_execution_time_ms: Optional[float] = Field(
        default=None,
        description="평균 실행 시간 (밀리초)"
    )
    
    # 시간 정보
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="템플릿 생성 시각"
    )
    last_used: Optional[datetime] = Field(
        default=None,
        description="최종 사용 시각"
    )
    last_modified: datetime = Field(
        default_factory=datetime.now,
        description="최종 수정 시각"
    )
    
    # LLM 프롬프트 정보
    to_agent_prompt: str = Field(
        description="예외 처리 시 LLM에 전달할 프롬프트 템플릿",
        example="""이 쿼리는 특정 기관의 응답률을 조회합니다.
필요한 파라미터:
- organization: 기관 코드 (KR, BV, CCS 등)
- days (선택): 조회 기간, 기본값 30일

사용자가 "{user_query}"라고 질문했습니다.
적절한 SQL을 생성해주세요."""
    )
    
    # 추가 메타데이터
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="추가 메타데이터",
        example={
            "author": "system",
            "tags": ["statistics", "organization", "response_rate"],
            "complexity": "medium",
            "estimated_rows": "1-10",
            "cacheable": True,
            "timeout_seconds": 30
        }
    )
    
    # 검증 정보
    validation_rules: Dict[str, Any] = Field(
        default_factory=dict,
        description="쿼리 검증 규칙",
        example={
            "min_params": 1,
            "max_results": 1000,
            "requires_date_range": False,
            "allow_wildcards": False
        }
    )

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# ========================================
# 2. 페이로드 변환 유틸리티
# ========================================

class VectorPayloadConverter:
    """벡터 페이로드 변환 및 관리 유틸리티"""
    
    @staticmethod
    def to_qdrant_payload(schema: VectorPayloadSchema) -> Dict[str, Any]:
        """Pydantic 모델을 Qdrant 페이로드로 변환"""
        payload = schema.dict()
        
        # datetime 필드를 문자열로 변환
        for field in ['created_at', 'last_used', 'last_modified']:
            if payload.get(field):
                payload[field] = payload[field].isoformat()
        
        # 리스트와 딕셔너리는 JSON 문자열로 저장 (필요한 경우)
        # Qdrant는 기본적으로 복잡한 구조를 지원하므로 대부분 그대로 사용 가능
        
        return payload
    
    @staticmethod
    def from_qdrant_payload(payload: Dict[str, Any]) -> VectorPayloadSchema:
        """Qdrant 페이로드를 Pydantic 모델로 변환"""
        # datetime 필드를 datetime 객체로 변환
        for field in ['created_at', 'last_used', 'last_modified']:
            if payload.get(field):
                if isinstance(payload[field], str):
                    payload[field] = datetime.fromisoformat(payload[field])
        
        return VectorPayloadSchema(**payload)
    
    @staticmethod
    def update_usage_stats(schema: VectorPayloadSchema, success: bool, execution_time_ms: float):
        """사용 통계 업데이트"""
        schema.usage_count += 1
        if success:
            schema.success_count += 1
        
        # 평균 실행 시간 계산 (누적 평균)
        if schema.avg_execution_time_ms is None:
            schema.avg_execution_time_ms = execution_time_ms
        else:
            total_executions = schema.usage_count
            schema.avg_execution_time_ms = (
                (schema.avg_execution_time_ms * (total_executions - 1) + execution_time_ms) 
                / total_executions
            )
        
        schema.last_used = datetime.now()
        schema.last_modified = datetime.now()

# ========================================
# 3. 페이로드 검색 헬퍼
# ========================================

class VectorPayloadFilter:
    """벡터 페이로드 필터링 및 검색 헬퍼"""
    
    @staticmethod
    def by_category(category: str) -> Dict[str, Any]:
        """카테고리별 필터"""
        return {
            "must": [
                {
                    "key": "category",
                    "match": {"value": category}
                }
            ]
        }
    
    @staticmethod
    def by_required_params(params: List[str]) -> Dict[str, Any]:
        """필수 파라미터별 필터"""
        return {
            "must": [
                {
                    "key": "required_params",
                    "match": {"any": params}
                }
            ]
        }
    
    @staticmethod
    def by_keywords(keywords: List[str]) -> Dict[str, Any]:
        """키워드별 필터"""
        return {
            "should": [
                {
                    "key": "keywords",
                    "match": {"any": keywords}
                }
            ]
        }
    
    @staticmethod
    def by_usage_threshold(min_usage: int) -> Dict[str, Any]:
        """최소 사용 횟수 필터"""
        return {
            "must": [
                {
                    "key": "usage_count",
                    "range": {"gte": min_usage}
                }
            ]
        }
    
    @staticmethod
    def by_success_rate(min_rate: float) -> Dict[str, Any]:
        """최소 성공률 필터"""
        # 성공률 = success_count / usage_count
        # Qdrant에서 직접 계산은 어려우므로, 후처리 필요
        return {
            "must": [
                {
                    "key": "usage_count",
                    "range": {"gt": 0}
                }
            ]
        }

# ========================================
# 4. 페이로드 예시 생성기
# ========================================

def create_example_payload() -> VectorPayloadSchema:
    """예시 페이로드 생성"""
    return VectorPayloadSchema(
        template_id="org_response_rate_v1",
        version="1.0",
        natural_questions=[
            "{organization} 기관의 응답률은 어떻게 되나요?",
            "{organization}의 응답률 통계를 보여주세요",
            "{organization} 응답 현황은?"
        ],
        sql_query="""
        SELECT 
            o.organization,
            COUNT(DISTINCT ac.agenda_id) as total_agendas,
            COUNT(DISTINCT arc.agenda_id) as responded_agendas,
            ROUND(COUNT(DISTINCT arc.agenda_id) * 100.0 / COUNT(DISTINCT ac.agenda_id), 2) as response_rate
        FROM agenda_chair ac
        LEFT JOIN agenda_responses_content arc ON ac.agenda_id = arc.agenda_id
        LEFT JOIN organization o ON arc.organization_id = o.id
        WHERE o.code = 'KR'
            AND ac.created_at >= date('now', '-30 days')
        GROUP BY o.organization
        """,
        sql_query_with_parameters="""
        SELECT 
            o.organization,
            COUNT(DISTINCT ac.agenda_id) as total_agendas,
            COUNT(DISTINCT arc.agenda_id) as responded_agendas,
            ROUND(COUNT(DISTINCT arc.agenda_id) * 100.0 / COUNT(DISTINCT ac.agenda_id), 2) as response_rate
        FROM agenda_chair ac
        LEFT JOIN agenda_responses_content arc ON ac.agenda_id = arc.agenda_id
        LEFT JOIN organization o ON arc.organization_id = o.id
        WHERE o.code = :organization
            AND ac.created_at >= date('now', '-' || :days || ' days')
        GROUP BY o.organization
        """,
        keywords=["응답률", "기관", "organization", "response", "rate", "통계", "현황"],
        category="statistics",
        required_params=["organization"],
        optional_params=["days"],
        default_params={
            "organization": "KR",
            "days": 30
        },
        param_metadata={
            "organization": {
                "type": "string",
                "allowed_values": ["KR", "BV", "CCS", "DNV", "LR", "ABS"],
                "description": "기관 코드",
                "validation_regex": "^[A-Z]{2,4}$",
                "examples": ["KR", "BV"]
            },
            "days": {
                "type": "integer",
                "min": 1,
                "max": 365,
                "description": "조회 기간 (일)",
                "default": 30
            }
        },
        related_tables=["agenda_chair", "agenda_responses_content", "organization"],
        to_agent_prompt="""이 쿼리는 특정 기관의 응답률을 조회합니다.

필요한 파라미터:
- organization: 기관 코드 (KR, BV, CCS, DNV, LR, ABS 중 하나)
- days (선택): 조회 기간, 기본값 30일

사용자가 "{user_query}"라고 질문했습니다.
파라미터를 추출하고 적절한 SQL을 생성해주세요.""",
        metadata={
            "author": "system",
            "tags": ["statistics", "organization", "response_rate"],
            "complexity": "medium",
            "estimated_rows": "1-10",
            "cacheable": True,
            "timeout_seconds": 30,
            "description": "기관별 응답률 통계를 조회하는 템플릿"
        },
        validation_rules={
            "min_params": 1,
            "max_results": 100,
            "requires_date_range": True,
            "allow_wildcards": False
        }
    )