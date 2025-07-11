"""Simplified SQL templates that work with actual schema"""

SIMPLE_TEMPLATES = [
    {
        "id": "all_agendas",
        "natural_query": "모든 아젠다 보여줘",
        "sql_template": """
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
        "required_params": [],
        "optional_params": ["limit"],
        "category": "list"
    },
    {
        "id": "recent_agendas_simple",
        "natural_query": "최근 아젠다",
        "sql_template": """
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
        "required_params": [],
        "optional_params": ["days", "limit"],
        "category": "recent"
    },
    {
        "id": "kr_response_rate_fixed",
        "natural_query": "KR 응답률",
        "sql_template": """
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
        "required_params": [],
        "optional_params": ["days"],
        "category": "statistics"
    }
]
