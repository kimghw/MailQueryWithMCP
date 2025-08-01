#!/usr/bin/env python3
"""
Mock Claude Desktop for testing with OpenRouter API
Simulates how Claude would process queries through MCP server
"""
import os
import json
import asyncio
from typing import Dict, Any, List, Optional
import aiohttp
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

class MockClaudeDesktop:
    """Mock Claude Desktop that uses OpenRouter for LLM processing"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not found in environment")
            
        self.api_base = "https://openrouter.ai/api/v1"
        self.model = "anthropic/claude-3.5-sonnet-20241022"  # More capable model
        
        # Load MCP system prompt from file
        prompt_file = Path(__file__).parent.parent / "prompts" / "mcp_system_prompt.txt"
        try:
            with open(prompt_file, 'r', encoding='utf-8') as f:
                self.system_prompt = f.read()
        except FileNotFoundError:
            # Fallback to default prompt if file not found
            self.system_prompt = """IACSGRAPH 해양 데이터베이스 쿼리 처리 시스템입니다.

사용자 질의에서 다음을 추출하세요:

1. keywords: 주요 키워드들
2. organization: 조직 코드 매핑
3. period: 기간 추출 (시작날짜와 종료날짜)
4. intent: 질의 의도 (search|list|analyze|count)
5. query_scope: "all"(모든 기관), "one"(단일 기관), "more"(여러 기관)"""

    async def analyze_queries_batch(self, queries: List[str], batch_size: int = 100) -> List[Dict[str, Any]]:
        """Analyze multiple queries in batch using LLM to extract keywords and parameters
        
        Args:
            queries: List of queries to analyze
            batch_size: Maximum number of queries per batch (default: 100)
            
        Returns:
            List of analysis results for each query
        """
        results = []
        
        # Process in batches
        for i in range(0, len(queries), batch_size):
            batch_queries = queries[i:i + batch_size]
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/kimghw/IACSGRAPH",
                "X-Title": "IACSGRAPH Batch Query Test"
            }
            
            # Get current date for relative date parsing
            from datetime import datetime
            today = datetime.now().strftime('%Y-%m-%d')
            
            # Create batch prompt
            batch_prompt = f"""다음 {len(batch_queries)}개의 질의를 각각 분석하여 JSON 배열 형식으로 응답하세요.

오늘 날짜: {today}

질의 목록:
"""
            for idx, query in enumerate(batch_queries):
                batch_prompt += f"{idx + 1}. {query}\n"
            
            batch_prompt += """
각 질의에 대해 다음 형식의 JSON 객체를 포함하는 배열을 반환하세요:
[
  {
    "query_index": 1,
    "keywords": ["keyword1", "keyword2", ...],
    "organization": "ORG_CODE" or null,
    "extracted_period": {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"} or null,
    "intent": "search|list|analyze|count",
    "query_scope": "all|one|more"
  },
  ...
]"""
            
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": batch_prompt}
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.3,
                "max_tokens": 4000  # Increased for batch processing
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_base}/chat/completions",
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"OpenRouter API error: {response.status} - {error_text}")
                    
                    result = await response.json()
                    content = result['choices'][0]['message']['content']
                    
                    try:
                        # Parse the batch response
                        batch_results = json.loads(content)
                        
                        # If response is wrapped in an object, extract the array
                        if isinstance(batch_results, dict) and 'results' in batch_results:
                            batch_results = batch_results['results']
                        elif isinstance(batch_results, dict) and 'queries' in batch_results:
                            batch_results = batch_results['queries']
                        
                        # Ensure we have a list
                        if not isinstance(batch_results, list):
                            batch_results = [batch_results]
                        
                        # Map results back to original queries
                        for idx, query in enumerate(batch_queries):
                            if idx < len(batch_results):
                                result_item = batch_results[idx]
                                # Add original query to result
                                result_item['original_query'] = query
                                results.append(result_item)
                            else:
                                # Fallback if not enough results
                                results.append({
                                    "original_query": query,
                                    "keywords": query.split(),
                                    "parameters": {},
                                    "intent": "unknown",
                                    "confidence": 0.5
                                })
                                
                    except (json.JSONDecodeError, KeyError) as e:
                        # Fallback for all queries in batch
                        for query in batch_queries:
                            results.append({
                                "original_query": query,
                                "keywords": query.split(),
                                "parameters": {},
                                "intent": "unknown",
                                "confidence": 0.5,
                                "error": str(e)
                            })
        
        return results
    
    async def analyze_query(self, query: str) -> Dict[str, Any]:
        """Analyze query using LLM to extract keywords and parameters"""
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/kimghw/IACSGRAPH",
            "X-Title": "IACSGRAPH Query Test"
        }
        
        # Get current date for relative date parsing
        from datetime import datetime
        today = datetime.now().strftime('%Y-%m-%d')
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": f"""사용자 질의: "{query}"

오늘 날짜: {today}

위 질의를 분석하여 다음 JSON 형식으로 응답하세요:
{{
    "keywords": ["keyword1", "keyword2", ...],
    "organization": "ORG_CODE" or null,
    "extracted_period": {{"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}} or null,
    "intent": "search|list|analyze|count",
    "query_scope": "all|one|more"
}}"""}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.3,
            "max_tokens": 500
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.api_base}/chat/completions",
                headers=headers,
                json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"OpenRouter API error: {response.status} - {error_text}")
                
                result = await response.json()
                content = result['choices'][0]['message']['content']
                
                # Extract JSON from the response
                try:
                    # Look for JSON block in the response
                    import re
                    json_match = re.search(r'\{[\s\S]*?\}(?=\s*<use_mcp_tool>|\s*$)', content)
                    if json_match:
                        json_str = json_match.group(0)
                        return json.loads(json_str)
                    else:
                        # Try to parse the entire content as JSON
                        return json.loads(content)
                except (json.JSONDecodeError, AttributeError) as e:
                    # Fallback if JSON parsing fails
                    return {
                        "keywords": query.split(),
                        "organization": None,
                        "extracted_period": None,
                        "intent": "search",
                        "query_scope": "one"
                    }

    async def process_query_with_mcp(self, query: str, category: Optional[str] = None, 
                                     execute: bool = True, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Process query through MCP server with LLM enhancement
        Simulates the exact MCP server call from Claude Desktop
        
        Real Claude Desktop flow:
        1. User query → Claude's system prompt extracts parameters
        2. Claude calls MCP with: query + extracted_dates + extracted_keywords + query_scope
        3. MCP server uses both LLM params and its own rule-based extraction
        """
        
        # First, analyze with LLM (simulating Claude's system prompt)
        print(f"[LLM] Analyzing: {query}")
        analysis = await self.analyze_query(query)
        print(f"[LLM] Extracted keywords: {analysis.get('keywords', [])}")
        print(f"[LLM] Extracted organization: {analysis.get('organization', 'None')}")
        print(f"[LLM] Extracted period: {analysis.get('extracted_period', 'None')}")
        print(f"[LLM] Query scope: {analysis.get('query_scope', 'one')}")
        
        # Convert LLM parameters to MCP format
        extracted_period = None
        
        # Use extracted_period if available from LLM
        if 'extracted_period' in analysis and analysis['extracted_period']:
            extracted_period = analysis['extracted_period']
        else:
            # Default: 3 months if period is not extracted
            from datetime import datetime, timedelta
            end_date = datetime.now()
            start_date = end_date - timedelta(days=90)
            extracted_period = {
                'start': start_date.strftime('%Y-%m-%d'),
                'end': end_date.strftime('%Y-%m-%d')
            }
        
        # Extract organization from LLM
        extracted_organization = analysis.get('organization')
        
        # Use query_scope from LLM or determine from query
        query_scope = analysis.get('query_scope', 'one')
        
        # Import the enhanced MCP server
        from ..mcp_server_enhanced import EnhancedIacsGraphQueryServer
        from ..mcp_server_enhanced import EnhancedQueryRequest
        
        try:
            # Initialize Enhanced MCP Server
            db_config = {"type": "sqlite", "path": "data/iacsgraph.db"}
            mcp_server = EnhancedIacsGraphQueryServer(db_config=db_config)
            
            # Create MCP request with LLM-extracted parameters
            # This is what Claude Desktop sends to MCP server
            mcp_request = EnhancedQueryRequest(
                query=query,
                extracted_period=extracted_period,
                extracted_keywords=analysis['keywords'],
                extracted_organization=extracted_organization,
                intent=analysis.get('intent', 'search'),
                query_scope=query_scope,
                category=category,
                execute=execute,
                limit=limit,
                use_defaults=True
            )
            
            print(f"\n📤 MCP Enhanced Request:")
            print(f"  Query: {mcp_request.query}")
            print(f"  Extracted Period: {mcp_request.extracted_period}")
            print(f"  Extracted Keywords: {mcp_request.extracted_keywords}")
            print(f"  Extracted Organization: {mcp_request.extracted_organization}")
            print(f"  Intent: {mcp_request.intent}")
            print(f"  Query Scope: {mcp_request.query_scope}")
            
            # Call MCP server's handler directly
            response = await mcp_server._handle_enhanced_query(mcp_request)
            
            # Extract the QueryResult from response
            result = response['result']
            
            # Apply limit if specified
            if limit and result.results:
                result.results = result.results[:limit]
            
            # Return complete response including all parameter info
            return {
                "tool": "query_with_llm_params",  # Enhanced MCP tool name
                "arguments": {    # Original MCP request as dict
                    "query": mcp_request.query,
                    "extracted_period": mcp_request.extracted_period,
                    "extracted_keywords": mcp_request.extracted_keywords,
                    "extracted_organization": mcp_request.extracted_organization,
                    "intent": mcp_request.intent,
                    "query_scope": mcp_request.query_scope,
                    "category": mcp_request.category,
                    "execute": mcp_request.execute,
                    "limit": mcp_request.limit,
                    "use_defaults": mcp_request.use_defaults
                },
                "result": {       # QueryResult as dict
                    "query_id": result.query_id,
                    "executed_sql": result.executed_sql,
                    "parameters": result.parameters,
                    "results": result.results,
                    "execution_time": result.execution_time,
                    "error": result.error,
                    "validation_info": result.validation_info if hasattr(result, 'validation_info') else None
                },
                "extracted_params": response.get('extracted_params', {}),
                "rule_based_params": response.get('rule_based_params', {}),
                "llm_contribution": response.get('llm_contribution', {}),
                "llm_analysis": analysis  # Original LLM analysis
            }
            
        except Exception as e:
            # Return error in enhanced MCP format
            return {
                "tool": "query_with_llm_params",
                "arguments": {
                    "query": query,
                    "extracted_period": extracted_period if 'extracted_period' in locals() else None,
                    "extracted_keywords": analysis['keywords'],
                    "extracted_organization": extracted_organization if 'extracted_organization' in locals() else None,
                    "query_scope": query_scope if 'query_scope' in locals() else 'one',
                    "category": category,
                    "execute": execute,
                    "limit": limit,
                    "use_defaults": True
                },
                "result": {
                    "query_id": "",
                    "executed_sql": "",
                    "parameters": {},
                    "results": [],
                    "execution_time": 0.0,
                    "error": str(e),
                    "validation_info": None
                },
                "extracted_params": {},
                "rule_based_params": {},
                "llm_contribution": {
                    "period": extracted_period if 'extracted_period' in locals() else None,
                    "keywords": analysis['keywords'],
                    "organization": extracted_organization if 'extracted_organization' in locals() else None,
                    "intent": analysis.get('intent', 'search')
                },
                "llm_analysis": analysis
            }


async def test_sample_queries(mock: MockClaudeDesktop, num_queries: int = 7):
    """Test sample queries using Mock Claude Desktop"""
    
    sample_queries = [
        "최근 아젠다 목록 보여줘",
        "한국선급 응답 현황",
        "어제 받은 이메일들",
        "IMO 관련 문서",
        "지난주 등록된 아젠다들",
        "의장이 보낸 메일 중 한국이 응답해야 하는 것",
        "PL25016a 아젠다 상세 정보"
    ]
    
    # Use only requested number of queries
    test_queries = sample_queries[:min(num_queries, len(sample_queries))]
    
    print("="*80)
    print(f"Testing {len(test_queries)} sample queries with Mock Claude Desktop")
    print("="*80)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*60}")
        print(f"[{i}/{len(test_queries)}] Query: {query}")
        print("="*60)
        
        try:
            # Call with MCP-compatible parameters
            result = await mock.process_query_with_mcp(
                query=query,
                category=None,  # Auto-detect category
                execute=True,   # Execute the SQL
                limit=10        # Limit results
            )
            
            # Display MCP request info
            if result.get('arguments'):
                args = result['arguments']
                print(f"\n📤 MCP Request:")
                print(f"  Tool: {result.get('tool', 'query')}")
                print(f"  Query: {args['query']}")
                print(f"  Execute: {args['execute']}")
                print(f"  Limit: {args['limit']}")
            
            # Display LLM analysis
            if result.get('llm_analysis'):
                llm = result['llm_analysis']
                print(f"\n📊 LLM Analysis:")
                print(f"  Keywords: {llm.get('keywords', [])[:5]}")
                print(f"  Organization: {llm.get('organization', 'None')}")
                print(f"  Period: {llm.get('extracted_period', 'None')}")
                print(f"  Intent: {llm.get('intent', 'search')}")
                print(f"  Query Scope: {llm.get('query_scope', 'one')}")
            
            # Display query result (MCP format)
            if result.get('result'):
                qr = result['result']
                print(f"\n💾 Query Result:")
                print(f"  Template ID: {qr['query_id']}")
                print(f"  SQL: {qr['executed_sql'][:100]}..." if qr['executed_sql'] else "  SQL: None")
                print(f"  Parameters: {qr['parameters']}")
                print(f"  Results: {len(qr['results'])} rows")
                print(f"  Time: {qr['execution_time']:.3f}s")
                
                if qr.get('error'):
                    print(f"  ❌ Error: {qr['error']}")
                elif qr['results']:
                    # Show first result
                    print(f"  First row: {qr['results'][0]}")
            else:
                print(f"\n✗ No result returned")
                
        except Exception as e:
            print(f"\n✗ Error: {e}")
        
        # Rate limiting
        await asyncio.sleep(0.5)


async def test_100_queries(mock: MockClaudeDesktop, detail: bool = False):
    """Test 100 queries from test_100_queries.py"""
    from .test_100_queries import generate_test_queries
    import time
    from datetime import datetime
    
    # Get 100 test queries
    test_queries = generate_test_queries()
    
    print("="*80)
    print(f"Testing {len(test_queries)} queries with Mock Claude Desktop")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # Results tracking
    results = []
    success_count = 0
    error_count = 0
    
    for i, test_case in enumerate(test_queries, 1):
        query = test_case['query']
        expected_category = test_case['expected_category']
        
        try:
            start_time = time.time()
            
            # Process query
            result = await mock.process_query_with_mcp(
                query=query,
                category=None,
                execute=True,
                limit=10
            )
            
            elapsed_time = time.time() - start_time
            
            # Analyze result
            query_result = result.get('result', {})
            success = query_result.get('query_id') and not query_result.get('error')
            
            test_result = {
                'index': i,
                'query': query,
                'expected_category': expected_category,
                'success': success,
                'elapsed_time': elapsed_time,
                'template_id': query_result.get('query_id', ''),
                'result_count': len(query_result.get('results', [])),
                'error': query_result.get('error'),
                'llm_keywords': result.get('llm_analysis', {}).get('keywords', []),
                'llm_organization': result.get('llm_analysis', {}).get('organization')
            }
            
            results.append(test_result)
            
            if success:
                success_count += 1
                status = "✅"
            else:
                error_count += 1
                status = "❌"
            
            # Progress indicator
            if i % 10 == 0:
                print(f"Progress: {i}/{len(test_queries)} - Success: {success_count}, Errors: {error_count}")
            
            # Show details only for failures or if detail mode
            if detail or not success:
                print(f"{status} [{i}] {query[:50]}... - {query_result.get('error', 'Template: ' + query_result.get('query_id', 'None'))}")
                
        except Exception as e:
            error_count += 1
            results.append({
                'index': i,
                'query': query,
                'expected_category': expected_category,
                'success': False,
                'error': str(e),
                'elapsed_time': 0
            })
            print(f"❌ [{i}] {query[:50]}... - Exception: {e}")
        
        # Rate limiting
        await asyncio.sleep(0.5)
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Total queries: {len(test_queries)}")
    print(f"Successful: {success_count} ({success_count/len(test_queries)*100:.1f}%)")
    print(f"Failed: {error_count} ({error_count/len(test_queries)*100:.1f}%)")
    
    # Category statistics
    category_stats = {}
    for result in results:
        cat = result['expected_category']
        if cat not in category_stats:
            category_stats[cat] = {'total': 0, 'success': 0}
        category_stats[cat]['total'] += 1
        if result['success']:
            category_stats[cat]['success'] += 1
    
    print("\nCategory Performance:")
    for cat, stats in category_stats.items():
        success_rate = stats['success'] / stats['total'] * 100 if stats['total'] > 0 else 0
        print(f"  {cat}: {stats['success']}/{stats['total']} ({success_rate:.1f}%)")
    
    # Save results
    output_file = 'mock_claude_test_results.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'test_date': datetime.now().isoformat(),
            'summary': {
                'total': len(test_queries),
                'success': success_count,
                'failed': error_count,
                'success_rate': success_count/len(test_queries)*100,
                'category_stats': category_stats
            },
            'detailed_results': results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\nDetailed results saved to: {output_file}")
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


async def main():
    """Main function with command line options"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Mock Claude Desktop Test')
    parser.add_argument('-n', '--num-queries', type=int, default=100,
                       help='Number of queries to test (default: 100)')
    parser.add_argument('--sample', action='store_true',
                       help='Use sample queries instead of 100 test queries')
    parser.add_argument('--detail', action='store_true',
                       help='Show detailed output for all queries')
    
    args = parser.parse_args()
    
    # Check API key
    if not os.getenv("OPENROUTER_API_KEY"):
        print("Please set OPENROUTER_API_KEY in .env file")
        print("Get your API key from: https://openrouter.ai/keys")
        exit(1)
    
    try:
        # Initialize Mock Claude Desktop
        mock = MockClaudeDesktop()
        
        if args.sample:
            # Use sample queries
            await test_sample_queries(mock, args.num_queries)
        else:
            # Use 100 test queries
            if args.num_queries != 100:
                print(f"Note: Using all 100 test queries (--num-queries ignored for non-sample mode)")
            await test_100_queries(mock, detail=args.detail)
            
    except Exception as e:
        print(f"Error: {e}")
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())