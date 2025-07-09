# modules/mail_dashboard/sql/create_tables_direct.py
"""
Email Dashboard 테이블 생성 스크립트 (직접 생성)

Python 코드로 직접 테이블을 생성합니다.
"""

import sys
import os

# 프로젝트 루트 경로 추가
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.insert(0, project_root)

from infra.core import get_database_manager, get_logger

logger = get_logger(__name__)


def create_tables_directly(db):
    """Python 코드로 직접 테이블 생성"""

    # 1. agenda_all 테이블
    agenda_all_sql = """
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
        keywords TEXT,
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
    )
    """

    # 2. agenda_chair 테이블
    agenda_chair_sql = """
    CREATE TABLE agenda_chair (
        agenda_base_version TEXT PRIMARY KEY,
        agenda_code TEXT NOT NULL UNIQUE,
        sender_type TEXT DEFAULT 'CHAIR',
        sender_organization TEXT NOT NULL,
        sent_time TIMESTAMP NOT NULL,
        mail_type TEXT NOT NULL DEFAULT 'REQUEST',
        decision_status TEXT DEFAULT 'created',
        subject TEXT NOT NULL,
        body TEXT,
        keywords TEXT,
        deadline TIMESTAMP,
        has_deadline BOOLEAN DEFAULT FALSE,
        sender TEXT,
        sender_address TEXT,
        agenda_panel TEXT NOT NULL,
        agenda_year TEXT NOT NULL,
        agenda_number TEXT NOT NULL,
        agenda_version TEXT,
        parsing_method TEXT,
        hasAttachments BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        
        CHECK (sender_type = 'CHAIR'),
        CHECK (mail_type IN ('REQUEST', 'RESPONSE', 'NOTIFICATION', 'COMPLETED', 'OTHER')),
        CHECK (decision_status IN ('created', 'comment', 'consolidated', 'review', 'decision'))
    )
    """

    # 3. agenda_responses_content 테이블
    agenda_responses_content_sql = """
    CREATE TABLE agenda_responses_content (
        agenda_base_version TEXT PRIMARY KEY,
        ABS TEXT,
        BV TEXT,
        CCS TEXT,
        CRS TEXT,
        DNV TEXT,
        IRS TEXT,
        KR TEXT,
        NK TEXT,
        PRS TEXT,
        RINA TEXT,
        IL TEXT,
        TL TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        
        FOREIGN KEY (agenda_base_version) 
            REFERENCES agenda_chair(agenda_base_version) 
            ON DELETE CASCADE
    )
    """

    # 4. agenda_responses_receivedtime 테이블
    agenda_responses_receivedtime_sql = """
    CREATE TABLE agenda_responses_receivedtime (
        agenda_base_version TEXT PRIMARY KEY,
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
    )
    """

    # 5. agenda_pending 테이블
    agenda_pending_sql = """
    CREATE TABLE agenda_pending (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id TEXT UNIQUE,
        raw_event_data TEXT NOT NULL,
        error_reason TEXT,
        sender_type TEXT,
        sender_organization TEXT,
        sent_time TIMESTAMP,
        subject TEXT,
        received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        processed BOOLEAN DEFAULT FALSE,
        processed_at TIMESTAMP,
        retry_count INTEGER DEFAULT 0
    )
    """

    # 테이블 생성
    tables = [
        ("agenda_all", agenda_all_sql),
        ("agenda_chair", agenda_chair_sql),
        ("agenda_responses_content", agenda_responses_content_sql),
        ("agenda_responses_receivedtime", agenda_responses_receivedtime_sql),
        ("agenda_pending", agenda_pending_sql),
    ]

    success_count = 0

    with db.transaction():
        for table_name, sql in tables:
            try:
                logger.info(f"테이블 생성 중: {table_name}")
                db.execute_query(sql)
                success_count += 1
            except Exception as e:
                if "already exists" in str(e):
                    logger.info(f"테이블 {table_name}이 이미 존재함")
                    success_count += 1
                else:
                    logger.error(f"테이블 {table_name} 생성 실패: {str(e)}")
                    raise

        # 인덱스 생성
        indices = [
            "CREATE INDEX idx_agenda_all_code ON agenda_all(agenda_code)",
            "CREATE INDEX idx_agenda_all_time ON agenda_all(sent_time)",
            "CREATE INDEX idx_agenda_all_org ON agenda_all(sender_organization)",
            "CREATE INDEX idx_chair_panel ON agenda_chair(agenda_panel)",
            "CREATE INDEX idx_chair_time ON agenda_chair(sent_time)",
            "CREATE INDEX idx_chair_deadline ON agenda_chair(deadline)",
            "CREATE INDEX idx_chair_status ON agenda_chair(decision_status)",
            "CREATE INDEX idx_chair_deadline_status ON agenda_chair(deadline, decision_status)",
            "CREATE INDEX idx_responses_updated ON agenda_responses_content(updated_at)",
            "CREATE INDEX idx_responses_time_updated ON agenda_responses_receivedtime(updated_at)",
            "CREATE INDEX idx_pending_processed ON agenda_pending(processed)",
            "CREATE INDEX idx_pending_received ON agenda_pending(received_at)",
        ]

        for index_sql in indices:
            try:
                index_name = index_sql.split("CREATE INDEX")[1].split(" ON")[0].strip()
                logger.info(f"인덱스 생성 중: {index_name}")
                db.execute_query(index_sql)
            except Exception as e:
                if "already exists" in str(e):
                    logger.debug(f"인덱스가 이미 존재함")
                else:
                    logger.error(f"인덱스 생성 실패: {str(e)}")
                    # 인덱스 실패는 치명적이지 않음

        # 트리거 생성
        triggers = [
            """
            CREATE TRIGGER after_chair_insert
            AFTER INSERT ON agenda_chair
            BEGIN
                INSERT INTO agenda_responses_content (agenda_base_version, created_at)
                VALUES (NEW.agenda_base_version, CURRENT_TIMESTAMP);
                
                INSERT INTO agenda_responses_receivedtime (agenda_base_version, created_at)
                VALUES (NEW.agenda_base_version, CURRENT_TIMESTAMP);
            END
            """,
            """
            CREATE TRIGGER update_chair_timestamp
            AFTER UPDATE ON agenda_chair
            BEGIN
                UPDATE agenda_chair 
                SET updated_at = CURRENT_TIMESTAMP 
                WHERE agenda_base_version = NEW.agenda_base_version;
            END
            """,
            """
            CREATE TRIGGER update_content_timestamp
            AFTER UPDATE ON agenda_responses_content
            BEGIN
                UPDATE agenda_responses_content 
                SET updated_at = CURRENT_TIMESTAMP 
                WHERE agenda_base_version = NEW.agenda_base_version;
            END
            """,
            """
            CREATE TRIGGER update_time_timestamp
            AFTER UPDATE ON agenda_responses_receivedtime
            BEGIN
                UPDATE agenda_responses_receivedtime 
                SET updated_at = CURRENT_TIMESTAMP 
                WHERE agenda_base_version = NEW.agenda_base_version;
            END
            """,
        ]

        for i, trigger_sql in enumerate(triggers):
            try:
                trigger_name = f"trigger_{i+1}"
                logger.info(f"트리거 생성 중: {trigger_name}")
                db.execute_query(trigger_sql)
            except Exception as e:
                if "already exists" in str(e):
                    logger.debug(f"트리거가 이미 존재함")
                else:
                    logger.error(f"트리거 생성 실패: {str(e)}")
                    # 트리거 실패는 치명적이지 않음

    logger.info(f"테이블 생성 완료: {success_count}개")
    return success_count == len(tables)


def drop_old_tables(db):
    """기존 테이블 삭제"""
    old_tables = [
        "email_events_unprocessed",
        "email_agenda_member_response_times",
        "email_agenda_member_responses",
        "email_agendas_chair",
    ]

    dropped = 0
    for table in old_tables:
        try:
            if db.table_exists(table):
                db.execute_query(f"DROP TABLE IF EXISTS {table}")
                logger.info(f"기존 테이블 삭제: {table}")
                dropped += 1
        except Exception as e:
            logger.error(f"테이블 삭제 실패 {table}: {str(e)}")

    return dropped


def drop_new_tables(db):
    """새 테이블 삭제 (재생성을 위해)"""
    new_tables = [
        "agenda_pending",
        "agenda_responses_receivedtime",
        "agenda_responses_content",
        "agenda_chair",
        "agenda_all",
    ]

    dropped = 0
    for table in new_tables:
        try:
            if db.table_exists(table):
                db.execute_query(f"DROP TABLE IF EXISTS {table}")
                logger.info(f"기존 테이블 삭제: {table}")
                dropped += 1
        except Exception as e:
            logger.error(f"테이블 삭제 실패 {table}: {str(e)}")

    return dropped


def main():
    """메인 함수"""
    print("=" * 60)
    print("Email Dashboard 테이블 생성 (직접 생성)")
    print("=" * 60)
    print()

    db = get_database_manager()

    # 1. 기존 테이블 삭제
    print("1. 기존 테이블 삭제 중...")
    old_dropped = drop_old_tables(db)
    print(f"   - 기존 테이블 {old_dropped}개 삭제됨")

    # 2. 새 테이블도 삭제 (재생성을 위해)
    if "--force" in sys.argv:
        print("\n2. 새 테이블 삭제 중 (강제 재생성)...")
        new_dropped = drop_new_tables(db)
        print(f"   - 새 테이블 {new_dropped}개 삭제됨")

    # 3. 새 테이블 생성
    print("\n3. 새 테이블 생성 중...")
    if create_tables_directly(db):
        print("   ✅ 테이블 생성 완료")
        print("\n✅ Email Dashboard 테이블 구성 완료")
    else:
        print("\n❌ 테이블 생성 실패")
        sys.exit(1)


if __name__ == "__main__":
    main()
