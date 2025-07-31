#!/usr/bin/env python3
"""
Simple query executor for template validation
Tests if queries execute successfully with default parameter values
"""

import json
import sqlite3
import re
import csv
from pathlib import Path
from typing import Dict, Any, List, Tuple
from datetime import datetime, timedelta

class QueryExecutor:
    """Simple query executor for testing templates"""
    
    def __init__(self, db_path: str):
        """Initialize with database path"""
        self.db_path = db_path
        
    def test_template(self, template: Dict[str, Any], save_results: bool = False) -> Tuple[bool, str, str, List[Any]]:
        """Test a single template
        
        Returns:
            Tuple of (success, query_used, error_message, results)
        """
        template_id = template.get('template_id', 'unknown')
        
        # Skip non-SQL templates
        if template.get('routing_type') != 'sql':
            return True, "", "Not an SQL template", []
            
        # Get SQL query
        sql_template = template.get('sql_template', {})
        sql_query = sql_template.get('query', '')
        
        if not sql_query:
            return False, "", "No SQL query found", []
            
        # Get parameters
        parameters = template.get('parameters', [])
        
        # Check for multi_query parameters
        multi_query_params = [p for p in parameters if p.get('multi_query', False)]
        
        if multi_query_params:
            # Handle multi-query execution
            return self._test_multi_query_template(template, multi_query_params, save_results)
        
        # Check if query uses named parameters (SQLite style with :param_name)
        uses_named_params = ':' in sql_query and any(':' + p.get('name', '') in sql_query for p in parameters)
        
        param_dict = None
        if uses_named_params:
            # Build parameter dictionary for SQLite parameter binding
            param_dict = {}
            for param in parameters:
                param_name = param.get('name')
                param_type = param.get('type')
                default_value = param.get('default')
                
                # Provide intelligent defaults for common parameters without default values
                if param_name and default_value is None:
                    if param_name == 'organization':
                        # Default organization to KR
                        param_dict[param_name] = 'KR'
                    elif param_name == 'agenda':
                        # Default agenda code
                        param_dict[param_name] = 'PL25001'
                    elif param_name == 'keyword':
                        # Default keyword
                        param_dict[param_name] = 'IMO'
                    elif param_name == 'organization1':
                        param_dict[param_name] = 'KR'
                    elif param_name == 'organization2':
                        param_dict[param_name] = 'DNV'
                    elif param_name == 'organization3':
                        param_dict[param_name] = 'ABS'
                elif param_name and default_value is not None:
                    # Handle datetime parameters
                    if param_type == 'datetime':
                        # Convert SQL datetime functions to actual datetime values
                        if default_value == "datetime('now', '-90 days')":
                            param_dict[param_name] = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d %H:%M:%S')
                        elif default_value == "datetime('now', '-30 days')":
                            param_dict[param_name] = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
                        elif default_value == "datetime('now', '-1 days')":
                            param_dict[param_name] = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
                        elif default_value == "datetime('now', '-7 days')":
                            param_dict[param_name] = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
                        elif default_value == "datetime('now', '-365 days')":
                            param_dict[param_name] = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d %H:%M:%S')
                        elif default_value == "datetime('now', '-60 days')":
                            param_dict[param_name] = (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d %H:%M:%S')
                        else:
                            param_dict[param_name] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    elif param_type == 'array':
                        # For array types, use the first value or default string
                        if isinstance(default_value, list):
                            param_dict[param_name] = default_value[0] if default_value else 'default'
                        else:
                            # Current implementation: default is stored as string
                            param_dict[param_name] = default_value
                    else:
                        # For other types, use the default value as-is
                        param_dict[param_name] = default_value
            
            final_query = sql_query
        else:
            # Legacy placeholder substitution for old-style templates
            final_query = sql_query
            for param in parameters:
                param_name = param.get('name')
                default_value = param.get('default')
                
                if param_name and default_value is not None:
                    placeholder = f'{{{param_name}}}'
                    if isinstance(default_value, str):
                        # Don't add quotes if already in a LIKE clause
                        if f"LIKE '%{placeholder}%'" in sql_query:
                            final_query = final_query.replace(placeholder, default_value)
                        # Check if placeholder is used as a column name (e.g., r.{organization})
                        elif f"r.{placeholder}" in sql_query or f"c.{placeholder}" in sql_query:
                            final_query = final_query.replace(placeholder, default_value)
                        else:
                            final_query = final_query.replace(placeholder, f"'{default_value}'")
                    elif isinstance(default_value, list):
                        # Check if it's in a LIKE clause (for keywords)
                        if f"LIKE '%{placeholder}%'" in sql_query:
                            # For LIKE clauses, join with OR
                            like_conditions = [f"'%{v}%'" for v in default_value]
                            final_query = final_query.replace(f"'%{placeholder}%'", like_conditions[0])
                            # Note: This only handles first keyword for simplicity
                        else:
                            # Convert list to SQL IN format
                            quoted_values = [f"'{v}'" for v in default_value]
                            final_query = final_query.replace(placeholder, f"({', '.join(quoted_values)})")
                    else:
                        final_query = final_query.replace(placeholder, str(default_value))
        
        # Handle common special placeholders
        special_replacements = {
            '{date_condition}': "sent_time >= DATE('now', '-30 days')",
            '{period_condition}': "sent_time >= DATE('now', '-30 days')",
            '{period_start}': "DATE('now', '-30 days')",
            '{period_end}': "DATE('now')",
            '{deadline_filter}': "deadline IS NOT NULL AND deadline >= DATE('now')",
            '{no_deadline_filter}': "deadline IS NULL",
            '{keywords_condition}': "(keywords LIKE '%PR%' OR subject LIKE '%PR%' OR keywords LIKE '%EG%' OR subject LIKE '%EG%')",
            '{keyword_condition}': "1=1",
            '{agenda}': "PL24005",  # This should be agenda_base_version value
            '{issue_condition}': "1=1"
        }
        
        for placeholder, replacement in special_replacements.items():
            final_query = final_query.replace(placeholder, replacement)
        
        # Check for remaining placeholders
        remaining_placeholders = re.findall(r'\{(\w+)\}', final_query)
        if remaining_placeholders:
            return False, final_query, f"Unsubstituted placeholders: {remaining_placeholders}", []
        
        # Try to execute
        try:
            # Use the related_db if specified
            db_to_use = template.get('related_db', self.db_path)
            if db_to_use == 'iacsgraph.db':
                db_to_use = self.db_path  # Use the provided path
                
            conn = sqlite3.connect(db_to_use)
            cursor = conn.cursor()
            
            # Add LIMIT for safety
            test_query = final_query
            if 'LIMIT' not in test_query.upper():
                test_query = f"{test_query} LIMIT 5"
            
            if param_dict is not None:
                # Use parameter binding for new-style queries
                cursor.execute(test_query, param_dict)
            else:
                # Execute directly for old-style queries
                cursor.execute(test_query)
            results = cursor.fetchall()
            
            # Get column names
            column_names = [description[0] for description in cursor.description] if cursor.description else []
            
            conn.close()
            
            # Format results with column names
            formatted_results = []
            for row in results:
                formatted_results.append(dict(zip(column_names, row)))
            
            return True, final_query, f"Success: {len(results)} rows returned", formatted_results
            
        except sqlite3.Error as e:
            return False, final_query, f"SQL Error: {str(e)}", []
        except Exception as e:
            return False, final_query, f"Error: {str(e)}", []
    
    def test_all_templates(self, templates_file: str) -> Dict[str, Any]:
        """Test all templates in a file"""
        # Load templates
        with open(templates_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        templates = data.get('templates', [])
        
        # Test results
        results = {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'failures': []
        }
        
        print(f"Testing {len(templates)} templates with database: {self.db_path}")
        print("=" * 80)
        
        for template in templates:
            template_id = template.get('template_id', 'unknown')
            
            # Skip non-SQL templates
            if template.get('routing_type') != 'sql':
                continue
                
            results['total'] += 1
            
            success, query, message, _ = self.test_template(template)
            
            if success:
                results['passed'] += 1
                print(f"✓ {template_id}")
            else:
                results['failed'] += 1
                print(f"✗ {template_id}: {message}")
                results['failures'].append({
                    'template_id': template_id,
                    'category': template.get('template_category'),
                    'error': message,
                    'query': query[:200] + '...' if len(query) > 200 else query
                })
        
        print("\n" + "=" * 80)
        print(f"SUMMARY:")
        print(f"Total SQL templates: {results['total']}")
        print(f"Passed: {results['passed']} ({results['passed']/results['total']*100:.1f}%)")
        print(f"Failed: {results['failed']} ({results['failed']/results['total']*100:.1f}%)")
        
        if results['failures']:
            print(f"\nFAILED TEMPLATES ({len(results['failures'])}):")
            print("-" * 80)
            for failure in results['failures'][:10]:  # Show first 10
                print(f"\n[{failure['template_id']}] ({failure['category']})")
                print(f"Error: {failure['error']}")
                print(f"Query: {failure['query']}")
            
            if len(results['failures']) > 10:
                print(f"\n... and {len(results['failures']) - 10} more failures")
        
        return results
    
    def test_and_save_results(self, templates_file: str, output_dir: str = "query_results") -> Dict[str, Any]:
        """Test templates and save results for review"""
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Load templates
        with open(templates_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        templates = data.get('templates', [])
        
        # Test results
        all_results = []
        summary = {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'test_date': datetime.now().isoformat()
        }
        
        print(f"Testing templates and saving results to: {output_path}")
        print("=" * 80)
        
        for template in templates:
            template_id = template.get('template_id', 'unknown')
            
            # Skip non-SQL templates
            if template.get('routing_type') != 'sql':
                continue
                
            summary['total'] += 1
            
            success, query, message, results = self.test_template(template, save_results=True)
            
            test_result = {
                'template_id': template_id,
                'category': template.get('template_category'),
                'success': success,
                'message': message,
                'query': query,
                'result_count': len(results),
                'sample_results': results[:5]  # Save first 5 results
            }
            
            all_results.append(test_result)
            
            if success:
                summary['passed'] += 1
                print(f"✓ {template_id} - {len(results)} rows")
                
                # Save individual result to CSV for successful queries
                if results:
                    csv_file = output_path / f"{template_id}.csv"
                    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                        if results:
                            writer = csv.DictWriter(f, fieldnames=results[0].keys())
                            writer.writeheader()
                            writer.writerows(results[:100])  # Save up to 100 rows
            else:
                summary['failed'] += 1
                print(f"✗ {template_id} - {message}")
        
        # Save summary JSON
        summary_file = output_path / "test_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump({
                'summary': summary,
                'results': all_results
            }, f, indent=2, ensure_ascii=False)
        
        print("\n" + "=" * 80)
        print(f"SUMMARY:")
        print(f"Total SQL templates: {summary['total']}")
        print(f"Passed: {summary['passed']} ({summary['passed']/summary['total']*100:.1f}%)")
        print(f"Failed: {summary['failed']} ({summary['failed']/summary['total']*100:.1f}%)")
        print(f"\nResults saved to: {output_path}")
        print(f"- Individual CSV files for successful queries")
        print(f"- test_summary.json for overall results")
        
        return summary
    
    def test_specific_template(self, templates_file: str, template_id: str) -> None:
        """Test a specific template and show detailed results"""
        # Load templates
        with open(templates_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        templates = data.get('templates', [])
        
        # Find the template
        template = None
        for t in templates:
            if t.get('template_id') == template_id:
                template = t
                break
        
        if not template:
            print(f"Template '{template_id}' not found")
            return
        
        print(f"Testing template: {template_id}")
        print("=" * 80)
        
        success, query, message, results = self.test_template(template)
        
        print(f"\nQuery:")
        print("-" * 40)
        print(query)
        
        print(f"\nResult: {'SUCCESS' if success else 'FAILED'}")
        print(f"Message: {message}")
        
        if success and results:
            print(f"\nQuery Results ({len(results)} rows):")
            print("-" * 40)
            
            # Show first 10 results
            for i, row in enumerate(results[:10]):
                print(f"\nRow {i+1}:")
                for key, value in row.items():
                    # Truncate long values
                    str_value = str(value) if value is not None else 'NULL'
                    if len(str_value) > 100:
                        str_value = str_value[:97] + '...'
                    print(f"  {key}: {str_value}")
            
            if len(results) > 10:
                print(f"\n... and {len(results) - 10} more rows")


def main():
    """Main function for command line usage"""
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='Test SQL query templates')
    parser.add_argument('templates_file', help='Path to templates JSON file')
    parser.add_argument('database_path', help='Path to database file')
    parser.add_argument('--save-results', action='store_true', help='Save query results to files')
    parser.add_argument('--output-dir', default='query_results', help='Directory to save results (default: query_results)')
    parser.add_argument('--template', help='Test specific template by ID')
    
    args = parser.parse_args()
    
    if not Path(args.templates_file).exists():
        print(f"Templates file not found: {args.templates_file}")
        sys.exit(1)
        
    if not Path(args.database_path).exists():
        print(f"Database not found: {args.database_path}")
        sys.exit(1)
    
    executor = QueryExecutor(args.database_path)
    
    if args.template:
        # Test specific template
        executor.test_specific_template(args.templates_file, args.template)
    elif args.save_results:
        # Test all and save results
        summary = executor.test_and_save_results(args.templates_file, args.output_dir)
        sys.exit(0 if summary['failed'] == 0 else 1)
    else:
        # Default: test all templates
        results = executor.test_all_templates(args.templates_file)
        sys.exit(0 if results['failed'] == 0 else 1)


if __name__ == "__main__":
    main()