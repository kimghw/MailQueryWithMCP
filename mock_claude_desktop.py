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
        
        # Load system prompt from file
        prompt_file = Path(__file__).parent / "modules" / "query_assistant" / "prompts" / "mcp_system_prompt.txt"
        try:
            with open(prompt_file, 'r', encoding='utf-8') as f:
                mcp_prompt = f.read()
        except FileNotFoundError:
            # Fallback to default prompt if file not found
            mcp_prompt = "Extract parameters from the query."
        
        # Convert MCP prompt format to JSON response format for OpenRouter
        self.system_prompt = f"""{mcp_prompt}

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
    "extracted_dates": {{"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}} or null,
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
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": f"Analyze this query: {query}"}
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
        
        # Convert LLM parameters to MCP format
        extracted_dates = None
        
        # Use extracted_dates if available from LLM
        if 'extracted_dates' in analysis and analysis['extracted_dates']:
            extracted_dates = analysis['extracted_dates']
        elif analysis['parameters'].get('days'):
            # Convert days to date range
            from datetime import datetime, timedelta
            end_date = datetime.now()
            start_date = end_date - timedelta(days=analysis['parameters']['days'])
            extracted_dates = {
                'start': start_date.strftime('%Y-%m-%d'),
                'end': end_date.strftime('%Y-%m-%d')
            }
        
        # Extract organization
        extracted_organization = None
        if analysis['parameters'].get('organization'):
            extracted_organization = analysis['parameters']['organization']
        elif analysis['parameters'].get('sender_organization'):
            extracted_organization = analysis['parameters']['sender_organization']
        elif analysis['parameters'].get('response_org'):
            extracted_organization = analysis['parameters']['response_org']
        
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
                extracted_dates=extracted_dates,
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
            print(f"  Extracted Dates: {mcp_request.extracted_dates}")
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
                    "extracted_dates": mcp_request.extracted_dates,
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
                    "extracted_dates": extracted_dates if 'extracted_dates' in locals() else None,
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
                    "dates": extracted_dates if 'extracted_dates' in locals() else None,
                    "keywords": analysis['keywords']
                },
                "llm_analysis": analysis
            }


async def test_with_mock_claude():
    """Test queries using Mock Claude Desktop"""
    mock = MockClaudeDesktop()
    
    test_queries = [
        "최근 아젠다 목록 보여줘",
        "한국선급 응답 현황",
        "어제 받은 이메일들",
        "IMO 관련 문서",
        "지난주 등록된 아젠다들",
        "의장이 보낸 메일 중 한국이 응답해야 하는 것",
        "PL25016a 아젠다 상세 정보"
    ]
    
    print("="*80)
    print("Testing with Mock Claude Desktop (OpenRouter)")
    print("="*80)
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
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
        await asyncio.sleep(1)


if __name__ == "__main__":
    # Test if API key exists
    if not os.getenv("OPENROUTER_API_KEY"):
        print("Please set OPENROUTER_API_KEY in .env file")
        print("Get your API key from: https://openrouter.ai/keys")
        exit(1)
    
    asyncio.run(test_with_mock_claude())