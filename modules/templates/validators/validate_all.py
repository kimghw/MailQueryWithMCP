#!/usr/bin/env python3
"""Run all validators and generate comprehensive report"""

import json
from pathlib import Path
from datetime import datetime
from template_validator import TemplateValidator
from parameter_validator import ParameterValidator


def main():
    template_dir = Path('/home/kimghw/IACSGRAPH/modules/templates/data/query_templates_split')
    
    print("=" * 80)
    print("IACSGRAPH Template Validation Report")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    template_validator = TemplateValidator()
    param_validator = ParameterValidator()
    
    # Summary statistics
    total_files = 0
    total_templates = 0
    total_errors = 0
    total_warnings = 0
    
    # Detailed results
    file_results = []
    
    for file_path in sorted(template_dir.glob('query_templates_group_*.json')):
        total_files += 1
        file_result = {
            'file': file_path.name,
            'template_errors': 0,
            'template_warnings': 0,
            'param_errors': 0,
            'param_warnings': 0,
            'issues': []
        }
        
        # Template validation
        is_valid, template_results = template_validator.validate_file(file_path)
        file_result['templates'] = template_results.get('total', 0)
        total_templates += template_results.get('total', 0)
        
        if not is_valid:
            for error_info in template_results.get('errors', []):
                file_result['template_errors'] += len(error_info['errors'])
                total_errors += len(error_info['errors'])
                file_result['issues'].append({
                    'type': 'template_error',
                    'template': error_info['template_id'],
                    'messages': error_info['errors']
                })
        
        for warning_info in template_results.get('warnings', []):
            file_result['template_warnings'] += len(warning_info['warnings'])
            total_warnings += len(warning_info['warnings'])
        
        # Parameter validation
        is_valid, param_results = param_validator.validate_file(file_path)
        
        if not is_valid:
            for error_info in param_results.get('errors', []):
                file_result['param_errors'] += len(error_info['errors'])
                total_errors += len(error_info['errors'])
                file_result['issues'].append({
                    'type': 'param_error',
                    'template': error_info['template_id'],
                    'messages': error_info['errors']
                })
        
        for warning_info in param_results.get('warnings', []):
            file_result['param_warnings'] += len(warning_info['warnings'])
            total_warnings += len(warning_info['warnings'])
        
        file_results.append(file_result)
    
    # Print results
    print(f"\nSummary:")
    print(f"  Files: {total_files}")
    print(f"  Templates: {total_templates}")
    print(f"  Total Errors: {total_errors}")
    print(f"  Total Warnings: {total_warnings}")
    
    print("\n" + "-" * 80)
    print("File-by-File Results:")
    print("-" * 80)
    
    for result in file_results:
        total_issues = result['template_errors'] + result['param_errors']
        status = "✓" if total_issues == 0 else "✗"
        
        print(f"\n{status} {result['file']} ({result['templates']} templates)")
        print(f"  Template Issues: {result['template_errors']} errors, {result['template_warnings']} warnings")
        print(f"  Parameter Issues: {result['param_errors']} errors, {result['param_warnings']} warnings")
        
        if result['issues']:
            print("  Critical Issues:")
            # Show first 3 issues
            for issue in result['issues'][:3]:
                print(f"    [{issue['template']}] {issue['type']}:")
                for msg in issue['messages'][:2]:
                    print(f"      - {msg}")
            if len(result['issues']) > 3:
                print(f"    ... and {len(result['issues']) - 3} more issues")
    
    # Common issues summary
    print("\n" + "-" * 80)
    print("Common Issues Found:")
    print("-" * 80)
    
    issue_counts = {}
    for result in file_results:
        for issue in result['issues']:
            for msg in issue['messages']:
                # Normalize message for counting
                if "Use uppercase for mail_type values" in msg:
                    key = "Use uppercase for mail_type values: 'REQUEST' not 'request'"
                elif "SQL uses old-style parameters" in msg:
                    key = "SQL uses old-style parameters {{}}. Use :param_name format"
                elif "missing 'mcp_format'" in msg:
                    key = "Parameter missing 'mcp_format' field"
                else:
                    key = msg
                
                issue_counts[key] = issue_counts.get(key, 0) + 1
    
    # Sort by frequency
    sorted_issues = sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)
    
    for issue, count in sorted_issues[:10]:
        print(f"  {count}x: {issue}")
    
    # Recommendations
    print("\n" + "-" * 80)
    print("Recommendations:")
    print("-" * 80)
    print("1. Update all SQL queries to use uppercase for mail_type values ('REQUEST', not 'request')")
    print("2. Ensure all templates are at version 2.0.0")
    print("3. Add mcp_format to all parameters for better MCP integration")
    print("4. Update natural_questions to follow (original), (similar1-N), (ext) format")
    print("5. Replace any remaining {{parameter}} with :parameter format")
    
    print("\n" + "=" * 80)
    if total_errors == 0:
        print("✓ All templates pass validation!")
    else:
        print(f"✗ Found {total_errors} errors that need to be fixed")
    print("=" * 80)


if __name__ == "__main__":
    main()