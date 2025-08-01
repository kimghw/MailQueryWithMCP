"""
Enhanced Query Assistant with simplified SQL generation and multi-query support
This is a demonstration of how to integrate the new components
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

# Import new components
try:
    from .services.sql_generator_v2 import SimplifiedSQLGenerator
    from .services.multi_query_executor import MultiQueryExecutor
except ImportError:
    # For direct execution
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from modules.query_assistant.services.sql_generator_v2 import SimplifiedSQLGenerator
    from modules.query_assistant.services.multi_query_executor import MultiQueryExecutor

logger = logging.getLogger(__name__)


class QueryAssistantV2:
    """Enhanced Query Assistant with multi-query support"""
    
    def __init__(self, db_connector, vector_store, config: Optional[Dict[str, Any]] = None):
        """
        Initialize enhanced query assistant
        
        Args:
            db_connector: Database connector instance
            vector_store: Vector store for template search
            config: Optional configuration
        """
        self.db_connector = db_connector
        self.vector_store = vector_store
        self.config = config or {}
        
        # Initialize new components
        self.sql_generator = SimplifiedSQLGenerator()
        self.multi_query_executor = MultiQueryExecutor(
            db_connector,
            max_workers=self.config.get('max_parallel_queries', 5)
        )
        
        logger.info("Initialized QueryAssistantV2 with simplified SQL generator")
    
    def process_query_with_multi_support(
        self,
        user_query: str,
        mcp_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process query with support for multi-query execution
        
        Args:
            user_query: Natural language query
            mcp_params: MCP extracted parameters
            
        Returns:
            Query results with metadata
        """
        try:
            # 1. Search for matching template
            template_result = self._find_best_template(user_query)
            if not template_result:
                return {
                    'success': False,
                    'error': 'No matching template found',
                    'query': user_query
                }
            
            template = template_result['template']
            
            # 2. Generate SQL with multi-query support
            sql_template = template.get('sql_template', {}).get('query', '')
            template_params = template.get('parameters', [])
            
            primary_sql, merged_params, additional_queries = self.sql_generator.generate_sql(
                sql_template,
                template_params,
                mcp_params or {},
                {},  # synonym_params
                template.get('template_defaults', {})
            )
            
            # 3. Execute queries
            if additional_queries:
                # Multi-query execution
                all_queries = [primary_sql] + additional_queries
                
                # Determine deduplication columns based on template
                dedupe_columns = self._get_dedupe_columns(template)
                
                results, metadata = self.multi_query_executor.execute_queries(
                    all_queries,
                    dedupe_columns=dedupe_columns,
                    parallel=True
                )
                
                execution_info = {
                    'multi_query': True,
                    'query_count': metadata['query_count'],
                    'total_results': metadata['total_results_after_dedup'],
                    'results_per_query': metadata['results_per_query']
                }
            else:
                # Single query execution
                results = self.db_connector.execute_query(primary_sql)
                execution_info = {
                    'multi_query': False,
                    'query_count': 1,
                    'total_results': len(results)
                }
            
            # 4. Format response
            response = {
                'success': True,
                'results': results,
                'metadata': {
                    'template_id': template.get('template_id'),
                    'template_category': template.get('template_category'),
                    'generated_sql': primary_sql,
                    'parameters': merged_params,
                    'execution_info': execution_info,
                    'timestamp': datetime.now().isoformat()
                }
            }
            
            # Add additional queries info if multi-query
            if additional_queries:
                response['metadata']['additional_queries'] = additional_queries
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return {
                'success': False,
                'error': str(e),
                'query': user_query
            }
    
    def _find_best_template(self, user_query: str) -> Optional[Dict[str, Any]]:
        """Find best matching template for user query"""
        # Simplified template search - in real implementation this would use vector store
        # This is just a placeholder
        search_results = self.vector_store.search(
            query=user_query,
            limit=1,
            score_threshold=0.7
        )
        
        if search_results:
            return {
                'template': search_results[0].template,
                'score': search_results[0].score
            }
        
        return None
    
    def _get_dedupe_columns(self, template: Dict[str, Any]) -> List[str]:
        """Get deduplication columns based on template"""
        # Determine dedupe columns based on template category and tables
        template_category = template.get('template_category', '')
        related_tables = template.get('related_tables', [])
        
        # Common deduplication strategies by category
        if 'agenda' in template_category or 'agenda_chair' in related_tables:
            return ['agenda_base_version']
        elif 'email' in template_category:
            return ['email_id']
        elif 'organization' in template_category:
            return ['organization', 'agenda_base_version']
        else:
            # Default: use ID if available
            return ['id']
    
    def test_multi_query_execution(self):
        """Test method to demonstrate multi-query execution"""
        print("\n=== Testing Multi-Query Execution ===")
        
        # Test case 1: Multiple keywords
        test_params = {
            'extracted_keywords': ['IMO', 'MEPC', 'Safety'],
            'extracted_period': {
                'start': '2025-01-01',
                'end': '2025-07-31'
            }
        }
        
        sql_template = """
        SELECT agenda_code, subject, keywords, sent_time 
        FROM agenda_chair 
        WHERE keywords LIKE '%' || :keyword || '%'
        AND sent_time >= :period_start
        ORDER BY sent_time DESC
        """
        
        template_params = [
            {'name': 'keyword', 'type': 'array'},
            {'name': 'period_start', 'type': 'datetime', 'default': "datetime('now', '-90 days')"}
        ]
        
        # Generate queries
        primary_sql, params, additional = self.sql_generator.generate_sql(
            sql_template,
            template_params,
            test_params,
            {},
            {}
        )
        
        print(f"Generated {1 + len(additional)} queries for keywords: {params['keyword']}")
        print(f"\nPrimary query (keyword='IMO'):")
        print(primary_sql)
        
        if additional:
            print(f"\nAdditional queries:")
            for i, query in enumerate(additional):
                keyword = params['keyword'][i+1]
                print(f"\nQuery {i+2} (keyword='{keyword}'):")
                print(query)
        
        # Simulate execution results
        print("\n=== Execution Results ===")
        print("Query 1: Found 15 results for 'IMO'")
        print("Query 2: Found 8 results for 'MEPC'") 
        print("Query 3: Found 12 results for 'Safety'")
        print("\nAfter deduplication: 28 unique results")
        print("(7 results contained multiple keywords)")


def demonstrate_usage():
    """Demonstrate how to use the enhanced query assistant"""
    
    # This is a demonstration - in real usage you would have actual instances
    print("Enhanced Query Assistant V2 - Usage Examples")
    print("=" * 60)
    
    print("\n1. Simple Query (Single Parameter):")
    print("   User: 'Show me DNV agendas from last month'")
    print("   → Generates single SQL query with organization='DNV' and period")
    
    print("\n2. Multi-Keyword Query:")
    print("   User: 'Find agendas about IMO, MEPC, and Safety regulations'")
    print("   → Generates 3 separate queries, one for each keyword")
    print("   → Results are merged and deduplicated")
    
    print("\n3. Complex Multi-Organization Query:")
    print("   User: 'Compare responses from KR, DNV, and ABS'")
    print("   → Could generate multiple queries or use CASE statement")
    print("   → Depends on template configuration")
    
    print("\n4. Benefits of Simplified Approach:")
    print("   ✓ No complex SQL builder logic")
    print("   ✓ Clear parameter substitution with :param syntax")
    print("   ✓ Automatic multi-query handling for arrays")
    print("   ✓ Parallel execution for better performance")
    print("   ✓ Automatic result deduplication")


if __name__ == "__main__":
    # Run demonstration
    demonstrate_usage()
    
    # If you want to test with mock objects
    class MockConnector:
        def execute_query(self, sql):
            return [{'id': 1, 'result': 'mock'}]
    
    class MockVectorStore:
        def search(self, **kwargs):
            return []
    
    assistant = QueryAssistantV2(MockConnector(), MockVectorStore())
    assistant.test_multi_query_execution()