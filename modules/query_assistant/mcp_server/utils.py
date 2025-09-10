"""Utility functions for Query Assistant MCP Server"""

import json
import logging
from typing import Any, Dict

from infra.core.logger import get_logger
from ..schema import QueryResult

logger = get_logger(__name__)


def preprocess_arguments(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Preprocess arguments from Claude Desktop"""
    
    # Clean backslashes from all string values
    def clean_backslashes(obj):
        if isinstance(obj, str):
            return obj.replace('\\', '')
        elif isinstance(obj, dict):
            return {k: clean_backslashes(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [clean_backslashes(item) for item in obj]
        return obj
    
    arguments = clean_backslashes(arguments)
    
    # Special handling for limit field
    if 'limit' in arguments and isinstance(arguments['limit'], str):
        cleaned_limit = arguments['limit'].strip().strip("'").strip('"')
        try:
            arguments['limit'] = int(cleaned_limit)
        except ValueError:
            pass
    
    # Handle string-wrapped JSON
    if 'extracted_period' in arguments and isinstance(arguments['extracted_period'], str):
        try:
            arguments['extracted_period'] = json.loads(arguments['extracted_period'])
        except:
            pass
    
    if 'extracted_keywords' in arguments and isinstance(arguments['extracted_keywords'], str):
        try:
            arguments['extracted_keywords'] = json.loads(arguments['extracted_keywords'])
        except:
            pass
    
    # Handle string "null" to actual null
    null_fields = ['extracted_organization', 'category', 'query_scope', 'intent']
    for key in null_fields:
        if key in arguments and arguments[key] == 'null':
            arguments[key] = None
    
    return arguments


def format_query_result(result: QueryResult) -> str:
    """Format query result for display"""
    if result.error:
        return f"❌ Error: {result.error}"
    
    lines = []
    lines.append(f"✅ Query executed successfully")
    lines.append(f"⏱️  Execution time: {result.execution_time:.2f}s")
    lines.append(f"📊 Results: {len(result.results)} rows")
    
    if result.results:
        lines.append("\n📈 Results:")
        for i, row in enumerate(result.results[:10]):
            lines.append(f"\nRow {i+1}:")
            for key, value in row.items():
                lines.append(f"  {key}: {value}")
                
        if len(result.results) > 10:
            lines.append(f"\n... and {len(result.results) - 10} more rows")
    
    return "\n".join(lines)


def format_enhanced_result(result: Dict[str, Any]) -> str:
    """Format enhanced query result"""
    if 'error' in result:
        return f"❌ Error: {result['error']}"
    
    lines = []
    
    # Rule-based parameters
    if any(result.get('rule_based_params', {}).values()):
        lines.append("🔧 Rule-based Parameters (MCP Extracted):")
        for key, value in result['rule_based_params'].items():
            if value:
                lines.append(f"  • {key}: {value}")
        lines.append("")
    
    # LLM contribution
    if any(result.get('llm_contribution', {}).values()):
        lines.append("🤖 LLM Extracted Parameters:")
        if result['llm_contribution'].get('period'):
            lines.append(f"  📅 Period: {result['llm_contribution']['period']}")
        if result['llm_contribution'].get('keywords'):
            lines.append(f"  🔑 Keywords: {', '.join(result['llm_contribution']['keywords'])}")
        if result['llm_contribution'].get('organization'):
            lines.append(f"  🏢 Organization: {result['llm_contribution']['organization']}")
        if result['llm_contribution'].get('intent'):
            lines.append(f"  🎯 Intent: {result['llm_contribution']['intent']}")
        lines.append("")
    
    # Query results
    query_result = result['result']
    if hasattr(query_result, 'error') and query_result.error:
        lines.append(f"❌ Query Error: {query_result.error}")
    else:
        lines.append(f"✅ Query executed successfully")
        if hasattr(query_result, 'execution_time'):
            lines.append(f"⏱️  Execution time: {query_result.execution_time:.2f}s")
        if hasattr(query_result, 'results'):
            lines.append(f"📊 Results: {len(query_result.results)} rows")
            
            if query_result.results:
                lines.append("\n📈 Sample Results:")
                for i, row in enumerate(query_result.results[:3]):
                    lines.append(f"\nRow {i+1}:")
                    for key, value in row.items():
                        lines.append(f"  {key}: {value}")
                        
                if len(query_result.results) > 3:
                    lines.append(f"\n... and {len(query_result.results) - 3} more rows")
    
    return "\n".join(lines)