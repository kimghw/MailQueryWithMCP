#!/usr/bin/env python3
"""
SQLite to VectorDB Migration Test Script

이 스크립트는 SQLite에 저장된 템플릿을 VectorDB(Qdrant)로 마이그레이션하는 테스트를 수행합니다.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from datetime import datetime
import json

# 프로젝트 루트 경로 추가
sys.path.append(str(Path(__file__).parent))

from modules.query_assistant.database.template_manager import TemplateManager
from modules.query_assistant.database.template_db_schema import QueryTemplateDB, get_session
from modules.query_assistant.services.vector_store_http import VectorStoreHTTP
from modules.query_assistant.models.vector_payload import VectorPayload
from infra.core.config import settings

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MigrationTest:
    """SQLite to VectorDB 마이그레이션 테스트"""
    
    def __init__(self):
        # SQLite DB 경로 설정
        self.db_path = Path("./data/templates.db")
        self.db_url = f"sqlite:///{self.db_path}"
        
        # VectorDB 연결 설정
        self.vector_store = VectorStoreHTTP(
            base_url="http://localhost:6333",
            api_key=settings.get("OPENAI_API_KEY")
        )
        
        # Template Manager 초기화
        self.template_manager = TemplateManager(
            db_url=self.db_url,
            vector_store=self.vector_store
        )
        
    def create_test_templates(self):
        """테스트용 템플릿 생성"""
        logger.info("테스트 템플릿 생성 중...")
        
        test_templates = [
            {
                "template_id": "test_agenda_response_rate",
                "natural_questions": "최근 아젠다 응답률은 어떻게 되나요?|아젠다 응답 통계 보여줘|응답률 확인",
                "sql_query": """
                    SELECT 
                        COUNT(DISTINCT ar.agenda_id) as total_agendas,
                        COUNT(DISTINCT CASE WHEN ar.response_status = 'received' THEN ar.agenda_id END) as responded_agendas,
                        ROUND(CAST(COUNT(DISTINCT CASE WHEN ar.response_status = 'received' THEN ar.agenda_id END) AS FLOAT) / 
                              COUNT(DISTINCT ar.agenda_id) * 100, 2) as response_rate
                    FROM agenda_responses ar
                    WHERE ar.created_at >= datetime('now', '-30 days')
                """,
                "keywords": ["아젠다", "응답률", "통계", "응답", "response", "rate"],
                "category": "statistics",
                "required_params": [],
                "optional_params": ["days"],
                "default_params": {"days": 30},
                "description": "최근 아젠다 응답률 통계를 조회합니다."
            },
            {
                "template_id": "test_organization_agendas",
                "natural_questions": "특정 기관의 아젠다 목록|{organization} 아젠다 보여줘|기관별 아젠다 조회",
                "sql_query_with_parameters": """
                    SELECT 
                        a.agenda_id,
                        a.title,
                        a.organization,
                        a.status,
                        a.created_at
                    FROM agenda_all a
                    WHERE a.organization = :organization
                    ORDER BY a.created_at DESC
                    LIMIT :limit
                """,
                "keywords": ["기관", "아젠다", "organization", "목록", "조회"],
                "category": "agenda",
                "required_params": ["organization"],
                "optional_params": ["limit"],
                "default_params": {"limit": 20},
                "description": "특정 기관의 아젠다 목록을 조회합니다."
            },
            {
                "template_id": "test_pending_decisions",
                "natural_questions": "미결정 아젠다 목록|결정 대기중인 아젠다|pending 아젠다",
                "sql_query": """
                    SELECT 
                        a.agenda_id,
                        a.title,
                        a.organization,
                        a.chair_name,
                        a.created_at,
                        JULIANDAY('now') - JULIANDAY(a.created_at) as days_pending
                    FROM agenda_pending a
                    WHERE a.decision_status = 'pending'
                    ORDER BY a.created_at ASC
                """,
                "keywords": ["미결정", "대기", "pending", "decision", "결정"],
                "category": "agenda",
                "required_params": [],
                "optional_params": [],
                "default_params": {},
                "description": "결정 대기중인 아젠다 목록을 조회합니다."
            }
        ]
        
        session = self.template_manager.get_db_session()
        created_count = 0
        
        try:
            for template_data in test_templates:
                try:
                    # 기존 템플릿 확인
                    existing = session.query(QueryTemplateDB).filter_by(
                        template_id=template_data["template_id"]
                    ).first()
                    
                    if existing:
                        logger.info(f"템플릿 {template_data['template_id']} 이미 존재 - 스킵")
                        continue
                    
                    # 새 템플릿 생성
                    template = self.template_manager.create_template(template_data)
                    created_count += 1
                    logger.info(f"템플릿 생성 완료: {template.template_id}")
                    
                except Exception as e:
                    logger.error(f"템플릿 생성 실패 ({template_data['template_id']}): {e}")
                    
            session.commit()
            logger.info(f"총 {created_count}개의 테스트 템플릿 생성 완료")
            
        except Exception as e:
            session.rollback()
            logger.error(f"템플릿 생성 중 오류: {e}")
            raise
        finally:
            session.close()
    
    async def test_migration(self):
        """마이그레이션 테스트 실행"""
        logger.info("=== SQLite to VectorDB 마이그레이션 테스트 시작 ===")
        
        # 1. SQLite 템플릿 확인
        session = self.template_manager.get_db_session()
        try:
            # 전체 템플릿 수 확인
            total_templates = session.query(QueryTemplateDB).filter_by(is_active=True).count()
            logger.info(f"SQLite 총 템플릿 수: {total_templates}")
            
            # 벡터 인덱싱되지 않은 템플릿 확인
            unindexed_templates = session.query(QueryTemplateDB).filter_by(
                is_active=True,
                vector_indexed=False
            ).all()
            logger.info(f"벡터 인덱싱 필요한 템플릿 수: {len(unindexed_templates)}")
            
            # 2. VectorDB 연결 테스트
            logger.info("\nVectorDB 연결 테스트...")
            try:
                collections = await self.vector_store.client.get_collections()
                logger.info(f"VectorDB 연결 성공! 현재 컬렉션: {[c.name for c in collections.collections]}")
            except Exception as e:
                logger.error(f"VectorDB 연결 실패: {e}")
                logger.info("Qdrant가 실행 중인지 확인하세요: docker-compose -f docker-compose.query-assistant.yml up -d qdrant")
                return
            
            # 3. 컬렉션 초기화
            logger.info("\nVectorDB 컬렉션 초기화...")
            try:
                await self.vector_store.initialize_collection()
                logger.info("컬렉션 초기화 완료")
            except Exception as e:
                logger.error(f"컬렉션 초기화 실패: {e}")
            
            # 4. 템플릿 마이그레이션
            logger.info("\n템플릿 마이그레이션 시작...")
            success_count = 0
            error_count = 0
            
            for template in unindexed_templates:
                try:
                    # VectorDB에 템플릿 추가
                    logger.info(f"\n템플릿 처리 중: {template.template_id}")
                    
                    # 페이로드 생성
                    payload_data = template.to_vector_payload()
                    
                    # 벡터 스토어에 추가
                    vector_id = await self.vector_store.add_template(
                        template_id=template.template_id,
                        natural_questions=template.natural_questions,
                        keywords=template.keywords or [],
                        metadata=payload_data
                    )
                    
                    # SQLite 업데이트
                    template.vector_indexed = True
                    template.vector_id = vector_id
                    session.commit()
                    
                    success_count += 1
                    logger.info(f"✓ 성공: {template.template_id} -> Vector ID: {vector_id}")
                    
                except Exception as e:
                    error_count += 1
                    logger.error(f"✗ 실패: {template.template_id} - {e}")
                    session.rollback()
            
            # 5. 마이그레이션 결과
            logger.info(f"\n=== 마이그레이션 완료 ===")
            logger.info(f"성공: {success_count}개")
            logger.info(f"실패: {error_count}개")
            
            # 6. 검증 - 벡터 검색 테스트
            logger.info("\n=== 벡터 검색 테스트 ===")
            test_queries = [
                "아젠다 응답률은?",
                "한국선급 아젠다 목록",
                "미결정 아젠다 보여줘"
            ]
            
            for query in test_queries:
                logger.info(f"\n검색 쿼리: '{query}'")
                try:
                    results = await self.vector_store.search_similar_templates(
                        query=query,
                        limit=3
                    )
                    
                    for i, result in enumerate(results, 1):
                        logger.info(f"  {i}. {result.get('template_id')} (점수: {result.get('score', 0):.3f})")
                        if 'natural_questions' in result:
                            questions = result['natural_questions'].split('|')[:2]
                            logger.info(f"     질문: {' | '.join(questions)}")
                            
                except Exception as e:
                    logger.error(f"  검색 실패: {e}")
            
        except Exception as e:
            logger.error(f"마이그레이션 테스트 중 오류: {e}")
            raise
        finally:
            session.close()
    
    async def verify_migration(self):
        """마이그레이션 검증"""
        logger.info("\n=== 마이그레이션 검증 ===")
        
        session = self.template_manager.get_db_session()
        try:
            # SQLite 통계
            total_templates = session.query(QueryTemplateDB).filter_by(is_active=True).count()
            indexed_templates = session.query(QueryTemplateDB).filter_by(
                is_active=True,
                vector_indexed=True
            ).count()
            
            logger.info(f"SQLite 전체 템플릿: {total_templates}")
            logger.info(f"벡터 인덱싱 완료: {indexed_templates}")
            logger.info(f"인덱싱률: {indexed_templates/total_templates*100:.1f}%")
            
            # VectorDB 통계
            try:
                collection_info = await self.vector_store.client.get_collection(
                    collection_name=self.vector_store.collection_name
                )
                logger.info(f"\nVectorDB 컬렉션 정보:")
                logger.info(f"  - 이름: {collection_info.name}")
                logger.info(f"  - 벡터 수: {collection_info.points_count}")
                logger.info(f"  - 벡터 차원: {collection_info.config.params.vectors.size}")
                
            except Exception as e:
                logger.error(f"VectorDB 정보 조회 실패: {e}")
                
        finally:
            session.close()

async def main():
    """메인 함수"""
    # 마이그레이션 테스트 객체 생성
    migration_test = MigrationTest()
    
    # 1. 테스트 템플릿 생성
    migration_test.create_test_templates()
    
    # 2. 마이그레이션 실행
    await migration_test.test_migration()
    
    # 3. 검증
    await migration_test.verify_migration()

if __name__ == "__main__":
    # 이벤트 루프 실행
    asyncio.run(main())