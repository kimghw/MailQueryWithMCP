#!/usr/bin/env python3
"""
Test templates and generate individual markdown reports for each file
"""

import json
import sqlite3
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Set

from .query_executor import QueryExecutor

class IndividualTemplateTest:
    def __init__(self, db_path: str, output_dir: str = "modules/templates/test_results"):
        self.db_path = db_path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.executor = QueryExecutor(db_path)
    
    def extract_placeholders(self, sql_query: str) -> Set[str]:
        """Extract placeholders from SQL query"""
        # Find placeholders in both old format {placeholder_name} and new format :param_name
        old_format = re.findall(r'\{([^}]+)\}', sql_query)
        new_format = re.findall(r':(\w+)', sql_query)
        # Combine both formats and remove duplicates
        return set(old_format + new_format)
        
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
            
            # Extract parameter information
            parameters = template.get('parameters', [])
            required_params = [p for p in parameters if p.get('required', False)]
            optional_params = [p for p in parameters if not p.get('required', False)]
            
            # Extract placeholders from SQL query
            sql_query = template.get('sql_template', {}).get('query', '')
            placeholders = self.extract_placeholders(sql_query)
            
            result = {
                'template_id': template_id,
                'category': template.get('template_category'),
                'natural_questions': template.get('query_info', {}).get('natural_questions', []),
                'success': success,
                'message': message,
                'query': query,
                'sql_query': sql_query,
                'result_count': len(query_results) if success else 0,
                'sample_results': query_results[:3] if success else [],
                'parameters': parameters,
                'required_params': required_params,
                'optional_params': optional_params,
                'placeholders': sorted(list(placeholders)),
                'routing_type': template.get('routing_type', 'sql'),
                'to_agent': template.get('to_agent', '')
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
            f.write(f"# {summary['file_name']} 테스트 보고서\n\n")
            f.write(f"**테스트 일시**: {summary['test_date']}\n")
            f.write(f"**데이터베이스**: {self.db_path}\n\n")
            
            # Summary
            f.write("## 요약\n\n")
            f.write(f"- **전체 템플릿 수**: {summary['total_templates']}\n")
            f.write(f"- **성공**: {summary['passed']} ({summary['passed']/max(summary['total_templates'],1)*100:.1f}%)\n")
            f.write(f"- **실패**: {summary['failed']}\n\n")
            
            # Category breakdown
            if summary['results_by_category']:
                f.write("### 카테고리별 결과\n\n")
                f.write("| 카테고리 | 전체 | 성공 | 실패 | 성공률 |\n")
                f.write("|----------|------|------|------|--------|\n")
                for category, stats in summary['results_by_category'].items():
                    success_rate = stats['passed'] / stats['total'] * 100
                    f.write(f"| {category} | {stats['total']} | {stats['passed']} | {stats['failed']} | {success_rate:.1f}% |\n")
                f.write("\n")
            
            # Detailed results
            f.write("## 상세 결과\n\n")
            
            # Write all templates (both successful and failed)
            for idx, result in enumerate(results, 1):
                status_icon = "✅" if result['success'] else "❌"
                f.write(f"### {idx}. {status_icon} {result['template_id']}\n\n")
                
                # Basic information
                f.write(f"**카테고리**: {result['category']}\n")
                f.write(f"**상태**: {'성공' if result['success'] else '실패'}\n")
                f.write(f"**Note**: \n")
                f.write(f"**라우팅 타입**: {result['routing_type']}\n")
                if result.get('to_agent'):
                    f.write(f"**에이전트 처리**: {result['to_agent'][:150]}{'...' if len(result['to_agent']) > 150 else ''}\n")
                
                # Natural questions
                if result['natural_questions']:
                    f.write("\n**자연어 질의**:\n")
                    for i, q in enumerate(result['natural_questions'][:3], 1):
                        f.write(f"{i}. {q}\n")
                    if len(result['natural_questions']) > 3:
                        f.write(f"   ... 외 {len(result['natural_questions']) - 3}개\n")
                
                # Parameters
                f.write("\n**파라미터 정보**:\n")
                if result['required_params']:
                    f.write("- 필수 파라미터:\n")
                    for param in result['required_params']:
                        f.write(f"  - `{param['name']}` ({param.get('type', 'string')})")
                        if param.get('default'):
                            f.write(f" - 기본값: {param['default']}")
                        f.write("\n")
                else:
                    f.write("- 필수 파라미터: 없음\n")
                
                if result['optional_params']:
                    f.write("- 선택 파라미터:\n")
                    for param in result['optional_params']:
                        f.write(f"  - `{param['name']}` ({param.get('type', 'string')})")
                        if param.get('default'):
                            f.write(f" - 기본값: {param['default']}")
                        f.write("\n")
                
                # Placeholders
                if result['placeholders']:
                    f.write(f"\n**SQL 파라미터**: `{', '.join([':' + p for p in result['placeholders']])}`\n")
                else:
                    f.write("\n**SQL 파라미터**: 없음\n")
                
                # SQL Query
                f.write("\n**SQL 쿼리**:\n```sql\n")
                # Show first 300 chars of query
                query_preview = result['sql_query'][:300]
                if len(result['sql_query']) > 300:
                    query_preview += "..."
                f.write(query_preview + "\n")
                f.write("```\n")
                
                # Test results
                if result['success']:
                    f.write(f"\n**실행 결과**: {result['result_count']}개 행 반환\n")
                    
                    if result['sample_results'] and result['result_count'] > 0:
                        f.write("\n**샘플 데이터** (최대 3행):\n\n")
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
                                    if len(val) > 30:
                                        val = val[:27] + "..."
                                    values.append(val)
                                f.write("| " + " | ".join(values) + " |\n")
                            
                            if len(columns) < len(first_result.keys()):
                                f.write(f"\n*참고: 전체 {len(first_result.keys())}개 컬럼 중 {len(columns)}개만 표시*\n")
                else:
                    f.write(f"\n**오류 내용**: {result['message']}\n")
                    
                    # Show the attempted query for debugging
                    if result['query']:
                        f.write("\n**실행 시도한 쿼리**:\n```sql\n")
                        query_preview = result['query'][:500]
                        if len(result['query']) > 500:
                            query_preview += "..."
                        f.write(query_preview + "\n")
                        f.write("```\n")
                
                f.write("\n---\n\n")
            
            # Footer
            f.write("\n## 테스트 설정\n\n")
            f.write(f"- **파일**: {summary['file_name']}\n")
            f.write(f"- **테스트 일시**: {summary['test_date']}\n")
            f.write(f"- **데이터베이스 경로**: {self.db_path}\n")
    
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
            f.write("# IACSGRAPH 쿼리 템플릿 - 전체 테스트 요약\n\n")
            f.write(f"**테스트 일시**: {datetime.now().isoformat()}\n\n")
            
            f.write("## 전체 통계\n\n")
            f.write(f"- **테스트한 파일 수**: {len(summaries)}\n")
            f.write(f"- **전체 템플릿 수**: {total_templates}\n")
            f.write(f"- **성공**: {total_passed} ({total_passed/max(total_templates,1)*100:.1f}%)\n")
            f.write(f"- **실패**: {total_failed}\n\n")
            
            f.write("## 파일별 요약\n\n")
            f.write("| 파일 | 전체 | 성공 | 실패 | 성공률 | 보고서 |\n")
            f.write("|------|------|------|------|--------|--------|\n")
            
            for summary in summaries:
                success_rate = summary['passed'] / max(summary['total_templates'], 1) * 100
                report_link = f"[보기](./{Path(summary['file_name']).stem}_test_report.md)"
                f.write(f"| {summary['file_name']} | {summary['total_templates']} | ")
                f.write(f"{summary['passed']} | {summary['failed']} | {success_rate:.1f}% | {report_link} |\n")
            
            f.write("\n## 개별 보고서\n\n")
            f.write("각 파일의 상세 테스트 보고서:\n\n")
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