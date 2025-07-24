"""Default templates for Query Assistant"""

from typing import List, Dict, Any

def get_templates() -> List[Dict[str, Any]]:
    """Get default query templates"""
    return [
        {
            "template_id": "agenda_search_basic",
            "template_name": "Basic Agenda Search",
            "description": "Search for agenda items by ID or keywords",
            "sql_query": "SELECT * FROM mail_history WHERE agenda_id LIKE '%' || :agenda_id || '%'",
            "sql_query_with_parameters": "SELECT * FROM mail_history WHERE agenda_id LIKE '%' || :agenda_id || '%'",
            "required_params": ["agenda_id"],
            "query_filter": ["limit"],
            "default_params": {"limit": 10},
            "category": "search"
        },
        {
            "template_id": "org_responses_date_range",
            "template_name": "Organization Responses by Date Range",
            "description": "Find responses from specific organization within date range",
            "sql_query": """
                SELECT * FROM mail_history 
                WHERE organization_code = :organization_code 
                AND received_date BETWEEN :start_date AND :end_date
                ORDER BY received_date DESC
            """,
            "sql_query_with_parameters": """
                SELECT * FROM mail_history 
                WHERE organization_code = :organization_code 
                AND received_date BETWEEN :start_date AND :end_date
                ORDER BY received_date DESC
            """,
            "required_params": ["organization_code", "start_date", "end_date"],
            "query_filter": ["status", "limit"],
            "default_params": {"limit": 100},
            "category": "filter"
        },
        {
            "template_id": "keyword_search",
            "template_name": "Keyword Search in Emails",
            "description": "Search emails by keywords in subject or body",
            "sql_query": """
                SELECT * FROM mail_history 
                WHERE subject LIKE '%' || :keyword || '%' 
                OR body LIKE '%' || :keyword || '%'
                ORDER BY received_date DESC
            """,
            "sql_query_with_parameters": """
                SELECT * FROM mail_history 
                WHERE subject LIKE '%' || :keyword || '%' 
                OR body LIKE '%' || :keyword || '%'
                ORDER BY received_date DESC
                LIMIT :limit
            """,
            "required_params": ["keyword"],
            "query_filter": ["limit", "days"],
            "default_params": {"limit": 50},
            "category": "search"
        }
    ]