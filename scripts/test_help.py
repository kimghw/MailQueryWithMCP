#!/usr/bin/env python3
"""
Help 기능 테스트 스크립트
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from modules.mail_query_without_db.mcp_server.tools.help_content import get_tool_help


def test_help_all_tools():
    """모든 도구 목록 조회 테스트"""
    print("\n" + "="*60)
    print("Test 1: List All Tools")
    print("="*60)

    result = get_tool_help()
    print(result)


def test_help_query_email():
    """query_email 도구 상세 도움말 테스트"""
    print("\n" + "="*60)
    print("Test 2: Help for query_email")
    print("="*60)

    result = get_tool_help("query_email")
    print(result)


def test_help_create_enrollment():
    """create_enrollment_file 도구 상세 도움말 테스트"""
    print("\n" + "="*60)
    print("Test 3: Help for create_enrollment_file")
    print("="*60)

    result = get_tool_help("create_enrollment_file")
    print(result)


def test_help_list_accounts():
    """list_accounts 도구 상세 도움말 테스트"""
    print("\n" + "="*60)
    print("Test 4: Help for list_accounts")
    print("="*60)

    result = get_tool_help("list_accounts")
    print(result)


def test_help_invalid_tool():
    """존재하지 않는 도구 테스트"""
    print("\n" + "="*60)
    print("Test 5: Help for Invalid Tool")
    print("="*60)

    result = get_tool_help("non_existent_tool")
    print(result)


def main():
    print("="*60)
    print("Help Function Test")
    print("="*60)

    # Test 1: All tools
    test_help_all_tools()

    # Test 2: query_email details
    test_help_query_email()

    # Test 3: create_enrollment_file details
    test_help_create_enrollment()

    # Test 4: list_accounts details
    test_help_list_accounts()

    # Test 5: Invalid tool
    test_help_invalid_tool()

    print("\n" + "="*60)
    print("Test completed!")
    print("="*60)


if __name__ == "__main__":
    main()
