"""Simplified SQL templates that work with actual schema"""

SIMPLE_TEMPLATES = [
    {
        "template_id": "all_agendas",
        "natural_questions": "모든 아젠다 보여줘",
        "sql_query": """
            SELECT 
                agenda_code,
                subject,
                sent_time,
                decision_status
            FROM agenda_chair
            ORDER BY sent_time DESC
            LIMIT 20
        """,
        "sql_query_with_parameters": """
            SELECT 
                agenda_code,
                subject,
                sent_time,
                decision_status
            FROM agenda_chair
            ORDER BY sent_time DESC
            LIMIT {limit}
        """,
        "keywords": ["아젠다", "모든", "전체", "목록", "all", "agenda"],
        "category": "list",
        "required_params": [],
        "default_params": {},
        "query_filter": ["limit"],
        "related_tables": ["agenda_chair"],
        "to_agent_prompt": null
    },
    {
        "template_id": "recent_agendas_simple",
        "natural_questions": "최근 아젠다",
        "sql_query": """
            SELECT 
                agenda_code,
                subject,
                sent_time,
                decision_status
            FROM agenda_chair
            WHERE sent_time >= datetime('now', '-30 days')
            ORDER BY sent_time DESC
            LIMIT 20
        """,
        "sql_query_with_parameters": """
            SELECT 
                agenda_code,
                subject,
                sent_time,
                decision_status
            FROM agenda_chair
            WHERE sent_time >= datetime('now', '-{days} days')
            ORDER BY sent_time DESC
            LIMIT {limit}
        """,
        "keywords": ["최근", "recent", "아젠다", "agenda"],
        "category": "recent",
        "required_params": [],
        "default_params": {},
        "query_filter": ["days", "limit"],
        "related_tables": ["agenda_chair"],
        "to_agent_prompt": null
    },
    {
        "template_id": "kr_response_rate_fixed",
        "natural_questions": "KR 응답률",
        "sql_query": """
            WITH org_responses AS (
                SELECT 
                    COUNT(CASE WHEN arc.KR IS NOT NULL AND arc.KR != '' THEN 1 END) as responded,
                    COUNT(*) as total
                FROM agenda_chair ac
                JOIN agenda_responses_content arc ON ac.agenda_base_version = arc.agenda_base_version
                WHERE ac.sent_time >= datetime('now', '-30 days')
            )
            SELECT 
                'KR' as organization,
                responded,
                total,
                ROUND(CAST(responded AS FLOAT) / total * 100, 2) as response_rate
            FROM org_responses
        """,
        "sql_query_with_parameters": """
            WITH org_responses AS (
                SELECT 
                    COUNT(CASE WHEN arc.KR IS NOT NULL AND arc.KR != '' THEN 1 END) as responded,
                    COUNT(*) as total
                FROM agenda_chair ac
                JOIN agenda_responses_content arc ON ac.agenda_base_version = arc.agenda_base_version
                WHERE ac.sent_time >= datetime('now', '-{days} days')
            )
            SELECT 
                'KR' as organization,
                responded,
                total,
                ROUND(CAST(responded AS FLOAT) / total * 100, 2) as response_rate
            FROM org_responses
        """,
        "keywords": ["KR", "응답률", "response", "rate"],
        "category": "statistics",
        "required_params": [],
        "default_params": {},
        "query_filter": ["days"],
        "related_tables": ["agenda_chair", "agenda_responses_content"],
        "to_agent_prompt": null
    }
]
