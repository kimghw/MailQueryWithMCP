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
        self.model = "anthropic/claude-3.5-haiku-20241022"  # Fast and cheap for testing
        
        # Load keyword extraction prompt
        keyword_prompt_file = Path(__file__).parent / "modules" / "query_assistant" / "prompts" / "keyword_extraction_prompt.txt"
        try:
            with open(keyword_prompt_file, 'r', encoding='utf-8') as f:
                keyword_prompt = f.read()
        except FileNotFoundError:
            keyword_prompt = ""
        
        # Load system prompt from file
        prompt_file = Path(__file__).parent / "modules" / "query_assistant" / "prompts" / "mcp_system_prompt.txt"
        try:
            with open(prompt_file, 'r', encoding='utf-8') as f:
                mcp_prompt = f.read()
        except FileNotFoundError:
            # Fallback to default prompt if file not found
            mcp_prompt = "Extract parameters from the query."
        
        # Combine prompts for better keyword extraction
        self.system_prompt = f"""{keyword_prompt}

{mcp_prompt}

Additionally, respond in JSON format:
{{
    "keywords": ["keyword1", "keyword2", ...],
    "parameters": {{
        "organization": "ORG_CODE" or null,
        "sender_organization": null,
        "response_org": null,
        "days": number or null,
        "date_range": null,
        "agenda_code": null,
        "agenda_panel": null,
        "status": "approved|rejected|pending" or null,
        "limit": number or null,
        "keyword": null
    }},
    "extracted_period": {{"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}} or null,
    "intent": "search|list|analyze|count",
    "confidence": 0.0-1.0
}}"""

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

위 질의를 분석하여 JSON 형식으로 응답하세요."""}
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
                        "parameters": {},
                        "intent": "unknown",
                        "confidence": 0.5
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
        print(f"[LLM] Extracted keywords: {analysis['keywords']}")
        print(f"[LLM] Extracted parameters: {analysis['parameters']}")
        print(f"[LLM] Extracted period: {analysis.get('extracted_period', 'None')}")
        
        # Convert LLM parameters to MCP format
        extracted_period = None
        
        # Use extracted_period if available from LLM
        if 'extracted_period' in analysis and analysis['extracted_period']:
            extracted_period = analysis['extracted_period']
        elif 'extracted_dates' in analysis and analysis['extracted_dates']:
            # Backward compatibility: extracted_dates → extracted_period
            extracted_period = analysis['extracted_dates']
        elif analysis['parameters'].get('days'):
            # Convert days to period
            from datetime import datetime, timedelta
            end_date = datetime.now()
            start_date = end_date - timedelta(days=analysis['parameters']['days'])
            extracted_period = {
                'start': start_date.strftime('%Y-%m-%d'),
                'end': end_date.strftime('%Y-%m-%d')
            }
        else:
            # Default: 3 months if period is ambiguous
            from datetime import datetime, timedelta
            end_date = datetime.now()
            start_date = end_date - timedelta(days=90)
            extracted_period = {
                'start': start_date.strftime('%Y-%m-%d'),
                'end': end_date.strftime('%Y-%m-%d')
            }
        
        # Extract organization from LLM or keywords
        extracted_organization = None
        if analysis['parameters'].get('organization'):
            extracted_organization = analysis['parameters']['organization']
        elif analysis['parameters'].get('sender_organization'):
            extracted_organization = analysis['parameters']['sender_organization']
        elif analysis['parameters'].get('response_org'):
            extracted_organization = analysis['parameters']['response_org']
        
        # If LLM didn't extract organization, check keywords
        if not extracted_organization:
            # Common organization mappings
            org_keywords = {
                '한국선급': 'KR',
                'KR': 'KR',
                '일본선급': 'NK',
                'NK': 'NK',
                '중국선급': 'CCS',
                'CCS': 'CCS',
                'IMO': 'IMO',
                'IACS': 'IACS'
            }
            for keyword in analysis['keywords']:
                if keyword in org_keywords:
                    extracted_organization = org_keywords[keyword]
                    print(f"[LLM] Extracted organization from keyword: {keyword} → {extracted_organization}")
                    break
        
        # Determine query scope
        query_scope = 'one'  # default
        if '모든' in query or '전체' in query:
            query_scope = 'all'
        elif '여러' in query or ('과' in query and '의' in query):
            query_scope = 'more'
        
        # Import the enhanced MCP server
        from modules.query_assistant.mcp_server_enhanced import EnhancedIacsGraphQueryServer
        from modules.query_assistant.mcp_server_enhanced import EnhancedQueryRequest
        
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
                    "organization": extracted_organization if 'extracted_organization' in locals() else None
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
                print(f"  Keywords: {llm['keywords'][:5]}")
                print(f"  Parameters: {llm['parameters']}")
                print(f"  Intent: {llm['intent']}")
                print(f"  Confidence: {llm['confidence']}")
            
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
    from modules.query_assistant.scripts.test_100_queries import generate_test_queries
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
                'llm_confidence': result.get('llm_analysis', {}).get('confidence', 0)
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