#!/usr/bin/env python3
"""Debug LLM response for date parsing"""
import asyncio
import json
from mock_claude_desktop import MockClaudeDesktop

async def debug_llm():
    mock = MockClaudeDesktop()
    
    # Test query
    query = "어제 받은 이메일들"
    
    print(f"Testing query: {query}")
    print("="*60)
    
    # Get LLM analysis
    analysis = await mock.analyze_query(query)
    
    print("LLM Response:")
    print(json.dumps(analysis, indent=2, ensure_ascii=False))
    
    # Check specific fields
    print("\nExtracted fields:")
    print(f"- keywords: {analysis.get('keywords', [])}")
    print(f"- extracted_period: {analysis.get('extracted_period', 'None')}")
    print(f"- parameters: {analysis.get('parameters', {})}")

if __name__ == "__main__":
    asyncio.run(debug_llm())