"""
Multi-Query Executor for handling array parameters
Executes multiple queries and merges results with deduplication
"""

import logging
from typing import List, Dict, Any, Set, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json

logger = logging.getLogger(__name__)


class MultiQueryExecutor:
    """Handles execution of multiple queries with result merging"""
    
    def __init__(self, db_connector, max_workers: int = 5):
        """
        Initialize multi-query executor
        
        Args:
            db_connector: Database connector instance
            max_workers: Maximum number of parallel query executions
        """
        self.db_connector = db_connector
        self.max_workers = max_workers
    
    def execute_queries(
        self, 
        queries: List[str], 
        dedupe_columns: Optional[List[str]] = None,
        parallel: bool = True
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Execute multiple queries and merge results
        
        Args:
            queries: List of SQL queries to execute
            dedupe_columns: Columns to use for deduplication (e.g., ['id'], ['agenda_code'])
            parallel: Whether to execute queries in parallel
            
        Returns:
            tuple: (merged_results, metadata)
                - merged_results: Deduplicated and merged results
                - metadata: Execution metadata (query count, result counts, etc.)
        """
        if not queries:
            return [], {"query_count": 0, "total_results": 0}
        
        # Execute queries
        if parallel and len(queries) > 1:
            all_results = self._execute_parallel(queries)
        else:
            all_results = self._execute_sequential(queries)
        
        # Merge and deduplicate results
        merged_results = self._merge_results(all_results, dedupe_columns)
        
        # Prepare metadata
        metadata = {
            "query_count": len(queries),
            "results_per_query": [len(results) for results in all_results],
            "total_results_before_dedup": sum(len(results) for results in all_results),
            "total_results_after_dedup": len(merged_results),
            "execution_method": "parallel" if parallel else "sequential"
        }
        
        return merged_results, metadata
    
    def _execute_sequential(self, queries: List[str]) -> List[List[Dict[str, Any]]]:
        """Execute queries sequentially"""
        all_results = []
        
        for i, query in enumerate(queries):
            try:
                logger.debug(f"Executing query {i+1}/{len(queries)}")
                results = self.db_connector.execute_query(query)
                all_results.append(results)
            except Exception as e:
                logger.error(f"Error executing query {i+1}: {e}")
                all_results.append([])  # Add empty results for failed query
        
        return all_results
    
    def _execute_parallel(self, queries: List[str]) -> List[List[Dict[str, Any]]]:
        """Execute queries in parallel"""
        results_map = {}
        
        with ThreadPoolExecutor(max_workers=min(self.max_workers, len(queries))) as executor:
            # Submit all queries
            future_to_index = {
                executor.submit(self._execute_single_query, query): i 
                for i, query in enumerate(queries)
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    results = future.result()
                    results_map[index] = results
                except Exception as e:
                    logger.error(f"Error in parallel execution of query {index+1}: {e}")
                    results_map[index] = []
        
        # Return results in original order
        return [results_map[i] for i in range(len(queries))]
    
    def _execute_single_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute a single query (for parallel execution)"""
        try:
            return self.db_connector.execute_query(query)
        except Exception as e:
            logger.error(f"Query execution error: {e}")
            raise
    
    def _merge_results(
        self, 
        all_results: List[List[Dict[str, Any]]], 
        dedupe_columns: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Merge and deduplicate results"""
        if not all_results:
            return []
        
        # If no deduplication columns specified, try to infer from data
        if not dedupe_columns:
            dedupe_columns = self._infer_dedupe_columns(all_results)
        
        # Use a set to track seen records
        seen_hashes: Set[str] = set()
        merged_results: List[Dict[str, Any]] = []
        
        for results in all_results:
            for record in results:
                # Create hash for deduplication
                record_hash = self._get_record_hash(record, dedupe_columns)
                
                if record_hash not in seen_hashes:
                    seen_hashes.add(record_hash)
                    merged_results.append(record)
        
        return merged_results
    
    def _infer_dedupe_columns(self, all_results: List[List[Dict[str, Any]]]) -> List[str]:
        """Infer deduplication columns from result data"""
        # Common ID columns to check
        common_id_columns = [
            'id', 'ID', 'agenda_code', 'agenda_base_version', 
            'email_id', 'template_id', 'organization', 'panel'
        ]
        
        # Get columns from first non-empty result
        for results in all_results:
            if results:
                available_columns = list(results[0].keys())
                # Use the first common ID column found
                for col in common_id_columns:
                    if col in available_columns:
                        return [col]
                # If no common ID found, use all columns
                return available_columns
        
        return []
    
    def _get_record_hash(self, record: Dict[str, Any], dedupe_columns: List[str]) -> str:
        """Get hash for a record based on deduplication columns"""
        if not dedupe_columns:
            # Hash entire record if no specific columns
            hash_data = json.dumps(record, sort_keys=True, default=str)
        else:
            # Hash only specified columns
            hash_data = json.dumps(
                {col: record.get(col) for col in dedupe_columns},
                sort_keys=True,
                default=str
            )
        
        return hashlib.md5(hash_data.encode()).hexdigest()
    
    def execute_with_array_params(
        self,
        sql_template: str,
        params: Dict[str, Any],
        array_param_names: List[str],
        dedupe_columns: Optional[List[str]] = None
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Execute query with array parameters by generating multiple queries
        
        Args:
            sql_template: SQL template with :param placeholders
            params: Parameter values (including arrays)
            array_param_names: Names of parameters that are arrays
            dedupe_columns: Columns for deduplication
            
        Returns:
            tuple: (results, metadata)
        """
        # Generate queries for each combination of array values
        queries = self._generate_array_queries(sql_template, params, array_param_names)
        
        # Execute and merge
        return self.execute_queries(queries, dedupe_columns)
    
    def _generate_array_queries(
        self,
        sql_template: str,
        params: Dict[str, Any],
        array_param_names: List[str]
    ) -> List[str]:
        """Generate multiple queries for array parameters"""
        queries = []
        
        # For simplicity, handle single array parameter
        # Future enhancement: handle multiple array parameters with cartesian product
        array_params = {name: params[name] for name in array_param_names 
                       if name in params and isinstance(params[name], list)}
        
        if not array_params:
            # No array parameters, return single query
            query = self._substitute_params(sql_template, params)
            return [query]
        
        if len(array_params) == 1:
            # Single array parameter - generate one query per value
            param_name, values = list(array_params.items())[0]
            
            for value in values:
                query_params = params.copy()
                query_params[param_name] = value
                query = self._substitute_params(sql_template, query_params)
                queries.append(query)
        else:
            # Multiple array parameters - for now, just use first value of each
            # TODO: Implement cartesian product for full coverage
            query_params = params.copy()
            for param_name, values in array_params.items():
                query_params[param_name] = values[0] if values else None
            
            query = self._substitute_params(sql_template, query_params)
            queries.append(query)
        
        return queries
    
    def _substitute_params(self, sql_template: str, params: Dict[str, Any]) -> str:
        """Simple parameter substitution"""
        sql = sql_template
        
        for param_name, value in params.items():
            placeholder = f":{param_name}"
            
            if placeholder in sql:
                if value is None:
                    sql = sql.replace(placeholder, "NULL")
                elif isinstance(value, str):
                    sql = sql.replace(placeholder, f"'{value}'")
                elif isinstance(value, (int, float)):
                    sql = sql.replace(placeholder, str(value))
                else:
                    sql = sql.replace(placeholder, f"'{str(value)}'")
        
        return sql