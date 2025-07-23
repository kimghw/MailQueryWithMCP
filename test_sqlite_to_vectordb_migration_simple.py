#!/usr/bin/env python3
"""
Simplified SQLite to VectorDB Migration Test Script

간단한 버전의 마이그레이션 테스트 스크립트
"""

import os
import asyncio
import logging
from datetime import datetime
import json
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import sqlite3
from openai import OpenAI

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SimpleMigrationTest:
    """간단한 SQLite to VectorDB 마이그레이션 테스트"""
    
    def __init__(self):
        # OpenAI 클라이언트 (임베딩 생성용)
        self.openai_client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Qdrant 클라이언트
        self.qdrant_client = QdrantClient(host="localhost", port=6333)
        self.collection_name = "test_templates"
        
        # SQLite 연결
        self.db_path = "./data/templates.db"
        
    def create_test_db(self):
        """테스트용 SQLite 데이터베이스 생성"""
        logger.info("테스트 데이터베이스 생성 중...")
        
        # 디렉토리 생성
        os.makedirs("data", exist_ok=True)
        
        # SQLite 연결
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 테이블 생성
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS query_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id TEXT UNIQUE NOT NULL,
                natural_questions TEXT NOT NULL,
                sql_query TEXT NOT NULL,
                keywords TEXT,
                category TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 테스트 데이터 삽입
        test_templates = [
            {
                "template_id": "test_agenda_stats",
                "natural_questions": "아젠다 통계 보여줘|최근 아젠다 현황|아젠다 상태별 통계",
                "sql_query": "SELECT status, COUNT(*) FROM agenda_all GROUP BY status",
                "keywords": json.dumps(["아젠다", "통계", "현황", "status"]),
                "category": "statistics"
            },
            {
                "template_id": "test_org_agendas",
                "natural_questions": "한국선급 아젠다 목록|KR 아젠다 조회|특정 기관 아젠다",
                "sql_query": "SELECT * FROM agenda_all WHERE organization = :org",
                "keywords": json.dumps(["기관", "선급", "아젠다", "조회"]),
                "category": "agenda"
            },
            {
                "template_id": "test_recent_responses",
                "natural_questions": "최근 응답 목록|최신 응답 보여줘|응답 리스트",
                "sql_query": "SELECT * FROM agenda_responses ORDER BY created_at DESC LIMIT 10",
                "keywords": json.dumps(["응답", "최근", "리스트", "response"]),
                "category": "response"
            }
        ]
        
        for template in test_templates:
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO query_templates 
                    (template_id, natural_questions, sql_query, keywords, category)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    template["template_id"],
                    template["natural_questions"],
                    template["sql_query"],
                    template["keywords"],
                    template["category"]
                ))
            except Exception as e:
                logger.error(f"템플릿 삽입 실패: {e}")
        
        conn.commit()
        conn.close()
        logger.info("테스트 데이터베이스 생성 완료")
    
    def get_embedding(self, text: str):
        """OpenAI API를 사용하여 텍스트 임베딩 생성"""
        try:
            response = self.openai_client.embeddings.create(
                input=text,
                model="text-embedding-3-large"
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"임베딩 생성 실패: {e}")
            return None
    
    async def setup_vector_collection(self):
        """Qdrant 컬렉션 설정"""
        logger.info("벡터 컬렉션 설정 중...")
        
        try:
            # 기존 컬렉션 삭제 (있는 경우)
            try:
                self.qdrant_client.delete_collection(self.collection_name)
                logger.info(f"기존 컬렉션 {self.collection_name} 삭제됨")
            except:
                pass
            
            # 새 컬렉션 생성
            self.qdrant_client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=3072,  # text-embedding-3-large 차원
                    distance=Distance.COSINE
                )
            )
            logger.info(f"컬렉션 {self.collection_name} 생성 완료")
            
        except Exception as e:
            logger.error(f"컬렉션 설정 실패: {e}")
            raise
    
    async def migrate_templates(self):
        """SQLite에서 VectorDB로 템플릿 마이그레이션"""
        logger.info("\n=== 템플릿 마이그레이션 시작 ===")
        
        # SQLite에서 템플릿 읽기
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM query_templates")
        templates = cursor.fetchall()
        conn.close()
        
        logger.info(f"마이그레이션할 템플릿 수: {len(templates)}")
        
        points = []
        for idx, template in enumerate(templates):
            template_id = template[1]
            natural_questions = template[2]
            sql_query = template[3]
            keywords = json.loads(template[4]) if template[4] else []
            category = template[5]
            
            logger.info(f"\n템플릿 처리 중: {template_id}")
            
            # 임베딩 생성 (자연어 질문 기반)
            embedding = self.get_embedding(natural_questions)
            if not embedding:
                logger.error(f"임베딩 생성 실패: {template_id}")
                continue
            
            # 포인트 생성
            point = PointStruct(
                id=idx,
                vector=embedding,
                payload={
                    "template_id": template_id,
                    "natural_questions": natural_questions,
                    "sql_query": sql_query,
                    "keywords": keywords,
                    "category": category
                }
            )
            points.append(point)
            logger.info(f"✓ 포인트 생성 완료: {template_id}")
        
        # 벡터 DB에 업로드
        if points:
            self.qdrant_client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            logger.info(f"\n✓ {len(points)}개 템플릿 VectorDB 업로드 완료")
        
        return len(points)
    
    async def test_vector_search(self):
        """벡터 검색 테스트"""
        logger.info("\n=== 벡터 검색 테스트 ===")
        
        test_queries = [
            "아젠다 통계 분석해줘",
            "한국선급 관련 아젠다",
            "최근에 응답한 내용"
        ]
        
        for query in test_queries:
            logger.info(f"\n검색 쿼리: '{query}'")
            
            # 쿼리 임베딩 생성
            query_embedding = self.get_embedding(query)
            if not query_embedding:
                continue
            
            # 벡터 검색
            results = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=3
            )
            
            for idx, result in enumerate(results, 1):
                logger.info(f"  {idx}. {result.payload['template_id']} (점수: {result.score:.3f})")
                logger.info(f"     질문: {result.payload['natural_questions'][:50]}...")
    
    async def verify_migration(self):
        """마이그레이션 검증"""
        logger.info("\n=== 마이그레이션 검증 ===")
        
        # SQLite 템플릿 수
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM query_templates")
        sqlite_count = cursor.fetchone()[0]
        conn.close()
        
        # VectorDB 템플릿 수
        collection_info = self.qdrant_client.get_collection(self.collection_name)
        vector_count = collection_info.points_count
        
        logger.info(f"SQLite 템플릿 수: {sqlite_count}")
        logger.info(f"VectorDB 템플릿 수: {vector_count}")
        logger.info(f"마이그레이션 완료율: {vector_count/sqlite_count*100:.1f}%")

async def main():
    """메인 함수"""
    # 환경변수 로드
    from dotenv import load_dotenv
    load_dotenv()
    
    # OpenAI API 키 확인
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("OPENAI_API_KEY 환경변수가 설정되지 않았습니다!")
        return
    
    # 마이그레이션 테스트
    test = SimpleMigrationTest()
    
    try:
        # 1. 테스트 DB 생성
        test.create_test_db()
        
        # 2. 벡터 컬렉션 설정
        await test.setup_vector_collection()
        
        # 3. 마이그레이션 실행
        migrated_count = await test.migrate_templates()
        
        # 4. 검색 테스트
        if migrated_count > 0:
            await test.test_vector_search()
        
        # 5. 검증
        await test.verify_migration()
        
    except Exception as e:
        logger.error(f"테스트 실행 중 오류: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())