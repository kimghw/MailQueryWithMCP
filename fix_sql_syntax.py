#!/usr/bin/env python3
"""
SQL 문법 수정 스크립트
CREATE TABLE 내부의 INDEX 정의를 별도의 CREATE INDEX 문으로 분리
"""

import sys
import os
from datetime import datetime
from pathlib import Path

# 프로젝트 루트 경로 추가
project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, project_root)


def fix_create_table_sql():
    """create_table.sql 파일의 문법 오류 수정"""

    # SQL 파일 경로
    sql_file = (
        Path(project_root)
        / "modules"
        / "mail_dashboard"
        / "sql"#!/usr/bin/env python3
"""
SQL 문법 수정 스크립트
CREATE TABLE 내부의 INDEX 정의를 별도의 CREATE INDEX 문으로 분리
"""

import sys
import os
from datetime import datetime
from pathlib import Path

# 프로젝트 루트 경로 추가
project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, project_root)


def fix_create_table_sql():
    """create_table.sql 파일의 문법 오류 수정"""
    
    # SQL 파일 경로
    sql_file = Path(project_root) / "modules" / "mail_dashboard" / "sql" / "migrations" / "create_table.sql"
    
    if not sql_file.exists():
        print(f"SQL 파일을 찾을 수 없습니다: {sql_file}")
        return False
    
    # 수정된 SQL (INDEX 문법 수정)
    fixed_sql = """-- =====================================================
-- 1. 모든 이벤트 로그 (참조용)
-- =====================================================
CREATE TABLE agenda_all (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL UNIQUE,
    agenda_code TEXT NOT NULL,
    sender_type TEXT NOT NULL CHECK (sender_type IN ('CHAIR', 'MEMBER')),
    sender_organization TEXT,
    sent_time TIMESTAMP NOT NULL,
    mail_type TEXT CHECK (mail_type IN ('REQUEST', 'RESPONSE', 'NOTIFICATION', 'COMPLETED', 'OTHER')),
    decision_status TEXT CHECK (decision_status IN ('created', 'comment', 'consolidated', 'review', 'decision')),
    subject TEXT,
    body TEXT,
    keywords TEXT, -- JSON array
    response_org TEXT,
    response_version TEXT,
    deadline TIMESTAMP,
    has_deadline BOOLEAN DEFAULT FALSE,
    sender TEXT,
    sender_address TEXT,
    agenda_panel TEXT,
    agenda_year TEXT,
    agenda_number TEXT,
    agenda_base TEXT,
    agenda_version TEXT,
    agenda_base_version TEXT,
    parsing_method TEXT,
    hasAttachments BOOLEAN DEFAULT FALSE,
    sentDateTime TEXT,
    webLink TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- agenda_all 인덱스
CREATE INDEX idx_agenda_all_code ON agenda_all(agenda_code);
CREATE INDEX idx_agenda_all_time ON agenda_all(sent_time);
CREATE INDEX idx_agenda_all_org ON agenda_all(sender_organization);

-- =====================================================
-- 2. 의장 발송 의제 (1개 메일 = 1개 행)
-- =====================================================
CREATE TABLE agenda_chair (
    agenda_base_version TEXT PRIMARY KEY,  -- 예: "PL25016"
    agenda_code TEXT NOT NULL UNIQUE,      -- 예: "PL25016_ILa"
    sender_type TEXT DEFAULT 'CHAIR',
    sender_organization TEXT NOT NULL,      -- 발송 기관 (의장 소속)
    sent_time TIMESTAMP NOT NULL,
    mail_type TEXT NOT NULL DEFAULT 'REQUEST',
    decision_status TEXT DEFAULT 'created',
    subject TEXT NOT NULL,
    body TEXT,
    keywords TEXT, -- JSON array
    deadline TIMESTAMP,
    has_deadline BOOLEAN DEFAULT FALSE,
    sender TEXT,
    sender_address TEXT,
    agenda_panel TEXT NOT NULL,            -- 예: "PL"
    agenda_year TEXT NOT NULL,             -- 예: "25"
    agenda_number TEXT NOT NULL,           -- 예: "016"
    agenda_version TEXT,                   -- 예: "" (초기 버전)
    parsing_method TEXT,
    hasAttachments BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CHECK (sender_type = 'CHAIR'),
    CHECK (mail_type IN ('REQUEST', 'RESPONSE', 'NOTIFICATION', 'COMPLETED', 'OTHER')),
    CHECK (decision_status IN ('created', 'comment', 'consolidated', 'review', 'decision'))
);

-- =====================================================
-- 3. 기관별 응답 내용 (1개 응답 = 1개 셀 업데이트)
-- =====================================================
CREATE TABLE agenda_responses_content (
    agenda_base_version TEXT PRIMARY KEY,
    -- 12개 IACS 멤버 기관
    ABS TEXT,     -- American Bureau of Shipping
    BV TEXT,      -- Bureau Veritas
    CCS TEXT,     -- China Classification Society
    CRS TEXT,     -- Croatian Register of Shipping
    DNV TEXT,     -- Det Norske Veritas
    IRS TEXT,     -- Indian Register of Shipping
    KR TEXT,      -- Korean Register
    NK TEXT,      -- Nippon Kaiji Kyokai
    PRS TEXT,     -- Polish Register of Shipping
    RINA TEXT,    -- Registro Italiano Navale
    IL TEXT,      -- (미확인 기관)
    TL TEXT,      -- Türk Loydu
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (agenda_base_version) 
        REFERENCES agenda_chair(agenda_base_version) 
        ON DELETE CASCADE
);

-- =====================================================
-- 4. 기관별 응답 수신 시간 (1개 응답 = 1개 셀 업데이트)
-- =====================================================
CREATE TABLE agenda_responses_receivedtime (
    agenda_base_version TEXT PRIMARY KEY,
    -- 12개 IACS 멤버 기관
    ABS TIMESTAMP,
    BV TIMESTAMP,
    CCS TIMESTAMP,
    CRS TIMESTAMP,
    DNV TIMESTAMP,
    IRS TIMESTAMP,
    KR TIMESTAMP,
    NK TIMESTAMP,
    PRS TIMESTAMP,
    RINA TIMESTAMP,
    IL TIMESTAMP,
    TL TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (agenda_base_version) 
        REFERENCES agenda_chair(agenda_base_version) 
        ON DELETE CASCADE
);

-- =====================================================
-- 5. 미처리 이벤트 (의제 코드가 없거나 처리 실패)
-- =====================================================
CREATE TABLE agenda_pending (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT UNIQUE,
    raw_event_data TEXT NOT NULL,          -- 전체 이벤트 JSON
    error_reason TEXT,                     -- 처리 실패 사유
    sender_type TEXT,
    sender_organization TEXT,
    sent_time TIMESTAMP,
    subject TEXT,
    received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMP,
    retry_count INTEGER DEFAULT 0
);

-- =====================================================
-- 인덱스 생성
-- =====================================================
-- agenda_chair 인덱스
CREATE INDEX idx_chair_panel ON agenda_chair(agenda_panel);
CREATE INDEX idx_chair_time ON agenda_chair(sent_time);
CREATE INDEX idx_chair_deadline ON agenda_chair(deadline);
CREATE INDEX idx_chair_status ON agenda_chair(decision_status);
CREATE INDEX idx_chair_deadline_status ON agenda_chair(deadline, decision_status);

-- agenda_responses 인덱스
CREATE INDEX idx_responses_updated ON agenda_responses_content(updated_at);
CREATE INDEX idx_responses_time_updated ON agenda_responses_receivedtime(updated_at);

-- agenda_pending 인덱스
CREATE INDEX idx_pending_processed ON agenda_pending(processed);
CREATE INDEX idx_pending_received ON agenda_pending(received_at);

-- =====================================================
-- 트리거: 응답 테이블 자동 초기화
-- =====================================================
CREATE TRIGGER after_chair_insert
AFTER INSERT ON agenda_chair
BEGIN
    -- 응답 내용 테이블 초기화
    INSERT INTO agenda_responses_content (agenda_base_version, created_at)
    VALUES (NEW.agenda_base_version, CURRENT_TIMESTAMP);
    
    -- 응답 시간 테이블 초기화  
    INSERT INTO agenda_responses_receivedtime (agenda_base_version, created_at)
    VALUES (NEW.agenda_base_version, CURRENT_TIMESTAMP);
END;

-- =====================================================
-- 트리거: 업데이트 시간 자동 갱신
-- =====================================================
CREATE TRIGGER update_chair_timestamp
AFTER UPDATE ON agenda_chair
BEGIN
    UPDATE agenda_chair 
    SET updated_at = CURRENT_TIMESTAMP 
    WHERE agenda_base_version = NEW.agenda_base_version;
END;

CREATE TRIGGER update_content_timestamp
AFTER UPDATE ON agenda_responses_content
BEGIN
    UPDATE agenda_responses_content 
    SET updated_at = CURRENT_TIMESTAMP 
    WHERE agenda_base_version = NEW.agenda_base_version;
END;

CREATE TRIGGER update_time_timestamp
AFTER UPDATE ON agenda_responses_receivedtime
BEGIN
    UPDATE agenda_responses_receivedtime 
    SET updated_at = CURRENT_TIMESTAMP 
    WHERE agenda_base_version = NEW.agenda_base_version;
END;"""
    
    # 백업 생성
    backup_file = sql_file.with_suffix('.sql.backup_' + datetime.now().strftime('%Y%m%d_%H%M%S'))
    
    try:
        # 원본 백업
        with open(sql_file, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        with open(backup_file, 'w', encoding='utf-8') as f:
            f.write(original_content)
        
        print(f"백업 생성: {backup_file}")
        
        # 수정된 내용 저장
        with open(sql_file, 'w', encoding='utf-8') as f:
            f.write(fixed_sql)
        
        print(f"SQL 파일 수정 완료: {sql_file}")
        return True
        
    except Exception as e:
        print(f"SQL 파일 수정 실패: {str(e)}")
        return False


def main():
    print("SQL 문법 수정 시작...")
    
    if fix_create_table_sql():
        print("\n✅ SQL 문법 수정 완료!")
        print("\n이제 다시 테스트를 실행할 수 있습니다:")
        print("python test_email_dashboard_kafka.py")
    else:
        print("\n❌ SQL 문법 수정 실패!")


if __name__ == "__main__":
    main()
        / "migrations"
        / "create_table.sql"
    )

    if not sql_file.exists():
        print(f"SQL 파일을 찾을 수 없습니다: {sql_file}")
        return False

    # 수정된 SQL (INDEX 문법 수정)
    fixed_sql = """-- =====================================================
-- 1. 모든 이벤트 로그 (참조용)
-- =====================================================
CREATE TABLE agenda_all (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL UNIQUE,
    agenda_code TEXT NOT NULL,
    sender_type TEXT NOT NULL CHECK (sender_type IN ('CHAIR', 'MEMBER')),
    sender_organization TEXT,
    sent_time TIMESTAMP NOT NULL,
    mail_type TEXT CHECK (mail_type IN ('REQUEST', 'RESPONSE', 'NOTIFICATION', 'COMPLETED', 'OTHER')),
    decision_status TEXT CHECK (decision_status IN ('created', 'comment', 'consolidated', 'review', 'decision')),
    subject TEXT,
    body TEXT,
    keywords TEXT, -- JSON array
    response_org TEXT,
    response_version TEXT,
    deadline TIMESTAMP,
    has_deadline BOOLEAN DEFAULT FALSE,
    sender TEXT,
    sender_address TEXT,
    agenda_panel TEXT,
    agenda_year TEXT,
    agenda_number TEXT,
    agenda_base TEXT,
    agenda_version TEXT,
    agenda_base_version TEXT,
    parsing_method TEXT,
    hasAttachments BOOLEAN DEFAULT FALSE,
    sentDateTime TEXT,
    webLink TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- agenda_all 인덱스
CREATE INDEX idx_agenda_all_code ON agenda_all(agenda_code);
CREATE INDEX idx_agenda_all_time ON agenda_all(sent_time);
CREATE INDEX idx_agenda_all_org ON agenda_all(sender_organization);

-- =====================================================
-- 2. 의장 발송 의제 (1개 메일 = 1개 행)
-- =====================================================
CREATE TABLE agenda_chair (
    agenda_base_version TEXT PRIMARY KEY,  -- 예: "PL25016"
    agenda_code TEXT NOT NULL UNIQUE,      -- 예: "PL25016_ILa"
    sender_type TEXT DEFAULT 'CHAIR',
    sender_organization TEXT NOT NULL,      -- 발송 기관 (의장 소속)
    sent_time TIMESTAMP NOT NULL,
    mail_type TEXT NOT NULL DEFAULT 'REQUEST',
    decision_status TEXT DEFAULT 'created',
    subject TEXT NOT NULL,
    body TEXT,
    keywords TEXT, -- JSON array
    deadline TIMESTAMP,
    has_deadline BOOLEAN DEFAULT FALSE,
    sender TEXT,
    sender_address TEXT,
    agenda_panel TEXT NOT NULL,            -- 예: "PL"
    agenda_year TEXT NOT NULL,             -- 예: "25"
    agenda_number TEXT NOT NULL,           -- 예: "016"
    agenda_version TEXT,                   -- 예: "" (초기 버전)
    parsing_method TEXT,
    hasAttachments BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CHECK (sender_type = 'CHAIR'),
    CHECK (mail_type IN ('REQUEST', 'RESPONSE', 'NOTIFICATION', 'COMPLETED', 'OTHER')),
    CHECK (decision_status IN ('created', 'comment', 'consolidated', 'review', 'decision'))
);

-- =====================================================
-- 3. 기관별 응답 내용 (1개 응답 = 1개 셀 업데이트)
-- =====================================================
CREATE TABLE agenda_responses_content (
    agenda_base_version TEXT PRIMARY KEY,
    -- 12개 IACS 멤버 기관
    ABS TEXT,     -- American Bureau of Shipping
    BV TEXT,      -- Bureau Veritas
    CCS TEXT,     -- China Classification Society
    CRS TEXT,     -- Croatian Register of Shipping
    DNV TEXT,     -- Det Norske Veritas
    IRS TEXT,     -- Indian Register of Shipping
    KR TEXT,      -- Korean Register
    NK TEXT,      -- Nippon Kaiji Kyokai
    PRS TEXT,     -- Polish Register of Shipping
    RINA TEXT,    -- Registro Italiano Navale
    IL TEXT,      -- (미확인 기관)
    TL TEXT,      -- Türk Loydu
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (agenda_base_version) 
        REFERENCES agenda_chair(agenda_base_version) 
        ON DELETE CASCADE
);

-- =====================================================
-- 4. 기관별 응답 수신 시간 (1개 응답 = 1개 셀 업데이트)
-- =====================================================
CREATE TABLE agenda_responses_receivedtime (
    agenda_base_version TEXT PRIMARY KEY,
    -- 12개 IACS 멤버 기관
    ABS TIMESTAMP,
    BV TIMESTAMP,
    CCS TIMESTAMP,
    CRS TIMESTAMP,
    DNV TIMESTAMP,
    IRS TIMESTAMP,
    KR TIMESTAMP,
    NK TIMESTAMP,
    PRS TIMESTAMP,
    RINA TIMESTAMP,
    IL TIMESTAMP,
    TL TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (agenda_base_version) 
        REFERENCES agenda_chair(agenda_base_version) 
        ON DELETE CASCADE
);

-- =====================================================
-- 5. 미처리 이벤트 (의제 코드가 없거나 처리 실패)
-- =====================================================
CREATE TABLE agenda_pending (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT UNIQUE,
    raw_event_data TEXT NOT NULL,          -- 전체 이벤트 JSON
    error_reason TEXT,                     -- 처리 실패 사유
    sender_type TEXT,
    sender_organization TEXT,
    sent_time TIMESTAMP,
    subject TEXT,
    received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMP,
    retry_count INTEGER DEFAULT 0
);

-- =====================================================
-- 인덱스 생성
-- =====================================================
-- agenda_chair 인덱스
CREATE INDEX idx_chair_panel ON agenda_chair(agenda_panel);
CREATE INDEX idx_chair_time ON agenda_chair(sent_time);
CREATE INDEX idx_chair_deadline ON agenda_chair(deadline);
CREATE INDEX idx_chair_status ON agenda_chair(decision_status);
CREATE INDEX idx_chair_deadline_status ON agenda_chair(deadline, decision_status);

-- agenda_responses 인덱스
CREATE INDEX idx_responses_updated ON agenda_responses_content(updated_at);
CREATE INDEX idx_responses_time_updated ON agenda_responses_receivedtime(updated_at);

-- agenda_pending 인덱스
CREATE INDEX idx_pending_processed ON agenda_pending(processed);
CREATE INDEX idx_pending_received ON agenda_pending(received_at);

-- =====================================================
-- 트리거: 응답 테이블 자동 초기화
-- =====================================================
CREATE TRIGGER after_chair_insert
AFTER INSERT ON agenda_chair
BEGIN
    -- 응답 내용 테이블 초기화
    INSERT INTO agenda_responses_content (agenda_base_version, created_at)
    VALUES (NEW.agenda_base_version, CURRENT_TIMESTAMP);
    
    -- 응답 시간 테이블 초기화  
    INSERT INTO agenda_responses_receivedtime (agenda_base_version, created_at)
    VALUES (NEW.agenda_base_version, CURRENT_TIMESTAMP);
END;

-- =====================================================
-- 트리거: 업데이트 시간 자동 갱신
-- =====================================================
CREATE TRIGGER update_chair_timestamp
AFTER UPDATE ON agenda_chair
BEGIN
    UPDATE agenda_chair 
    SET updated_at = CURRENT_TIMESTAMP 
    WHERE agenda_base_version = NEW.agenda_base_version;
END;

CREATE TRIGGER update_content_timestamp
AFTER UPDATE ON agenda_responses_content
BEGIN
    UPDATE agenda_responses_content 
    SET updated_at = CURRENT_TIMESTAMP 
    WHERE agenda_base_version = NEW.agenda_base_version;
END;

CREATE TRIGGER update_time_timestamp
AFTER UPDATE ON agenda_responses_receivedtime
BEGIN
    UPDATE agenda_responses_receivedtime 
    SET updated_at = CURRENT_TIMESTAMP 
    WHERE agenda_base_version = NEW.agenda_base_version;
END;"""

    # 백업 생성
    backup_file = sql_file.with_suffix(
        ".sql.backup_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    )

    try:
        # 원본 백업
        with open(sql_file, "r", encoding="utf-8") as f:
            original_content = f.read()

        with open(backup_file, "w", encoding="utf-8") as f:
            f.write(original_content)

        print(f"백업 생성: {backup_file}")

        # 수정된 내용 저장
        with open(sql_file, "w", encoding="utf-8") as f:
            f.write(fixed_sql)

        print(f"SQL 파일 수정 완료: {sql_file}")
        return True

    except Exception as e:
        print(f"SQL 파일 수정 실패: {str(e)}")
        return False


def main():
    print("SQL 문법 수정 시작...")

    if fix_create_table_sql():
        print("\n✅ SQL 문법 수정 완료!")
        print("\n이제 다시 테스트를 실행할 수 있습니다:")
        print("python test_email_dashboard_kafka.py")
    else:
        print("\n❌ SQL 문법 수정 실패!")


if __name__ == "__main__":
    main()
EOF
