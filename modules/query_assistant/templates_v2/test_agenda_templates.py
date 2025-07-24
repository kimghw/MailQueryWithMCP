#!/usr/bin/env python3
import json
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from datetime import datetime
from pathlib import Path
import sys

QUERIES_TO_TEST = [
    {
        "name": "Test 1: 진행중인 의제 목록 조회",
        "query": "최근 모든 패널에서 진행되고 있는 의제 목록"
    },
    {
        "name": "Test 2: 미완료 의제 조회",
        "query": "최근 모든 패널에서 완료되지 않은 의제 리스트"
    },
    {
        "name": "Test 3: 최근 3개월 논의 의제",
        "query": "최근 3개월 동안 논의 되었던 의제 목록"
    },
    {
        "name": "Test 4: KR 미응답 의제",
        "query": "진행되고 있는 의제들 중에서 KR이 아직 응답하지 않는 의제"
    },
    {
        "name": "Test 5: KR 응답 필요 의제",
        "query": "KR이 응답을 해야 하는 의제"
    },
    {
        "name": "Test 6: 대기중 의제 수",
        "query": "처리 대기 중인 agenda의 수는?"
    },
    {
        "name": "Test 7: KR 의제 이슈 정리",
        "query": "KR이 응답해야하는 의제에서 의제들의 주요 이슈 및 다른 기관의 의견 정리"
    },
    {
        "name": "Test 8: KR 의제 키워드",
        "query": "KR이 응답해야하는 의제들의 주요 키워드"
    },
    {
        "name": "Test 9: KR 응답 중요 키워드",
        "query": "KR이 응답해야 하는 의제들의 회신 중 중요 키워드"
    },
    {
        "name": "Test 10: 키워드 검색 - 보안",
        "query": "최근 논의된 의제들 중에 보안에 대해서 논의되고 있는 의제"
    },
    {
        "name": "Test 11: 키워드 검색 - AI",
        "query": "최근 논의된 의제들 중에 AI에 대해서 논의되고 있는 의제"
    }
]

async def test_mcp_server():
    print("=" * 80)
    print("MCP Server Query Test - Agenda Templates")
    print("=" * 80)
    print(f"Test started at: {datetime.now()}")
    print("=" * 80)
    
    config_path = Path(__file__).parent / "claude_desktop_config.json"
    
    if not config_path.exists():
        print(f"Error: Config file not found at {config_path}")
        return
    
    with open(config_path) as f:
        config = json.load(f)
    
    server_config = config["mcpServers"]["iacsgraph-enhanced"]
    server_command = server_config["command"]
    server_args = server_config["args"]
    
    server_params = StdioServerParameters(
        command=server_command,
        args=server_args,
        env=server_config.get("env")
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            try:
                await session.initialize()
                
                tools = await session.list_tools()
                
                # Handle different response formats
                if hasattr(tools, 'tools'):
                    tool_list = tools.tools
                elif isinstance(tools, list):
                    tool_list = tools
                else:
                    tool_list = []
                
                tool_names = []
                for tool in tool_list:
                    if hasattr(tool, 'name'):
                        tool_names.append(tool.name)
                    elif isinstance(tool, dict) and 'name' in tool:
                        tool_names.append(tool['name'])
                
                print(f"Available tools: {tool_names}")
                print("=" * 80)
                
                if "query" not in tool_names:
                    print("Error: 'query' tool not found!")
                    print(f"Tools response: {tools}")
                    return
                
                for test_case in QUERIES_TO_TEST:
                    print(f"\n{test_case['name']}")
                    print(f"Query: {test_case['query']}")
                    print("-" * 40)
                    
                    try:
                        result = await session.call_tool(
                            "query",
                            arguments={
                                "query": test_case["query"]
                            }
                        )
                        
                        if hasattr(result, 'content') and result.content:
                            content = result.content[0]
                            if hasattr(content, 'text'):
                                raw_text = content.text
                                
                                # Try to parse as JSON first
                                try:
                                    result_data = json.loads(raw_text)
                                    
                                    print(f"Status: {result_data.get('status', 'unknown')}")
                                    
                                    if result_data.get('status') == 'success':
                                        print(f"Template used: {result_data.get('template_id', 'N/A')}")
                                        print(f"Generated SQL: {result_data.get('sql_query', 'N/A')}")
                                        print(f"Parameters: {result_data.get('parameters', {})}")
                                        print(f"Result count: {len(result_data.get('results', []))}")
                                        
                                        if result_data.get('results'):
                                            print("\nFirst few results:")
                                            for i, row in enumerate(result_data['results'][:3]):
                                                print(f"  {i+1}. {json.dumps(row, ensure_ascii=False)[:100]}...")
                                    else:
                                        print(f"Error: {result_data.get('error', 'Unknown error')}")
                                except json.JSONDecodeError:
                                    # If not JSON, just print the text response
                                    print(f"Response: {raw_text[:500]}...")
                            else:
                                print(f"Unexpected response format: {content}")
                        else:
                            print("No content in response")
                            
                    except Exception as e:
                        print(f"Error testing query: {str(e)}")
                        import traceback
                        traceback.print_exc()
                    
                    await asyncio.sleep(0.5)  # Small delay between queries
                    
            except Exception as e:
                print(f"Session error: {str(e)}")
                import traceback
                traceback.print_exc()
    
    print("\n" + "=" * 80)
    print(f"Test completed at: {datetime.now()}")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_mcp_server())