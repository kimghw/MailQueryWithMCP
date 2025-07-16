"""
Fallback Queries Repository
폴백 쿼리 데이터베이스 접근 계층
"""

import sqlite3
from typing import List, Optional, Dict, Any
from datetime import datetime
import json

from ..models.fallback_queries import FallbackQuery
from infra.core.config import get_config


class FallbackRepository:
    """폴백 쿼리 저장소"""
    
    def __init__(self, db_path: Optional[str] = None):
        config = get_config()
        self.db_path = db_path or config.database_path
    
    def save(self, query: FallbackQuery) -> int:
        """폴백 쿼리 저장"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            data = query.to_dict()
            del data['id']  # id는 자동 생성
            
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['?' for _ in data])
            values = list(data.values())
            
            cursor.execute(
                f"INSERT INTO fallback_queries ({columns}) VALUES ({placeholders})",
                values
            )
            
            query_id = cursor.lastrowid
            conn.commit()
            
            query.id = query_id
            return query_id
            
        finally:
            conn.close()
    
    def update(self, query: FallbackQuery) -> bool:
        """폴백 쿼리 업데이트"""
        if not query.id:
            raise ValueError("Query ID is required for update")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            query.updated_at = datetime.now()
            data = query.to_dict()
            query_id = data.pop('id')
            
            set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
            values = list(data.values()) + [query_id]
            
            cursor.execute(
                f"UPDATE fallback_queries SET {set_clause} WHERE id = ?",
                values
            )
            
            success = cursor.rowcount > 0
            conn.commit()
            
            return success
            
        finally:
            conn.close()
    
    def find_by_id(self, query_id: int) -> Optional[FallbackQuery]:
        """ID로 쿼리 조회"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT * FROM fallback_queries WHERE id = ?",
                (query_id,)
            )
            
            row = cursor.fetchone()
            if row:
                return FallbackQuery.from_dict(dict(row))
            
            return None
            
        finally:
            conn.close()
    
    def find_by_pattern_hash(self, pattern_hash: str) -> List[FallbackQuery]:
        """패턴 해시로 쿼리 조회"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT * FROM fallback_queries WHERE pattern_hash = ? ORDER BY created_at DESC",
                (pattern_hash,)
            )
            
            rows = cursor.fetchall()
            return [FallbackQuery.from_dict(dict(row)) for row in rows]
            
        finally:
            conn.close()
    
    def find_template_candidates(self, min_frequency: int = 3) -> List[Dict[str, Any]]:
        """템플릿 후보 조회"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT 
                    pattern_hash,
                    COUNT(*) as occurrence_count,
                    AVG(match_score) as avg_match_score,
                    MAX(original_query) as sample_query,
                    GROUP_CONCAT(DISTINCT missing_params) as common_missing_params
                FROM fallback_queries
                WHERE is_template_candidate = 0
                    AND sql_validation_status = 'valid'
                    AND user_feedback != 'unsatisfied'
                GROUP BY pattern_hash
                HAVING occurrence_count >= ?
                ORDER BY occurrence_count DESC
            """, (min_frequency,))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
            
        finally:
            conn.close()
    
    def find_recent_queries(self, limit: int = 100) -> List[FallbackQuery]:
        """최근 쿼리 조회"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT * FROM fallback_queries ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
            
            rows = cursor.fetchall()
            return [FallbackQuery.from_dict(dict(row)) for row in rows]
            
        finally:
            conn.close()
    
    def find_by_session(self, session_id: str) -> List[FallbackQuery]:
        """세션별 쿼리 조회"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT * FROM fallback_queries WHERE session_id = ? ORDER BY created_at",
                (session_id,)
            )
            
            rows = cursor.fetchall()
            return [FallbackQuery.from_dict(dict(row)) for row in rows]
            
        finally:
            conn.close()
    
    def get_statistics(self) -> Dict[str, Any]:
        """통계 조회"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 전체 통계
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_queries,
                    COUNT(DISTINCT session_id) as unique_sessions,
                    AVG(match_score) as avg_match_score,
                    AVG(execution_time_ms) as avg_execution_time,
                    SUM(CASE WHEN user_feedback = 'satisfied' THEN 1 ELSE 0 END) as satisfied_count,
                    SUM(CASE WHEN user_feedback = 'unsatisfied' THEN 1 ELSE 0 END) as unsatisfied_count
                FROM fallback_queries
            """)
            
            row = cursor.fetchone()
            stats = {
                'total_queries': row[0],
                'unique_sessions': row[1],
                'avg_match_score': row[2],
                'avg_execution_time': row[3],
                'satisfied_count': row[4],
                'unsatisfied_count': row[5]
            }
            
            # 폴백 타입별 통계
            cursor.execute("""
                SELECT 
                    fallback_type,
                    COUNT(*) as count
                FROM fallback_queries
                WHERE fallback_type IS NOT NULL
                GROUP BY fallback_type
            """)
            
            stats['fallback_type_distribution'] = {
                row[0]: row[1] for row in cursor.fetchall()
            }
            
            # SQL 검증 상태별 통계
            cursor.execute("""
                SELECT 
                    sql_validation_status,
                    COUNT(*) as count
                FROM fallback_queries
                WHERE sql_validation_status IS NOT NULL
                GROUP BY sql_validation_status
            """)
            
            stats['validation_status_distribution'] = {
                row[0]: row[1] for row in cursor.fetchall()
            }
            
            return stats
            
        finally:
            conn.close()
    
    def cleanup_old_queries(self, days_to_keep: int = 90) -> int:
        """오래된 쿼리 정리"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                DELETE FROM fallback_queries
                WHERE created_at < datetime('now', '-' || ? || ' days')
                    AND is_template_candidate = 0
                    AND template_created = 0
            """, (days_to_keep,))
            
            deleted_count = cursor.rowcount
            conn.commit()
            
            return deleted_count
            
        finally:
            conn.close()