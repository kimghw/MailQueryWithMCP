# modules/mail_dashboard/sql/create_tables.py
"""
Email Dashboard 테이블 생성 스크립트

새로운 테이블 구조를 생성합니다.
기존 테이블이 있으면 삭제하고 새로 생성합니다.
"""

import sys
import os
from pathlib import Path

# 프로젝트 루트 경로 추가
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.insert(0, project_root)

from infra.core import get_database_manager, get_logger

logger = get_logger(__name__)


def drop_old_tables(db):
    """기존 테이블 삭제"""
    old_tables = [
        "email_events_unprocessed",
        "email_agenda_member_response_times",
        "email_agenda_member_responses",
        "email_agendas_chair"
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
        "agenda_all"
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


def create_new_tables(db):
    """새 테이블 생성"""
    # SQL 파일 경로
    sql_file_path = Path(__file__).parent / "migrations" / "create_table.sql"
    
    if not sql_file_path.exists():
        logger.error(f"SQL 파일을 찾을 수 없습니다: {sql_file_path}")
        return False
    
    # SQL 파일 읽기
    with open(sql_file_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    
    logger.info(f"SQL 파일 로드 완료: {sql_file_path}")
    
    # SQL 문장별로 분리하여 실행
    statements = [stmt.strip() for stmt in schema_sql.split(";") if stmt.strip()]
    
    success_count = 0
    error_count = 0
    
    logger.info(f"총 {len(statements)}개의 SQL 문장을 실행합니다.")
    
    with db.transaction():
        for i, statement in enumerate(statements):
            if statement:
                try:
                    # 디버깅용 로그
                    if "CREATE TABLE" in statement:
                        table_name = statement.split("CREATE TABLE")[1].split("(")[0].strip()
                        logger.info(f"테이블 생성 중: {table_name}")
                    elif "CREATE INDEX" in statement:
                        index_name = statement.split("CREATE INDEX")[1].split(" ON")[0].strip()
                        if "IF NOT EXISTS" in index_name:
                            index_name = index_name.replace("IF NOT EXISTS", "").strip()
                        logger.info(f"인덱스 생성 중: {index_name}")
                    elif "CREATE TRIGGER" in statement:
                        trigger_name = statement.split("CREATE TRIGGER")[1].split()[0].strip()
                        logger.info(f"트리거 생성 중: {trigger_name}")
                    
                    db.execute_query(statement)
                    success_count += 1
                    
                except Exception as e:
                    # CREATE IF NOT EXISTS는 오류가 아님
                    if "already exists" in str(e):
                        logger.debug(f"테이블/인덱스/트리거가 이미 존재함 (정상)")
                        success_count += 1
                    else:
                        error_count += 1
                        logger.error(f"SQL 문장 {i+1} 실행 실패: {str(e)}")
                        logger.error(f"실패한 SQL:\n{statement[:200]}...")
                        raise
    
    logger.info(f"\nSQL 실행 완료: 성공 {success_count}개, 실패 {error_count}개")
    
    return error_count == 0


def verify_tables(db):
    """생성된 테이블 확인"""
    logger.info("\n테이블 생성 확인:")
    
    expected_tables = [
        ("agenda_all", "모든 이벤트 로그"),
        ("agenda_chair", "의장 발송 의제"),
        ("agenda_responses_content", "기관별 응답 내용"),
        ("agenda_responses_receivedtime", "기관별 응답 시간"),
        ("agenda_pending", "미처리 이벤트")
    ]
    
    all_created = True
    for table_name, description in expected_tables:
        if db.table_exists(table_name):
            # 테이블 정보 조회
            result = db.fetch_one(f"SELECT COUNT(*) as count FROM {table_name}")
            row_count = result["count"] if result else 0
            logger.info(f"✓ {table_name} - {description} (레코드: {row_count}개)")
            
            # 컬럼 확인
            columns = db.fetch_all(f"PRAGMA table_info({table_name})")
            logger.info(f"  컬럼 수: {len(columns)}개")
            
            # 조직 컬럼 확인 (responses 테이블)
            if table_name in ["agenda_responses_content", "agenda_responses_receivedtime"]:
                org_columns = ["ABS", "BV", "CCS", "CRS", "DNV", "IRS", "KR", "NK", "PRS", "RINA", "IL", "TL"]
                missing_orgs = []
                for org in org_columns:
                    if not any(col["name"] == org for col in columns):
                        missing_orgs.append(org)
                
                if missing_orgs:
                    logger.error(f"  누락된 조직 컬럼: {missing_orgs}")
                    all_created = False
                else:
                    logger.info(f"  모든 조직 컬럼 확인: ✓")
        else:
            logger.error(f"✗ {table_name} - 생성 실패")
            all_created = False
    
    return all_created


def verify_indices(db):
    """인덱스 생성 확인"""
    logger.info("\n인덱스 생성 확인:")
    
    # 모든 인덱스 조회
    indices = db.fetch_all(
        """
        SELECT name, tbl_name 
        FROM sqlite_master 
        WHERE type='index' 
        AND tbl_name LIKE 'agenda_%'
        AND name NOT LIKE 'sqlite_%'
        ORDER BY tbl_name, name
        """
    )
    
    if indices:
        current_table = None
        index_count = 0
        for idx in indices:
            if current_table != idx["tbl_name"]:
                if current_table:
                    logger.info(f"  └─ 총 {index_count}개 인덱스")
                current_table = idx["tbl_name"]
                index_count = 0
                logger.info(f"\n{current_table}:")
            logger.info(f"  - {idx['name']}")
            index_count += 1
        if current_table:
            logger.info(f"  └─ 총 {index_count}개 인덱스")
    else:
        logger.warning("생성된 인덱스가 없습니다.")


def verify_triggers(db):
    """트리거 생성 확인"""
    logger.info("\n트리거 생성 확인:")
    
    # 모든 트리거 조회
    triggers = db.fetch_all(
        """
        SELECT name, tbl_name 
        FROM sqlite_master 
        WHERE type='trigger'
        ORDER BY tbl_name, name
        """
    )
    
    if triggers:
        for trigger in triggers:
            logger.info(f"✓ {trigger['name']} (테이블: {trigger['tbl_name']})")
    else:
        logger.warning("생성된 트리거가 없습니다.")


def main():
    """메인 함수"""
    print("=" * 60)
    print("Email Dashboard 테이블 생성")
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
    if create_new_tables(db):
        print("   ✅ 테이블 생성 완료")
        
        # 4. 검증
        print("\n4. 테이블 검증 중...")
        if verify_tables(db):
            print("   ✅ 모든 테이블 생성 확인")
            
            # 5. 인덱스 확인
            verify_indices(db)
            
            # 6. 트리거 확인
            verify_triggers(db)
            
            print("\n✅ Email Dashboard 테이블 구성 완료")
        else:
            print("\n❌ 일부 테이블 생성 실패")
            sys.exit(1)
    else:
        print("\n❌ 테이블 생성 실패")
        sys.exit(1)


if __name__ == "__main__":
    main()