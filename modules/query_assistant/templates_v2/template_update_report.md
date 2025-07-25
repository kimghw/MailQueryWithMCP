# Query Templates Update Report

## Update Summary
- **Date**: 2025-07-25
- **File**: query_templates_unified.json
- **Total Templates**: 174

## Changes Made

### 1. Version Standardization
- Changed all `template_version` fields from various versions (2.2, 2.3, 2.5, 2.7, 2.8, 2.9, 2.10) to unified version **"1.0.0"**
- Updated file version to **"1.0.0-unified"**

### 2. Date Parameter Additions
- Added **76 missing date parameters** to templates that reference dates in their queries
- Standard date parameter configuration:
  ```json
  {
    "name": "date_range",
    "type": "date_range",
    "required": false,
    "default": {
      "type": "relative",
      "days": 30
    },
    "sql_builder": {
      "type": "date_range",
      "field": "sent_time",
      "placeholder": "{date_condition}"
    }
  }
  ```

### 3. Template Categories (23 total)
| Category | Count | Description |
|----------|-------|-------------|
| agenda_search | 29 | Search for specific agendas |
| agenda_analysis | 26 | Analysis of agenda content and patterns |
| panel_specific | 17 | Panel-specific queries |
| keyword_analysis | 15 | Keyword extraction and analysis |
| vectordb_search | 15 | Vector database search queries |
| organization_response | 14 | Organization response tracking |
| agenda_statistics | 13 | Statistical analysis of agendas |
| agenda_status | 7 | Status tracking queries |
| project_team | 6 | Project team related queries |
| meeting_info | 5 | Meeting information queries |
| system_config | 4 | System configuration queries |
| time_based_query | 3 | Time-based filtering queries |
| data_quality | 3 | Data quality checks |
| llm_direct_response | 3 | Direct LLM response queries |
| statistics | 3 | General statistics |
| organization_analysis | 2 | Organization analysis |
| keyword_search | 2 | Keyword search |
| panel_statistics | 2 | Panel statistics |
| chair_communication | 1 | Chair communication tracking |
| response_analysis | 1 | Response analysis |
| deadline_analysis | 1 | Deadline tracking |
| organization_info | 1 | Organization information |
| mail_content | 1 | Mail content analysis |

### 4. Template ID Patterns

Templates follow consistent naming patterns:
- **agenda_*** - Agenda-related operations
- **org_*** - Organization-related queries
- **panel_*** - Panel-specific queries
- **keyword_*** - Keyword analysis
- **chair_*** - Chair-related queries
- **pt_*** - Project team queries
- All templates end with **_v2** suffix

### 5. Consistency Improvements
- All templates now have required fields:
  - `template_id`
  - `template_version`
  - `template_category`
  - `query_info`
- Standardized parameter structure
- Consistent date handling across all templates

## Templates Updated with Date Parameters

Examples of templates that were missing date parameters and now have them:
1. `all_panels_recent_3months_v2` - Time-based query
2. `pending_agenda_count_v2` - Agenda statistics
3. `yearly_agenda_count_v2` - Yearly statistics
4. `monthly_agenda_response_status_v2` - Monthly statistics
5. `org_avg_response_time_v2` - Response time analysis
6. `keyword_analysis_3months_v2` - 3-month keyword analysis
7. `keyword_analysis_lastyear_v2` - Last year keyword analysis

## Routing Distribution
- **SQL queries**: 173 templates (99.4%)
- **LLM direct**: 3 templates (identified by template ID)
- **VectorDB**: 15 templates (identified by category)

## Next Steps
1. Test updated templates with the query processing system
2. Verify date parameter handling in SQL query builder
3. Update documentation for template usage
4. Consider adding validation tests for template structure