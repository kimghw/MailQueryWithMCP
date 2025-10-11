#!/usr/bin/env python3
"""
Test MCP server connection via HTTP
"""

import requests
import json

# Render 서버 URL (배포 후 실제 URL로 변경)
SERVER_URL = "https://your-app-name.onrender.com"
API_KEY = "your-api-key-here"

def test_health():
    """Health check endpoint test"""
    print("🏥 Testing health endpoint...")
    response = requests.get(f"{SERVER_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}\n")
    return response.status_code == 200

def test_initialize():
    """Test MCP initialize"""
    print("🚀 Testing MCP initialize...")

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        }
    }

    headers = {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY
    }

    response = requests.post(SERVER_URL, json=payload, headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}\n")
    return response.status_code == 200

def test_list_tools():
    """Test listing available tools"""
    print("🔧 Testing tools/list...")

    payload = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list"
    }

    headers = {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY
    }

    response = requests.post(SERVER_URL, json=payload, headers=headers)
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        tools = result.get("result", {}).get("tools", [])
        print(f"Available tools ({len(tools)}):")
        for tool in tools:
            print(f"  - {tool.get('name')}: {tool.get('description')}")
    else:
        print(f"Error: {response.text}")
    print()

def main():
    """Run all tests"""
    print("="*60)
    print("MCP Server Connection Test")
    print("="*60)
    print(f"Server URL: {SERVER_URL}")
    print(f"API Key: {API_KEY[:10]}..." if len(API_KEY) > 10 else "Not set")
    print("="*60 + "\n")

    # Run tests
    tests = [
        ("Health Check", test_health),
        ("MCP Initialize", test_initialize),
        ("List Tools", test_list_tools),
    ]

    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, "✅ PASS" if success else "❌ FAIL"))
        except Exception as e:
            print(f"Error: {e}\n")
            results.append((name, f"❌ ERROR: {str(e)}"))

    # Summary
    print("="*60)
    print("Test Results:")
    print("="*60)
    for name, result in results:
        print(f"{result} - {name}")
    print("="*60)

if __name__ == "__main__":
    main()
