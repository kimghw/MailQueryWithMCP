#!/usr/bin/env python3
"""
대량 템플릿 업로더

하나의 JSON 파일에서 여러 템플릿을 읽어 업로드합니다.
"""

import os
import sys
import json
import sqlite3
import asyncio
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple

# 프로젝트 루트 추가
sys.path.append(str(Path(__file__).parent))


class BulkTemplateUploader:
    """대량 템플릿 업로더"""
    
    def __init__(self, db_path: str = "./data/templates.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """데이터베이스 초기화"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 간소화된 템플릿 테이블 (template_manager와 호환)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS query_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id TEXT UNIQUE NOT NULL,
                version TEXT DEFAULT '1.0.0',
                natural_questions TEXT NOT NULL,
                sql_query TEXT NOT NULL,
                sql_query_with_parameters TEXT,
                keywords TEXT,
                category TEXT NOT NULL,
                required_params TEXT,
                optional_params TEXT,
                default_params TEXT,
                examples TEXT,
                description TEXT,
                to_agent_prompt TEXT,
                vector_indexed BOOLEAN DEFAULT 0,
                vector_id TEXT,
                embedding_model TEXT DEFAULT 'text-embedding-3-large',
                embedding_dimension INTEGER DEFAULT 3072,
                usage_count INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                avg_execution_time_ms INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used_at TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        """)
        
        conn.commit()
        conn.close()
    
    def load_templates_from_file(self, file_path: str) -> List[Dict]:
        """JSON 파일에서 템플릿 로드"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 단일 템플릿이면 리스트로 변환
        if isinstance(data, dict):
            return [data]
        return data
    
    def upload_templates(self, templates: List[Dict]) -> Tuple[int, List[str]]:
        """템플릿을 데이터베이스에 업로드"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        success_count = 0
        errors = []
        
        for template in templates:
            try:
                # 필수 필드 확인
                if not all(key in template for key in ['template_id', 'natural_questions', 'category']):
                    errors.append(f"{template.get('template_id', 'Unknown')}: 필수 필드 누락")
                    continue
                
                # SQL 쿼리 확인 (sql_query 또는 sql_query_with_parameters 중 하나는 있어야 함)
                sql_query = template.get('sql_query', '')
                sql_query_with_params = template.get('sql_query_with_parameters', '')
                
                if not sql_query and not sql_query_with_params:
                    errors.append(f"{template['template_id']}: SQL 쿼리 누락")
                    continue
                
                # JSON 필드 직렬화
                keywords = json.dumps(template.get('keywords', []), ensure_ascii=False)
                required_params = json.dumps(template.get('required_params', []), ensure_ascii=False)
                optional_params = json.dumps(template.get('optional_params', []), ensure_ascii=False)
                default_params = json.dumps(template.get('default_params', {}), ensure_ascii=False)
                examples = json.dumps(template.get('examples', []), ensure_ascii=False) if 'examples' in template else None
                
                # 업서트 (INSERT OR REPLACE)
                cursor.execute("""
                    INSERT OR REPLACE INTO query_templates (
                        template_id, natural_questions, sql_query, sql_query_with_parameters,
                        keywords, category, required_params, optional_params, 
                        default_params, examples, description, to_agent_prompt,
                        updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    template['template_id'],
                    template['natural_questions'],
                    sql_query,
                    sql_query_with_params,
                    keywords,
                    template['category'],
                    required_params,
                    optional_params,
                    default_params,
                    examples,
                    template.get('description', ''),
                    template.get('to_agent_prompt', '')
                ))
                
                success_count += 1
                print(f"✓ 업로드 성공: {template['template_id']}")
                
            except sqlite3.IntegrityError as e:
                errors.append(f"{template['template_id']}: 중복된 템플릿 ID")
            except Exception as e:
                errors.append(f"{template.get('template_id', 'Unknown')}: {str(e)}")
        
        conn.commit()
        conn.close()
        
        return success_count, errors
    
    def list_templates(self):
        """업로드된 템플릿 목록 확인"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT template_id, category, 
                   SUBSTR(natural_questions, 1, 50) as questions,
                   vector_indexed, created_at
            FROM query_templates
            WHERE is_active = 1
            ORDER BY created_at DESC
        """)
        
        templates = cursor.fetchall()
        conn.close()
        
        return templates
    
    def get_statistics(self):
        """템플릿 통계"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 전체 템플릿 수
        cursor.execute("SELECT COUNT(*) FROM query_templates WHERE is_active = 1")
        total = cursor.fetchone()[0]
        
        # 카테고리별 수
        cursor.execute("""
            SELECT category, COUNT(*) 
            FROM query_templates 
            WHERE is_active = 1
            GROUP BY category
        """)
        categories = cursor.fetchall()
        
        # 벡터 인덱싱 상태
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN vector_indexed = 1 THEN 1 ELSE 0 END) as indexed,
                SUM(CASE WHEN vector_indexed = 0 THEN 1 ELSE 0 END) as not_indexed
            FROM query_templates
            WHERE is_active = 1
        """)
        indexing = cursor.fetchone()
        
        conn.close()
        
        return {
            'total': total,
            'categories': categories,
            'indexed': indexing[0] or 0,
            'not_indexed': indexing[1] or 0
        }


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="대량 템플릿 업로더")
    parser.add_argument('action', choices=['upload', 'list', 'stats'], 
                       help='수행할 작업')
    parser.add_argument('--file', default='templates/bulk_templates.json',
                       help='업로드할 JSON 파일 경로')
    parser.add_argument('--db', default='./data/templates.db',
                       help='데이터베이스 경로')
    
    args = parser.parse_args()
    
    uploader = BulkTemplateUploader(db_path=args.db)
    
    if args.action == 'upload':
        # 템플릿 업로드
        print(f"템플릿 파일 로드: {args.file}")
        
        if not os.path.exists(args.file):
            print(f"파일을 찾을 수 없습니다: {args.file}")
            return
        
        try:
            templates = uploader.load_templates_from_file(args.file)
            print(f"로드된 템플릿 수: {len(templates)}\n")
            
            success, errors = uploader.upload_templates(templates)
            
            print(f"\n업로드 완료: 성공 {success}개")
            if errors:
                print(f"오류 {len(errors)}개:")
                for error in errors:
                    print(f"  - {error}")
            
            print(f"\n다음 단계: VectorDB 동기화")
            print("python -m modules.query_assistant.cli_template_manager sync")
            
        except Exception as e:
            print(f"오류 발생: {e}")
    
    elif args.action == 'list':
        # 템플릿 목록
        templates = uploader.list_templates()
        
        print(f"업로드된 템플릿 ({len(templates)}개):\n")
        print(f"{'ID':<30} {'카테고리':<15} {'질문':<40} {'인덱싱':<8} {'생성일'}")
        print("-" * 120)
        
        for template in templates:
            indexed = "✓" if template[3] else "✗"
            print(f"{template[0]:<30} {template[1]:<15} {template[2]:<40} {indexed:<8} {template[4]}")
    
    elif args.action == 'stats':
        # 통계
        stats = uploader.get_statistics()
        
        print("템플릿 통계:\n")
        print(f"전체 템플릿: {stats['total']}개")
        print(f"벡터 인덱싱: {stats['indexed']}개 완료, {stats['not_indexed']}개 대기")
        
        print("\n카테고리별:")
        for category, count in stats['categories']:
            print(f"  - {category}: {count}개")


if __name__ == "__main__":
    main()