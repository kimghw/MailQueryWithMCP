#!/usr/bin/env python3
"""Test yesterday query specifically"""
import asyncio
from mock_claude_desktop import MockClaudeDesktop

async def test_yesterday():
    mock = MockClaudeDesktop()
    
    # Test "어제" query multiple times
    for i in range(3):
        print(f"\n{'='*60}")
        print(f"Test {i+1}/3: 어제 받은 이메일들")
        print('='*60)
        
        result = await mock.process_query_with_mcp(
            query="어제 받은 이메일들",
            execute=False
        )
        
        # Check what was extracted
        args = result.get('arguments', {})
        print(f"MCP extracted_period: {args.get('extracted_period')}")
        
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(test_yesterday())