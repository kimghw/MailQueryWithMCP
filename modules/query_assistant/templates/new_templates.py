"""New format SQL templates for IACSGraph Email Dashboard"""

from typing import List, Dict, Any

TEMPLATES: List[Dict[str, Any]] = [
    # Agenda Summary Templates
    {
        "template_id": "recent_agendas_by_period",
        "natural_questions": "최근 {period} 주요 아젠다는 무엇인가?",
        "sql_query": """
            SELECT 
                ac.agenda_code,
                ac.subject,
                ac.sent_time,
                ac.decision_status,
                COUNT(DISTINCT CASE 
                    WHEN arc.ABS IS NOT NULL OR arc.BV IS NOT NULL OR arc.CCS IS NOT NULL 
                    OR arc.CRS IS NOT NULL OR arc.DNV IS NOT NULL OR arc.IRS IS NOT NULL 
                    OR arc.KR IS NOT NULL OR arc.NK IS NOT NULL OR arc.PRS IS NOT NULL 
                    OR arc.RINA IS NOT NULL OR arc.LR IS NOT NULL 
                    THEN 1 ELSE NULL END) as response_count
            FROM agenda_chair ac
            LEFT JOIN agenda_responses_content arc ON ac.agenda_base_version = arc.agenda_base_version
            WHERE ac.sent_time >= datetime('now', '-30 days')
            GROUP BY ac.agenda_code, ac.subject, ac.sent_time, ac.decision_status
            ORDER BY ac.sent_time DESC
            LIMIT 20
        """,
        "sql_query_with_parameters": """
            SELECT 
                ac.agenda_code,
                ac.subject,
                ac.sent_time,
                ac.decision_status,
                COUNT(DISTINCT CASE 
                    WHEN arc.ABS IS NOT NULL OR arc.BV IS NOT NULL OR arc.CCS IS NOT NULL 
                    OR arc.CRS IS NOT NULL OR arc.DNV IS NOT NULL OR arc.IRS IS NOT NULL 
                    OR arc.KR IS NOT NULL OR arc.NK IS NOT NULL OR arc.PRS IS NOT NULL 
                    OR arc.RINA IS NOT NULL OR arc.LR IS NOT NULL 
                    THEN 1 ELSE NULL END) as response_count
            FROM agenda_chair ac
            LEFT JOIN agenda_responses_content arc ON ac.agenda_base_version = arc.agenda_base_version
            WHERE ac.sent_time >= datetime('now', '-{days} days')
            GROUP BY ac.agenda_code, ac.subject, ac.sent_time, ac.decision_status
            ORDER BY ac.sent_time DESC
            LIMIT {limit}
        """,
        "keywords": ["최근", "아젠다", "주요", "기간", "period", "recent", "agenda"],
        "category": "agenda_summary",
        "required_params": ["period"],
        "default_params": {
            "period": "30일",
            "days": 30,
            "limit": 20,
            "status": "all"
        },
        "query_filter": ["limit", "status"],
        "related_tables": ["agenda_chair", "agenda_responses_content"],
        "to_agent_prompt": None,
        "template_version": "1.0.0",
        "embedding_model": "text-embedding-3-large",
        "embedding_dimension": 3072
    },
    
    # Organization Response Statistics
    {
        "template_id": "org_response_rate",
        "natural_questions": "{organization} 기관의 응답률은 어떻게 되나요?",
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
                    COUNT(CASE WHEN arc.{organization} IS NOT NULL AND arc.{organization} != '' THEN 1 END) as responded,
                    COUNT(*) as total
                FROM agenda_chair ac
                JOIN agenda_responses_content arc ON ac.agenda_base_version = arc.agenda_base_version
                WHERE ac.sent_time >= datetime('now', '-{days} days')
            )
            SELECT 
                '{organization}' as organization,
                responded,
                total,
                ROUND(CAST(responded AS FLOAT) / total * 100, 2) as response_rate
            FROM org_responses
        """,
        "keywords": ["응답률", "기관", "organization", "response", "rate", "통계", "KR", "BV", "CCS", "DNV"],
        "category": "statistics",
        "required_params": ["organization"],
        "default_params": {
            "organization": "KR",
            "days": 30
        },
        "query_filter": ["days"],
        "related_tables": ["agenda_chair", "agenda_responses_content"],
        "to_agent_prompt": None,
        "template_version": "1.0.0",
        "embedding_model": "text-embedding-3-large",
        "embedding_dimension": 3072
    },
    
    # Agenda Decision Status
    {
        "template_id": "agenda_decision_status", 
        "natural_questions": "{status} 상태인 아젠다 목록을 보여주세요",
        "sql_query": """
            SELECT 
                ac.agenda_code,
                ac.subject,
                ac.sent_time,
                ac.decision_status,
                ac.decision_date,
                COUNT(DISTINCT arc.organization) as response_count
            FROM agenda_chair ac
            LEFT JOIN agenda_responses_content arc ON ac.agenda_base_version = arc.agenda_base_version
            WHERE ac.decision_status = 'created'
                AND ac.sent_time >= datetime('now', '-30 days')
            GROUP BY ac.agenda_code, ac.subject, ac.sent_time, ac.decision_status, ac.decision_date
            ORDER BY ac.sent_time DESC
            LIMIT 20
        """,
        "sql_query_with_parameters": """
            SELECT 
                ac.agenda_code,
                ac.subject,
                ac.sent_time,
                ac.decision_status,
                ac.decision_date,
                COUNT(DISTINCT arc.organization) as response_count
            FROM agenda_chair ac
            LEFT JOIN agenda_responses_content arc ON ac.agenda_base_version = arc.agenda_base_version
            WHERE ac.decision_status = '{status}'
                AND ac.sent_time >= datetime('now', '-{days} days')
            GROUP BY ac.agenda_code, ac.subject, ac.sent_time, ac.decision_status, ac.decision_date
            ORDER BY ac.sent_time DESC
            LIMIT {limit}
        """,
        "keywords": ["상태", "status", "결정", "decision", "목록", "list"],
        "category": "agenda_status",
        "required_params": ["status"],
        "default_params": {
            "status": "created",
            "days": 30,
            "limit": 20
        },
        "query_filter": ["days", "limit"],
        "related_tables": ["agenda_chair", "agenda_responses_content"],
        "to_agent_prompt": None,
        "template_version": "1.0.0",
        "embedding_model": "text-embedding-3-large",
        "embedding_dimension": 3072
    },
    
    # Organization-specific Agendas
    {
        "template_id": "org_related_agendas",
        "natural_questions": "{organization}과 관련된 아젠다를 보여주세요",
        "sql_query": """
            SELECT 
                ac.agenda_code,
                ac.subject,
                ac.sent_time,
                ac.decision_status,
                arc.KR as response_content
            FROM agenda_chair ac
            JOIN agenda_responses_content arc ON ac.agenda_base_version = arc.agenda_base_version
            WHERE arc.KR IS NOT NULL
                AND ac.sent_time >= datetime('now', '-30 days')
            ORDER BY ac.sent_time DESC
            LIMIT 20
        """,
        "sql_query_with_parameters": """
            SELECT 
                ac.agenda_code,
                ac.subject,
                ac.sent_time,
                ac.decision_status,
                arc.{organization} as response_content
            FROM agenda_chair ac
            JOIN agenda_responses_content arc ON ac.agenda_base_version = arc.agenda_base_version
            WHERE arc.{organization} IS NOT NULL
                AND ac.sent_time >= datetime('now', '-{days} days')
            ORDER BY ac.sent_time DESC
            LIMIT {limit}
        """,
        "keywords": ["관련", "related", "기관", "organization", "아젠다"],
        "category": "organization_agendas",
        "required_params": ["organization"],
        "default_params": {
            "organization": "KR",
            "days": 30,
            "limit": 20
        },
        "query_filter": ["days", "limit"],
        "related_tables": ["agenda_chair", "agenda_responses_content"],
        "to_agent_prompt": None,
        "template_version": "1.0.0",
        "embedding_model": "text-embedding-3-large",
        "embedding_dimension": 3072
    },
    
    # Response Time Analysis
    {
        "template_id": "response_time_analysis",
        "natural_questions": "평균 응답 시간은 얼마나 되나요?",
        "sql_query": """
            WITH response_times AS (
                SELECT 
                    ac.agenda_code,
                    ac.sent_time,
                    MIN(arc.response_date) as first_response,
                    julianday(MIN(arc.response_date)) - julianday(ac.sent_time) as response_days
                FROM agenda_chair ac
                JOIN agenda_responses_content arc ON ac.agenda_base_version = arc.agenda_base_version
                WHERE arc.response_date IS NOT NULL
                    AND ac.sent_time >= datetime('now', '-30 days')
                GROUP BY ac.agenda_code, ac.sent_time
            )
            SELECT 
                COUNT(*) as total_agendas,
                ROUND(AVG(response_days), 1) as avg_response_days,
                ROUND(MIN(response_days), 1) as min_response_days,
                ROUND(MAX(response_days), 1) as max_response_days
            FROM response_times
        """,
        "sql_query_with_parameters": """
            WITH response_times AS (
                SELECT 
                    ac.agenda_code,
                    ac.sent_time,
                    MIN(arc.response_date) as first_response,
                    julianday(MIN(arc.response_date)) - julianday(ac.sent_time) as response_days
                FROM agenda_chair ac
                JOIN agenda_responses_content arc ON ac.agenda_base_version = arc.agenda_base_version
                WHERE arc.response_date IS NOT NULL
                    AND ac.sent_time >= datetime('now', '-{days} days')
                GROUP BY ac.agenda_code, ac.sent_time
            )
            SELECT 
                COUNT(*) as total_agendas,
                ROUND(AVG(response_days), 1) as avg_response_days,
                ROUND(MIN(response_days), 1) as min_response_days,
                ROUND(MAX(response_days), 1) as max_response_days
            FROM response_times
        """,
        "keywords": ["응답시간", "response time", "평균", "average", "분석"],
        "category": "time_analysis",
        "required_params": [],
        "default_params": {
            "days": 30
        },
        "query_filter": ["days"],
        "related_tables": ["agenda_chair", "agenda_responses_content"],
        "to_agent_prompt": None,
        "template_version": "1.0.0",
        "embedding_model": "text-embedding-3-large",
        "embedding_dimension": 3072
    },
    
    # Pending Agendas
    {
        "template_id": "pending_agendas",
        "natural_questions": "미결정 아젠다는 무엇인가요?",
        "sql_query": """
            SELECT 
                ac.agenda_code,
                ac.subject,
                ac.sent_time,
                julianday('now') - julianday(ac.sent_time) as days_pending,
                COUNT(DISTINCT CASE 
                    WHEN arc.ABS IS NOT NULL OR arc.BV IS NOT NULL OR arc.CCS IS NOT NULL 
                    OR arc.CRS IS NOT NULL OR arc.DNV IS NOT NULL OR arc.IRS IS NOT NULL 
                    OR arc.KR IS NOT NULL OR arc.NK IS NOT NULL OR arc.PRS IS NOT NULL 
                    OR arc.RINA IS NOT NULL OR arc.LR IS NOT NULL 
                    THEN 1 ELSE NULL END) as response_count,
                GROUP_CONCAT(DISTINCT 
                    CASE 
                        WHEN arc.ABS IS NOT NULL THEN 'ABS'
                        WHEN arc.BV IS NOT NULL THEN 'BV'
                        WHEN arc.KR IS NOT NULL THEN 'KR'
                        ELSE NULL
                    END, ', ') as responded_orgs
            FROM agenda_chair ac
            LEFT JOIN agenda_responses_content arc ON ac.agenda_base_version = arc.agenda_base_version
            WHERE ac.decision_status IN ('pending', '미결정', NULL)
            GROUP BY ac.agenda_code, ac.subject, ac.sent_time
            ORDER BY days_pending DESC
            LIMIT 10
        """,
        "sql_query_with_parameters": """
            SELECT 
                ac.agenda_code,
                ac.subject,
                ac.sent_time,
                julianday('now') - julianday(ac.sent_time) as days_pending,
                COUNT(DISTINCT CASE 
                    WHEN arc.ABS IS NOT NULL OR arc.BV IS NOT NULL OR arc.CCS IS NOT NULL 
                    OR arc.CRS IS NOT NULL OR arc.DNV IS NOT NULL OR arc.IRS IS NOT NULL 
                    OR arc.KR IS NOT NULL OR arc.NK IS NOT NULL OR arc.PRS IS NOT NULL 
                    OR arc.RINA IS NOT NULL OR arc.LR IS NOT NULL 
                    THEN 1 ELSE NULL END) as response_count,
                GROUP_CONCAT(DISTINCT 
                    CASE 
                        WHEN arc.ABS IS NOT NULL THEN 'ABS'
                        WHEN arc.BV IS NOT NULL THEN 'BV'
                        WHEN arc.KR IS NOT NULL THEN 'KR'
                        ELSE NULL
                    END, ', ') as responded_orgs
            FROM agenda_chair ac
            LEFT JOIN agenda_responses_content arc ON ac.agenda_base_version = arc.agenda_base_version
            WHERE ac.decision_status IN ('pending', '미결정', NULL)
            GROUP BY ac.agenda_code, ac.subject, ac.sent_time
            ORDER BY days_pending DESC
            LIMIT {limit}
        """,
        "keywords": ["미결정", "pending", "대기", "waiting", "undecided"],
        "category": "pending_items",
        "required_params": [],
        "default_params": {
            "limit": 10
        },
        "query_filter": ["limit"],
        "related_tables": ["agenda_chair", "agenda_responses_content"],
        "to_agent_prompt": None,
        "template_version": "1.0.0",
        "embedding_model": "text-embedding-3-large",
        "embedding_dimension": 3072
    },
    
    # High Priority Agendas
    {
        "template_id": "high_priority_agendas",
        "natural_questions": "중요도가 높은 아젠다를 보여주세요",
        "sql_query": """
            SELECT 
                ac.agenda_code,
                ac.subject,
                ac.sent_time,
                ac.priority,
                ac.decision_status,
                COUNT(DISTINCT arc.organization) as response_count
            FROM agenda_chair ac
            LEFT JOIN agenda_responses_content arc ON ac.agenda_base_version = arc.agenda_base_version
            WHERE ac.priority IN ('high', '높음', 'urgent', '긴급')
                AND ac.sent_time >= datetime('now', '-30 days')
            GROUP BY ac.agenda_code, ac.subject, ac.sent_time, ac.priority, ac.decision_status
            ORDER BY ac.sent_time DESC
            LIMIT 20
        """,
        "sql_query_with_parameters": """
            SELECT 
                ac.agenda_code,
                ac.subject,
                ac.sent_time,
                ac.priority,
                ac.decision_status,
                COUNT(DISTINCT arc.organization) as response_count
            FROM agenda_chair ac
            LEFT JOIN agenda_responses_content arc ON ac.agenda_base_version = arc.agenda_base_version
            WHERE ac.priority IN ('high', '높음', 'urgent', '긴급')
                AND ac.sent_time >= datetime('now', '-{days} days')
            GROUP BY ac.agenda_code, ac.subject, ac.sent_time, ac.priority, ac.decision_status
            ORDER BY ac.sent_time DESC
            LIMIT {limit}
        """,
        "keywords": ["중요", "important", "priority", "높은", "high", "긴급"],
        "category": "priority",
        "required_params": [],
        "default_params": {
            "days": 30,
            "limit": 20
        },
        "query_filter": ["days", "limit"],
        "related_tables": ["agenda_chair", "agenda_responses_content"],
        "to_agent_prompt": None,
        "template_version": "1.0.0",
        "embedding_model": "text-embedding-3-large",
        "embedding_dimension": 3072
    },
    
    # Response Content Search
    {
        "template_id": "response_content_search",
        "natural_questions": "{keyword}가 포함된 응답을 검색해주세요",
        "sql_query": """
            SELECT 
                ac.agenda_code,
                ac.subject,
                arc.organization,
                arc.response_content,
                arc.response_date
            FROM agenda_chair ac
            JOIN agenda_responses_content arc ON ac.agenda_base_version = arc.agenda_base_version
            WHERE arc.response_content LIKE '%테스트%'
                AND ac.sent_time >= datetime('now', '-30 days')
            ORDER BY arc.response_date DESC
            LIMIT 20
        """,
        "sql_query_with_parameters": """
            SELECT 
                ac.agenda_code,
                ac.subject,
                arc.organization,
                arc.response_content,
                arc.response_date
            FROM agenda_chair ac
            JOIN agenda_responses_content arc ON ac.agenda_base_version = arc.agenda_base_version
            WHERE arc.response_content LIKE '%{keyword}%'
                AND ac.sent_time >= datetime('now', '-{days} days')
            ORDER BY arc.response_date DESC
            LIMIT {limit}
        """,
        "keywords": ["검색", "search", "포함", "contains", "응답", "response", "내용"],
        "category": "content_search",
        "required_params": ["keyword"],
        "default_params": {
            "keyword": "",
            "days": 30,
            "limit": 20
        },
        "query_filter": ["days", "limit"],
        "related_tables": ["agenda_chair", "agenda_responses_content"],
        "to_agent_prompt": None,
        "template_version": "1.0.0",
        "embedding_model": "text-embedding-3-large",
        "embedding_dimension": 3072
    },
    
    # Organization Comparison
    {
        "template_id": "org_comparison",
        "natural_questions": "기관별 응답률을 비교해주세요",
        "sql_query": """
            WITH org_stats AS (
                SELECT 
                    org.organization_name,
                    COUNT(DISTINCT ac.agenda_code) as total_agendas,
                    SUM(CASE 
                        WHEN arc.ABS IS NOT NULL OR arc.BV IS NOT NULL OR arc.CCS IS NOT NULL 
                        OR arc.CRS IS NOT NULL OR arc.DNV IS NOT NULL OR arc.IRS IS NOT NULL 
                        OR arc.KR IS NOT NULL OR arc.NK IS NOT NULL OR arc.PRS IS NOT NULL 
                        OR arc.RINA IS NOT NULL OR arc.LR IS NOT NULL 
                        THEN 1 ELSE 0 END) as responded_agendas
                FROM (
                    SELECT DISTINCT organization_name 
                    FROM organization_list
                ) org
                CROSS JOIN agenda_chair ac
                LEFT JOIN agenda_responses_content arc 
                    ON ac.agenda_base_version = arc.agenda_base_version
                WHERE ac.sent_time >= datetime('now', '-30 days')
                GROUP BY org.organization_name
            )
            SELECT 
                organization_name,
                total_agendas,
                responded_agendas,
                ROUND(CAST(responded_agendas AS FLOAT) / total_agendas * 100, 2) as response_rate
            FROM org_stats
            ORDER BY response_rate DESC
        """,
        "sql_query_with_parameters": """
            WITH org_stats AS (
                SELECT 
                    org.organization_name,
                    COUNT(DISTINCT ac.agenda_code) as total_agendas,
                    SUM(CASE 
                        WHEN arc.ABS IS NOT NULL OR arc.BV IS NOT NULL OR arc.CCS IS NOT NULL 
                        OR arc.CRS IS NOT NULL OR arc.DNV IS NOT NULL OR arc.IRS IS NOT NULL 
                        OR arc.KR IS NOT NULL OR arc.NK IS NOT NULL OR arc.PRS IS NOT NULL 
                        OR arc.RINA IS NOT NULL OR arc.LR IS NOT NULL 
                        THEN 1 ELSE 0 END) as responded_agendas
                FROM (
                    SELECT DISTINCT organization_name 
                    FROM organization_list
                ) org
                CROSS JOIN agenda_chair ac
                LEFT JOIN agenda_responses_content arc 
                    ON ac.agenda_base_version = arc.agenda_base_version
                WHERE ac.sent_time >= datetime('now', '-{days} days')
                GROUP BY org.organization_name
            )
            SELECT 
                organization_name,
                total_agendas,
                responded_agendas,
                ROUND(CAST(responded_agendas AS FLOAT) / total_agendas * 100, 2) as response_rate
            FROM org_stats
            ORDER BY response_rate DESC
        """,
        "keywords": ["비교", "compare", "기관별", "organizations", "응답률"],
        "category": "comparison",
        "required_params": [],
        "default_params": {
            "days": 30
        },
        "query_filter": ["days"],
        "related_tables": ["agenda_chair", "agenda_responses_content", "organization_list"],
        "to_agent_prompt": None
    },
    
    # Daily Summary
    {
        "template_id": "daily_summary",
        "natural_questions": "일간 요약 보고서를 만들어주세요",
        "sql_query": """
            SELECT 
                strftime('%Y-%m-%d', ac.sent_time) as report_date,
                COUNT(DISTINCT ac.agenda_code) as total_agendas,
                COUNT(DISTINCT CASE WHEN ac.decision_status = 'approved' 
                      THEN ac.agenda_code END) as approved_count,
                COUNT(DISTINCT CASE WHEN ac.decision_status = 'rejected' 
                      THEN ac.agenda_code END) as rejected_count,
                COUNT(DISTINCT CASE WHEN ac.decision_status IN ('pending', NULL) 
                      THEN ac.agenda_code END) as pending_count,
                COUNT(DISTINCT arc.organization) as active_organizations,
                AVG(response_count) as avg_responses_per_agenda
            FROM (
                SELECT 
                    ac.*,
                    COUNT(DISTINCT arc.organization) as response_count
                FROM agenda_chair ac
                LEFT JOIN agenda_responses_content arc 
                    ON ac.agenda_base_version = arc.agenda_base_version
                WHERE ac.sent_time >= datetime('now', '-7 days')
                GROUP BY ac.agenda_code
            ) ac
            LEFT JOIN agenda_responses_content arc 
                ON ac.agenda_base_version = arc.agenda_base_version
            GROUP BY report_date
            ORDER BY report_date DESC
            LIMIT 7
        """,
        "sql_query_with_parameters": """
            SELECT 
                strftime('%Y-%m-%d', ac.sent_time) as report_date,
                COUNT(DISTINCT ac.agenda_code) as total_agendas,
                COUNT(DISTINCT CASE WHEN ac.decision_status = 'approved' 
                      THEN ac.agenda_code END) as approved_count,
                COUNT(DISTINCT CASE WHEN ac.decision_status = 'rejected' 
                      THEN ac.agenda_code END) as rejected_count,
                COUNT(DISTINCT CASE WHEN ac.decision_status IN ('pending', NULL) 
                      THEN ac.agenda_code END) as pending_count,
                COUNT(DISTINCT arc.organization) as active_organizations,
                AVG(response_count) as avg_responses_per_agenda
            FROM (
                SELECT 
                    ac.*,
                    COUNT(DISTINCT arc.organization) as response_count
                FROM agenda_chair ac
                LEFT JOIN agenda_responses_content arc 
                    ON ac.agenda_base_version = arc.agenda_base_version
                WHERE ac.sent_time >= datetime('now', '-{days} days')
                GROUP BY ac.agenda_code
            ) ac
            LEFT JOIN agenda_responses_content arc 
                ON ac.agenda_base_version = arc.agenda_base_version
            GROUP BY report_date
            ORDER BY report_date DESC
            LIMIT {limit}
        """,
        "keywords": ["일간", "일일", "daily", "요약", "summary", "보고서", "report", "오늘", "today"],
        "category": "summary_report",
        "required_params": [],
        "default_params": {
            "days": 7,
            "limit": 7
        },
        "query_filter": ["days", "limit"],
        "related_tables": ["agenda_chair", "agenda_responses_content"],
        "to_agent_prompt": None,
        "template_version": "1.0.0",
        "embedding_model": "text-embedding-3-large",
        "embedding_dimension": 3072
    },
    
    # Weekly Summary
    {
        "template_id": "weekly_summary",
        "natural_questions": "주간 요약 보고서를 만들어주세요",
        "sql_query": """
            SELECT 
                strftime('%Y-W%W', ac.sent_time) as report_week,
                strftime('%Y-%m-%d', date(ac.sent_time, 'weekday 0', '-6 days')) as week_start,
                strftime('%Y-%m-%d', date(ac.sent_time, 'weekday 0')) as week_end,
                COUNT(DISTINCT ac.agenda_code) as total_agendas,
                COUNT(DISTINCT CASE WHEN ac.decision_status = 'approved' 
                      THEN ac.agenda_code END) as approved_count,
                COUNT(DISTINCT CASE WHEN ac.decision_status = 'rejected' 
                      THEN ac.agenda_code END) as rejected_count,
                COUNT(DISTINCT CASE WHEN ac.decision_status IN ('pending', NULL) 
                      THEN ac.agenda_code END) as pending_count,
                COUNT(DISTINCT arc.organization) as active_organizations,
                AVG(response_count) as avg_responses_per_agenda,
                ROUND(AVG(response_rate), 2) as avg_response_rate
            FROM (
                SELECT 
                    ac.*,
                    COUNT(DISTINCT arc.organization) as response_count,
                    CAST(COUNT(DISTINCT CASE WHEN arc.organization IS NOT NULL THEN arc.organization END) AS FLOAT) / 11 * 100 as response_rate
                FROM agenda_chair ac
                LEFT JOIN agenda_responses_content arc 
                    ON ac.agenda_base_version = arc.agenda_base_version
                WHERE ac.sent_time >= datetime('now', '-4 weeks')
                GROUP BY ac.agenda_code
            ) ac
            LEFT JOIN agenda_responses_content arc 
                ON ac.agenda_base_version = arc.agenda_base_version
            GROUP BY report_week
            ORDER BY report_week DESC
            LIMIT 4
        """,
        "sql_query_with_parameters": """
            SELECT 
                strftime('%Y-W%W', ac.sent_time) as report_week,
                strftime('%Y-%m-%d', date(ac.sent_time, 'weekday 0', '-6 days')) as week_start,
                strftime('%Y-%m-%d', date(ac.sent_time, 'weekday 0')) as week_end,
                COUNT(DISTINCT ac.agenda_code) as total_agendas,
                COUNT(DISTINCT CASE WHEN ac.decision_status = 'approved' 
                      THEN ac.agenda_code END) as approved_count,
                COUNT(DISTINCT CASE WHEN ac.decision_status = 'rejected' 
                      THEN ac.agenda_code END) as rejected_count,
                COUNT(DISTINCT CASE WHEN ac.decision_status IN ('pending', NULL) 
                      THEN ac.agenda_code END) as pending_count,
                COUNT(DISTINCT arc.organization) as active_organizations,
                AVG(response_count) as avg_responses_per_agenda,
                ROUND(AVG(response_rate), 2) as avg_response_rate
            FROM (
                SELECT 
                    ac.*,
                    COUNT(DISTINCT arc.organization) as response_count,
                    CAST(COUNT(DISTINCT CASE WHEN arc.organization IS NOT NULL THEN arc.organization END) AS FLOAT) / 11 * 100 as response_rate
                FROM agenda_chair ac
                LEFT JOIN agenda_responses_content arc 
                    ON ac.agenda_base_version = arc.agenda_base_version
                WHERE ac.sent_time >= datetime('now', '-{weeks} weeks')
                GROUP BY ac.agenda_code
            ) ac
            LEFT JOIN agenda_responses_content arc 
                ON ac.agenda_base_version = arc.agenda_base_version
            GROUP BY report_week
            ORDER BY report_week DESC
            LIMIT {limit}
        """,
        "keywords": ["주간", "weekly", "요약", "summary", "보고서", "report", "이번주", "지난주"],
        "category": "summary_report",
        "required_params": [],
        "default_params": {
            "weeks": 4,
            "limit": 4
        },
        "query_filter": ["weeks", "limit"],
        "related_tables": ["agenda_chair", "agenda_responses_content"],
        "to_agent_prompt": None,
        "template_version": "1.0.0",
        "embedding_model": "text-embedding-3-large",
        "embedding_dimension": 3072
    },
    
    # Monthly Summary
    {
        "template_id": "monthly_summary",
        "natural_questions": "월간 요약 보고서를 만들어주세요",
        "sql_query": """
            SELECT 
                strftime('%Y-%m', ac.sent_time) as report_month,
                strftime('%Y년 %m월', ac.sent_time) as month_korean,
                COUNT(DISTINCT ac.agenda_code) as total_agendas,
                COUNT(DISTINCT CASE WHEN ac.decision_status = 'approved' 
                      THEN ac.agenda_code END) as approved_count,
                COUNT(DISTINCT CASE WHEN ac.decision_status = 'rejected' 
                      THEN ac.agenda_code END) as rejected_count,
                COUNT(DISTINCT CASE WHEN ac.decision_status IN ('pending', NULL) 
                      THEN ac.agenda_code END) as pending_count,
                COUNT(DISTINCT arc.organization) as active_organizations,
                AVG(response_count) as avg_responses_per_agenda,
                ROUND(AVG(response_rate), 2) as avg_response_rate,
                MAX(response_count) as max_responses,
                MIN(response_count) as min_responses
            FROM (
                SELECT 
                    ac.*,
                    COUNT(DISTINCT arc.organization) as response_count,
                    CAST(COUNT(DISTINCT CASE WHEN arc.organization IS NOT NULL THEN arc.organization END) AS FLOAT) / 11 * 100 as response_rate
                FROM agenda_chair ac
                LEFT JOIN agenda_responses_content arc 
                    ON ac.agenda_base_version = arc.agenda_base_version
                WHERE ac.sent_time >= datetime('now', '-6 months')
                GROUP BY ac.agenda_code
            ) ac
            LEFT JOIN agenda_responses_content arc 
                ON ac.agenda_base_version = arc.agenda_base_version
            GROUP BY report_month
            ORDER BY report_month DESC
            LIMIT 6
        """,
        "sql_query_with_parameters": """
            SELECT 
                strftime('%Y-%m', ac.sent_time) as report_month,
                strftime('%Y년 %m월', ac.sent_time) as month_korean,
                COUNT(DISTINCT ac.agenda_code) as total_agendas,
                COUNT(DISTINCT CASE WHEN ac.decision_status = 'approved' 
                      THEN ac.agenda_code END) as approved_count,
                COUNT(DISTINCT CASE WHEN ac.decision_status = 'rejected' 
                      THEN ac.agenda_code END) as rejected_count,
                COUNT(DISTINCT CASE WHEN ac.decision_status IN ('pending', NULL) 
                      THEN ac.agenda_code END) as pending_count,
                COUNT(DISTINCT arc.organization) as active_organizations,
                AVG(response_count) as avg_responses_per_agenda,
                ROUND(AVG(response_rate), 2) as avg_response_rate,
                MAX(response_count) as max_responses,
                MIN(response_count) as min_responses
            FROM (
                SELECT 
                    ac.*,
                    COUNT(DISTINCT arc.organization) as response_count,
                    CAST(COUNT(DISTINCT CASE WHEN arc.organization IS NOT NULL THEN arc.organization END) AS FLOAT) / 11 * 100 as response_rate
                FROM agenda_chair ac
                LEFT JOIN agenda_responses_content arc 
                    ON ac.agenda_base_version = arc.agenda_base_version
                WHERE ac.sent_time >= datetime('now', '-{months} months')
                GROUP BY ac.agenda_code
            ) ac
            LEFT JOIN agenda_responses_content arc 
                ON ac.agenda_base_version = arc.agenda_base_version
            GROUP BY report_month
            ORDER BY report_month DESC
            LIMIT {limit}
        """,
        "keywords": ["월간", "monthly", "요약", "summary", "보고서", "report", "이번달", "지난달"],
        "category": "summary_report",
        "required_params": [],
        "default_params": {
            "months": 6,
            "limit": 6
        },
        "query_filter": ["months", "limit"],
        "related_tables": ["agenda_chair", "agenda_responses_content"],
        "to_agent_prompt": None,
        "template_version": "1.0.0",
        "embedding_model": "text-embedding-3-large",
        "embedding_dimension": 3072
    },
    
    # Quarterly Summary
    {
        "template_id": "quarterly_summary",
        "natural_questions": "분기 요약 보고서를 만들어주세요",
        "sql_query": """
            SELECT 
                CAST((CAST(strftime('%m', ac.sent_time) AS INTEGER) - 1) / 3 + 1 AS TEXT) || 'Q' || strftime('%Y', ac.sent_time) as report_quarter,
                strftime('%Y년 ', ac.sent_time) || CAST((CAST(strftime('%m', ac.sent_time) AS INTEGER) - 1) / 3 + 1 AS TEXT) || '분기' as quarter_korean,
                COUNT(DISTINCT ac.agenda_code) as total_agendas,
                COUNT(DISTINCT CASE WHEN ac.decision_status = 'approved' 
                      THEN ac.agenda_code END) as approved_count,
                COUNT(DISTINCT CASE WHEN ac.decision_status = 'rejected' 
                      THEN ac.agenda_code END) as rejected_count,
                COUNT(DISTINCT CASE WHEN ac.decision_status IN ('pending', NULL) 
                      THEN ac.agenda_code END) as pending_count,
                COUNT(DISTINCT arc.organization) as active_organizations,
                AVG(response_count) as avg_responses_per_agenda,
                ROUND(AVG(response_rate), 2) as avg_response_rate,
                COUNT(DISTINCT strftime('%Y-%m', ac.sent_time)) as active_months
            FROM (
                SELECT 
                    ac.*,
                    COUNT(DISTINCT arc.organization) as response_count,
                    CAST(COUNT(DISTINCT CASE WHEN arc.organization IS NOT NULL THEN arc.organization END) AS FLOAT) / 11 * 100 as response_rate
                FROM agenda_chair ac
                LEFT JOIN agenda_responses_content arc 
                    ON ac.agenda_base_version = arc.agenda_base_version
                WHERE ac.sent_time >= datetime('now', '-12 months')
                GROUP BY ac.agenda_code
            ) ac
            LEFT JOIN agenda_responses_content arc 
                ON ac.agenda_base_version = arc.agenda_base_version
            GROUP BY report_quarter
            ORDER BY ac.sent_time DESC
            LIMIT 4
        """,
        "sql_query_with_parameters": """
            SELECT 
                CAST((CAST(strftime('%m', ac.sent_time) AS INTEGER) - 1) / 3 + 1 AS TEXT) || 'Q' || strftime('%Y', ac.sent_time) as report_quarter,
                strftime('%Y년 ', ac.sent_time) || CAST((CAST(strftime('%m', ac.sent_time) AS INTEGER) - 1) / 3 + 1 AS TEXT) || '분기' as quarter_korean,
                COUNT(DISTINCT ac.agenda_code) as total_agendas,
                COUNT(DISTINCT CASE WHEN ac.decision_status = 'approved' 
                      THEN ac.agenda_code END) as approved_count,
                COUNT(DISTINCT CASE WHEN ac.decision_status = 'rejected' 
                      THEN ac.agenda_code END) as rejected_count,
                COUNT(DISTINCT CASE WHEN ac.decision_status IN ('pending', NULL) 
                      THEN ac.agenda_code END) as pending_count,
                COUNT(DISTINCT arc.organization) as active_organizations,
                AVG(response_count) as avg_responses_per_agenda,
                ROUND(AVG(response_rate), 2) as avg_response_rate,
                COUNT(DISTINCT strftime('%Y-%m', ac.sent_time)) as active_months
            FROM (
                SELECT 
                    ac.*,
                    COUNT(DISTINCT arc.organization) as response_count,
                    CAST(COUNT(DISTINCT CASE WHEN arc.organization IS NOT NULL THEN arc.organization END) AS FLOAT) / 11 * 100 as response_rate
                FROM agenda_chair ac
                LEFT JOIN agenda_responses_content arc 
                    ON ac.agenda_base_version = arc.agenda_base_version
                WHERE ac.sent_time >= datetime('now', '-{quarters} months')
                GROUP BY ac.agenda_code
            ) ac
            LEFT JOIN agenda_responses_content arc 
                ON ac.agenda_base_version = arc.agenda_base_version
            GROUP BY report_quarter
            ORDER BY ac.sent_time DESC
            LIMIT {limit}
        """,
        "keywords": ["분기", "quarterly", "요약", "summary", "보고서", "report", "사분기", "quarter"],
        "category": "summary_report",
        "required_params": [],
        "default_params": {
            "quarters": 12,
            "limit": 4
        },
        "query_filter": ["quarters", "limit"],
        "related_tables": ["agenda_chair", "agenda_responses_content"],
        "to_agent_prompt": None,
        "template_version": "1.0.0",
        "embedding_model": "text-embedding-3-large",
        "embedding_dimension": 3072
    },
    
    # Yearly Summary
    {
        "template_id": "yearly_summary",
        "natural_questions": "연간 요약 보고서를 만들어주세요",
        "sql_query": """
            SELECT 
                strftime('%Y', ac.sent_time) as report_year,
                strftime('%Y년', ac.sent_time) as year_korean,
                COUNT(DISTINCT ac.agenda_code) as total_agendas,
                COUNT(DISTINCT CASE WHEN ac.decision_status = 'approved' 
                      THEN ac.agenda_code END) as approved_count,
                COUNT(DISTINCT CASE WHEN ac.decision_status = 'rejected' 
                      THEN ac.agenda_code END) as rejected_count,
                COUNT(DISTINCT CASE WHEN ac.decision_status IN ('pending', NULL) 
                      THEN ac.agenda_code END) as pending_count,
                COUNT(DISTINCT arc.organization) as active_organizations,
                AVG(response_count) as avg_responses_per_agenda,
                ROUND(AVG(response_rate), 2) as avg_response_rate,
                COUNT(DISTINCT strftime('%Y-%m', ac.sent_time)) as active_months,
                MAX(response_count) as max_responses,
                MIN(response_count) as min_responses
            FROM (
                SELECT 
                    ac.*,
                    COUNT(DISTINCT arc.organization) as response_count,
                    CAST(COUNT(DISTINCT CASE WHEN arc.organization IS NOT NULL THEN arc.organization END) AS FLOAT) / 11 * 100 as response_rate
                FROM agenda_chair ac
                LEFT JOIN agenda_responses_content arc 
                    ON ac.agenda_base_version = arc.agenda_base_version
                WHERE ac.sent_time >= datetime('now', '-3 years')
                GROUP BY ac.agenda_code
            ) ac
            LEFT JOIN agenda_responses_content arc 
                ON ac.agenda_base_version = arc.agenda_base_version
            GROUP BY report_year
            ORDER BY report_year DESC
            LIMIT 3
        """,
        "sql_query_with_parameters": """
            SELECT 
                strftime('%Y', ac.sent_time) as report_year,
                strftime('%Y년', ac.sent_time) as year_korean,
                COUNT(DISTINCT ac.agenda_code) as total_agendas,
                COUNT(DISTINCT CASE WHEN ac.decision_status = 'approved' 
                      THEN ac.agenda_code END) as approved_count,
                COUNT(DISTINCT CASE WHEN ac.decision_status = 'rejected' 
                      THEN ac.agenda_code END) as rejected_count,
                COUNT(DISTINCT CASE WHEN ac.decision_status IN ('pending', NULL) 
                      THEN ac.agenda_code END) as pending_count,
                COUNT(DISTINCT arc.organization) as active_organizations,
                AVG(response_count) as avg_responses_per_agenda,
                ROUND(AVG(response_rate), 2) as avg_response_rate,
                COUNT(DISTINCT strftime('%Y-%m', ac.sent_time)) as active_months,
                MAX(response_count) as max_responses,
                MIN(response_count) as min_responses
            FROM (
                SELECT 
                    ac.*,
                    COUNT(DISTINCT arc.organization) as response_count,
                    CAST(COUNT(DISTINCT CASE WHEN arc.organization IS NOT NULL THEN arc.organization END) AS FLOAT) / 11 * 100 as response_rate
                FROM agenda_chair ac
                LEFT JOIN agenda_responses_content arc 
                    ON ac.agenda_base_version = arc.agenda_base_version
                WHERE ac.sent_time >= datetime('now', '-{years} years')
                GROUP BY ac.agenda_code
            ) ac
            LEFT JOIN agenda_responses_content arc 
                ON ac.agenda_base_version = arc.agenda_base_version
            GROUP BY report_year
            ORDER BY report_year DESC
            LIMIT {limit}
        """,
        "keywords": ["연간", "yearly", "annual", "연도별", "요약", "summary", "보고서", "report", "올해", "작년"],
        "category": "summary_report",
        "required_params": [],
        "default_params": {
            "years": 3,
            "limit": 3
        },
        "query_filter": ["years", "limit"],
        "related_tables": ["agenda_chair", "agenda_responses_content"],
        "to_agent_prompt": None,
        "template_version": "1.0.0",
        "embedding_model": "text-embedding-3-large",
        "embedding_dimension": 3072
    },
    
    # Custom Period Summary
    {
        "template_id": "periodic_summary",
        "natural_questions": "{period} 요약 보고서를 만들어주세요",
        "sql_query": """
            SELECT 
                strftime('%Y-%m', ac.sent_time) as period,
                COUNT(DISTINCT ac.agenda_code) as total_agendas,
                COUNT(DISTINCT CASE WHEN ac.decision_status = 'approved' 
                      THEN ac.agenda_code END) as approved_count,
                COUNT(DISTINCT CASE WHEN ac.decision_status = 'rejected' 
                      THEN ac.agenda_code END) as rejected_count,
                COUNT(DISTINCT CASE WHEN ac.decision_status IN ('pending', NULL) 
                      THEN ac.agenda_code END) as pending_count,
                AVG(response_count) as avg_responses_per_agenda
            FROM (
                SELECT 
                    ac.*,
                    COUNT(DISTINCT arc.organization) as response_count
                FROM agenda_chair ac
                LEFT JOIN agenda_responses_content arc 
                    ON ac.agenda_base_version = arc.agenda_base_version
                WHERE ac.sent_time >= datetime('now', '-90 days')
                GROUP BY ac.agenda_code
            ) ac
            GROUP BY period
            ORDER BY period DESC
        """,
        "sql_query_with_parameters": """
            SELECT 
                strftime('{period_format}', ac.sent_time) as period,
                COUNT(DISTINCT ac.agenda_code) as total_agendas,
                COUNT(DISTINCT CASE WHEN ac.decision_status = 'approved' 
                      THEN ac.agenda_code END) as approved_count,
                COUNT(DISTINCT CASE WHEN ac.decision_status = 'rejected' 
                      THEN ac.agenda_code END) as rejected_count,
                COUNT(DISTINCT CASE WHEN ac.decision_status IN ('pending', NULL) 
                      THEN ac.agenda_code END) as pending_count,
                AVG(response_count) as avg_responses_per_agenda
            FROM (
                SELECT 
                    ac.*,
                    COUNT(DISTINCT arc.organization) as response_count
                FROM agenda_chair ac
                LEFT JOIN agenda_responses_content arc 
                    ON ac.agenda_base_version = arc.agenda_base_version
                WHERE ac.sent_time >= datetime('now', '-{days} days')
                GROUP BY ac.agenda_code
            ) ac
            GROUP BY period
            ORDER BY period DESC
        """,
        "keywords": ["요약", "summary", "보고서", "report", "기간", "period", "custom"],
        "category": "summary_report",
        "required_params": ["period"],
        "default_params": {
            "period": "월간",
            "period_format": "%Y-%m",
            "days": 90
        },
        "query_filter": ["days", "period_format"],
        "related_tables": ["agenda_chair", "agenda_responses_content"],
        "to_agent_prompt": None
    }
]

# Add version, embedding model, and dimension to all templates
for template in TEMPLATES:
    if "template_version" not in template:
        template["template_version"] = "1.0.0"
    if "embedding_model" not in template:
        template["embedding_model"] = "text-embedding-3-large"
    if "embedding_dimension" not in template:
        template["embedding_dimension"] = 1536