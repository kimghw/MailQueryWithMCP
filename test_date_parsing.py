#!/usr/bin/env python3
"""Test date parsing with mock claude desktop"""
import asyncio
from mock_claude_desktop import MockClaudeDesktop

async def test_date_queries():
    mock = MockClaudeDesktop()
    
    test_queries = [
        "어제 받은 이메일들",
        "오늘 아젠다 목록",
        "지난주 등록된 문서들",
        "이번달 응답 현황"
    ]
    
    for query in test_queries:
        print(f"\nTesting: {query}")
        try:
            result = await mock.process_query_with_mcp(query, execute=False)
            
            # Check LLM analysis
            llm_analysis = result.get('llm_analysis', {})
            print(f"LLM extracted_period: {llm_analysis.get('extracted_period', 'None')}")
            
            # Check MCP request
            args = result.get('arguments', {})
            print(f"MCP extracted_period: {args.get('extracted_period', 'None')}")
            
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_date_queries())