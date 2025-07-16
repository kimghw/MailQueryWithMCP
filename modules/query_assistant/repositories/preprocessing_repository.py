"""
Preprocessing Dataset Repository
전처리 데이터셋 데이터베이스 접근 계층
"""

import sqlite3
from typing import List, Optional, Dict, Any
from datetime import datetime
import json

from ..models.preprocessing_dataset import PreprocessingTerm, PreprocessingDataset
from ...infra.core.config import get_config


class PreprocessingRepository:
    """전처리 데이터셋 저장소"""
    
    def __init__(self, db_path: Optional[str] = None):
        config = get_config()
        self.db_path = db_path or config.database_path
    
    def save(self, term: PreprocessingTerm) -> int:
        """전처리 용어 저장"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            data = term.to_dict()
            del data['id']  # id는 자동 생성
            
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['?' for _ in data])
            values = list(data.values())
            
            cursor.execute(
                f"INSERT INTO preprocessing_dataset ({columns}) VALUES ({placeholders})",
                values
            )
            
            term_id = cursor.lastrowid
            conn.commit()
            
            term.id = term_id
            return term_id
            
        finally:
            conn.close()
    
    def update(self, term: PreprocessingTerm) -> bool:
        """전처리 용어 업데이트"""
        if not term.id:
            raise ValueError("Term ID is required for update")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            term.updated_at = datetime.now()
            data = term.to_dict()
            term_id = data.pop('id')
            
            set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
            values = list(data.values()) + [term_id]
            
            cursor.execute(
                f"UPDATE preprocessing_dataset SET {set_clause} WHERE id = ?",
                values
            )
            
            success = cursor.rowcount > 0
            conn.commit()
            
            return success
            
        finally:
            conn.close()
    
    def find_by_id(self, term_id: int) -> Optional[PreprocessingTerm]:
        """ID로 용어 조회"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT * FROM preprocessing_dataset WHERE id = ?",
                (term_id,)
            )
            
            row = cursor.fetchone()
            if row:
                return PreprocessingTerm.from_dict(dict(row))
            
            return None
            
        finally:
            conn.close()
    
    def find_by_original_term(self, original_term: str) -> List[PreprocessingTerm]:
        """원본 용어로 조회"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT * FROM preprocessing_dataset WHERE original_term = ? AND is_active = 1",
                (original_term,)
            )
            
            rows = cursor.fetchall()
            return [PreprocessingTerm.from_dict(dict(row)) for row in rows]
            
        finally:
            conn.close()
    
    def find_by_type(self, term_type: str) -> List[PreprocessingTerm]:
        """타입별 용어 조회"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT * FROM preprocessing_dataset WHERE term_type = ? AND is_active = 1 ORDER BY usage_count DESC",
                (term_type,)
            )
            
            rows = cursor.fetchall()
            return [PreprocessingTerm.from_dict(dict(row)) for row in rows]
            
        finally:
            conn.close()
    
    def find_by_category(self, category: str) -> List[PreprocessingTerm]:
        """카테고리별 용어 조회"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT * FROM preprocessing_dataset WHERE category = ? AND is_active = 1 ORDER BY usage_count DESC",
                (category,)
            )
            
            rows = cursor.fetchall()
            return [PreprocessingTerm.from_dict(dict(row)) for row in rows]
            
        finally:
            conn.close()
    
    def get_all_active_terms(self) -> List[PreprocessingTerm]:
        """모든 활성 용어 조회"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT * FROM preprocessing_dataset WHERE is_active = 1 ORDER BY pattern_priority, usage_count DESC"
            )
            
            rows = cursor.fetchall()
            return [PreprocessingTerm.from_dict(dict(row)) for row in rows]
            
        finally:
            conn.close()
    
    def load_dataset(self) -> PreprocessingDataset:
        """전체 데이터셋 로드"""
        terms = self.get_all_active_terms()
        return PreprocessingDataset(terms)
    
    def record_usage(self, term_id: int, accuracy: float = 1.0) -> bool:
        """사용 기록 업데이트"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE preprocessing_dataset 
                SET usage_count = usage_count + 1,
                    last_used_at = CURRENT_TIMESTAMP,
                    match_accuracy = ((match_accuracy * usage_count) + ?) / (usage_count + 1),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (accuracy, term_id))
            
            success = cursor.rowcount > 0
            conn.commit()
            
            return success
            
        finally:
            conn.close()
    
    def find_similar_terms(self, normalized_term: str, limit: int = 5) -> List[PreprocessingTerm]:
        """유사한 정규화 용어를 가진 항목 조회"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT * FROM preprocessing_dataset 
                WHERE normalized_term = ? 
                    AND is_active = 1
                ORDER BY usage_count DESC
                LIMIT ?
            """, (normalized_term, limit))
            
            rows = cursor.fetchall()
            return [PreprocessingTerm.from_dict(dict(row)) for row in rows]
            
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
                    COUNT(*) as total_terms,
                    SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active_terms,
                    SUM(CASE WHEN is_pattern = 1 THEN 1 ELSE 0 END) as pattern_terms,
                    SUM(usage_count) as total_usage_count,
                    AVG(match_accuracy) as avg_match_accuracy
                FROM preprocessing_dataset
            """)
            
            stats = dict(cursor.fetchone())
            
            # 타입별 통계
            cursor.execute("""
                SELECT 
                    term_type,
                    COUNT(*) as count,
                    SUM(usage_count) as total_usage
                FROM preprocessing_dataset
                WHERE is_active = 1
                GROUP BY term_type
            """)
            
            stats['type_distribution'] = {
                row[0]: {'count': row[1], 'usage': row[2]}
                for row in cursor.fetchall()
            }
            
            # 가장 많이 사용된 용어
            cursor.execute("""
                SELECT 
                    original_term,
                    normalized_term,
                    usage_count
                FROM preprocessing_dataset
                WHERE is_active = 1
                ORDER BY usage_count DESC
                LIMIT 10
            """)
            
            stats['most_used_terms'] = [
                dict(zip(['original', 'normalized', 'usage'], row))
                for row in cursor.fetchall()
            ]
            
            return stats
            
        finally:
            conn.close()
    
    def bulk_insert(self, terms: List[PreprocessingTerm]) -> int:
        """대량 삽입"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            inserted_count = 0
            
            for term in terms:
                data = term.to_dict()
                del data['id']  # id는 자동 생성
                
                columns = ', '.join(data.keys())
                placeholders = ', '.join(['?' for _ in data])
                values = list(data.values())
                
                cursor.execute(
                    f"INSERT INTO preprocessing_dataset ({columns}) VALUES ({placeholders})",
                    values
                )
                
                inserted_count += 1
            
            conn.commit()
            return inserted_count
            
        finally:
            conn.close()
    
    def search_terms(self, query: str, limit: int = 20) -> List[PreprocessingTerm]:
        """용어 검색"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            search_pattern = f"%{query}%"
            cursor.execute("""
                SELECT * FROM preprocessing_dataset 
                WHERE (original_term LIKE ? OR normalized_term LIKE ?)
                    AND is_active = 1
                ORDER BY usage_count DESC
                LIMIT ?
            """, (search_pattern, search_pattern, limit))
            
            rows = cursor.fetchall()
            return [PreprocessingTerm.from_dict(dict(row)) for row in rows]
            
        finally:
            conn.close()