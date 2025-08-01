#!/usr/bin/env python3
"""
Mock Claude Desktop Batch Processing
Process 100 queries with batch LLM analysis
"""
import os
import json
import asyncio
import time
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path

from .mock_claude_desktop import MockClaudeDesktop
from ..mcp_server_enhanced import EnhancedIacsGraphQueryServer, EnhancedQueryRequest


async def process_queries_with_batch_llm(queries: List[str], batch_size: int = 100) -> Dict[str, Any]:
    """
    Process queries with batch LLM analysis followed by individual MCP processing
    
    Args:
        queries: List of queries to process
        batch_size: Number of queries to analyze at once with LLM (default: 100)
    """
    print(f"\n🚀 Starting batch processing for {len(queries)} queries")
    print(f"   Batch size: {batch_size} queries per LLM call")
    
    # Initialize services
    mock = MockClaudeDesktop()
    db_config = {"type": "sqlite", "path": "data/iacsgraph.db"}
    mcp_server = EnhancedIacsGraphQueryServer(db_config=db_config)
    
    # Phase 1: Batch LLM Analysis
    print("\n📊 Phase 1: Batch LLM Analysis")
    print("-" * 60)
    
    llm_start_time = time.time()
    all_llm_results = []
    
    for i in range(0, len(queries), batch_size):
        batch_queries = queries[i:i + min(batch_size, len(queries) - i)]
        batch_num = i // batch_size + 1
        total_batches = (len(queries) + batch_size - 1) // batch_size
        
        print(f"\n[Batch {batch_num}/{total_batches}] Analyzing {len(batch_queries)} queries...")
        
        try:
            batch_start = time.time()
            batch_results = await mock.analyze_queries_batch(batch_queries, batch_size=batch_size)
            batch_time = time.time() - batch_start
            
            all_llm_results.extend(batch_results)
            
            print(f"   ✅ Batch completed in {batch_time:.2f}s ({batch_time/len(batch_queries):.2f}s per query)")
            
            # Show sample result
            if batch_results:
                sample = batch_results[0]
                print(f"   Sample: '{sample.get('original_query', '')[:50]}...'")
                print(f"           Keywords: {sample.get('keywords', [])[:3]}")
                print(f"           Intent: {sample.get('intent', 'None')}")
                
        except Exception as e:
            print(f"   ❌ Batch failed: {e}")
            # Add fallback results for failed batch
            for query in batch_queries:
                all_llm_results.append({
                    "original_query": query,
                    "keywords": query.split(),
                    "organization": None,
                    "extracted_period": None,
                    "intent": "search",
                    "query_scope": "one",
                    "error": str(e)
                })
        
        # Rate limiting between batches
        if i + batch_size < len(queries):
            await asyncio.sleep(1)
    
    llm_total_time = time.time() - llm_start_time
    print(f"\n✅ LLM Analysis Complete: {llm_total_time:.2f}s total ({llm_total_time/len(queries):.2f}s per query)")
    
    # Phase 2: MCP Processing with Pre-analyzed Parameters
    print("\n📊 Phase 2: MCP Processing")
    print("-" * 60)
    
    mcp_start_time = time.time()
    final_results = []
    success_count = 0
    error_count = 0
    
    for idx, (query, llm_result) in enumerate(zip(queries, all_llm_results)):
        try:
            # Extract parameters from LLM result
            extracted_period = llm_result.get('extracted_period')
            extracted_keywords = llm_result.get('keywords', [])
            extracted_organization = None
            
            # Get organization directly from LLM result
            extracted_organization = llm_result.get('organization')
            
            # Get query scope from LLM result
            query_scope = llm_result.get('query_scope', 'one')
            
            # Get intent from LLM result
            intent = llm_result.get('intent', 'search')
            
            # Create MCP request
            mcp_request = EnhancedQueryRequest(
                query=query,
                extracted_period=extracted_period,
                extracted_keywords=extracted_keywords,
                extracted_organization=extracted_organization,
                intent=intent,
                query_scope=query_scope,
                category=None,
                execute=True,
                limit=10,
                use_defaults=True
            )
            
            # Process with MCP
            mcp_response = await mcp_server._handle_enhanced_query(mcp_request)
            
            # Check success
            query_result = mcp_response.get('result', {})
            success = bool(query_result.query_id) and not query_result.error
            
            if success:
                success_count += 1
                status = "✅"
            else:
                error_count += 1
                status = "❌"
            
            # Store result
            final_results.append({
                'index': idx + 1,
                'query': query,
                'llm_analysis': llm_result,
                'mcp_response': mcp_response,
                'success': success,
                'template_id': query_result.query_id if query_result.query_id else None,
                'error': query_result.error if hasattr(query_result, 'error') else None
            })
            
            # Progress indicator
            if (idx + 1) % 10 == 0:
                print(f"Progress: {idx + 1}/{len(queries)} - Success: {success_count}, Errors: {error_count}")
            
            # Show failures
            if not success:
                print(f"{status} [{idx + 1}] {query[:50]}... - {query_result.error if hasattr(query_result, 'error') else 'No match'}")
                
        except Exception as e:
            error_count += 1
            final_results.append({
                'index': idx + 1,
                'query': query,
                'llm_analysis': llm_result,
                'success': False,
                'error': str(e)
            })
            print(f"❌ [{idx + 1}] {query[:50]}... - Exception: {e}")
    
    mcp_total_time = time.time() - mcp_start_time
    total_time = time.time() - llm_start_time
    
    # Summary
    print("\n" + "="*80)
    print("BATCH PROCESSING SUMMARY")
    print("="*80)
    print(f"\n⏱️  Time Breakdown:")
    print(f"   LLM Batch Analysis: {llm_total_time:.2f}s ({llm_total_time/total_time*100:.1f}%)")
    print(f"   MCP Processing: {mcp_total_time:.2f}s ({mcp_total_time/total_time*100:.1f}%)")
    print(f"   Total Time: {total_time:.2f}s")
    print(f"   Average per query: {total_time/len(queries):.2f}s")
    
    print(f"\n📊 Results:")
    print(f"   Total queries: {len(queries)}")
    print(f"   Successful: {success_count} ({success_count/len(queries)*100:.1f}%)")
    print(f"   Failed: {error_count} ({error_count/len(queries)*100:.1f}%)")
    
    return {
        'summary': {
            'total_queries': len(queries),
            'success_count': success_count,
            'error_count': error_count,
            'success_rate': success_count/len(queries)*100,
            'llm_time': llm_total_time,
            'mcp_time': mcp_total_time,
            'total_time': total_time,
            'avg_time_per_query': total_time/len(queries)
        },
        'results': final_results
    }


async def test_100_queries_batch():
    """Test 100 queries with batch processing"""
    
    # 100 test queries
    test_cases = [
        # 아젠다 관련 (15개)
        {"query": "최근 아젠다 목록 보여줘", "expected_category": "agenda"},
        {"query": "어제 등록된 아젠다 조회", "expected_category": "agenda"},
        {"query": "오늘 아젠다 뭐 있어?", "expected_category": "agenda"},
        {"query": "IMO 관련 아젠다 찾아줘", "expected_category": "agenda"},
        {"query": "한국선급 아젠다 목록", "expected_category": "agenda"},
        {"query": "긴급 아젠다 있나요?", "expected_category": "agenda"},
        {"query": "마감일 임박한 아젠다", "expected_category": "agenda"},
        {"query": "내일까지 처리해야 하는 아젠다", "expected_category": "agenda"},
        {"query": "진행중인 아젠다 보여줘", "expected_category": "agenda"},
        {"query": "완료된 아젠다 목록", "expected_category": "agenda"},
        {"query": "이번 주 아젠다 현황", "expected_category": "agenda"},
        {"query": "지난주 등록된 아젠다들", "expected_category": "agenda"},
        {"query": "의장이 만든 아젠다", "expected_category": "agenda"},
        {"query": "환경 관련 아젠다 조회", "expected_category": "agenda"},
        {"query": "안전 관련 아젠다 목록", "expected_category": "agenda"},
        
        # 메일 관련 (15개)
        {"query": "의장이 보낸 메일 목록", "expected_category": "mail"},
        {"query": "어제 받은 이메일들", "expected_category": "mail"},
        {"query": "오늘 온 메일 보여줘", "expected_category": "mail"},
        {"query": "IMO에서 온 편지", "expected_category": "mail"},
        {"query": "한국선급에서 보낸 메일", "expected_category": "mail"},
        {"query": "긴급 메일 있어?", "expected_category": "mail"},
        {"query": "읽지 않은 이메일", "expected_category": "mail"},
        {"query": "중요 표시된 메일들", "expected_category": "mail"},
        {"query": "회의 관련 메일 조회", "expected_category": "mail"},
        {"query": "승인 요청 메일들", "expected_category": "mail"},
        {"query": "이번 주 받은 메일", "expected_category": "mail"},
        {"query": "지난달 메일 통계", "expected_category": "mail"},
        {"query": "첨부파일 있는 메일", "expected_category": "mail"},
        {"query": "답장 필요한 메일들", "expected_category": "mail"},
        {"query": "전체 메일 목록 조회", "expected_category": "mail"},
        
        # 문서/문서제출 관련 (15개)
        {"query": "IMO 문서 목록", "expected_category": "document"},
        {"query": "제출된 문서 현황", "expected_category": "document"},
        {"query": "오늘 제출한 문서들", "expected_category": "document"},
        {"query": "문서 제출 마감일 확인", "expected_category": "document"},
        {"query": "한국선급 제출 문서", "expected_category": "document"},
        {"query": "미제출 문서 목록", "expected_category": "document"},
        {"query": "승인된 문서들 조회", "expected_category": "document"},
        {"query": "반려된 문서 확인", "expected_category": "document"},
        {"query": "검토중인 문서 현황", "expected_category": "document"},
        {"query": "이번 달 제출 문서", "expected_category": "document"},
        {"query": "환경 관련 제출 문서", "expected_category": "document"},
        {"query": "안전 규정 문서 목록", "expected_category": "document"},
        {"query": "기술 문서 제출 현황", "expected_category": "document"},
        {"query": "위원회별 문서 통계", "expected_category": "document"},
        {"query": "최근 업데이트된 문서", "expected_category": "document"},
        
        # 응답/의견서 관련 (10개)
        {"query": "한국선급 응답 현황", "expected_category": "response"},
        {"query": "의견서 제출 상태", "expected_category": "response"},
        {"query": "미응답 항목 조회", "expected_category": "response"},
        {"query": "오늘 제출한 의견서", "expected_category": "response"},
        {"query": "응답 대기중인 건들", "expected_category": "response"},
        {"query": "승인된 의견서 목록", "expected_category": "response"},
        {"query": "반려된 응답 확인", "expected_category": "response"},
        {"query": "이번 주 응답 통계", "expected_category": "response"},
        {"query": "위원회별 응답 현황", "expected_category": "response"},
        {"query": "긴급 응답 필요 항목", "expected_category": "response"},
        
        # 위원회/조직 관련 (10개)
        {"query": "MSC 위원회 정보", "expected_category": "committee"},
        {"query": "MEPC 회의 일정", "expected_category": "committee"},
        {"query": "위원회별 담당자 목록", "expected_category": "committee"},
        {"query": "한국선급 소속 위원", "expected_category": "committee"},
        {"query": "위원회 참석 현황", "expected_category": "committee"},
        {"query": "소위원회 구성 정보", "expected_category": "committee"},
        {"query": "위원회별 안건 통계", "expected_category": "committee"},
        {"query": "다음 회의 일정 확인", "expected_category": "committee"},
        {"query": "위원회 의장 정보", "expected_category": "committee"},
        {"query": "작업반 구성원 조회", "expected_category": "committee"},
        
        # 일정/마감일 관련 (10개)
        {"query": "오늘 일정 확인", "expected_category": "schedule"},
        {"query": "내일 예정된 회의", "expected_category": "schedule"},
        {"query": "이번 주 마감일", "expected_category": "schedule"},
        {"query": "다음 달 주요 일정", "expected_category": "schedule"},
        {"query": "연간 회의 계획", "expected_category": "schedule"},
        {"query": "마감 임박 항목들", "expected_category": "schedule"},
        {"query": "지연된 일정 확인", "expected_category": "schedule"},
        {"query": "휴일 일정 조회", "expected_category": "schedule"},
        {"query": "반복 일정 목록", "expected_category": "schedule"},
        {"query": "일정 충돌 확인", "expected_category": "schedule"},
        
        # 통계/분석 관련 (10개)
        {"query": "월별 문서 제출 통계", "expected_category": "statistics"},
        {"query": "위원회별 활동 분석", "expected_category": "statistics"},
        {"query": "응답률 통계 조회", "expected_category": "statistics"},
        {"query": "아젠다 처리 현황", "expected_category": "statistics"},
        {"query": "메일 수신 통계", "expected_category": "statistics"},
        {"query": "참여율 분석 보고", "expected_category": "statistics"},
        {"query": "연도별 실적 비교", "expected_category": "statistics"},
        {"query": "부서별 성과 지표", "expected_category": "statistics"},
        {"query": "프로젝트 진행률", "expected_category": "statistics"},
        {"query": "리스크 분석 현황", "expected_category": "statistics"},
        
        # 검색/조회 관련 (10개)
        {"query": "김철수가 작성한 문서", "expected_category": "search"},
        {"query": "환경 규제 관련 자료", "expected_category": "search"},
        {"query": "2024년 회의록 찾기", "expected_category": "search"},
        {"query": "승인 대기 항목들", "expected_category": "search"},
        {"query": "최근 변경사항 조회", "expected_category": "search"},
        {"query": "키워드로 문서 검색", "expected_category": "search"},
        {"query": "담당자별 업무 현황", "expected_category": "search"},
        {"query": "프로젝트 관련 자료", "expected_category": "search"},
        {"query": "규정 변경 이력", "expected_category": "search"},
        {"query": "참조 문서 목록", "expected_category": "search"},
        
        # 알림/리마인더 (5개)
        {"query": "오늘 알림 목록", "expected_category": "notification"},
        {"query": "마감일 리마인더", "expected_category": "notification"},
        {"query": "중요 공지사항", "expected_category": "notification"},
        {"query": "시스템 알림 확인", "expected_category": "notification"},
        {"query": "업데이트 알림", "expected_category": "notification"}
    ]
    
    queries = [tc['query'] for tc in test_cases]
    
    print("="*80)
    print(f"Testing {len(queries)} queries with Batch LLM Processing")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # Process with 100 queries at once
    batch_size = 100
    print(f"\n\n{'='*80}")
    print(f"Testing with batch size: {batch_size}")
    print(f"{'='*80}")
    
    result = await process_queries_with_batch_llm(queries, batch_size=batch_size)
    
    # Save results
    output_file = f'mock_claude_batch_results_{batch_size}.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'test_date': datetime.now().isoformat(),
            'batch_size': batch_size,
            'summary': result['summary'],
            'detailed_results': result['results']
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 Results saved to: {output_file}")


async def test_sample_batch():
    """Test with a small sample for verification"""
    sample_queries = [
        "최근 아젠다 목록 보여줘",
        "한국선급 응답 현황",
        "어제 받은 이메일들",
        "IMO 관련 문서",
        "지난주 등록된 아젠다들"
    ]
    
    print("="*80)
    print(f"Testing {len(sample_queries)} sample queries with Batch Processing")
    print("="*80)
    
    result = await process_queries_with_batch_llm(sample_queries, batch_size=5)
    
    # Show detailed results for samples
    print("\n📋 Detailed Results:")
    for r in result['results']:
        print(f"\n[{r['index']}] {r['query']}")
        print(f"   Success: {r['success']}")
        if r['success']:
            print(f"   Template: {r.get('template_id', 'N/A')}")
        else:
            print(f"   Error: {r.get('error', 'Unknown')}")
        
        llm = r.get('llm_analysis', {})
        print(f"   Keywords: {llm.get('keywords', [])}")
        print(f"   Organization: {llm.get('organization', 'None')}")


async def main():
    """Main function with command line options"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Mock Claude Desktop Batch Processing')
    parser.add_argument('--sample', action='store_true',
                       help='Test with 5 sample queries instead of 100')
    parser.add_argument('--batch-size', type=int, default=100,
                       help='Number of queries per LLM batch (default: 100)')
    
    args = parser.parse_args()
    
    # Check API key
    if not os.getenv("OPENROUTER_API_KEY"):
        print("❌ OPENROUTER_API_KEY not found in environment")
        print("Please set it in .env file or export it")
        return
    
    try:
        if args.sample:
            await test_sample_batch()
        else:
            # Always use test_100_queries_batch
            await test_100_queries_batch()
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())