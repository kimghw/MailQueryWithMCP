#!/usr/bin/env python3
"""
Query Report Generator
Generates a comprehensive report showing each template's query and its results
"""

import json
import sqlite3
import re
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

class QueryReportGenerator:
    """Generate detailed reports for query templates"""
    
    def __init__(self, db_path: str):
        """Initialize with database path"""
        self.db_path = db_path
        
    def generate_report(self, templates_file: str, output_file: str = "query_report.txt"):
        """Generate a comprehensive report with queries and results"""
        # Load templates
        with open(templates_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        templates = data.get('templates', [])
        
        # Open output file
        with open(output_file, 'w', encoding='utf-8') as report:
            report.write("=" * 120 + "\n")
            report.write("QUERY TEMPLATE EXECUTION REPORT\n")
            report.write(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            report.write(f"Database: {self.db_path}\n")
            report.write("=" * 120 + "\n\n")
            
            total = 0
            passed = 0
            failed = 0
            
            for template in templates:
                template_id = template.get('template_id', 'unknown')
                
                # Skip non-SQL templates
                if template.get('routing_type') != 'sql':
                    continue
                    
                total += 1
                
                report.write("-" * 120 + "\n")
                report.write(f"Template ID: {template_id}\n")
                report.write(f"Category: {template.get('template_category', 'N/A')}\n")
                report.write("-" * 120 + "\n\n")
                
                # Get query_info for natural questions
                query_info = template.get('query_info', {})
                natural_questions = query_info.get('natural_questions', [])
                
                if natural_questions:
                    report.write("NATURAL QUESTIONS:\n")
                    for i, question in enumerate(natural_questions, 1):
                        report.write(f"  {i}. {question}\n")
                    report.write("\n")
                
                # Get SQL query
                sql_template = template.get('sql_template', {})
                sql_query = sql_template.get('query', '')
                
                # Write original query
                report.write("ORIGINAL QUERY:\n")
                report.write(sql_query + "\n\n")
                
                # Write system and user prompts if available
                if sql_template.get('system'):
                    report.write("SYSTEM CONTEXT:\n")
                    report.write(sql_template.get('system') + "\n\n")
                
                if sql_template.get('user'):
                    report.write("USER REQUEST:\n")
                    report.write(sql_template.get('user') + "\n\n")
                
                # Process query with default values
                final_query = self._process_query(sql_query, template.get('parameters', []))
                
                report.write("PROCESSED QUERY (with defaults):\n")
                report.write(final_query + "\n\n")
                
                # Execute query
                success, message, results = self._execute_query(final_query)
                
                if success:
                    passed += 1
                    report.write(f"EXECUTION RESULT: SUCCESS ({len(results)} rows)\n\n")
                    
                    if results:
                        # Show results (up to 30 rows)
                        rows_to_show = min(len(results), 30)
                        report.write(f"QUERY RESULTS ({len(results)} total rows, showing {rows_to_show}):\n")
                        report.write("-" * 80 + "\n")
                        
                        # Column headers
                        if results:
                            columns = list(results[0].keys())
                            report.write(" | ".join(columns) + "\n")
                            report.write("-" * 80 + "\n")
                            
                            # Data rows
                            for i, row in enumerate(results[:rows_to_show]):
                                row_values = []
                                for col in columns:
                                    value = str(row[col]) if row[col] is not None else 'NULL'
                                    # Truncate long values
                                    if len(value) > 50:
                                        value = value[:47] + '...'
                                    row_values.append(value)
                                report.write(" | ".join(row_values) + "\n")
                            
                            if len(results) > 30:
                                report.write(f"\n... and {len(results) - 30} more rows not shown\n")
                    else:
                        report.write("NO RESULTS RETURNED\n")
                else:
                    failed += 1
                    report.write(f"EXECUTION RESULT: FAILED\n")
                    report.write(f"ERROR: {message}\n")
                
                report.write("\n\n")
            
            # Summary
            report.write("=" * 120 + "\n")
            report.write("SUMMARY\n")
            report.write("=" * 120 + "\n")
            report.write(f"Total SQL templates: {total}\n")
            report.write(f"Successful executions: {passed} ({passed/total*100:.1f}%)\n")
            report.write(f"Failed executions: {failed} ({failed/total*100:.1f}%)\n")
        
        print(f"Report generated: {output_file}")
        print(f"Total templates: {total}, Passed: {passed}, Failed: {failed}")
    
    def _process_query(self, sql_query: str, parameters: List[Dict[str, Any]]) -> str:
        """Process query with default parameter values"""
        final_query = sql_query
        
        # Process defined parameters
        for param in parameters:
            param_name = param.get('name')
            default_value = param.get('default')
            
            if param_name and default_value is not None:
                placeholder = f'{{{param_name}}}'
                if isinstance(default_value, str):
                    final_query = final_query.replace(placeholder, f"'{default_value}'")
                elif isinstance(default_value, list):
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
            '{keywords_condition}': "1=1",
            '{keyword_condition}': "1=1",
            '{organization}': "'KR'",
            '{panel}': "'PL'",
            '{agenda}': "'PL25017'",
            '{issue_condition}': "1=1"
        }
        
        for placeholder, replacement in special_replacements.items():
            final_query = final_query.replace(placeholder, replacement)
        
        return final_query
    
    def _execute_query(self, query: str):
        """Execute query and return results"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Add LIMIT for safety
            test_query = query
            if 'LIMIT' not in test_query.upper():
                test_query = f"{test_query} LIMIT 100"
            
            cursor.execute(test_query)
            results = cursor.fetchall()
            
            # Get column names
            column_names = [description[0] for description in cursor.description] if cursor.description else []
            
            conn.close()
            
            # Format results with column names
            formatted_results = []
            for row in results:
                formatted_results.append(dict(zip(column_names, row)))
            
            return True, f"Success: {len(results)} rows", formatted_results
            
        except Exception as e:
            return False, str(e), []


def main():
    """Main function"""
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python query_report_generator.py <templates_file> <database_path> [output_file]")
        sys.exit(1)
    
    templates_file = sys.argv[1]
    db_path = sys.argv[2]
    output_file = sys.argv[3] if len(sys.argv) > 3 else "query_report.txt"
    
    if not Path(templates_file).exists():
        print(f"Templates file not found: {templates_file}")
        sys.exit(1)
        
    if not Path(db_path).exists():
        print(f"Database not found: {db_path}")
        sys.exit(1)
    
    generator = QueryReportGenerator(db_path)
    generator.generate_report(templates_file, output_file)


if __name__ == "__main__":
    main()