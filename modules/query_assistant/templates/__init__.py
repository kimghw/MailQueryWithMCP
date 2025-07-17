"""SQL query templates for IACSGraph Email Dashboard"""

from typing import List, Dict, Any, Optional
from ..schema import QueryTemplate
from datetime import datetime
from .new_templates import TEMPLATES

# Import templates from new_templates.py
QUERY_TEMPLATES: List[Dict[str, Any]] = TEMPLATES

# Legacy templates (kept for reference)
LEGACY_TEMPLATES: List[Dict[str, Any]] = [
    # Agenda Summary Templates
    {
        "id": "recent_agendas_by_period",
        "natural_query": "최근 {period} 주요 아젠다는 무엇인가?",
        "sql_template": """
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
        "required_params": ["period"],
        "optional_params": ["limit", "status"],
        "default_params": {
            "period": "30일",
            "days": 30,
            "limit": 20,
            "status": "all"
        },
        "category": "agenda_summary"
    },
    
    # Organization Response Statistics
    {
        "id": "org_response_rate",
        "natural_query": "{organization} 기관의 응답률은 어떻게 되나요?",
        "sql_template": """
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
        "required_params": ["organization"],
        "optional_params": ["days"],
        "category": "statistics"
    },
    
    # Agenda Decision Status
    {
        "id": "agenda_decision_status",
        "natural_query": "{status} 상태인 아젠다 목록을 보여주세요",
        "sql_template": """
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
        "required_params": ["status"],
        "optional_params": ["days", "limit"],
        "category": "agenda_status"
    },
    
    # Organization-specific Agendas
    {
        "id": "org_related_agendas",
        "natural_query": "{organization}과 관련된 아젠다를 보여주세요",
        "sql_template": """
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
        "required_params": ["organization"],
        "optional_params": ["days", "limit"],
        "category": "organization_agendas"
    },
    
    # Response Time Analysis
    {
        "id": "response_time_analysis",
        "natural_query": "평균 응답 시간은 얼마나 되나요?",
        "sql_template": """
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
        "required_params": [],
        "optional_params": ["days"],
        "category": "time_analysis"
    },
    
    # Pending Agendas
    {
        "id": "pending_agendas",
        "natural_query": "미결정 아젠다는 무엇인가요?",
        "sql_template": """
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
        "required_params": [],
        "optional_params": ["limit"],
        "category": "pending_items"
    },
    
    # High Priority Agendas
    {
        "id": "high_priority_agendas",
        "natural_query": "중요도가 높은 아젠다를 보여주세요",
        "sql_template": """
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
        "required_params": [],
        "optional_params": ["days", "limit"],
        "category": "priority"
    },
    
    # Response Content Search
    {
        "id": "response_content_search",
        "natural_query": "{keyword}가 포함된 응답을 검색해주세요",
        "sql_template": """
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
        "required_params": ["keyword"],
        "optional_params": ["days", "limit"],
        "category": "content_search"
    },
    
    # Organization Comparison
    {
        "id": "org_comparison",
        "natural_query": "기관별 응답률을 비교해주세요",
        "sql_template": """
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
        "required_params": [],
        "optional_params": ["days"],
        "category": "comparison"
    },
    
    # Daily Summary
    {
        "id": "daily_summary",
        "natural_query": "일간 요약 보고서를 만들어주세요",
        "sql_template": """
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
        "required_params": [],
        "optional_params": ["days", "limit"],
        "default_params": {
            "days": 7,
            "limit": 7
        },
        "category": "summary_report"
    },
    
    # Weekly Summary
    {
        "id": "weekly_summary",
        "natural_query": "주간 요약 보고서를 만들어주세요",
        "sql_template": """
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
        "required_params": [],
        "optional_params": ["weeks", "limit"],
        "default_params": {
            "weeks": 4,
            "limit": 4
        },
        "category": "summary_report"
    },
    
    # Monthly Summary
    {
        "id": "monthly_summary",
        "natural_query": "월간 요약 보고서를 만들어주세요",
        "sql_template": """
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
        "required_params": [],
        "optional_params": ["months", "limit"],
        "default_params": {
            "months": 6,
            "limit": 6
        },
        "category": "summary_report"
    },
    
    # Quarterly Summary
    {
        "id": "quarterly_summary",
        "natural_query": "분기 요약 보고서를 만들어주세요",
        "sql_template": """
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
        "required_params": [],
        "optional_params": ["quarters", "limit"],
        "default_params": {
            "quarters": 12,
            "limit": 4
        },
        "category": "summary_report"
    },
    
    # Yearly Summary
    {
        "id": "yearly_summary",
        "natural_query": "연간 요약 보고서를 만들어주세요",
        "sql_template": """
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
        "required_params": [],
        "optional_params": ["years", "limit"],
        "default_params": {
            "years": 3,
            "limit": 3
        },
        "category": "summary_report"
    },
    
    # Custom Period Summary (Original flexible version)
    {
        "id": "periodic_summary",
        "natural_query": "{period} 요약 보고서를 만들어주세요",
        "sql_template": """
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
        "required_params": ["period"],
        "optional_params": ["days", "period_format"],
        "category": "summary_report"
    }
]


def get_templates() -> List[QueryTemplate]:
    """Get all query templates as QueryTemplate objects"""
    templates = []
    for template_dict in QUERY_TEMPLATES:
        template = QueryTemplate(
            **template_dict,
            created_at=datetime.now()
        )
        templates.append(template)
    return templates


def get_template_by_id(template_id: str) -> Optional[QueryTemplate]:
    """Get a specific template by ID"""
    for template_dict in QUERY_TEMPLATES:
        if template_dict["template_id"] == template_id:
            return QueryTemplate(
                **template_dict,
                created_at=datetime.now()
            )
    return None


def get_templates_by_category(category: str) -> List[QueryTemplate]:
    """Get templates filtered by category"""
    templates = []
    for template_dict in QUERY_TEMPLATES:
        if template_dict["category"] == category:
            template = QueryTemplate(
                **template_dict,
                created_at=datetime.now()
            )
            templates.append(template)
    return templates