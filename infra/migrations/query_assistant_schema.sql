-- ========================================
-- Query Assistant Module Database Schema
-- Version: 1.0
-- Description: Tables for LLM fallback handling and preprocessing
-- ========================================

-- ========================================
-- 1. fallback_queries 테이블
-- 용도: LLM 폴백 처리된 쿼리 로그 및 학습 데이터
-- ========================================

CREATE TABLE IF NOT EXISTS fallback_queries (
    -- 기본 식별자
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,                          -- 세션 추적용
    
    -- 사용자 입력 정보
    original_query TEXT NOT NULL,             -- 원본 사용자 질의
    normalized_query TEXT,                    -- 정규화된 질의
    query_category TEXT,                      -- 추정된 카테고리
    
    -- 매칭 시도 정보
    best_template_id TEXT,                    -- 가장 유사했던 템플릿 ID
    match_score REAL,                         -- 매칭 점수 (0.0 ~ 1.0)
    vector_score REAL,                        -- 벡터 유사도 점수
    keyword_score REAL,                       -- 키워드 매칭 점수
    
    -- 파라미터 추출 정보
    extracted_params TEXT,                    -- JSON: 추출된 파라미터
    missing_params TEXT,                      -- JSON: 누락된 필수 파라미터
    
    -- 폴백 처리 정보
    fallback_type TEXT,                       -- 'llm_generation', 'user_interaction', 'parameter_completion'
    llm_prompt TEXT,                          -- LLM에 전달된 프롬프트
    llm_response TEXT,                        -- LLM 응답
    
    -- 생성된 SQL 정보
    generated_sql TEXT,                       -- 최종 생성된 SQL
    sql_validation_status TEXT,               -- 'valid', 'syntax_error', 'execution_error'
    execution_error TEXT,                     -- SQL 실행 오류 메시지
    
    -- 결과 및 피드백
    result_count INTEGER,                     -- 쿼리 결과 행 수
    execution_time_ms INTEGER,                -- 실행 시간 (밀리초)
    user_feedback TEXT,                       -- 'satisfied', 'unsatisfied', NULL
    user_comment TEXT,                        -- 사용자 추가 코멘트
    
    -- 템플릿 후보 정보
    is_template_candidate BOOLEAN DEFAULT FALSE,  -- 템플릿 후보 여부
    template_created BOOLEAN DEFAULT FALSE,       -- 템플릿으로 생성됨
    new_template_id TEXT,                         -- 생성된 템플릿 ID
    
    -- 메타데이터
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,                       -- 분석/처리 완료 시간
    
    -- 인덱스를 위한 추가 컬럼
    frequency_count INTEGER DEFAULT 1,            -- 유사 쿼리 발생 횟수
    pattern_hash TEXT                             -- 쿼리 패턴 해시 (중복 감지용)
);

-- 인덱스 생성
CREATE INDEX idx_fallback_queries_created_at ON fallback_queries(created_at);
CREATE INDEX idx_fallback_queries_template_candidate ON fallback_queries(is_template_candidate);
CREATE INDEX idx_fallback_queries_pattern_hash ON fallback_queries(pattern_hash);
CREATE INDEX idx_fallback_queries_match_score ON fallback_queries(match_score);

-- ========================================
-- 2. preprocessing_dataset 테이블
-- 용도: 동의어 사전 및 정규화 패턴
-- ========================================

CREATE TABLE IF NOT EXISTS preprocessing_dataset (
    -- 기본 식별자
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- 용어 분류
    term_type TEXT NOT NULL,                  -- 'synonym', 'organization', 'time_expression', 'status', 'keyword'
    category TEXT,                            -- 세부 카테고리 (예: 'equipment', 'panel', 'decision')
    
    -- 용어 매핑
    original_term TEXT NOT NULL,              -- 원본 용어/표현
    normalized_term TEXT NOT NULL,            -- 정규화된 용어
    language TEXT DEFAULT 'ko',               -- 언어 코드 ('ko', 'en')
    
    -- 패턴 정보 (정규식 등)
    is_pattern BOOLEAN DEFAULT FALSE,         -- 패턴 여부
    pattern_regex TEXT,                       -- 정규식 패턴
    pattern_priority INTEGER DEFAULT 100,     -- 패턴 우선순위 (낮을수록 높은 우선순위)
    
    -- 컨텍스트 정보
    context_clues TEXT,                       -- JSON: 문맥 단서 (예: ["응답", "율"])
    domain_specific BOOLEAN DEFAULT TRUE,     -- 도메인 특화 여부
    
    -- 사용 통계
    usage_count INTEGER DEFAULT 0,            -- 사용 횟수
    last_used_at TIMESTAMP,                   -- 마지막 사용 시간
    match_accuracy REAL DEFAULT 1.0,          -- 매칭 정확도 (0.0 ~ 1.0)
    
    -- 관계 정보
    related_terms TEXT,                       -- JSON: 관련 용어 리스트
    parent_term_id INTEGER,                   -- 상위 용어 ID (계층 구조)
    
    -- 메타데이터
    source TEXT,                              -- 출처 ('manual', 'auto_extracted', 'llm_suggested')
    created_by TEXT,                          -- 생성자 (사용자 ID 또는 시스템)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,           -- 활성화 여부
    
    -- 외래키
    FOREIGN KEY (parent_term_id) REFERENCES preprocessing_dataset(id)
);

-- 인덱스 생성
CREATE INDEX idx_preprocessing_original_term ON preprocessing_dataset(original_term);
CREATE INDEX idx_preprocessing_normalized_term ON preprocessing_dataset(normalized_term);
CREATE INDEX idx_preprocessing_term_type ON preprocessing_dataset(term_type);
CREATE INDEX idx_preprocessing_category ON preprocessing_dataset(category);
CREATE INDEX idx_preprocessing_usage ON preprocessing_dataset(usage_count DESC);

-- ========================================
-- 3. 초기 데이터 삽입
-- ========================================

-- 동의어 데이터
INSERT INTO preprocessing_dataset (term_type, category, original_term, normalized_term, language) VALUES
-- 아젠다 관련
('synonym', 'agenda', '아젠다', 'agenda', 'ko'),
('synonym', 'agenda', '안건', 'agenda', 'ko'),
('synonym', 'agenda', '의제', 'agenda', 'ko'),
('synonym', 'agenda', '어젠다', 'agenda', 'ko'),

-- 응답 관련
('synonym', 'response', '응답', 'response', 'ko'),
('synonym', 'response', '답변', 'response', 'ko'),
('synonym', 'response', '회신', 'response', 'ko'),
('synonym', 'response', '의견', 'response', 'ko'),
('synonym', 'response', '코멘트', 'response', 'ko'),

-- 기관 관련
('synonym', 'organization', '기관', 'organization', 'ko'),
('synonym', 'organization', '부서', 'organization', 'ko'),
('synonym', 'organization', '조직', 'organization', 'ko'),
('synonym', 'organization', '선급', 'class_society', 'ko'),

-- 상태 관련
('synonym', 'status', '승인', 'approved', 'ko'),
('synonym', 'status', '허가', 'approved', 'ko'),
('synonym', 'status', '반려', 'rejected', 'ko'),
('synonym', 'status', '거부', 'rejected', 'ko'),
('synonym', 'status', '거절', 'rejected', 'ko'),
('synonym', 'status', '미결정', 'pending', 'ko'),
('synonym', 'status', '대기', 'pending', 'ko'),
('synonym', 'status', '보류', 'pending', 'ko'),

-- 시간 표현
('time_expression', 'relative', '최근', 'recent', 'ko'),
('time_expression', 'relative', '최신', 'latest', 'ko'),
('time_expression', 'relative', '오늘', 'today', 'ko'),
('time_expression', 'relative', '어제', 'yesterday', 'ko'),
('time_expression', 'relative', '이번주', 'this_week', 'ko'),
('time_expression', 'relative', '지난주', 'last_week', 'ko'),
('time_expression', 'relative', '이번달', 'this_month', 'ko'),
('time_expression', 'relative', '지난달', 'last_month', 'ko'),
('time_expression', 'relative', '올해', 'this_year', 'ko'),
('time_expression', 'relative', '작년', 'last_year', 'ko'),

-- 기관 코드
('organization', 'class_society', '한국선급', 'KR', 'ko'),
('organization', 'class_society', 'Korean Register', 'KR', 'en'),
('organization', 'class_society', '케이알', 'KR', 'ko'),
('organization', 'class_society', 'Bureau Veritas', 'BV', 'en'),
('organization', 'class_society', '뷰로베리타스', 'BV', 'ko'),
('organization', 'class_society', 'China Classification Society', 'CCS', 'en'),
('organization', 'class_society', '중국선급', 'CCS', 'ko'),
('organization', 'class_society', 'DNV GL', 'DNV', 'en'),
('organization', 'class_society', 'Lloyd''s Register', 'LR', 'en'),
('organization', 'class_society', '로이드', 'LR', 'ko'),
('organization', 'class_society', 'American Bureau of Shipping', 'ABS', 'en'),

-- 패턴 기반 시간 표현
('time_expression', 'pattern', '(\d+)\s*일\s*전', '{days}_days_ago', 'ko'),
('time_expression', 'pattern', '(\d+)\s*주\s*전', '{weeks}_weeks_ago', 'ko'),
('time_expression', 'pattern', '(\d+)\s*개월\s*전', '{months}_months_ago', 'ko'),
('time_expression', 'pattern', '(\d+)\s*년\s*전', '{years}_years_ago', 'ko');

-- 패턴 정보 업데이트
UPDATE preprocessing_dataset 
SET is_pattern = TRUE, 
    pattern_regex = original_term,
    pattern_priority = 50
WHERE term_type = 'time_expression' 
  AND category = 'pattern';

-- ========================================
-- 4. 뷰 생성 (분석용)
-- ========================================

-- 자주 실패하는 쿼리 패턴 분석 뷰
CREATE VIEW v_frequent_fallback_patterns AS
SELECT 
    pattern_hash,
    COUNT(*) as occurrence_count,
    AVG(match_score) as avg_match_score,
    MAX(original_query) as sample_query,
    GROUP_CONCAT(DISTINCT missing_params) as common_missing_params
FROM fallback_queries
WHERE is_template_candidate = FALSE
GROUP BY pattern_hash
HAVING occurrence_count >= 3
ORDER BY occurrence_count DESC;

-- 활성 전처리 규칙 뷰
CREATE VIEW v_active_preprocessing_rules AS
SELECT 
    term_type,
    category,
    original_term,
    normalized_term,
    usage_count,
    match_accuracy
FROM preprocessing_dataset
WHERE is_active = TRUE
ORDER BY term_type, usage_count DESC;