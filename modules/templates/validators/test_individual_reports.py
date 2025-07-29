#!/usr/bin/env python3
"""
Test templates and generate individual markdown reports for each file
"""

import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

from .query_executor import QueryExecutor

class IndividualTemplateTest:
    def __init__(self, db_path: str, output_dir: str = "modules/templates/test_results"):
        self.db_path = db_path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.executor = QueryExecutor(db_path)
        
    def test_single_file(self, file_path: Path):
        """Test a single template file and generate markdown report"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        templates = data.get('templates', [])
        results = []
        summary = {
            'file_name': file_path.name,
            'test_date': datetime.now().isoformat(),
            'total_templates': 0,
            'passed': 0,
            'failed': 0,
            'results_by_category': {}
        }
        
        for template in templates:
            if template.get('routing_type') != 'sql':
                continue
            
            template_id = template.get('template_id')
            print(f"  Testing {template_id}...", end='')
            
            # Test template
            success, query, message, query_results = self.executor.test_template(template)
            
            result = {
                'template_id': template_id,
                'category': template.get('template_category'),
                'natural_questions': template.get('query_info', {}).get('natural_questions', []),
                'success': success,
                'message': message,
                'query': query,
                'sql_query': template.get('sql_template', {}).get('query', ''),
                'result_count': len(query_results) if success else 0,
                'sample_results': query_results[:3] if success else []
            }
            
            results.append(result)
            summary['total_templates'] += 1
            
            if success:
                summary['passed'] += 1
                print(f" ✓ ({result['result_count']} rows)")
            else:
                summary['failed'] += 1
                print(f" ✗")
            
            # Group by category
            category = result['category']
            if category not in summary['results_by_category']:
                summary['results_by_category'][category] = {
                    'total': 0, 'passed': 0, 'failed': 0
                }
            summary['results_by_category'][category]['total'] += 1
            if result['success']:
                summary['results_by_category'][category]['passed'] += 1
            else:
                summary['results_by_category'][category]['failed'] += 1
        
        # Generate markdown report
        self.create_individual_report(file_path.stem, results, summary)
        return summary
    
    def create_individual_report(self, file_stem: str, results: List[Dict], summary: Dict):
        """Create individual markdown report for a single file"""
        md_path = self.output_dir / f"{file_stem}_test_report.md"
        
        with open(md_path, 'w', encoding='utf-8') as f:
            # Header
            f.write(f"# {summary['file_name']} Test Report\n\n")
            f.write(f"**Test Date**: {summary['test_date']}\n")
            f.write(f"**Database**: {self.db_path}\n\n")
            
            # Summary
            f.write("## Summary\n\n")
            f.write(f"- **Total Templates**: {summary['total_templates']}\n")
            f.write(f"- **Passed**: {summary['passed']} ({summary['passed']/max(summary['total_templates'],1)*100:.1f}%)\n")
            f.write(f"- **Failed**: {summary['failed']}\n\n")
            
            # Category breakdown
            if summary['results_by_category']:
                f.write("### Results by Category\n\n")
                f.write("| Category | Total | Passed | Failed | Success Rate |\n")
                f.write("|----------|-------|---------|---------|-------------|\n")
                for category, stats in summary['results_by_category'].items():
                    success_rate = stats['passed'] / stats['total'] * 100
                    f.write(f"| {category} | {stats['total']} | {stats['passed']} | {stats['failed']} | {success_rate:.1f}% |\n")
                f.write("\n")
            
            # Detailed results
            f.write("## Detailed Results\n\n")
            
            # Successful queries
            successful = [r for r in results if r['success']]
            if successful:
                f.write("### ✓ Successful Queries\n\n")
                for result in successful:
                    f.write(f"#### {result['template_id']} ({result['category']})\n\n")
                    f.write(f"**Results**: {result['result_count']} rows\n\n")
                    
                    if result['natural_questions']:
                        f.write("**Natural Questions**:\n")
                        for q in result['natural_questions'][:3]:  # Show first 3
                            f.write(f"- {q}\n")
                        if len(result['natural_questions']) > 3:
                            f.write(f"- ... and {len(result['natural_questions']) - 3} more\n")
                        f.write("\n")
                    
                    if result['sample_results'] and result['result_count'] > 0:
                        f.write("**Sample Results**:\n\n")
                        first_result = result['sample_results'][0]
                        if isinstance(first_result, dict):
                            # Table header
                            columns = list(first_result.keys())[:5]  # Show max 5 columns
                            f.write("| " + " | ".join(columns) + " |\n")
                            f.write("|" + "|".join(["---"] * len(columns)) + "|\n")
                            
                            # Table rows (max 3)
                            for row in result['sample_results'][:3]:
                                values = []
                                for col in columns:
                                    val = str(row.get(col, ''))
                                    if len(val) > 50:
                                        val = val[:47] + "..."
                                    values.append(val)
                                f.write("| " + " | ".join(values) + " |\n")
                        f.write("\n")
                    
                    f.write("---\n\n")
            
            # Failed queries
            failed = [r for r in results if not r['success']]
            if failed:
                f.write("### ✗ Failed Queries\n\n")
                for result in failed:
                    f.write(f"#### {result['template_id']} ({result['category']})\n\n")
                    f.write(f"**Error**: {result['message']}\n\n")
                    
                    if result['natural_questions']:
                        f.write("**Natural Questions**:\n")
                        for q in result['natural_questions'][:3]:
                            f.write(f"- {q}\n")
                        if len(result['natural_questions']) > 3:
                            f.write(f"- ... and {len(result['natural_questions']) - 3} more\n")
                        f.write("\n")
                    
                    # Show SQL query for debugging
                    if result['sql_query']:
                        f.write("**SQL Query**:\n```sql\n")
                        # Truncate very long queries
                        if len(result['sql_query']) > 500:
                            f.write(result['sql_query'][:500] + "...\n")
                        else:
                            f.write(result['sql_query'] + "\n")
                        f.write("```\n\n")
                    
                    f.write("---\n\n")
            
            # Footer
            f.write("\n## Test Configuration\n\n")
            f.write(f"- **File**: {summary['file_name']}\n")
            f.write(f"- **Test Date**: {summary['test_date']}\n")
            f.write(f"- **Database Path**: {self.db_path}\n")
    
    def test_all_files(self, template_dir: str):
        """Test all template files and generate individual reports"""
        template_files = sorted(Path(template_dir).glob('query_templates_group_*.json'))
        
        all_summaries = []
        
        print("="*80)
        print("TESTING TEMPLATES - INDIVIDUAL REPORTS")
        print("="*80)
        
        for file_path in template_files:
            print(f"\nTesting {file_path.name}...")
            summary = self.test_single_file(file_path)
            all_summaries.append(summary)
            
            print(f"  Summary: {summary['passed']}/{summary['total_templates']} passed ({summary['passed']/max(summary['total_templates'],1)*100:.1f}%)")
            print(f"  Report saved: {file_path.stem}_test_report.md")
        
        # Create overall summary
        self.create_overall_summary(all_summaries)
        
        return all_summaries
    
    def create_overall_summary(self, summaries: List[Dict]):
        """Create an overall summary report"""
        total_templates = sum(s['total_templates'] for s in summaries)
        total_passed = sum(s['passed'] for s in summaries)
        total_failed = sum(s['failed'] for s in summaries)
        
        md_path = self.output_dir / "test_results_summary_report.md"
        
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write("# IACSGRAPH Query Templates - Overall Test Summary\n\n")
            f.write(f"**Test Date**: {datetime.now().isoformat()}\n\n")
            
            f.write("## Overall Statistics\n\n")
            f.write(f"- **Total Files Tested**: {len(summaries)}\n")
            f.write(f"- **Total Templates**: {total_templates}\n")
            f.write(f"- **Total Passed**: {total_passed} ({total_passed/max(total_templates,1)*100:.1f}%)\n")
            f.write(f"- **Total Failed**: {total_failed}\n\n")
            
            f.write("## File-by-File Summary\n\n")
            f.write("| File | Total | Passed | Failed | Success Rate | Report |\n")
            f.write("|------|-------|---------|---------|-------------|--------|\n")
            
            for summary in summaries:
                success_rate = summary['passed'] / max(summary['total_templates'], 1) * 100
                report_link = f"[View](./{Path(summary['file_name']).stem}_test_report.md)"
                f.write(f"| {summary['file_name']} | {summary['total_templates']} | ")
                f.write(f"{summary['passed']} | {summary['failed']} | {success_rate:.1f}% | {report_link} |\n")
            
            f.write("\n## Individual Reports\n\n")
            f.write("Detailed test reports for each file:\n\n")
            for summary in summaries:
                f.write(f"- [{summary['file_name']}](./{Path(summary['file_name']).stem}_test_report.md)\n")

def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python test_individual_reports.py <database_path> [output_dir]")
        sys.exit(1)
    
    db_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "modules/templates/test_results"
    template_dir = "/home/kimghw/IACSGRAPH/modules/templates/data/query_templates_split"
    
    tester = IndividualTemplateTest(db_path, output_dir)
    summaries = tester.test_all_files(template_dir)
    
    print("\n" + "="*80)
    print("ALL TESTS COMPLETED")
    print("="*80)
    print(f"Reports saved to: {output_dir}")
    print(f"- Individual reports: query_templates_group_*_test_report.md")
    print(f"- Summary report: test_results_summary_report.md")

if __name__ == "__main__":
    main()