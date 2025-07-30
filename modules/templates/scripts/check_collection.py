#!/usr/bin/env python3
"""
템플릿 컬렉션 상태 확인 스크립트
"""
import os
import sys
import argparse
from qdrant_client import QdrantClient
from dotenv import load_dotenv

load_dotenv()


def check_collections(detail=False):
    """Qdrant 컬렉션 상태 확인"""
    
    # Qdrant 연결
    client = QdrantClient(
        url=os.getenv("QDRANT_URL", "localhost"),
        port=int(os.getenv("QDRANT_PORT", 6333)),
        check_compatibility=False
    )
    
    # 모든 컬렉션 목록
    print("="*60)
    print("📚 Qdrant 컬렉션 목록")
    print("="*60)
    
    collections = client.get_collections()
    for col in collections.collections:
        # 각 컬렉션의 정보를 개별적으로 가져오기
        try:
            col_info = client.get_collection(col.name)
            points_count = col_info.points_count
        except:
            points_count = 0
        print(f"  • {col.name} (벡터 수: {points_count:,})")
    
    # 템플릿 컬렉션 상세 정보
    collection_name = os.getenv('QDRANT_COLLECTION_NAME', 'query_templates_unified')
    print(f"\n📋 템플릿 컬렉션 정보: '{collection_name}'")
    print("-"*60)
    
    try:
        info = client.get_collection(collection_name)
        print(f"  ✅ 상태: 정상")
        print(f"  📊 총 벡터 수: {info.points_count:,}")
        print(f"  📏 벡터 차원: {info.config.params.vectors.size}")
        print(f"  📐 거리 메트릭: {info.config.params.vectors.distance}")
        
        if detail and info.points_count > 0:
            print(f"\n📝 샘플 템플릿 (최대 5개):")
            print("-"*60)
            
            # 샘플 조회
            points, _ = client.scroll(
                collection_name=collection_name,
                limit=5,
                with_payload=True,
                with_vectors=False
            )
            
            templates_seen = set()
            for i, point in enumerate(points, 1):
                payload = point.payload
                template_id = payload.get('template_id', 'N/A')
                
                # 중복 템플릿 ID 스킵
                if template_id in templates_seen:
                    continue
                templates_seen.add(template_id)
                
                print(f"\n  [{i}] Template ID: {template_id}")
                print(f"      카테고리: {payload.get('template_category', 'N/A')}")
                print(f"      임베딩 타입: {payload.get('embedding_type', 'N/A')}")
                
                # 질문 표시
                question = payload.get('embedded_question') or payload.get('embedded_text', '')
                if question:
                    print(f"      질문: {question[:80]}{'...' if len(question) > 80 else ''}")
                
                # 키워드 표시
                keywords = payload.get('keywords', [])
                if keywords:
                    print(f"      키워드: {', '.join(keywords[:5])}")
            
            # 템플릿별 통계
            print(f"\n📊 템플릿별 벡터 통계:")
            print("-"*60)
            
            # 전체 포인트 조회하여 통계 계산
            all_points, _ = client.scroll(
                collection_name=collection_name,
                limit=10000,  # 충분히 큰 수
                with_payload=["template_id", "embedding_type"],
                with_vectors=False
            )
            
            template_stats = {}
            for point in all_points:
                tid = point.payload.get('template_id', 'unknown')
                etype = point.payload.get('embedding_type', 'unknown')
                
                if tid not in template_stats:
                    template_stats[tid] = {}
                
                if etype not in template_stats[tid]:
                    template_stats[tid][etype] = 0
                template_stats[tid][etype] += 1
            
            # 상위 5개 템플릿 표시
            sorted_templates = sorted(template_stats.items(), 
                                    key=lambda x: sum(x[1].values()), 
                                    reverse=True)[:5]
            
            for tid, etypes in sorted_templates:
                total = sum(etypes.values())
                print(f"  • {tid}: {total}개 벡터")
                for etype, count in etypes.items():
                    print(f"    - {etype}: {count}개")
                    
    except Exception as e:
        print(f"  ❌ 오류: {e}")
        print(f"  💡 컬렉션이 존재하지 않습니다. 템플릿을 먼저 업로드하세요.")
        print(f"\n  업로드 명령:")
        print(f"  python -m modules.templates.upload_templates --vector-only --recreate-vector")
        return False
    
    return True


def main():
    parser = argparse.ArgumentParser(description='템플릿 컬렉션 상태 확인')
    parser.add_argument('--detail', '-d', action='store_true', 
                       help='상세 정보 표시 (샘플 템플릿 포함)')
    
    args = parser.parse_args()
    
    try:
        check_collections(detail=args.detail)
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()